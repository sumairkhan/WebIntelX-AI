from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.config import MLConfig, ml_config


class IsolationForestAnomalyDetector:
    """Thin, deterministic wrapper around sklearn IsolationForest for MVP anomaly detection."""

    def __init__(self, config: MLConfig | None = None) -> None:
        self.config = config or ml_config
        self.model = IsolationForest(
            n_estimators=self.config.n_estimators,
            contamination=self.config.contamination,
            random_state=self.config.random_state,
        )

    def fit(self, X: np.ndarray) -> "IsolationForestAnomalyDetector":
        self.model.fit(X)
        return self

    def predict(self, X: np.ndarray) -> dict[str, object]:
        if X.size == 0:
            return {"is_anomaly": [], "anomaly_scores": [], "labels": []}

        labels = self.model.predict(X)
        decision = self.model.decision_function(X)
        anomaly_scores = self._normalize_scores(decision)
        return {
            "is_anomaly": [bool(label == -1) for label in labels],
            "anomaly_scores": anomaly_scores,
            "labels": labels.tolist(),
        }

    @staticmethod
    def _normalize_scores(scores: np.ndarray) -> np.ndarray:
        values = np.asarray(scores, dtype=float)
        if values.size == 0:
            return np.array([], dtype=float)

        min_score = float(np.min(values))
        max_score = float(np.max(values))
        if np.isclose(max_score, min_score):
            return np.full(values.shape, 0.5, dtype=float)

        normalized = (max_score - values) / (max_score - min_score + 1e-9)
        return np.clip(normalized, 0.0, 1.0)

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": self.model,
            "model_version": self.config.model_version,
            "feature_version": self.config.feature_version,
            "algorithm": "IsolationForest",
            "training_event_count": getattr(self, "training_event_count", 0),
        }
        joblib.dump(payload, target)
        metadata_path = target.with_suffix(".json")
        metadata = {
            "website_id": getattr(self, "website_id", None),
            "model_version": self.config.model_version,
            "feature_version": self.config.feature_version,
            "algorithm": "IsolationForest",
            "training_event_count": getattr(self, "training_event_count", 0),
            "trained_at": None,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def load(path: str | Path) -> "IsolationForestAnomalyDetector":
        target = Path(path)
        payload = joblib.load(target)
        detector = IsolationForestAnomalyDetector()
        detector.model = payload["model"]
        detector.model_version = payload.get("model_version", detector.config.model_version)
        detector.feature_version = payload.get("feature_version", detector.config.feature_version)
        detector.training_event_count = payload.get("training_event_count", 0)
        return detector
