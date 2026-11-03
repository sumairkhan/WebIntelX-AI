from __future__ import annotations

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
    "sessionid",
    "jwt",
    "bearer",
}


def _is_sensitive_key(key: str) -> bool:
    key_name = str(key).lower()
    return any(sensitive in key_name for sensitive in SENSITIVE_KEYS)


def sanitize_payload(value):
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = sanitize_payload(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    return value
