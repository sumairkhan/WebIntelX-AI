from __future__ import annotations

from urllib.parse import urlsplit


def _normalize_browser(value: str) -> str:
    lowered = value.lower()
    if "chrome" in lowered:
        return "Chrome"
    if "firefox" in lowered:
        return "Firefox"
    if "safari" in lowered:
        return "Safari"
    if "edge" in lowered:
        return "Edge"
    return "Unknown"


def _normalize_os(value: str) -> str:
    lowered = value.lower()
    if "windows" in lowered:
        return "Windows"
    if "mac" in lowered:
        return "macOS"
    if "android" in lowered:
        return "Android"
    if "iphone" in lowered or "ipad" in lowered:
        return "iOS"
    return "Unknown"


def _normalize_device(value: str) -> str:
    lowered = value.lower()
    if "mobile" in lowered or "iphone" in lowered or "android" in lowered:
        return "mobile"
    if "tablet" in lowered:
        return "tablet"
    return "desktop"


def extract_features(event: dict) -> dict:
    metadata = event.get("metadata") if isinstance(event, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}

    page_url = event.get("page_url") or metadata.get("page_url") or metadata.get("url") or metadata.get("page") or ""
    referrer = metadata.get("referrer") if isinstance(metadata, dict) else ""
    user_agent = metadata.get("user_agent") or metadata.get("userAgent") or event.get("user_agent") or ""
    session_id = event.get("session_id") or metadata.get("session_id") or ""
    language = metadata.get("language") or metadata.get("locale") or ""

    parsed = urlsplit(str(page_url)) if page_url else urlsplit("")
    path = parsed.path or "/"
    query_count = 0
    query_keys: list[str] = []
    if parsed.query:
        query_count = len([part for part in parsed.query.split("&") if part])
        for part in parsed.query.split("&"):
            if "=" in part:
                key = part.split("=", 1)[0]
            else:
                key = part
            if key:
                query_keys.append(key)

    browser_name = _normalize_browser(str(user_agent))
    os_name = _normalize_os(str(user_agent))
    device_type = _normalize_device(str(user_agent))
    has_referrer = bool(str(referrer).strip())

    features = {
        "event_type": str(event.get("event_type", "custom")).lower(),
        "page_url": str(page_url),
        "url_depth": max(0, len([segment for segment in path.split("/") if segment])),
        "query_parameter_count": query_count,
        "query_keys": sorted(set(query_keys)),
        "has_referrer": has_referrer,
        "browser_family": browser_name,
        "os_family": os_name,
        "device_type": device_type,
        "session_id_present": bool(str(session_id).strip()),
        "language": str(language).split("-")[0] if language else "unknown",
    }

    if parsed.hostname:
        features["hostname"] = parsed.hostname.lower()
    return features
