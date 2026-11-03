from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Correlation, Event, Finding, Incident, User, Website
from app.correlation.engine import CorrelationEngine


@pytest.fixture
def correlation_db(tmp_path):
    db_path = tmp_path / "correlation_test.db"
    engine = database.build_engine(f"sqlite:///{db_path}")
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)
    return database.SessionLocal


def _make_user(session, email: str = "user@example.com") -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_website(session, user_id: int, domain: str) -> Website:
    website = Website(user_id=user_id, name=f"Site {domain}", domain=domain)
    session.add(website)
    session.commit()
    session.refresh(website)
    return website


def _make_event(session, website_id: int, *, event_id: str, session_id: str, event_type: str = "page_view", timestamp: datetime | None = None, metadata: dict | None = None) -> Event:
    event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        event_type=event_type,
        source="browser_sdk",
        source_ip="127.0.0.1",
        session_id=session_id,
        user_id="browser-uid",
        method="GET",
        endpoint="/products",
        status_code=200,
        user_agent="Mozilla/5.0",
        metadata=metadata or {"page_url": "https://example.com/products"},
        processing_status="processed",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def _make_finding(session, website_id: int, event_id: int, *, agent_name: str, finding_type: str, evidence: dict | None = None, confidence: float = 0.8) -> Finding:
    finding = Finding(
        website_id=website_id,
        event_id=event_id,
        agent_name=agent_name,
        finding_type=finding_type,
        confidence=confidence,
        evidence=evidence or {"example": True},
    )
    session.add(finding)
    session.commit()
    session.refresh(finding)
    return finding


def test_same_session_correlation_applies_within_same_website(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "same@example.com")
        site = _make_website(session, user.id, "same.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site.id, event_id="a1", session_id="abc", timestamp=now, event_type="page_view")
        event_b = _make_event(session, site.id, event_id="b1", session_id="abc", timestamp=now + timedelta(seconds=10), event_type="button_click")

        engine = CorrelationEngine(session)
        results = engine.correlate_events([event_a, event_b])
        assert any(item.relationship_type == "same_session" for item in results)
        assert all(0.0 <= item.strength <= 1.0 for item in results)


def test_cross_website_same_session_does_not_correlate(correlation_db):
    with correlation_db() as session:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        site_a = _make_website(session, user_a.id, "a.example.com")
        site_b = _make_website(session, user_b.id, "b.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site_a.id, event_id="site-a", session_id="shared", timestamp=now, event_type="page_view")
        event_b = _make_event(session, site_b.id, event_id="site-b", session_id="shared", timestamp=now + timedelta(seconds=5), event_type="page_view")

        engine = CorrelationEngine(session)
        results = engine.correlate_events([event_a, event_b])
        assert not any(item.relationship_type == "same_session" for item in results)


def test_rule_plus_ml_correlation_is_created(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "ml@example.com")
        site = _make_website(session, user.id, "ml.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site.id, event_id="ml-a", session_id="trig", timestamp=now, event_type="page_view")
        event_b = _make_event(session, site.id, event_id="ml-b", session_id="trig", timestamp=now + timedelta(seconds=6), event_type="api_request")
        _make_finding(session, site.id, event_a.id, agent_name="detection_engine", finding_type="suspicious_path")
        _make_finding(session, site.id, event_b.id, agent_name="ml_anomaly_detector", finding_type="ml_anomaly")

        engine = CorrelationEngine(session)
        results = engine.correlate_events([event_a, event_b])
        assert any(item.relationship_type == "rule_plus_ml" for item in results)


def test_suspicious_cluster_requires_multiple_signals(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "cluster@example.com")
        site = _make_website(session, user.id, "cluster.example.com")
        now = datetime.now(timezone.utc)
        events = [
            _make_event(session, site.id, event_id=f"cluster-{i}", session_id="cluster-session", timestamp=now + timedelta(seconds=i), event_type=event_type)
            for i, event_type in enumerate(["page_view", "api_request", "page_view", "button_click"])
        ]
        for idx, signal in enumerate(["suspicious_path", "suspicious_user_agent", "high_request_frequency", "ml_anomaly"]):
            _make_finding(session, site.id, events[idx].id, agent_name="detection_engine" if idx < 3 else "ml_anomaly_detector", finding_type=signal)

        engine = CorrelationEngine(session)
        results = engine.correlate_events(events)
        assert any(item.relationship_type == "suspicious_activity_cluster" for item in results)


def test_duplicate_correlations_are_not_inserted_twice(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "dup@example.com")
        site = _make_website(session, user.id, "dup.example.com")
        now = datetime.now(timezone.utc)
        e1 = _make_event(session, site.id, event_id="d1", session_id="dup-session", timestamp=now)
        e2 = _make_event(session, site.id, event_id="d2", session_id="dup-session", timestamp=now + timedelta(seconds=20))
        engine = CorrelationEngine(session)
        first = engine.correlate_events([e1, e2])
        second = engine.correlate_events([e1, e2])
        stored = session.query(Correlation).count()
        assert len(first) >= 1
        assert len(second) >= 1
        assert stored <= len(first) + 1


def test_no_incident_is_created_by_correlation(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "incident@example.com")
        site = _make_website(session, user.id, "incident.example.com")
        now = datetime.now(timezone.utc)
        e1 = _make_event(session, site.id, event_id="i1", session_id="incident-session", timestamp=now)
        e2 = _make_event(session, site.id, event_id="i2", session_id="incident-session", timestamp=now + timedelta(seconds=5))
        engine = CorrelationEngine(session)
        engine.correlate_events([e1, e2])
        assert session.query(Incident).count() == 0


def test_correlation_evidence_remains_safe(correlation_db):
    with correlation_db() as session:
        user = _make_user(session, "safe@example.com")
        site = _make_website(session, user.id, "safe.example.com")
        now = datetime.now(timezone.utc)
        e1 = _make_event(session, site.id, event_id="safe-1", session_id="safe-session", timestamp=now, metadata={"page_url": "https://example.com/.env?token=secret"})
        e2 = _make_event(session, site.id, event_id="safe-2", session_id="safe-session", timestamp=now + timedelta(seconds=9), event_type="button_click")
        engine = CorrelationEngine(session)
        results = engine.correlate_events([e1, e2])
        assert results
        assert all("token" not in str(item.evidence) for item in results)
