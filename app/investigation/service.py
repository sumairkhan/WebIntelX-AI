from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import Correlation, Event, User
from app.database.repositories import (
    create_investigation,
    create_investigation_evidence,
    get_investigation_for_website,
    get_website_for_user,
    update_investigation_status,
)
from app.investigation.context import build_investigation_context
from app.investigation.crew import run_investigation_crew
from app.investigation.validator import validate_investigation_output


class InvestigationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start_investigation(self, *, user: User, website_id: int, correlation_id: int) -> dict[str, Any]:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")

        correlation = self.session.get(Correlation, correlation_id)
        if correlation is None:
            raise ValueError("Correlation not found.")

        event_a = self.session.get(Event, correlation.event_id)
        event_b = self.session.get(Event, correlation.related_event_id)
        if event_a is None or event_b is None:
            raise ValueError("Correlation references missing event records.")
        if event_a.website_id != website_id or event_b.website_id != website_id:
            raise PermissionError("Correlation does not belong to the selected website.")

        investigation = create_investigation(
            self.session,
            website_id=website_id,
            correlation_id=correlation_id,
            investigation_id=f"inv-{uuid.uuid4().hex[:12]}",
            title=f"Investigation for correlation {correlation_id}",
            status="pending",
            summary="Investigation started.",
            confidence=0.0,
        )

        try:
            context = build_investigation_context(
                self.session,
                website_id=website_id,
                correlation_id=correlation_id,
            )
            output = run_investigation_crew(context)
            if not isinstance(output, dict):
                raise ValueError("Investigation output was not a valid structured object.")

            validation = validate_investigation_output(output, self.session, website_id)
            if validation["status"] != "valid":
                update_investigation_status(self.session, investigation, status="failed", summary="Investigation output was rejected as invalid.")
                raise ValueError("Investigation output was invalid: " + "; ".join(validation["errors"]))

            normalized = validation["result"]
            investigation.status = "completed"
            investigation.summary = normalized.get("summary", "Investigation completed.")
            investigation.confidence = float(normalized.get("confidence", 0.0))
            investigation.completed_at = datetime.now(timezone.utc)
            self.session.add(investigation)
            self.session.flush()

            for fact in normalized.get("facts", []):
                create_investigation_evidence(
                    self.session,
                    investigation_id=investigation.id,
                    evidence_type="fact",
                    source_type=fact.get("finding_type") or "fact",
                    source_id=fact["evidence_references"][0]["id"] if fact.get("evidence_references") else investigation.id,
                    classification="fact",
                    content=fact.get("description", ""),
                    confidence=float(fact.get("confidence", 0.0)),
                )

            for inference in normalized.get("inferences", []):
                create_investigation_evidence(
                    self.session,
                    investigation_id=investigation.id,
                    evidence_type="inference",
                    source_type=inference.get("finding_type") or "inference",
                    source_id=inference["evidence_references"][0]["id"] if inference.get("evidence_references") else investigation.id,
                    classification="inference",
                    content=inference.get("description", ""),
                    confidence=float(inference.get("confidence", 0.0)),
                )

            self.session.commit()
            return {
                "id": investigation.id,
                "website_id": investigation.website_id,
                "correlation_id": investigation.correlation_id,
                "investigation_id": investigation.investigation_id,
                "title": investigation.title,
                "status": investigation.status,
                "summary": investigation.summary,
                "confidence": investigation.confidence,
                "facts": normalized.get("facts", []),
                "inferences": normalized.get("inferences", []),
                "uncertainties": normalized.get("uncertainties", []),
                "evidence": normalized.get("evidence", []),
                "created_at": investigation.created_at.isoformat() if investigation.created_at else None,
                "completed_at": investigation.completed_at.isoformat() if investigation.completed_at else None,
            }
        except Exception as exc:
            update_investigation_status(self.session, investigation, status="failed", summary=f"Investigation failed: {str(exc)[:200]}")
            self.session.commit()
            raise

    def validate_output(self, payload: dict[str, Any], *, website_id: int) -> dict[str, Any]:
        return validate_investigation_output(payload, self.session, website_id)

    def get_investigation(self, *, user: User, website_id: int, investigation_id: str) -> dict[str, Any] | None:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        investigation = get_investigation_for_website(self.session, website_id=website_id, investigation_id=investigation_id)
        if investigation is None:
            return None
        return {
            "id": investigation.id,
            "website_id": investigation.website_id,
            "correlation_id": investigation.correlation_id,
            "investigation_id": investigation.investigation_id,
            "title": investigation.title,
            "status": investigation.status,
            "summary": investigation.summary,
            "confidence": investigation.confidence,
            "created_at": investigation.created_at.isoformat() if investigation.created_at else None,
            "completed_at": investigation.completed_at.isoformat() if investigation.completed_at else None,
        }
