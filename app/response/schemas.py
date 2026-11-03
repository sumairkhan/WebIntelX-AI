from __future__ import annotations

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    action: str
    reason: str
    priority: str = Field(default="medium")
    evidence: list[str] = Field(default_factory=list)
