from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from app.threat_intel.models import ThreatIntelResult


class ThreatIntelProvider:
    """Base provider contract for enrichment lookups."""

    name = "provider"

    def check_indicator(self, indicator: str, indicator_type: str) -> ThreatIntelResult:
        raise NotImplementedError


class DemoThreatIntelProvider(ThreatIntelProvider):
    name = "demo"

    def check_indicator(self, indicator: str, indicator_type: str) -> ThreatIntelResult:
        clean = indicator.strip()
        if indicator_type == "ip":
            try:
                ipaddress.ip_address(clean)
            except ValueError as exc:
                raise ValueError("Invalid IP address.") from exc
            malicious = clean in {"8.8.8.8", "1.1.1.1", "203.0.113.42"}
            categories = ["scanner"] if malicious else ["benign"]
            reputation = "malicious" if malicious else "clean"
            confidence = 0.93 if malicious else 0.12
        elif indicator_type == "domain":
            parsed = clean.lower().strip(".")
            malicious = parsed.endswith("bad.example") or "malware" in parsed
            categories = ["suspicious"] if malicious else ["benign"]
            reputation = "malicious" if malicious else "clean"
            confidence = 0.88 if malicious else 0.18
        elif indicator_type == "url":
            parsed = urlparse(clean)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL.")
            malicious = "login" in clean.lower() and "token=" in clean.lower()
            categories = ["credential abuse"] if malicious else ["benign"]
            reputation = "malicious" if malicious else "clean"
            confidence = 0.79 if malicious else 0.16
        else:
            raise ValueError("Unsupported indicator type.")

        return ThreatIntelResult(
            indicator=clean,
            indicator_type=indicator_type,
            provider=self.name,
            malicious=malicious,
            confidence=confidence,
            reputation=reputation,
            categories=categories,
            source="demo_provider",
        )
