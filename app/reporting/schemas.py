from __future__ import annotations

from pydantic import BaseModel


class ReportingRequest(BaseModel):
    summary: str = ""
    facts: list[str] | None = None
    inferences: list[str] | None = None
    uncertainties: list[str] | None = None
