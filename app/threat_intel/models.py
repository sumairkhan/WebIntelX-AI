from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ThreatIntelResult:
    indicator: str
    indicator_type: str
    provider: str = "demo"
    malicious: bool | str = False
    confidence: float = 0.0
    reputation: str = "unknown"
    categories: list[str] = field(default_factory=list)
    source: str = "external"
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict[str, object]:
        return {
            "indicator": self.indicator,
            "indicator_type": self.indicator_type,
            "provider": self.provider,
            "malicious": self.malicious,
            "confidence": float(self.confidence),
            "reputation": self.reputation,
            "categories": list(self.categories),
            "source": self.source,
            "checked_at": self.checked_at.isoformat(),
        }
