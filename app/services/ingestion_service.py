from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.models import Event, IngestionCredential, Website
from app.database.repositories import create_events, get_event_ids_for_website, get_active_credential_by_hash
from app.processing.processor import process_event
from app.services.credentials import hash_ingestion_credential


class IngestionRateLimiter:
    """Simple in-memory per-client rate limiting for local MVP use."""

    def __init__(self, limit_per_minute: int = 60):
        self.limit_per_minute = limit_per_minute
        self._request_times: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._request_times.setdefault(key, [])
            bucket[:] = [timestamp for timestamp in bucket if now - timestamp < 60]
            if len(bucket) >= self.limit_per_minute:
                return False
            bucket.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._request_times.clear()


ingestion_rate_limiter = IngestionRateLimiter(settings.ingestion_rate_limit_per_minute)


def resolve_active_credential(session: Session, raw_credential: str) -> IngestionCredential:
    credential_hash = hash_ingestion_credential(raw_credential)
    credential = get_active_credential_by_hash(session, credential_hash=credential_hash)
    if credential is None or credential.website is None:
        raise ValueError("Invalid ingestion credential")

    if credential.website.status != "active":
        raise ValueError("Invalid ingestion credential")

    return credential


def resolve_website_for_credential(session: Session, raw_credential: str) -> Website:
    """Resolve a valid active ingestion key to its active registered website."""
    return resolve_active_credential(session, raw_credential).website


def build_event_metadata(event) -> dict | None:
    metadata: dict[str, object] = {}
    for key in [
        "page_url",
        "page_path",
        "referrer",
        "user_agent",
        "screen_width",
        "screen_height",
        "language",
    ]:
        value = getattr(event, key, None)
        if value is not None and value != "":
            metadata[key] = value

    if getattr(event, "data", None):
        metadata["data"] = event.data

    if not metadata:
        return None

    if len(str(metadata)) > 8192:
        raise ValueError("Event metadata exceeds the allowed size.")

    return metadata


def process_event_batch(
    session: Session,
    *,
    website_id: int,
    events: list,
    credential_id: int | None = None,
) -> tuple[int, int, list[Event]]:
    if not events:
        return 0, 0, []

    incoming_ids = [event.event_id for event in events]
    existing_ids = get_event_ids_for_website(session, website_id=website_id, event_ids=incoming_ids)

    seen: set[str] = set()
    valid_events: list[Event] = []
    duplicates = 0

    for event in events:
        if event.event_id in seen or event.event_id in existing_ids:
            duplicates += 1
            seen.add(event.event_id)
            continue
        seen.add(event.event_id)

        metadata = build_event_metadata(event)
        valid_events.append(
            Event(
                website_id=website_id,
                ingestion_credential_id=credential_id,
                event_id=event.event_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                source=event.source,
                session_id=event.session_id,
                user_agent=event.user_agent,
                metadata=metadata,
            )
        )

    created = create_events(session, website_id=website_id, events=valid_events)
    for event in created:
        try:
            process_event(session, event_id=event.event_id)
        except Exception:
            event.processing_status = "failed"
            event.processing_version = "v1"
            event.processing_error = "Processing failed."
            session.add(event)
            session.commit()
    return len(created), duplicates, created
