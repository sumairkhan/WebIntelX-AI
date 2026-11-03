from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import Incident
from app.database.repositories import create_incident, get_website_for_user
from app.risk.calculator import RiskCalculator


class RiskService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate(self, website_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload)
        data["site_id"] = website_id
        assessment = RiskCalculator.calculate(data)
        return {
            "site_id": website_id,
            "risk_score": round(assessment.risk_score, 2),
            "risk_level": assessment.risk_level,
            "confidence": round(float(assessment.confidence), 4),
            "factors": [
                {"name": factor.name, "contribution": round(factor.contribution, 2), "detail": factor.detail}
                for factor in assessment.factors
            ],
            "explanation": assessment.explanation,
        }

    def create_incident(self, website_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "Suspicious activity")
        description = str(payload.get("description") or "Suspicious activity reported by the platform.")
        risk_score = float(payload.get("risk_score", 0.0) or 0.0)
        normalized_score = max(0.0, min(100.0, risk_score)) / 100.0
        incident = create_incident(
            self.session,
            website_id=website_id,
            incident_id=f"inc-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{abs(hash(title)) % 10000}",
            title=title,
            risk_level=str(payload.get("risk_level") or "medium"),
            risk_score=normalized_score,
            confidence=float(payload.get("confidence", 0.5) or 0.5),
            status=str(payload.get("status") or "open"),
        )
        if description:
            incident.description = description
            self.session.add(incident)
            self.session.commit()
            self.session.refresh(incident)
        return {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "website_id": incident.website_id,
            "title": incident.title,
            "risk_level": incident.risk_level,
            "risk_score": round(incident.risk_score * 100.0, 2),
            "confidence": incident.confidence,
            "status": incident.status,
            "description": incident.description,
        }

    def get_incident_for_website(self, user_id: int, website_id: int, incident_id: int) -> dict[str, Any]:
        website = get_website_for_user(self.session, user_id=user_id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        incident = self.session.get(Incident, incident_id)
        if incident is None or incident.website_id != website_id:
            raise PermissionError("Incident not found for this website.")
        return {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "website_id": incident.website_id,
            "title": incident.title,
            "risk_level": incident.risk_level,
            "risk_score": round(float(incident.risk_score) * 100.0, 2),
            "confidence": incident.confidence,
            "status": incident.status,
            "description": incident.description,
        }

    @staticmethod
    def load_rules() -> dict[str, Any]:
        rules_path = Path(__file__).resolve().parents[2] / "config" / "risk_rules.json"
        if not rules_path.exists():
            return {"rule_detection": 12, "ml_anomaly": 15, "correlation_strength": 12, "investigation_confidence": 20}
        try:
            return json.loads(rules_path.read_text(encoding="utf-8"))
        except Exception:
            return {"rule_detection": 12, "ml_anomaly": 15, "correlation_strength": 12, "investigation_confidence": 20}
