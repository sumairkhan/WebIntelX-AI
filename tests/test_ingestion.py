from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Event
from app.main import app
from app.services.ingestion_service import ingestion_rate_limiter


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "ingestion_test.db"
    engine = database.build_engine(f"sqlite:///{db_path}")
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

    ingestion_rate_limiter.clear()
    ingestion_rate_limiter.limit_per_minute = 60

    with TestClient(app) as test_client:
        yield test_client


def register_user(client: TestClient, email: str, password: str = "password123") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def login_user(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def create_website(client: TestClient, headers: dict[str, str], name: str, domain: str) -> dict:
    response = client.post(
        "/api/websites",
        json={"name": name, "domain": domain},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def create_credential(client: TestClient, headers: dict[str, str], website_id: int) -> str:
    response = client.post(
        f"/api/websites/{website_id}/credentials",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["credential"]


def event_payload(**overrides):
    payload = {
        "event_id": "event-uuid-1",
        "timestamp": "2026-10-03T12:00:00Z",
        "event_type": "page_view",
        "source": "browser_sdk",
        "session_id": "session-123",
        "page_url": "https://example.com/products",
        "page_path": "/products",
        "referrer": "https://example.com/",
        "user_agent": "Mozilla/5.0",
        "screen_width": 1920,
        "screen_height": 1080,
        "language": "en-US",
    }
    payload.update(overrides)
    return payload


def test_valid_ingestion_stores_event(client: TestClient) -> None:
    register_user(client, "ingest@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'ingest@example.com')}"}
    website = create_website(client, headers, "Ingest Site", "ingest.example.com")
    credential = create_credential(client, headers, website["id"])

    response = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [event_payload()]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["accepted"] == 1
    assert payload["duplicates"] == 0
    assert payload["rejected"] == 0

    with database.SessionLocal() as session:
        saved = session.query(Event).filter_by(event_id="event-uuid-1").one()
        assert saved.website_id == website["id"]
        assert saved.source == "browser_sdk"
        assert saved.metadata["page_url"] == "https://example.com/products"


def test_website_telemetry_is_real_and_owner_scoped(client: TestClient) -> None:
    register_user(client, "telemetry-owner@example.com")
    register_user(client, "telemetry-other@example.com")
    owner_headers = {"Authorization": f"Bearer {login_user(client, 'telemetry-owner@example.com')}"}
    other_headers = {"Authorization": f"Bearer {login_user(client, 'telemetry-other@example.com')}"}
    website = create_website(client, owner_headers, "Telemetry", "telemetry.example.com")
    credential = create_credential(client, owner_headers, website["id"])
    client.post("/api/ingest/events", json={"credential": credential, "events": [event_payload(event_id="telemetry-real-1")]})

    response = client.get(f"/api/websites/{website['id']}/telemetry", headers=owner_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_count"] == 1
    assert payload["finding_count"] == 0
    assert payload["active_credential"] is True
    assert payload["connected"] is True
    assert payload["sdk_detected"] is True
    assert payload["telemetry_received"] is True
    assert payload["ingestion_working"] is True
    assert payload["last_event"]["event_id"] == "telemetry-real-1"
    assert payload["last_event"]["created_at"]
    assert client.get(f"/api/websites/{website['id']}/telemetry", headers=other_headers).status_code == 404


def test_customer_site_origin_can_only_preflight_ingestion(client: TestClient) -> None:
    register_user(client, "cors-owner@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'cors-owner@example.com')}"}
    website = create_website(client, headers, "CORS Site", "cors.example.com")

    allowed = client.options(
        "/api/ingest/events",
        headers={
            "Origin": f"https://{website['domain']}",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    blocked = client.options(
        "/api/ingest/events",
        headers={"Origin": "https://unregistered.example", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == f"https://{website['domain']}"
    assert blocked.status_code == 400
    assert "access-control-allow-origin" not in blocked.headers


def test_localhost_origin_is_limited_to_the_registered_port(client: TestClient) -> None:
    register_user(client, "local-origin@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'local-origin@example.com')}"}
    website = create_website(client, headers, "Local Site", "http://localhost:5501")
    credential = create_credential(client, headers, website["id"])

    wrong_port = client.post(
        "/api/ingest/events",
        headers={"Origin": "http://localhost:5500"},
        json={"credential": credential, "events": [event_payload(event_id="wrong-port")]},
    )
    correct_port = client.post(
        "/api/ingest/events",
        headers={"Origin": "http://localhost:5501"},
        json={"credential": credential, "events": [event_payload(event_id="right-port")]},
    )

    assert wrong_port.status_code == 403
    assert correct_port.status_code == 200
    assert correct_port.json()["accepted"] == 1

    with database.SessionLocal() as session:
        assert session.query(Event).filter_by(event_id="wrong-port").count() == 0


def test_verification_requires_telemetry_from_the_active_connection_key(client: TestClient) -> None:
    register_user(client, "active-key@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'active-key@example.com')}"}
    website = create_website(client, headers, "Active Key Site", "https://active-key.example")
    first_credential = create_credential(client, headers, website["id"])
    client.post(
        "/api/ingest/events",
        json={"credential": first_credential, "events": [event_payload(event_id="old-key-event")]},
    )

    credential_record = client.get(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    ).json()[0]
    rotated = client.post(
        f"/api/websites/{website['id']}/credentials/{credential_record['id']}/rotate",
        headers=headers,
    )
    assert rotated.status_code == 200

    waiting = client.get(f"/api/websites/{website['id']}/telemetry", headers=headers)
    assert waiting.status_code == 200
    assert waiting.json()["connected"] is False
    assert waiting.json()["last_event"] is None

    current_credential = rotated.json()["credential"]
    accepted = client.post(
        "/api/ingest/events",
        json={"credential": current_credential, "events": [event_payload(event_id="new-key-event")]},
    )
    assert accepted.status_code == 200

    connected = client.get(f"/api/websites/{website['id']}/telemetry", headers=headers)
    assert connected.json()["connected"] is True
    assert connected.json()["last_event"]["event_id"] == "new-key-event"


def test_duplicate_event_is_counted_without_reinsert(client: TestClient) -> None:
    register_user(client, "dup@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'dup@example.com')}"}
    website = create_website(client, headers, "Duplicate Site", "dup.example.com")
    credential = create_credential(client, headers, website["id"])

    request = {"credential": credential, "events": [event_payload(event_id="dup-1")]}
    first = client.post("/api/ingest/events", json=request)
    second = client.post("/api/ingest/events", json=request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["accepted"] == 0
    assert second.json()["duplicates"] == 1


def test_invalid_credential_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/ingest/events",
        json={"credential": "wix_ing_invalid", "events": [event_payload()]},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid ingestion credential"


def test_revoked_credential_is_rejected(client: TestClient) -> None:
    register_user(client, "revoke@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'revoke@example.com')}"}
    website = create_website(client, headers, "Revoke Site", "revoke.example.com")
    credential = create_credential(client, headers, website["id"])

    revoke_response = client.post(
        f"/api/websites/{website['id']}/credentials/{client.get(f'/api/websites/{website['id']}/credentials', headers=headers).json()[0]['id']}/revoke",
        headers=headers,
    )
    assert revoke_response.status_code == 200

    response = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [event_payload(event_id="revoked-1")]},
    )

    assert response.status_code == 401


def test_inactive_website_is_rejected(client: TestClient) -> None:
    register_user(client, "inactive@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'inactive@example.com')}"}
    website = create_website(client, headers, "Inactive Site", "inactive.example.com")
    credential = create_credential(client, headers, website["id"])

    patch_response = client.patch(
        f"/api/websites/{website['id']}",
        json={"status": "inactive"},
        headers=headers,
    )
    assert patch_response.status_code == 200

    response = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [event_payload(event_id="inactive-1")]},
    )

    assert response.status_code == 401


def test_malformed_event_is_rejected(client: TestClient) -> None:
    register_user(client, "bad@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'bad@example.com')}"}
    website = create_website(client, headers, "Bad Site", "bad.example.com")
    credential = create_credential(client, headers, website["id"])

    response = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [{"event_type": "page_view", "source": "browser_sdk"}]},
    )

    assert response.status_code == 422


def test_batch_limit_is_enforced(client: TestClient) -> None:
    register_user(client, "limit@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'limit@example.com')}"}
    website = create_website(client, headers, "Limit Site", "limit.example.com")
    credential = create_credential(client, headers, website["id"])

    events = [event_payload(event_id=f"batch-{index}") for index in range(51)]
    response = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": events},
    )

    assert response.status_code in {400, 413, 422}


def test_metadata_limits_are_enforced(client: TestClient) -> None:
    register_user(client, "meta@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'meta@example.com')}"}
    website = create_website(client, headers, "Meta Site", "meta.example.com")
    credential = create_credential(client, headers, website["id"])

    response = client.post(
        "/api/ingest/events",
        json={
            "credential": credential,
            "events": [
                event_payload(
                    event_id="meta-1",
                    data={"payload": "x" * 2000},
                )
            ],
        },
    )

    assert response.status_code in {400, 422}


def test_rate_limit_blocks_excessive_requests(client: TestClient) -> None:
    register_user(client, "rate@example.com")
    headers = {"Authorization": f"Bearer {login_user(client, 'rate@example.com')}"}
    website = create_website(client, headers, "Rate Site", "rate.example.com")
    credential = create_credential(client, headers, website["id"])

    ingestion_rate_limiter.clear()
    ingestion_rate_limiter.limit_per_minute = 1

    first = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [event_payload(event_id="rate-1")]},
    )
    second = client.post(
        "/api/ingest/events",
        json={"credential": credential, "events": [event_payload(event_id="rate-2")]},
    )

    assert first.status_code == 200
    assert second.status_code == 429
