from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "session",
    "jwt",
    "bearer",
}


def load_detection_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else Path(__file__).resolve().parents[2] / "config" / "detection_rules.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_evidence(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        key_name = str(key).lower()
        if any(sensitive in key_name for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = safe_evidence(value)
        elif isinstance(value, list):
            sanitized[key] = [safe_evidence(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, str):
            sanitized[key] = _sanitize_string_value(value)
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_string_value(value: str) -> str:
    if not value:
        return value

    try:
        parsed = urlsplit(value)
    except ValueError:
        return value

    if not parsed.query:
        return value

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    redacted_pairs: list[tuple[str, str]] = []
    for pair_key, pair_value in pairs:
        lower_key = pair_key.lower()
        if any(sensitive in lower_key for sensitive in SENSITIVE_KEYS):
            redacted_pairs.append((pair_key, "[REDACTED]"))
        else:
            redacted_pairs.append((pair_key, pair_value))

    if redacted_pairs == pairs:
        return value

    return urlunsplit(parsed._replace(query=urlencode(redacted_pairs, doseq=True)))


def normalize_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith("/"):
        text = "/" + text
    return text.rstrip("/") or "/"


def extract_event_path(event: dict[str, Any]) -> str:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    page_path = metadata.get("page_path") or metadata.get("path")
    if page_path:
        return normalize_path(page_path)

    page_url = metadata.get("page_url") or metadata.get("url") or event.get("page_url") or event.get("url")
    if page_url:
        parsed = urlsplit(str(page_url))
        return normalize_path(parsed.path)

    endpoint = event.get("endpoint")
    if endpoint:
        return normalize_path(endpoint)

    return ""


def extract_query_params(event: dict[str, Any]) -> dict[str, str]:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    page_url = metadata.get("page_url") or metadata.get("url") or event.get("page_url") or event.get("url")
    if not page_url:
        return {}
    parsed = urlsplit(str(page_url))
    return {k: v for k, v in parse_qsl(parsed.query, keep_blank_values=True)}


def normalize_user_agent(value: Any) -> str:
    return str(value or "").strip()


def match_path(pattern: str, candidate: str) -> bool:
    normalized_pattern = normalize_path(pattern).lower()
    normalized_candidate = normalize_path(candidate).lower()
    if normalized_candidate == normalized_pattern:
        return True
    if normalized_pattern and normalized_candidate.startswith(normalized_pattern + "/"):
        return True
    return False


def event_session_key(event: dict[str, Any]) -> str | None:
    session_id = event.get("session_id") or (event.get("metadata") or {}).get("session_id")
    if session_id:
        return str(session_id)
    return None
