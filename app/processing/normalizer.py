from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit


def normalize_string(value: str | None, *, max_length: int | None = None, default: str = "") -> str:
    if value is None:
        return default

    text = str(value).strip()
    if not text:
        return default
    if max_length is not None:
        text = text[:max_length]
    return text


def normalize_event_type(value: str | None) -> str:
    text = normalize_string(value, max_length=100)
    if not text:
        return "custom"

    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    if not normalized:
        return "custom"
    if normalized in {"page_view", "button_click", "product_view", "form_submit", "navigation", "api_request", "custom"}:
        return normalized
    return normalized


def normalize_language(value: str | None) -> str | None:
    text = normalize_string(value, max_length=50)
    if not text:
        return None
    return text.replace("_", "-")


def normalize_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = normalize_string(value, max_length=255)
        if not text:
            raise ValueError("Timestamp is required.")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("Invalid timestamp.") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def normalize_url(value: str | None) -> dict[str, object]:
    text = normalize_string(value, max_length=2048)
    if not text:
        return {
            "scheme": "",
            "hostname": "",
            "port": None,
            "path": "",
            "query": "",
            "has_query": False,
            "query_parameter_count": 0,
            "masked_query": {},
        }

    parsed = urlsplit(text)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    masked_query: dict[str, str] = {}

    for key, raw_value in query_items:
        if any(token in key.lower() for token in ["password", "token", "secret", "api_key", "apikey", "authorization", "cookie", "session"]):
            masked_query[key] = "[REDACTED]"
        else:
            masked_query[key] = raw_value

    return {
        "scheme": parsed.scheme.lower(),
        "hostname": (parsed.hostname or "").lower(),
        "port": parsed.port,
        "path": parsed.path or "/",
        "query": parsed.query,
        "has_query": bool(parsed.query),
        "query_parameter_count": len(query_items),
        "masked_query": masked_query,
    }
