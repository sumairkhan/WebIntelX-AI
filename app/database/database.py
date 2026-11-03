from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.database.models import Base
from app.investigation.models import Investigation, InvestigationEvidence


def build_engine(database_url: str | None = None):
    """Build a database engine that supports the configured runtime."""

    resolved_url = database_url or settings.database_url
    engine_kwargs: dict[str, object] = {"future": True}

    if resolved_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    return create_engine(resolved_url, **engine_kwargs)


def migrate_event_processing_columns() -> None:
    """Add Event processing columns safely for SQLite MVP databases without dropping data."""
    try:
        with SessionLocal() as session:
            result = session.execute(text("PRAGMA table_info(events)"))
            columns = [row[1] for row in result.all()]

            if "processing_status" not in columns:
                session.execute(text("ALTER TABLE events ADD COLUMN processing_status VARCHAR(50) DEFAULT 'pending' NOT NULL"))
            if "processed_at" not in columns:
                session.execute(text("ALTER TABLE events ADD COLUMN processed_at DATETIME"))
            if "processing_version" not in columns:
                session.execute(text("ALTER TABLE events ADD COLUMN processing_version VARCHAR(50)"))
            if "processing_error" not in columns:
                session.execute(text("ALTER TABLE events ADD COLUMN processing_error VARCHAR(500)"))

            session.execute(
                text(
                    "UPDATE events SET processing_status = 'pending' WHERE processing_status IS NULL OR processing_status = ''"
                )
            )
            session.commit()
    except Exception:
        return


def migrate_website_origin_column() -> None:
    """Add exact website origins to existing SQLite databases without dropping data."""
    with SessionLocal() as session:
        result = session.execute(text("PRAGMA table_info(websites)"))
        columns = [row[1] for row in result.all()]
        if "origin" not in columns:
            session.execute(text("ALTER TABLE websites ADD COLUMN origin VARCHAR(512)"))

        session.execute(
            text(
                """
                UPDATE websites
                SET origin = CASE
                    WHEN lower(domain) = 'localhost' OR lower(domain) LIKE 'localhost:%'
                         OR lower(domain) LIKE '127.0.0.1%'
                    THEN 'http://' || lower(domain)
                    ELSE 'https://' || lower(domain)
                END
                WHERE origin IS NULL OR origin = ''
                """
            )
        )
        session.commit()


def migrate_event_ingestion_credential_column() -> None:
    """Track which active website key produced each newly ingested browser event."""
    with SessionLocal() as session:
        result = session.execute(text("PRAGMA table_info(events)"))
        columns = [row[1] for row in result.all()]
        if "ingestion_credential_id" not in columns:
            session.execute(
                text("ALTER TABLE events ADD COLUMN ingestion_credential_id INTEGER")
            )
        session.commit()


def init_db() -> None:
    """Create all tables without dropping existing data."""

    Base.metadata.create_all(bind=engine)
    migrate_event_processing_columns()
    migrate_website_origin_column()
    migrate_event_ingestion_credential_column()


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for request-scoped operations."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Return True when the configured database can accept a query."""

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1")).scalar_one()
        return True
    except Exception:
        return False
