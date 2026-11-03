from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Website
from app.response.recommendations import RecommendationBuilder


class ResponseService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_recommendations(self, website_id: int, payload: dict[str, object] | None = None) -> list[dict[str, object]]:
        payload = payload or {}
        website = self.session.get(Website, website_id)
        if website is None:
            return [{"action": "No recommendations available for the selected website.", "reason": "Website not found.", "priority": "low", "evidence": []}]
        risk_level = str(payload.get("risk_level") or "medium")
        evidence = payload.get("evidence")
        if isinstance(evidence, list):
            evidence_list = [str(item) for item in evidence]
        else:
            evidence_list = []
        return RecommendationBuilder.build(risk_level, evidence_list)
