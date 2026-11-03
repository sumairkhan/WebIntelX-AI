from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Correlation, Event, Finding
from app.detection.utils import safe_evidence


def _sanitize_event(event: Event) -> dict[str, Any]:
    metadata = event.metadata or {}
    if isinstance(metadata, dict):
        cleaned = safe_evidence(metadata)
    else:
        cleaned = {"value": str(metadata)}
    return {
        "id": event.id,
        "website_id": event.website_id,
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
        "event_type": event.event_type,
        "method": event.method,
        "endpoint": event.endpoint,
        "status_code": event.status_code,
        "session_id": event.session_id,
        "source": event.source,
        "user_agent": event.user_agent,
        "metadata": cleaned,
    }


def _sanitize_finding(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "website_id": finding.website_id,
        "event_id": finding.event_id,
        "agent_name": finding.agent_name,
        "finding_type": finding.finding_type,
        "confidence": float(finding.confidence),
        "evidence": safe_evidence(finding.evidence or {}),
    }


def _sanitize_correlation(correlation: Correlation) -> dict[str, Any]:
    return {
        "id": correlation.id,
        "website_id": correlation.event.website_id if correlation.event is not None else None,
        "event_id": correlation.event_id,
        "related_event_id": correlation.related_event_id,
        "relationship_type": correlation.relationship_type,
        "strength": float(correlation.strength),
        "evidence": safe_evidence({"relationship_type": correlation.relationship_type, "strength": correlation.strength}),
    }


def build_investigation_context(
    session: Session,
    *,
    website_id: int,
    correlation_id: int | None = None,
    max_events: int = 100,
    max_findings: int = 50,
    max_correlations: int = 50,
) -> dict[str, Any]:
    """Build a bounded, sanitized context for one website and a selected correlation."""
    event_ids: set[int] = set()
    all_event_rows: list[Event] = []

    if correlation_id is not None:
        correlation = session.get(Correlation, correlation_id)
        if correlation is not None and correlation.event is not None and correlation.related_event is not None:
            event_ids.add(correlation.event_id)
            event_ids.add(correlation.related_event_id)
            if correlation.event.website_id != website_id or correlation.related_event.website_id != website_id:
                raise PermissionError("Correlation does not belong to the specified website.")

    if event_ids:
        event_rows = session.execute(select(Event).where(Event.id.in_(sorted(event_ids)), Event.website_id == website_id)).scalars().all()
    else:
        event_rows = session.execute(select(Event).where(Event.website_id == website_id).order_by(Event.timestamp.asc())).scalars().all()

    selected_events = list(event_rows)[:max_events]
    for event in selected_events:
        event_ids.add(event.id)
        all_event_rows.append(event)

    findings_rows = session.execute(
        select(Finding)
        .where(Finding.website_id == website_id, Finding.event_id.in_([event.id for event in selected_events]))
        .order_by(Finding.confidence.desc())
        .limit(max_findings)
    ).scalars().all()

    correlation_rows = session.execute(
        select(Correlation)
        .where(
            Correlation.event_id.in_([event.id for event in selected_events]),
            Correlation.related_event_id.in_([event.id for event in selected_events]),
        )
        .order_by(Correlation.strength.desc())
        .limit(max_correlations)
    ).scalars().all()

    if correlation_id is not None and not any(row.id == correlation_id for row in correlation_rows):
        correlation = session.get(Correlation, correlation_id)
        if correlation is not None and correlation.event.website_id == website_id:
            correlation_rows = [correlation, *correlation_rows][:max_correlations]

    return {
        "website_id": website_id,
        "correlation_id": correlation_id,
        "events": [_sanitize_event(event) for event in selected_events],
        "findings": [_sanitize_finding(finding) for finding in findings_rows],
        "correlations": [_sanitize_correlation(correlation) for correlation in correlation_rows],
    }
