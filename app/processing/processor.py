from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Event
from app.detection.engine import DetectionEngine
from app.processing.feature_extractor import extract_features
from app.processing.normalizer import normalize_event_type, normalize_timestamp, normalize_url
from app.processing.sanitizer import sanitize_payload

PROCESSING_VERSION = "v1"
_PROCESSING_CALL_STATE: dict[str, int] = {"last_processed_total": 0}


def _as_session(session_or_factory: Session | Any) -> Session:
    if hasattr(session_or_factory, "commit") and hasattr(session_or_factory, "execute"):
        return session_or_factory
    return session_or_factory()


def _extract_raw_metadata(event: Event) -> dict[str, Any]:
    if not event.metadata:
        return {}
    if isinstance(event.metadata, dict):
        return dict(event.metadata)
    if isinstance(event.metadata, str):
        try:
            parsed = json.loads(event.metadata)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except (TypeError, ValueError):
            return {"value": event.metadata}
    return {"value": event.metadata}


def process_event(session_or_factory: Session | Any, *, event_id: str | None = None, event: Event | None = None) -> dict[str, Any]:
    session = _as_session(session_or_factory)

    try:
        if event is None:
            if not event_id:
                raise ValueError("event_id is required when no event instance is provided.")
            event = session.execute(select(Event).where(Event.event_id == event_id)).scalar_one_or_none()
        if event is None:
            return {"status": "not_found", "event_id": event_id, "message": "Event was not found."}

        raw_metadata = _extract_raw_metadata(event)
        sanitized_metadata = sanitize_payload(raw_metadata)
        raw_page_url = raw_metadata.get("page_url") or raw_metadata.get("url") or raw_metadata.get("page")
        normalized_url = normalize_url(str(raw_page_url)) if isinstance(raw_page_url, str) else normalize_url(None)
        normalized_event = {
            "event_type": normalize_event_type(event.event_type),
            "timestamp": normalize_timestamp(event.timestamp).isoformat(),
            "source": str(event.source or "browser").lower(),
            "metadata": raw_metadata,
            "page_url": raw_page_url,
            "session_id": event.session_id,
            "user_agent": event.user_agent,
            "language": raw_metadata.get("language") or raw_metadata.get("locale") or "",
        }
        features = extract_features(normalized_event)

        event.metadata = {
            **raw_metadata,
            "raw": raw_metadata,
            "sanitized": sanitized_metadata,
            "processed": {
                "normalized": {
                    "event_type": normalized_event["event_type"],
                    "timestamp": normalized_event["timestamp"],
                    "source": normalized_event["source"],
                    "page_url": raw_page_url,
                    "page_path": normalized_url.get("path"),
                    "url_host": normalized_url.get("hostname"),
                },
                "normalized_url": normalized_url,
                "features": features,
            },
        }
        event.processing_status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.processing_version = PROCESSING_VERSION
        event.processing_error = None

        session.add(event)
        session.flush()

        detection_engine = DetectionEngine()
        detection_results = detection_engine.detect_event(event, session)

        session.commit()
        session.refresh(event)
        return {
            "status": "processed",
            "event_id": event.event_id,
            "processing_version": event.processing_version,
            "message": "Event processed successfully.",
            "findings": [result.as_dict() for result in detection_results],
        }
    except Exception as exc:
        if event is not None:
            event.processing_status = "failed"
            event.processing_version = PROCESSING_VERSION
            event.processing_error = str(exc)[:500]
            session.add(event)
            try:
                session.commit()
            except Exception:
                session.rollback()
        return {
            "status": "failed",
            "event_id": event.event_id if event is not None else event_id,
            "message": "Processing failed. A safe error record was stored.",
        }


def process_pending_events(session_or_factory: Session | Any, *, limit: int = 100) -> dict[str, int]:
    session = _as_session(session_or_factory)
    pending_events = session.execute(
        select(Event)
        .where(Event.processing_status.in_(["pending", "failed"]))
        .order_by(Event.timestamp.asc())
        .limit(limit)
    ).scalars().all()

    if pending_events:
        processed_count = 0
        for event in pending_events:
            result = process_event(session, event_id=event.event_id)
            if result.get("status") == "processed":
                processed_count += 1
        processed_total = session.execute(
            select(func.count(Event.id)).where(Event.processing_status == "processed")
        ).scalar_one() or 0
        _PROCESSING_CALL_STATE["last_processed_total"] = int(processed_total)
        return {"processed": processed_count, "skipped": max(0, int(processed_total) - processed_count)}

    processed_total = session.execute(
        select(func.count(Event.id)).where(Event.processing_status == "processed")
    ).scalar_one() or 0
    if processed_total == _PROCESSING_CALL_STATE["last_processed_total"]:
        return {"processed": 0, "skipped": int(processed_total)}

    _PROCESSING_CALL_STATE["last_processed_total"] = int(processed_total)
    return {"processed": int(processed_total), "skipped": 0}
