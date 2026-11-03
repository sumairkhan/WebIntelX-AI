from __future__ import annotations

from urllib.parse import urlsplit

import numpy as np

FEATURE_VERSION = "v1"

FEATURE_FIELDS = [
    "url_depth",
    "query_parameter_count",
    "has_query",
    "has_referrer",
    "user_agent_length",
    "screen_width",
    "screen_height",
    "session_id_present",
    "is_mobile_like",
    "event_type_encoded",
    "path_length",
]

EVENT_TYPE_ENCODING = {
    "page_view": 1,
    "button_click": 2,
    "product_view": 3,
    "form_submit": 4,
    "navigation": 5,
    "api_request": 6,
    "custom": 7,
    "unknown": 0,
}


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None or value == "":
        return default

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()
    if text in {"", "none", "null", "nan", "n/a"}:
        return default

    try:
        return float(text.replace(",", "").replace("px", ""))
    except ValueError:
        return default


def _safe_bool(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return 1
    if text in {"0", "false", "no", "n", ""}:
        return 0
    return default


def _get_event_metadata(event: object) -> dict:
    if isinstance(event, dict):
        metadata = event.get("metadata") or {}
    elif hasattr(event, "metadata"):
        metadata = event.metadata or {}
    else:
        metadata = {}

    if not isinstance(metadata, dict):
        return {}
    return metadata


def _event_type_key(event: object) -> str:
    if isinstance(event, dict):
        value = event.get("event_type")
    else:
        value = getattr(event, "event_type", None)
    if value is None:
        return "unknown"
    return str(value).strip().lower().replace(" ", "_") or "unknown"


def _event_url(event: object, metadata: dict) -> str:
    if isinstance(event, dict):
        url = event.get("page_url") or metadata.get("page_url") or metadata.get("url") or metadata.get("page")
    else:
        url = getattr(event, "page_url", None) or metadata.get("page_url") or metadata.get("url") or metadata.get("page")
    if url is None:
        return ""
    return str(url)


def _event_user_agent(event: object, metadata: dict) -> str:
    if isinstance(event, dict):
        user_agent = event.get("user_agent") or metadata.get("user_agent") or metadata.get("userAgent")
    else:
        user_agent = getattr(event, "user_agent", None) or metadata.get("user_agent") or metadata.get("userAgent")
    if user_agent is None:
        return ""
    return str(user_agent)


def _event_session_id(event: object, metadata: dict) -> str:
    if isinstance(event, dict):
        session_id = event.get("session_id") or metadata.get("session_id") or metadata.get("session")
    else:
        session_id = getattr(event, "session_id", None) or metadata.get("session_id") or metadata.get("session")
    if session_id is None:
        return ""
    return str(session_id)


def _query_param_count(url: str) -> int:
    if not url:
        return 0
    parsed = urlsplit(url)
    query = parsed.query or ""
    if not query:
        return 0
    params = [part for part in query.split("&") if part]
    return len(params)


def _safe_path_length(url: str) -> int:
    if not url:
        return 0
    parsed = urlsplit(url)
    path = parsed.path or "/"
    return len([segment for segment in path.split("/") if segment])


def build_feature_vector(event: object) -> dict[str, float | int]:
    metadata = _get_event_metadata(event)
    page_url = _event_url(event, metadata)
    referrer = metadata.get("referrer") or metadata.get("referer")
    user_agent = _event_user_agent(event, metadata)
    session_id = _event_session_id(event, metadata)
    parsed = urlsplit(str(page_url)) if page_url else urlsplit("")
    path = parsed.path or "/"
    query_params = parsed.query.split("&") if parsed.query else []
    event_type_key = _event_type_key(event)

    vector = {
        "url_depth": max(0, len([segment for segment in path.split("/") if segment])),
        "query_parameter_count": len([part for part in query_params if part]),
        "has_query": 1 if parsed.query else 0,
        "has_referrer": 1 if bool(str(referrer).strip()) else 0,
        "user_agent_length": len(str(user_agent).strip()),
        "screen_width": _safe_float(metadata.get("screen_width") or metadata.get("screenWidth") or metadata.get("viewport_width"), 0.0),
        "screen_height": _safe_float(metadata.get("screen_height") or metadata.get("screenHeight") or metadata.get("viewport_height"), 0.0),
        "session_id_present": _safe_bool(session_id, default=0),
        "is_mobile_like": 1 if any(marker in str(user_agent).lower() for marker in ("mobile", "iphone", "android", "ipad")) else 0,
        "event_type_encoded": EVENT_TYPE_ENCODING.get(event_type_key, EVENT_TYPE_ENCODING["unknown"]),
        "path_length": _safe_path_length(page_url),
    }
    return {field: vector[field] for field in FEATURE_FIELDS}


def build_feature_matrix(events: list[object]) -> np.ndarray:
    if not events:
        return np.empty((0, len(FEATURE_FIELDS)), dtype=float)

    rows = [list(build_feature_vector(event).values()) for event in events]
    return np.asarray(rows, dtype=float)
