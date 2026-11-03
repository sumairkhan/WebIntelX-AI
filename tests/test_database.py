from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database import database
from app.database.models import (
    Correlation,
    Event,
    Feedback,
    Finding,
    Incident,
    IngestionCredential,
    User,
    Website,
)


@pytest.fixture
def db_session(monkeypatch, tmp_path) -> Generator[Session, None, None]:
    test_db = tmp_path / "test_webintelx.db"
    database_url = f"sqlite:///{test_db}"

    engine = database.build_engine(database_url)
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)

    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_database_initializes_successfully(db_session: Session) -> None:
    inspector = inspect(database.engine)
    expected_tables = {
        "users",
        "websites",
        "ingestion_credentials",
        "events",
        "findings",
        "incidents",
        "correlations",
        "feedback",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))


def test_user_website_relationship_works(db_session: Session) -> None:
    user = User(email="user@example.com", password_hash="hash-1")
    website = Website(user=user, name="Example", domain="example.com", status="active")
    db_session.add(user)
    db_session.add(website)
    db_session.commit()

    saved = db_session.query(User).filter_by(email="user@example.com").one()
    assert saved.websites[0].domain == "example.com"


def test_website_event_relationship_works(db_session: Session) -> None:
    user = User(email="event-user@example.com", password_hash="hash-2")
    website = Website(user=user, name="Event Site", domain="eventsite.com", status="active")
    event = Event(
        website=website,
        event_id="evt-001",
        timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        event_type="login",
        source="api",
        source_ip="127.0.0.1",
        session_id="session-001",
        user_id="user-001",
        method="GET",
        endpoint="/health",
        status_code=200,
        user_agent="test-agent",
        metadata={"hello": "world"},
    )
    db_session.add_all([user, website, event])
    db_session.commit()

    saved_website = db_session.query(Website).filter_by(domain="eventsite.com").one()
    assert saved_website.events[0].event_id == "evt-001"


def test_website_incident_relationship_works(db_session: Session) -> None:
    user = User(email="incident-user@example.com", password_hash="hash-3")
    website = Website(user=user, name="Incident Site", domain="incidentsite.com", status="active")
    incident = Incident(
        website=website,
        incident_id="inc-001",
        title="Test incident",
        risk_level="HIGH",
        risk_score=0.88,
        confidence=0.91,
        status="DETECTED",
    )
    db_session.add_all([user, website, incident])
    db_session.commit()

    saved_website = db_session.query(Website).filter_by(domain="incidentsite.com").one()
    assert saved_website.incidents[0].incident_id == "inc-001"


def test_incident_feedback_relationship_works(db_session: Session) -> None:
    user = User(email="feedback-user@example.com", password_hash="hash-4")
    website = Website(user=user, name="Feedback Site", domain="feedbacksite.com", status="active")
    incident = Incident(
        website=website,
        incident_id="inc-002",
        title="Feedback case",
        risk_level="MEDIUM",
        risk_score=0.5,
        confidence=0.7,
        status="INVESTIGATING",
    )
    feedback = Feedback(incident=incident, analyst_decision="CONFIRMED", comment="Looks valid")
    db_session.add_all([user, website, incident, feedback])
    db_session.commit()

    saved_incident = db_session.query(Incident).filter_by(incident_id="inc-002").one()
    assert saved_incident.feedback[0].analyst_decision == "CONFIRMED"


def test_event_finding_relationship_works(db_session: Session) -> None:
    user = User(email="finding-user@example.com", password_hash="hash-5")
    website = Website(user=user, name="Finding Site", domain="findingsite.com", status="active")
    event = Event(
        website=website,
        event_id="evt-002",
        timestamp=datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        event_type="request",
        source="gateway",
        source_ip="192.168.1.1",
        session_id="session-002",
        user_id="user-002",
        method="POST",
        endpoint="/login",
        status_code=401,
        user_agent="curl",
        metadata={"attempt": 1},
    )
    finding = Finding(
        website=website,
        event=event,
        agent_name="baseline",
        finding_type="anomaly",
        confidence=0.86,
        evidence={"reason": "rate-limited"},
    )
    db_session.add_all([user, website, event, finding])
    db_session.commit()

    saved_event = db_session.query(Event).filter_by(event_id="evt-002").one()
    assert saved_event.findings[0].finding_type == "anomaly"


def test_event_correlation_relationship_works(db_session: Session) -> None:
    user = User(email="correlation-user@example.com", password_hash="hash-6")
    website = Website(user=user, name="Correlation Site", domain="corrsite.com", status="active")
    event_a = Event(
        website=website,
        event_id="evt-003",
        timestamp=datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
        event_type="scan",
        source="scanner",
        source_ip="10.0.0.1",
        session_id="session-003",
        user_id="user-003",
        method="GET",
        endpoint="/",
        status_code=200,
        user_agent="bot",
        metadata={},
    )
    event_b = Event(
        website=website,
        event_id="evt-004",
        timestamp=datetime(2026, 1, 3, 0, 5, 0, tzinfo=timezone.utc),
        event_type="error",
        source="app",
        source_ip="10.0.0.2",
        session_id="session-004",
        user_id="user-004",
        method="POST",
        endpoint="/login",
        status_code=500,
        user_agent="bot",
        metadata={},
    )
    incident = Incident(
        website=website,
        incident_id="inc-003",
        title="Correlation case",
        risk_level="MEDIUM",
        risk_score=0.6,
        confidence=0.8,
        status="DETECTED",
    )
    correlation = Correlation(
        incident=incident,
        event=event_a,
        related_event=event_b,
        relationship_type="SEQUENCE",
        strength=0.75,
    )
    db_session.add_all([user, website, event_a, event_b, incident, correlation])
    db_session.commit()

    saved_incident = db_session.query(Incident).filter_by(incident_id="inc-003").one()
    assert saved_incident.correlations[0].relationship_type == "SEQUENCE"


def test_unique_event_id_is_enforced(db_session: Session) -> None:
    user = User(email="uniqueevent-user@example.com", password_hash="hash-7")
    website = Website(user=user, name="Unique Event Site", domain="uniqueeventsite.com", status="active")
    event_one = Event(
        website=website,
        event_id="duplicate-event",
        timestamp=datetime(2026, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
        event_type="login",
        source="api",
        source_ip="127.0.0.1",
        session_id="session-005",
        user_id="user-005",
        method="GET",
        endpoint="/health",
        status_code=200,
        user_agent="test",
        metadata={},
    )
    db_session.add_all([user, website, event_one])
    db_session.commit()

    event_two = Event(
        website=website,
        event_id="duplicate-event",
        timestamp=datetime(2026, 1, 4, 0, 1, 0, tzinfo=timezone.utc),
        event_type="login",
        source="api",
        source_ip="127.0.0.1",
        session_id="session-006",
        user_id="user-006",
        method="GET",
        endpoint="/health",
        status_code=200,
        user_agent="test",
        metadata={},
    )
    db_session.add(event_two)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_incident_id_is_enforced(db_session: Session) -> None:
    user = User(email="uniqueincident-user@example.com", password_hash="hash-8")
    website = Website(user=user, name="Unique Incident Site", domain="uniqueincidentsite.com", status="active")
    incident_one = Incident(
        website=website,
        incident_id="duplicate-incident",
        title="First",
        risk_level="LOW",
        risk_score=0.1,
        confidence=0.5,
        status="DETECTED",
    )
    db_session.add_all([user, website, incident_one])
    db_session.commit()

    incident_two = Incident(
        website=website,
        incident_id="duplicate-incident",
        title="Second",
        risk_level="LOW",
        risk_score=0.2,
        confidence=0.6,
        status="DETECTED",
    )
    db_session.add(incident_two)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_website_data_can_be_retrieved_by_user_id(db_session: Session) -> None:
    user = User(email="lookup-user@example.com", password_hash="hash-9")
    website = Website(user=user, name="Lookup Site", domain="lookupsite.com", status="active")
    db_session.add_all([user, website])
    db_session.commit()

    result = db_session.query(Website).filter_by(user_id=user.id).all()
    assert len(result) == 1
    assert result[0].domain == "lookupsite.com"


def test_database_initialization_does_not_delete_existing_records(db_session: Session) -> None:
    user = User(email="preserve-user@example.com", password_hash="hash-10")
    website = Website(user=user, name="Persist Site", domain="persistsite.com", status="active")
    db_session.add_all([user, website])
    db_session.commit()

    database.Base.metadata.create_all(bind=database.engine)
    reloaded = db_session.query(Website).filter_by(domain="persistsite.com").one()
    assert reloaded.name == "Persist Site"
