from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Website


class ReportingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_report(self, website_id: int, payload: dict[str, object] | None = None) -> dict[str, object]:
        payload = payload or {}
        website = self.session.get(Website, website_id)
        if website is None:
            return {
                "website_id": website_id,
                "summary": "No report available for the selected website.",
                "facts": [],
                "inferences": [],
                "uncertainties": [],
            }
        facts = [str(item) for item in payload.get("facts", []) if item]
        inferences = [str(item) for item in payload.get("inferences", []) if item]
        uncertainties = [str(item) for item in payload.get("uncertainties", []) if item]
        summary = str(payload.get("summary") or f"Investigation report for {website.domain}")
        return {
            "website_id": website_id,
            "website": website.domain,
            "summary": summary,
            "facts": facts or ["The website has recorded suspicious event activity."],
            "inferences": inferences or ["The observed pattern is consistent with possible abuse but not confirmed compromise."],
            "uncertainties": uncertainties or ["Additional telemetry may be required to confirm the final user impact."],
            "format": "json",
        }
