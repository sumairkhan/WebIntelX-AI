from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CredentialCreateResponse(BaseModel):
    id: int
    website_id: int
    credential: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CredentialResponse(BaseModel):
    id: int
    website_id: int
    status: str
    created_at: datetime
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
