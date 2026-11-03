from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceReference(BaseSchema):
    type: Literal["event", "finding", "correlation"]
    id: int


class AgentFinding(BaseSchema):
    title: str
    description: str
    classification: Literal["fact", "inference"]
    finding_type: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)


class InvestigationCreate(BaseSchema):
    correlation_id: int


class InvestigationEvidenceResponse(BaseSchema):
    id: int
    investigation_id: int
    evidence_type: str
    source_type: str
    source_id: int
    classification: str
    content: str | None = None
    confidence: float


class InvestigationResult(BaseSchema):
    summary: str
    facts: list[AgentFinding] = Field(default_factory=list)
    inferences: list[AgentFinding] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class InvestigationResponse(BaseSchema):
    id: int
    website_id: int
    correlation_id: int | None = None
    investigation_id: str
    title: str
    status: str
    summary: str | None = None
    confidence: float = 0.0
    facts: list[AgentFinding] = Field(default_factory=list)
    inferences: list[AgentFinding] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    created_at: str | None = None
    completed_at: str | None = None
