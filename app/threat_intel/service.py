from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.models import Website
from app.threat_intel.cache import ThreatIntelCache
from app.threat_intel.models import ThreatIntelResult
from app.threat_intel.providers import DemoThreatIntelProvider


class ThreatIntelService:
    def __init__(self, session: Session, *, cache: ThreatIntelCache | None = None) -> None:
        self.session = session
        self.cache = cache or ThreatIntelCache(ttl_seconds=int(getattr(settings, "threat_intel_timeout_seconds", 300)))

    @staticmethod
    def _sanitize_indicator(indicator: str, indicator_type: str) -> str:
        value = (indicator or "").strip()
        if indicator_type == "ip":
            try:
                ipaddress.ip_address(value)
            except ValueError as exc:
                raise ValueError("Invalid IP address.") from exc
            return value
        if indicator_type == "domain":
            candidate = value.lower().strip("./ ")
            if not candidate or any(token in candidate for token in ["@", " ", "://", "?", "="]):
                raise ValueError("Invalid domain.")
            return candidate
        if indicator_type == "url":
            parsed = urlsplit(value)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL.")
            return value
        raise ValueError("Unsupported indicator type.")

    def check_indicator(self, website_id: int, indicator: str, indicator_type: str) -> dict[str, object]:
        website = self.session.get(Website, website_id)
        if website is None:
            raise ValueError("Website not found.")

        clean_indicator = self._sanitize_indicator(indicator, indicator_type)
        cache_key = f"{website_id}:{indicator_type}:{clean_indicator}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        provider_name = str(getattr(settings, "threat_intel_provider", "") or "demo").lower()
        enabled = bool(getattr(settings, "threat_intel_enabled", False))
        if not enabled or not provider_name:
            result = ThreatIntelResult(
                indicator=clean_indicator,
                indicator_type=indicator_type,
                provider="unavailable",
                malicious="unavailable",
                confidence=0.0,
                reputation="unavailable",
                categories=["disabled"],
                source="internal",
                checked_at=datetime.now(timezone.utc),
            )
            payload = result.as_dict()
            self.cache.set(cache_key, payload)
            return payload

        try:
            provider = DemoThreatIntelProvider()
            result = provider.check_indicator(clean_indicator, indicator_type)
            payload = result.as_dict()
            self.cache.set(cache_key, payload)
            return payload
        except Exception:
            fallback = ThreatIntelResult(
                indicator=clean_indicator,
                indicator_type=indicator_type,
                provider="unavailable",
                malicious="unavailable",
                confidence=0.0,
                reputation="unavailable",
                categories=["error"],
                source="internal",
                checked_at=datetime.now(timezone.utc),
            )
            payload = fallback.as_dict()
            self.cache.set(cache_key, payload)
            return payload
