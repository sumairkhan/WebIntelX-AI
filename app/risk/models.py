from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskFactor:
    name: str
    contribution: float
    detail: str


@dataclass
class RiskAssessment:
    risk_score: float
    risk_level: str
    confidence: float
    factors: list[RiskFactor] = field(default_factory=list)
    explanation: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "risk_score": float(self.risk_score),
            "risk_level": self.risk_level,
            "confidence": float(self.confidence),
            "factors": [
                {"name": factor.name, "contribution": factor.contribution, "detail": factor.detail}
                for factor in self.factors
            ],
            "explanation": self.explanation,
        }
