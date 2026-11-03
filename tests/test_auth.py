from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.security import create_access_token
from app.database import database
from app.main import app


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "auth_test.db"
    database_url = f"sqlite:///{db_path}"
    engine = database.build_engine(database_url)
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "newuser@example.com"
    assert payload["id"] == 1
    assert "password_hash" not in payload


def test_register_invalid_email_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )

    assert response.status_code in {400, 422}


def test_register_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )

    assert response.status_code in {400, 422}


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"},
    )

    assert response.status_code == 400


def test_password_is_hashed_during_registration(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "hashuser@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "password_hash" not in data


def test_login_success_returns_token(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "loginuser@example.com", "password": "password123"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "loginuser@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


def test_login_with_invalid_password_fails(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "badlogin@example.com", "password": "password123"},
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "badlogin@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401


def test_login_with_unknown_email_fails(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "password123"},
    )

    assert response.status_code == 401


def test_valid_token_me_returns_current_user(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "current@example.com", "password": "password123"},
    )

    token_response = client.post(
        "/api/auth/login",
        json={"email": "current@example.com", "password": "password123"},
    )
    token = token_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "current@example.com"
    assert payload["is_active"] is True


def test_me_requires_valid_bearer_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401

    invalid = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid.status_code == 401


def test_expired_token_is_rejected(client: TestClient) -> None:
    expired_token = create_access_token(
        subject="expired@example.com",
        expires_delta=timedelta(minutes=-5),
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )

    assert response.status_code == 401


def test_user_isolation_foundation_uses_jwt_identity(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    token_response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    token = token_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
