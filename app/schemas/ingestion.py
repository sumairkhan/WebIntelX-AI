from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.settings import settings


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class IngestionEvent(BaseSchema):
    event_id: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime
    event_type: str = Field(..., min_length=1, max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    session_id: str = Field(..., min_length=1, max_length=255)
    page_url: str | None = Field(default=None, max_length=2048)
    page_path: str | None = Field(default=None, max_length=2048)
    referrer: str | None = Field(default=None, max_length=2048)
    user_agent: str | None = Field(default=None, max_length=500)
    screen_width: int | None = Field(default=None, ge=1, le=10000)
    screen_height: int | None = Field(default=None, ge=1, le=10000)
    language: str | None = Field(default=None, max_length=50)
    data: dict[str, Any] | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value != "browser_sdk":
            raise ValueError("source must be browser_sdk")
        return value

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None

        if len(value) > 20:
            raise ValueError("Metadata object is too large.")

        sanitized: dict[str, Any] = {}
        for key, raw_value in value.items():
            normalized_key = str(key).strip()
            lower_key = normalized_key.lower()
            if not normalized_key or len(normalized_key) > 80:
                raise ValueError("Invalid metadata key.")
            if any(token in lower_key for token in ["password", "token", "secret", "cookie", "authorization", "credit", "card"]):
                raise ValueError("Sensitive metadata is not allowed.")

            if isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
                text_value = str(raw_value)
                if len(text_value) > 500:
                    raise ValueError("Metadata value is too large.")
                sanitized[normalized_key] = raw_value
            elif isinstance(raw_value, dict):
                nested = cls.validate_data(raw_value)
                if nested is None:
                    continue
                sanitized[normalized_key] = nested
            else:
                raise ValueError("Unsupported metadata value type.")

        return sanitized


class IngestionRequest(BaseSchema):
    credential: str = Field(..., min_length=10, max_length=255)
    events: list[IngestionEvent] = Field(..., min_length=1, max_length=settings.ingestion_max_batch_size)


class IngestionResponse(BaseSchema):
    success: bool = True
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
