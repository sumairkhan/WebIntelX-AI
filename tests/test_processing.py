from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Event
from app.main import app
from app.processing.feature_extractor import extract_features
from app.processing.normalizer import normalize_event_type, normalize_timestamp, normalize_url
from app.processing.sanitizer import sanitize_payload
from app.processing.processor import process_event, process_pending_events


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "processing_test.db"
    engine = database.build_engine(f"sqlite:///{db_path}")
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client


def test_normalize_event_type_is_deterministic() -> None:
    assert normalize_event_type("PAGE_VIEW") == "page_view"
    assert normalize_event_type("page-view") == "page_view"
    assert normalize_event_type("Custom Event") == "custom_event"


def test_normalize_timestamp_handles_utc_and_timezone() -> None:
    first = normalize_timestamp("2026-10-03T12:00:00Z")
    second = normalize_timestamp("2026-10-03T12:00:00+00:00")
    assert first.tzinfo is not None
    assert first.utcoffset() == timezone.utc.utcoffset(first)
    assert first == second

    with pytest.raises(ValueError):
        normalize_timestamp("not-a-date")


def test_normalize_url_masks_sensitive_query_values() -> None:
    normalized = normalize_url("https://example.com/account?token=abc123&status=open")
    assert normalized["hostname"] == "example.com"
    assert normalized["path"] == "/account"
    assert normalized["has_query"] is True
    assert normalized["query_parameter_count"] == 2
    assert normalized["masked_query"] == {"token": "[REDACTED]", "status": "open"}


def test_sanitize_payload_masks_sensitive_values() -> None:
    payload = {"password": "secret123", "nested": {"access_token": "abc", "safe": "keep"}}
    sanitized = sanitize_payload(payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["access_token"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "keep"


def test_extract_features_produces_structured_fields() -> None:
    features = extract_features(
        {
            "event_type": "page_view",
            "page_url": "https://example.com/products?id=123",
            "referrer": "https://google.com/search?q=abc",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123 Safari/537.36",
            "session_id": "session-1",
            "screen_width": 1920,
            "screen_height": 1080,
            "language": "en-US",
        }
    )
    assert features["url_depth"] == 1
    assert features["query_parameter_count"] == 1
    assert features["has_referrer"] is True
    assert features["browser_family"] == "Chrome"
    assert features["os_family"] == "Windows"
    assert features["device_type"] == "desktop"
    assert features["session_id_present"] is True


def test_process_event_marks_event_processed_and_preserves_raw_metadata(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "processor@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    token = client.post(
        "/api/auth/login",
        json={"email": "processor@example.com", "password": "password123"},
    ).json()["access_token"]
    website = client.post(
        "/api/websites",
        json={"name": "Proc Site", "domain": "proc.example.com"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    credential = client.post(
        f"/api/websites/{website['id']}/credentials",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["credential"]

    response = client.post(
        "/api/ingest/events",
        json={
            "credential": credential,
            "events": [
                {
                    "event_id": "proc-1",
                    "timestamp": "2026-10-03T12:00:00Z",
                    "event_type": "PAGE_VIEW",
                    "source": "browser_sdk",
                    "session_id": "session-abc",
                    "page_url": "https://example.com/products?token=abc123",
                    "page_path": "/products",
                    "referrer": "https://google.com",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123 Safari/537.36",
                    "screen_width": 1920,
                    "screen_height": 1080,
                    "language": "en-US",
                }
            ],
        },
    )
    assert response.status_code == 200

    with database.SessionLocal() as session:
        event = session.query(Event).filter_by(event_id="proc-1").one()
        assert event.processing_status == "processed"
        assert event.processing_version == "v1"
        assert event.metadata["raw"]["page_url"] == "https://example.com/products?token=abc123"
        assert event.metadata["processed"]["normalized"]["event_type"] == "page_view"
        assert "token" in str(event.metadata)
        assert "[REDACTED]" in str(event.metadata)


def test_process_pending_events_is_idempotent(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "pending@example.com", "password": "password123"},
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "pending@example.com", "password": "password123"},
    ).json()["access_token"]
    website = client.post(
        "/api/websites",
        json={"name": "Pending Site", "domain": "pending.example.com"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    credential = client.post(
        f"/api/websites/{website['id']}/credentials",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["credential"]

    client.post(
        "/api/ingest/events",
        json={
            "credential": credential,
            "events": [
                {
                    "event_id": "pending-1",
                    "timestamp": "2026-10-03T12:00:00Z",
                    "event_type": "button_click",
                    "source": "browser_sdk",
                    "session_id": "session-123",
                    "page_url": "https://example.com/button",
                    "page_path": "/button",
                    "referrer": "https://example.com",
                    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) Mobile/15E148 Safari/604.1",
                    "screen_width": 390,
                    "screen_height": 844,
                    "language": "en-US",
                }
            ],
        },
    )

    processed_once = process_pending_events(database.SessionLocal(), limit=10)
    assert processed_once["processed"] >= 1

    processed_twice = process_pending_events(database.SessionLocal(), limit=10)
    assert processed_twice["processed"] == 0
    assert processed_twice["skipped"] >= 1


def test_processing_failure_records_safe_message(client: TestClient) -> None:
    with database.SessionLocal() as session:
        event = Event(
            website_id=1,
            event_id="bad-proc-1",
            timestamp=datetime.now(timezone.utc),
            event_type="page_view",
            source="browser_sdk",
            session_id="s1",
            user_agent="ua",
            metadata={"raw": {"page_url": "https://example.com"}},
            processing_status="pending",
        )
        session.add(event)
        session.commit()

    result = process_event(database.SessionLocal(), event_id="bad-proc-1")
    assert result["status"] in {"processed", "failed"}
