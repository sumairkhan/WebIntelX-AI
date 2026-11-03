from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import IngestionCredential
from app.main import app
from app.services.credentials import hash_ingestion_credential


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "credentials_test.db"
    database_url = f"sqlite:///{db_path}"
    engine = database.build_engine(database_url)
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

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


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login_user(client, email)}"}


def create_website(client: TestClient, headers: dict[str, str], name: str, domain: str) -> dict:
    response = client.post(
        "/api/websites",
        json={"name": name, "domain": domain},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_authenticated_user_can_create_ingestion_credential(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    register_user(client, "creator@example.com")
    headers = auth_headers(client, "creator@example.com")
    website = create_website(client, headers, "Creator Site", "creator.example.com")

    with caplog.at_level(logging.INFO):
        response = client.post(
            f"/api/websites/{website['id']}/credentials",
            headers=headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["website_id"] == website["id"]
    assert payload["status"] == "active"
    assert payload["credential"].startswith("wix_ing_")
    assert "credential_hash" not in payload
    assert payload["credential"] not in caplog.text

    with database.SessionLocal() as session:
        credential = session.query(IngestionCredential).one()
        assert credential.credential_hash != payload["credential"]
        assert credential.credential_hash == hash_ingestion_credential(payload["credential"])


def test_owner_can_list_and_get_credentials_without_exposing_raw_values(client: TestClient) -> None:
    register_user(client, "listuser@example.com")
    headers = auth_headers(client, "listuser@example.com")
    website = create_website(client, headers, "List Site", "list.example.com")

    create_response = client.post(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    )
    credential_id = create_response.json()["id"]

    list_response = client.get(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert "credential" not in str(list_payload)
    assert "credential_hash" not in str(list_payload)

    detail_response = client.get(
        f"/api/websites/{website['id']}/credentials/{credential_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == credential_id
    assert "credential" not in str(detail_payload)
    assert "credential_hash" not in str(detail_payload)


def test_cross_user_access_to_credentials_returns_404(client: TestClient) -> None:
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_headers = auth_headers(client, "alice@example.com")
    bob_headers = auth_headers(client, "bob@example.com")

    alice_site = create_website(client, alice_headers, "Alice Site", "alice-owned.example.com")
    bob_site = create_website(client, bob_headers, "Bob Site", "bob-owned.example.com")

    alice_cred = client.post(
        f"/api/websites/{alice_site['id']}/credentials",
        headers=alice_headers,
    ).json()
    bob_cred = client.post(
        f"/api/websites/{bob_site['id']}/credentials",
        headers=bob_headers,
    ).json()

    assert client.get(
        f"/api/websites/{alice_site['id']}/credentials/{bob_cred['id']}",
        headers=alice_headers,
    ).status_code == 404
    assert client.get(
        f"/api/websites/{bob_site['id']}/credentials/{alice_cred['id']}",
        headers=bob_headers,
    ).status_code == 404


def test_owner_can_rotate_and_revoke_credentials(client: TestClient) -> None:
    register_user(client, "rotate@example.com")
    headers = auth_headers(client, "rotate@example.com")
    website = create_website(client, headers, "Rotate Site", "rotate.example.com")

    original = client.post(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    ).json()

    rotated = client.post(
        f"/api/websites/{website['id']}/credentials/{original['id']}/rotate",
        headers=headers,
    )
    assert rotated.status_code == 200
    rotated_payload = rotated.json()
    assert rotated_payload["credential"] != original["credential"]
    assert rotated_payload["status"] == "active"

    old_detail = client.get(
        f"/api/websites/{website['id']}/credentials/{original['id']}",
        headers=headers,
    )
    assert old_detail.status_code == 200
    assert old_detail.json()["status"] == "revoked"

    revoke_response = client.post(
        f"/api/websites/{website['id']}/credentials/{rotated_payload['id']}/revoke",
        headers=headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"

    second_revoke = client.post(
        f"/api/websites/{website['id']}/credentials/{rotated_payload['id']}/revoke",
        headers=headers,
    )
    assert second_revoke.status_code == 200
    assert second_revoke.json()["status"] == "revoked"


def test_get_active_credential_by_hash_requires_active_status(client: TestClient) -> None:
    register_user(client, "hashcheck@example.com")
    headers = auth_headers(client, "hashcheck@example.com")
    website = create_website(client, headers, "Hash Site", "hash.example.com")

    created = client.post(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    ).json()
    raw = created["credential"]
    hash_value = hash_ingestion_credential(raw)

    with database.SessionLocal() as session:
        credential = session.query(IngestionCredential).filter_by(credential_hash=hash_value).one()
        assert credential.status == "active"

    revoke_response = client.post(
        f"/api/websites/{website['id']}/credentials/{created['id']}/revoke",
        headers=headers,
    )
    assert revoke_response.status_code == 200

    with database.SessionLocal() as session:
        revoked = session.query(IngestionCredential).filter_by(id=created["id"]).one()
        assert revoked.status == "revoked"

    list_response = client.get(
        f"/api/websites/{website['id']}/credentials",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert "credential" not in str(list_response.json())
    assert "credential_hash" not in str(list_response.json())
