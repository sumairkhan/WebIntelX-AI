from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["application"] == settings.app_name
    assert payload["environment"] == settings.app_env
