from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""


def utc_now() -> datetime:
    """Return the current UTC timestamp for database records."""

    return datetime.now(timezone.utc)


class TimestampMixin:
    """Common UTC timestamp fields for auditable tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    websites: Mapped[list["Website"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Website(Base, TimestampMixin):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    origin: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    user: Mapped[User] = relationship(back_populates="websites")
    ingestion_credentials: Mapped[list["IngestionCredential"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )
    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )
    investigations: Mapped[list["Investigation"]] = relationship(
        back_populates="website",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "domain", name="uq_websites_user_domain"),
    )


class IngestionCredential(Base, TimestampMixin):
    __tablename__ = "ingestion_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True, nullable=False)
    credential_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    website: Mapped[Website] = relationship(back_populates="ingestion_credentials")


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True, nullable=False)
    ingestion_credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_credentials.id"),
        index=True,
        nullable=True,
    )
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    website: Mapped[Website] = relationship(back_populates="events")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    correlations_as_event: Mapped[list["Correlation"]] = relationship(
        back_populates="event",
        foreign_keys="Correlation.event_id",
        cascade="all, delete-orphan",
    )
    correlations_as_related_event: Mapped[list["Correlation"]] = relationship(
        back_populates="related_event",
        foreign_keys="Correlation.related_event_id",
        cascade="all, delete-orphan",
    )


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True, nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finding_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0,
        info={"min": 0, "max": 1},
    )
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    website: Mapped[Website] = relationship(back_populates="findings")
    event: Mapped[Event] = relationship(back_populates="findings")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_findings_confidence_range"),
    )


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    risk_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    website: Mapped[Website] = relationship(back_populates="incidents")
    correlations: Mapped[list["Correlation"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_incidents_risk_score_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_incidents_confidence_range"),
    )


class Correlation(Base, TimestampMixin):
    __tablename__ = "correlations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), index=True, nullable=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    related_event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    strength: Mapped[float] = mapped_column(nullable=False, default=0.0)

    incident: Mapped[Incident | None] = relationship(back_populates="correlations")
    event: Mapped[Event] = relationship(
        foreign_keys=[event_id],
        back_populates="correlations_as_event",
    )
    related_event: Mapped[Event] = relationship(
        foreign_keys=[related_event_id],
        back_populates="correlations_as_related_event",
    )

    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 1", name="ck_correlations_strength_range"),
    )


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True, nullable=False)
    analyst_decision: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="feedback")
