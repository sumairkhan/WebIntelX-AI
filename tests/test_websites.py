from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.main import app


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "website_test.db"
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
    token = login_user(client, email)
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_user_cannot_manage_websites(client: TestClient) -> None:
    response = client.post(
        "/api/websites",
        json={"name": "Test", "domain": "example.com"},
    )
    assert response.status_code == 401

    list_response = client.get("/api/websites")
    assert list_response.status_code == 401

    get_response = client.get("/api/websites/1")
    assert get_response.status_code == 401


def test_authenticated_user_can_create_and_see_website(client: TestClient) -> None:
    register_user(client, "owner@example.com")
    headers = auth_headers(client, "owner@example.com")

    response = client.post(
        "/api/websites",
        json={"name": "Owner Website", "domain": "HTTPS://Example.COM/"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Owner Website"
    assert payload["domain"] == "example.com"
    assert payload["status"] == "active"

    list_response = client.get("/api/websites", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["domain"] == "example.com"
    assert items[0]["origin"] == "https://example.com"


def test_local_website_origins_keep_the_registered_protocol_and_port(client: TestClient) -> None:
    register_user(client, "local-sites@example.com")
    headers = auth_headers(client, "local-sites@example.com")

    first = client.post(
        "/api/websites",
        json={"name": "Local 5500", "domain": "http://localhost:5500/"},
        headers=headers,
    )
    second = client.post(
        "/api/websites",
        json={"name": "Local 5501", "domain": "localhost:5501"},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["domain"] == "localhost:5500"
    assert first.json()["origin"] == "http://localhost:5500"
    assert second.status_code == 200
    assert second.json()["domain"] == "localhost:5501"
    assert second.json()["origin"] == "http://localhost:5501"


def test_sdk_asset_is_served_from_the_existing_sdk_source(client: TestClient) -> None:
    response = client.get("/sdk/webintelx.js")

    assert response.status_code == 200
    assert "application/javascript" in response.headers["content-type"]
    assert "init: function (config)" in response.text


def test_user_only_sees_their_own_websites(client: TestClient) -> None:
    user_a = "usera@example.com"
    user_b = "userb@example.com"
    register_user(client, user_a)
    register_user(client, user_b)

    headers_a = auth_headers(client, user_a)
    headers_b = auth_headers(client, user_b)

    client.post(
        "/api/websites",
        json={"name": "User A Site", "domain": "alpha.example.com"},
        headers=headers_a,
    )
    client.post(
        "/api/websites",
        json={"name": "User B Site", "domain": "beta.example.com"},
        headers=headers_b,
    )

    user_a_list = client.get("/api/websites", headers=headers_a).json()
    user_b_list = client.get("/api/websites", headers=headers_b).json()

    assert len(user_a_list) == 1
    assert len(user_b_list) == 1
    assert user_a_list[0]["domain"] == "alpha.example.com"
    assert user_b_list[0]["domain"] == "beta.example.com"


def test_owner_can_get_site_but_non_owner_gets_404(client: TestClient) -> None:
    register_user(client, "owner1@example.com")
    register_user(client, "owner2@example.com")

    owner1_headers = auth_headers(client, "owner1@example.com")
    owner2_headers = auth_headers(client, "owner2@example.com")

    created = client.post(
        "/api/websites",
        json={"name": "Owned Site", "domain": "owned.example.com"},
        headers=owner1_headers,
    )
    website_id = created.json()["id"]

    owner_ok = client.get(f"/api/websites/{website_id}", headers=owner1_headers)
    owner_bad = client.get(f"/api/websites/{website_id}", headers=owner2_headers)

    assert owner_ok.status_code == 200
    assert owner_bad.status_code == 404


def test_owner_can_update_website_and_normalize_domain(client: TestClient) -> None:
    register_user(client, "update@example.com")
    headers = auth_headers(client, "update@example.com")

    created = client.post(
        "/api/websites",
        json={"name": "Original", "domain": "original.example.com"},
        headers=headers,
    )
    website_id = created.json()["id"]

    response = client.patch(
        f"/api/websites/{website_id}",
        json={"name": "Updated", "domain": "HTTPS://New-Example.COM/", "status": "active"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Updated"
    assert payload["domain"] == "new-example.com"
    assert payload["status"] == "active"


def test_non_owner_cannot_update_or_delete_site(client: TestClient) -> None:
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_headers = auth_headers(client, "alice@example.com")
    bob_headers = auth_headers(client, "bob@example.com")

    created = client.post(
        "/api/websites",
        json={"name": "Alice Site", "domain": "alice.example.com"},
        headers=alice_headers,
    )
    website_id = created.json()["id"]

    update_resp = client.patch(
        f"/api/websites/{website_id}",
        json={"name": "Hacked"},
        headers=bob_headers,
    )
    delete_resp = client.delete(f"/api/websites/{website_id}", headers=bob_headers)

    assert update_resp.status_code == 404
    assert delete_resp.status_code == 404


def test_owner_can_deactivate_website_without_deleting_record(client: TestClient) -> None:
    register_user(client, "deactivate@example.com")
    headers = auth_headers(client, "deactivate@example.com")

    created = client.post(
        "/api/websites",
        json={"name": "Inactive", "domain": "inactive.example.com"},
        headers=headers,
    )
    website_id = created.json()["id"]
    created_credential = client.post(f"/api/websites/{website_id}/credentials", headers=headers).json()

    response = client.delete(f"/api/websites/{website_id}", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "inactive"

    credentials = client.get(f"/api/websites/{website_id}/credentials", headers=headers).json()
    assert credentials[0]["status"] == "revoked"
    assert credentials[0]["id"] == created_credential["id"]
    assert client.post(f"/api/websites/{website_id}/credentials", headers=headers).status_code == 409
    assert client.post(
        f"/api/websites/{website_id}/credentials/{created_credential['id']}/rotate",
        headers=headers,
    ).status_code == 409

    fetched = client.get(f"/api/websites/{website_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "inactive"


def test_duplicate_domain_for_same_user_is_rejected(client: TestClient) -> None:
    register_user(client, "dupe@example.com")
    headers = auth_headers(client, "dupe@example.com")

    first = client.post(
        "/api/websites",
        json={"name": "First", "domain": "Example.com"},
        headers=headers,
    )
    second = client.post(
        "/api/websites",
        json={"name": "Second", "domain": "https://example.com/"},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_same_domain_for_different_users_is_allowed(client: TestClient) -> None:
    register_user(client, "user1@example.com")
    register_user(client, "user2@example.com")

    headers_1 = auth_headers(client, "user1@example.com")
    headers_2 = auth_headers(client, "user2@example.com")

    resp_1 = client.post(
        "/api/websites",
        json={"name": "One", "domain": "shared.example.com"},
        headers=headers_1,
    )
    resp_2 = client.post(
        "/api/websites",
        json={"name": "Two", "domain": "https://shared.example.com/"},
        headers=headers_2,
    )

    assert resp_1.status_code == 200
    assert resp_2.status_code == 200
