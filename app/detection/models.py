from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DetectionResult:
    rule_name: str
    finding_type: str
    confidence: float
    severity: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    event_id: str | int | None = None
    website_id: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0.")

        if self.severity not in {"low", "medium", "high"}:
            raise ValueError("Severity must be one of: low, medium, high.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "finding_type": self.finding_type,
            "confidence": float(self.confidence),
            "severity": self.severity,
            "reason": self.reason,
            "evidence": self.evidence,
            "event_id": self.event_id,
            "website_id": self.website_id,
        }
