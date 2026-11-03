from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Event, Finding, Website
from app.database.repositories import create_finding
from app.ml.anomaly_detector import IsolationForestAnomalyDetector
from app.ml.config import MLConfig, ml_config
from app.ml.features import FEATURE_VERSION, build_feature_matrix, build_feature_vector


class MLAnomalyService:
    """Service wrapper for per-website Isolation Forest training and prediction."""

    def __init__(self, session: Session, model_dir: str | Path | None = None, config: MLConfig | None = None) -> None:
        self.session = session
        self.config = config or ml_config
        self.model_dir = Path(model_dir) if model_dir is not None else Path(self.config.model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def _model_path(self, website_id: int) -> Path:
        return self.model_dir / f"website_{website_id}.joblib"

    def _metadata_path(self, website_id: int) -> Path:
        return self.model_dir / f"website_{website_id}.json"

    def _load_metadata(self, website_id: int) -> dict[str, Any]:
        path = self._metadata_path(website_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_metadata(self, website_id: int, metadata: dict[str, Any]) -> None:
        path = self._metadata_path(website_id)
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def _get_processed_events(self, website_id: int) -> list[Event]:
        return self.session.execute(
            select(Event).where(Event.website_id == website_id, Event.processing_status == "processed").order_by(Event.timestamp.asc())
        ).scalars().all()

    def load_model(self, website_id: int) -> IsolationForestAnomalyDetector | None:
        model_path = self._model_path(website_id)
        if not model_path.exists():
            return None

        detector = IsolationForestAnomalyDetector.load(model_path)
        metadata = self._load_metadata(website_id)
        detector.website_id = website_id
        detector.model_version = metadata.get("model_version", self.config.model_version)
        detector.feature_version = metadata.get("feature_version", FEATURE_VERSION)
        detector.training_event_count = metadata.get("training_event_count", 0)
        return detector

    def train_website_model(self, website_id: int) -> dict[str, Any]:
        website = self.session.get(Website, website_id)
        if website is None:
            return {
                "status": "not_ready",
                "website_id": website_id,
                "reason": "Website not found.",
            }

        events = self._get_processed_events(website_id)
        if len(events) < self.config.min_training_events:
            return {
                "status": "not_ready",
                "website_id": website_id,
                "training_event_count": len(events),
                "reason": (
                    f"Insufficient processed events for ML training. Minimum required: {self.config.min_training_events}."
                ),
                "model_version": self.config.model_version,
                "feature_version": FEATURE_VERSION,
            }

        matrix = build_feature_matrix(events)
        detector = IsolationForestAnomalyDetector(config=self.config)
        detector.fit(matrix)
        detector.website_id = website_id
        detector.training_event_count = len(events)
        model_path = self._model_path(website_id)
        detector.save(model_path)

        metadata = {
            "website_id": website_id,
            "model_version": self.config.model_version,
            "feature_version": FEATURE_VERSION,
            "algorithm": "IsolationForest",
            "training_event_count": len(events),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_metadata(website_id, metadata)

        return {
            "status": "trained",
            "website_id": website_id,
            "training_event_count": len(events),
            "model_version": self.config.model_version,
            "feature_version": FEATURE_VERSION,
        }

    def predict_event_anomaly(self, website_id: int, event: Event | dict[str, Any]) -> dict[str, Any]:
        website = self.session.get(Website, website_id)
        if website is None:
            return {
                "status": "not_ready",
                "website_id": website_id,
                "reason": "Website not found.",
            }

        detector = self.load_model(website_id)
        if detector is None:
            return {
                "status": "not_ready",
                "website_id": website_id,
                "reason": "Insufficient processed events for ML training.",
            }

        metadata = self._load_metadata(website_id)
        current_feature_version = metadata.get("feature_version", FEATURE_VERSION)
        if current_feature_version != FEATURE_VERSION:
            return {
                "status": "model_incompatible",
                "website_id": website_id,
                "reason": "Feature version mismatch detected. Re-train the website model.",
                "model_version": metadata.get("model_version", self.config.model_version),
                "feature_version": current_feature_version,
            }

        vector = build_feature_vector(event)
        matrix = build_feature_matrix([event])
        prediction = detector.predict(matrix)
        score = float(prediction["anomaly_scores"][0]) if prediction["anomaly_scores"] else 0.0
        is_anomaly = bool(score >= self.config.anomaly_threshold)
        return {
            "status": "ok",
            "website_id": website_id,
            "is_anomaly": is_anomaly,
            "anomaly_score": max(0.0, min(1.0, score)),
            "threshold": self.config.anomaly_threshold,
            "model_version": metadata.get("model_version", self.config.model_version),
            "feature_version": current_feature_version,
            "training_event_count": metadata.get("training_event_count", 0),
            "feature_vector": vector,
        }

    def persist_anomaly_finding(self, website_id: int, event: Event | dict[str, Any], prediction: dict[str, Any]) -> Finding | None:
        if not prediction.get("is_anomaly"):
            return None

        event_row = event if isinstance(event, Event) else self.session.execute(
            select(Event).where(Event.website_id == website_id, Event.event_id == str(event.get("event_id")))
        ).scalar_one_or_none()

        if event_row is None:
            return None

        existing = self.session.execute(
            select(Finding).where(
                Finding.website_id == website_id,
                Finding.event_id == event_row.id,
                Finding.agent_name == "ml_anomaly_detector",
                Finding.finding_type == "ml_anomaly",
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        metadata = self._load_metadata(website_id)
        finding = create_finding(
            session=self.session,
            website_id=website_id,
            event_id=event_row.id,
            agent_name="ml_anomaly_detector",
            finding_type="ml_anomaly",
            confidence=float(prediction.get("anomaly_score", 0.0)),
            evidence={
                "model_version": metadata.get("model_version", self.config.model_version),
                "feature_version": metadata.get("feature_version", FEATURE_VERSION),
                "anomaly_score": float(prediction.get("anomaly_score", 0.0)),
                "threshold": self.config.anomaly_threshold,
                "training_event_count": metadata.get("training_event_count", 0),
            },
        )
        return finding

    def process_event(self, website_id: int, event: Event | dict[str, Any]) -> dict[str, Any]:
        prediction = self.predict_event_anomaly(website_id, event)
        if prediction.get("status") == "ok" and prediction.get("is_anomaly"):
            self.persist_anomaly_finding(website_id, event, prediction)
        return prediction
