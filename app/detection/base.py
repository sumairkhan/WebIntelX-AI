from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.detection.models import DetectionResult


class DetectionRule(ABC):
    """Base interface for deterministic detection rules."""

    name: str = "base_rule"
    finding_type: str = "generic_finding"
    severity: str = "low"
    confidence: float = 0.5

    @abstractmethod
    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        """Return zero or more detection results for the event."""
