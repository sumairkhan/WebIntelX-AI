from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from app.config.settings import settings


def discover_backend_base_url() -> str:
    candidate_ports = [
        int(os.getenv("WEBINTELX_API_PORT", "")) if os.getenv("WEBINTELX_API_PORT") else None,
        18080,
        8000,
        8001,
        9000,
    ]
    seen: set[int] = set()
    for port in candidate_ports:
        if port is None or port in seen:
            continue
        seen.add(port)
        base_url = f"http://127.0.0.1:{port}"
        try:
            with request.urlopen(f"{base_url}/health", timeout=2) as response:
                if response.status == 200:
                    return base_url
        except Exception:
            continue
    return f"http://{settings.api_host}:{settings.api_port}"


class APIClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or discover_backend_base_url()).rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with request.urlopen(req, timeout=15) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if detail:
                raise RuntimeError(detail) from exc
            raise RuntimeError(f"API error: {exc.code}") from exc
        except Exception as exc:
            raise RuntimeError(f"Backend unavailable: {exc}") from exc

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, payload)

    def patch(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, payload)

    def delete(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, payload)

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self.post("/api/auth/login", {"email": email, "password": password})

    def register(self, email: str, password: str) -> dict[str, Any]:
        return self.post("/api/auth/register", {"email": email, "password": password})

    def get_me(self) -> dict[str, Any]:
        return self.get("/api/auth/me")

    def list_websites(self) -> list[dict[str, Any]]:
        return self.get("/api/websites")

    def create_website(self, name: str, domain: str) -> dict[str, Any]:
        return self.post("/api/websites", {"name": name, "domain": domain, "status": "active"})

    def create_credential(self, website_id: int) -> dict[str, Any]:
        return self.post(f"/api/websites/{website_id}/credentials")

    def list_credentials(self, website_id: int) -> list[dict[str, Any]]:
        return self.get(f"/api/websites/{website_id}/credentials")

    def rotate_credential(self, website_id: int, credential_id: int) -> dict[str, Any]:
        return self.post(f"/api/websites/{website_id}/credentials/{credential_id}/rotate")

    def revoke_credential(self, website_id: int, credential_id: int) -> dict[str, Any]:
        return self.post(f"/api/websites/{website_id}/credentials/{credential_id}/revoke")

    def get_graph(self, website_id: int) -> dict[str, Any]:
        return self.get(f"/api/websites/{website_id}/graph")

    def list_incidents(self, website_id: int) -> list[dict[str, Any]]:
        try:
            return self.get(f"/api/websites/{website_id}/incidents")
        except RuntimeError:
            return []

    def get_investigations(self, website_id: int) -> list[dict[str, Any]]:
        try:
            data = self.get(f"/api/websites/{website_id}/investigations")
            return data if isinstance(data, list) else []
        except RuntimeError:
            return []

    def get_threat_intel(self, website_id: int, indicator: str, indicator_type: str) -> dict[str, Any]:
        payload = {"indicator": indicator, "indicator_type": indicator_type}
        return self.post(f"/api/websites/{website_id}/threat-intelligence/check", payload)
