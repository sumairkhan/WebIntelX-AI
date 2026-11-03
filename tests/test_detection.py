from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Event, User, Website, Finding
from app.detection.engine import DetectionEngine


@pytest.fixture
def detection_db(tmp_path):
    db_path = tmp_path / "detection_test.db"
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


def _make_event(session, website_id: int, *, event_id: str, path: str = "/products", user_agent: str = "Mozilla/5.0", method: str | None = None, status_code: int | None = None, session_id: str = "sess-1", timestamp: datetime | None = None, metadata: dict | None = None) -> Event:
    event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        event_type="page_view",
        source="browser_sdk",
        session_id=session_id,
        user_agent=user_agent,
        method=method,
        status_code=status_code,
        metadata=metadata or {"page_url": f"https://example.com{path}", "page_path": path},
        processing_status="processed",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_suspicious_path_rule_detects_common_payloads(detection_db):
    with detection_db() as session:
        user = _make_user(session)
        website = _make_website(session, user.id, "det.example.com")
        event = _make_event(session, website.id, event_id="path-1", path="/.env")
        engine = DetectionEngine()
        results = engine.evaluate(event)
        assert any(item.finding_type == "suspicious_path" for item in results)
        assert results[0].confidence >= 0.0
        assert results[0].confidence <= 1.0


def test_sensitive_endpoint_rule_detects_admin_paths(detection_db):
    with detection_db() as session:
        user = _make_user(session, "admin@example.com")
        website = _make_website(session, user.id, "admin.example.com")
        event = _make_event(session, website.id, event_id="admin-1", path="/admin")
        results = DetectionEngine().evaluate(event)
        assert any(item.finding_type == "sensitive_endpoint_access" for item in results)


def test_suspicious_user_agent_rule_detects_scanners(detection_db):
    with detection_db() as session:
        user = _make_user(session, "ua@example.com")
        website = _make_website(session, user.id, "ua.example.com")
        event = _make_event(session, website.id, event_id="ua-1", user_agent="sqlmap/1.0")
        results = DetectionEngine().evaluate(event)
        assert any(item.finding_type == "suspicious_user_agent" for item in results)


def test_suspicious_query_parameter_rule_detects_sensitive_keys(detection_db):
    with detection_db() as session:
        user = _make_user(session, "q@example.com")
        website = _make_website(session, user.id, "query.example.com")
        event = _make_event(
            session,
            website.id,
            event_id="query-1",
            path="/search",
            metadata={"page_url": "https://example.com/search?cmd=ls"},
        )
        results = DetectionEngine().evaluate(event)
        assert any(item.finding_type == "suspicious_query_parameter" for item in results)


def test_high_request_frequency_rule_triggers_over_threshold(detection_db):
    with detection_db() as session:
        user = _make_user(session, "freq@example.com")
        website = _make_website(session, user.id, "freq.example.com")
        now = datetime.now(timezone.utc)
        base = [
            _make_event(session, website.id, event_id=f"freq-{i}", session_id="freq-session", timestamp=now - timedelta(seconds=i), path=f"/page{i}")
            for i in range(1, 31)
        ]
        results = DetectionEngine().evaluate(base[-1], history=base)
        assert any(item.finding_type == "high_request_frequency" for item in results)


def test_repeated_authentication_failure_rule_triggers_after_threshold(detection_db):
    with detection_db() as session:
        user = _make_user(session, "auth@example.com")
        website = _make_website(session, user.id, "auth.example.com")
        now = datetime.now(timezone.utc)
        failures = [
            {
                "event_id": f"login-fail-{i}",
                "website_id": website.id,
                "event_type": "login_failed",
                "timestamp": (now - timedelta(seconds=10 * i)).isoformat(),
                "session_id": "auth-session",
                "status_code": 401,
                "endpoint": "/login",
                "metadata": {"page_url": "https://example.com/login"},
            }
            for i in range(5)
        ]
        event = failures[-1]
        results = DetectionEngine().evaluate(event, history=failures)
        assert any(item.finding_type == "repeated_authentication_failure" for item in results)


def test_detection_engine_deduplicates_same_event_and_rule(detection_db):
    with detection_db() as session:
        user = _make_user(session, "dedup@example.com")
        website = _make_website(session, user.id, "dedup.example.com")
        event = _make_event(session, website.id, event_id="dedup-1", path="/.git/config")
        engine = DetectionEngine()
        first = engine.evaluate(event)
        second = engine.evaluate(event)
        assert len(first) >= 1
        assert len(second) >= 1
        assert len(engine.deduplicate(first + second)) == len(first)


def test_detection_persistence_is_website_isolated(detection_db):
    with detection_db() as session:
        user_a = _make_user(session, "a@example.com")
        user_b = _make_user(session, "b@example.com")
        site_a = _make_website(session, user_a.id, "site-a.example.com")
        site_b = _make_website(session, user_b.id, "site-b.example.com")
        event_a = _make_event(session, site_a.id, event_id="site-a-1", path="/wp-admin")
        event_b = _make_event(session, site_b.id, event_id="site-b-1", path="/wp-admin")

        engine = DetectionEngine()
        engine.detect_event(event_a, session)
        engine.detect_event(event_b, session)

        findings_a = session.query(Finding).filter_by(website_id=site_a.id).all()
        findings_b = session.query(Finding).filter_by(website_id=site_b.id).all()
        assert any(item.finding_type == "suspicious_path" for item in findings_a)
        assert any(item.finding_type == "suspicious_path" for item in findings_b)


def test_detection_results_are_safe_and_structured(detection_db):
    with detection_db() as session:
        user = _make_user(session, "safe@example.com")
        website = _make_website(session, user.id, "safe.example.com")
        event = _make_event(
            session,
            website.id,
            event_id="safe-1",
            path="/admin",
            metadata={"page_url": "https://example.com/admin?token=secret", "page_path": "/admin"},
        )
        result = DetectionEngine().evaluate(event)[0]
        assert 0.0 <= result.confidence <= 1.0
        assert result.evidence
        assert "secret" not in str(result.evidence)
