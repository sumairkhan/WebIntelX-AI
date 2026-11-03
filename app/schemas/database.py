from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseSchema):
    email: str
    is_active: bool = True


class WebsiteCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    status: str = "active"


class WebsiteUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=50)


class WebsiteResponse(BaseSchema):
    id: int
    user_id: int
    name: str
    domain: str
    origin: str | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EventResponse(BaseSchema):
    id: int
    website_id: int
    event_id: str
    timestamp: datetime
    event_type: str
    source: str
    session_id: str | None = None
    method: str | None = None
    endpoint: str | None = None
    status_code: int | None = None
    created_at: datetime


class WebsiteTelemetryResponse(BaseModel):
    event_count: int
    finding_count: int
    active_credential: bool
    connected: bool
    sdk_detected: bool
    telemetry_received: bool
    ingestion_working: bool
    last_event: EventResponse | None = None


class FindingResponse(BaseSchema):
    id: int
    website_id: int
    event_id: int
    agent_name: str | None = None
    finding_type: str
    confidence: float
    evidence: dict[str, Any] | None = None
    created_at: datetime


class WebsiteBase(BaseSchema):
    user_id: int
    name: str
    domain: str
    status: str = "active"


class EventBase(BaseSchema):
    website_id: int
    event_id: str
    timestamp: str
    event_type: str
    source: str
    source_ip: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    method: str | None = None
    endpoint: str | None = None
    status_code: int | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None


class FindingBase(BaseSchema):
    website_id: int
    event_id: int
    agent_name: str | None = None
    finding_type: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: dict[str, Any] | None = None


class IncidentBase(BaseSchema):
    website_id: int
    incident_id: str
    title: str
    risk_level: str
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = "DETECTED"


class CorrelationBase(BaseSchema):
    incident_id: int | None = None
    event_id: int
    related_event_id: int
    relationship_type: str
    strength: float = Field(default=0.0, ge=0.0, le=1.0)


class FeedbackBase(BaseSchema):
    incident_id: int
    analyst_decision: str
    comment: str | None = None
