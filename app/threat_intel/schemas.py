from __future__ import annotations

from pydantic import BaseModel, Field


class ThreatIntelCheckRequest(BaseModel):
    indicator: str = Field(..., min_length=1, max_length=2048)
    indicator_type: str = Field(..., pattern=r"^(ip|domain|url)$")


class ThreatIntelCheckResponse(BaseModel):
    indicator: str
    indicator_type: str
    provider: str
    malicious: bool | str
    confidence: float
    reputation: str
    categories: list[str]
    source: str
    checked_at: str
