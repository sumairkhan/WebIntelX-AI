from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base, Correlation, TimestampMixin, Website


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True, nullable=False)
    correlation_id: Mapped[int | None] = mapped_column(ForeignKey("correlations.id"), index=True, nullable=True)
    investigation_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    website: Mapped[Website] = relationship(back_populates="investigations")
    correlation: Mapped[Correlation | None] = relationship()
    evidence: Mapped[list["InvestigationEvidence"]] = relationship(
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("website_id", "correlation_id", "investigation_id", name="uq_investigation_website_corr_id"),
    )


class InvestigationEvidence(Base, TimestampMixin):
    __tablename__ = "investigation_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)

    investigation: Mapped[Investigation] = relationship(back_populates="evidence")
