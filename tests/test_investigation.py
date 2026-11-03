from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Correlation, Event, Finding, User, Website
from app.investigation.context import build_investigation_context
from app.investigation.service import InvestigationService


@pytest.fixture
def investigation_db(tmp_path):
    db_path = tmp_path / "investigation_test.db"
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
    site = Website(user_id=user_id, name=f"Site {domain}", domain=domain)
    session.add(site)
    session.commit()
    session.refresh(site)
    return site


def _make_event(session, website_id: int, *, event_id: str, session_id: str, timestamp: datetime, metadata: dict | None = None, event_type: str = "page_view") -> Event:
    event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        source="browser_sdk",
        source_ip="127.0.0.1",
        session_id=session_id,
        user_id="browser-user",
        method="GET",
        endpoint="/login",
        status_code=401,
        user_agent="Mozilla/5.0",
        metadata=metadata or {"page_url": "https://example.com/login"},
        processing_status="processed",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def _make_finding(session, website_id: int, event_id: int, *, finding_type: str, agent_name: str = "detection_engine", confidence: float = 0.8) -> Finding:
    finding = Finding(
        website_id=website_id,
        event_id=event_id,
        agent_name=agent_name,
        finding_type=finding_type,
        confidence=confidence,
        evidence={"reason": "test"},
    )
    session.add(finding)
    session.commit()
    session.refresh(finding)
    return finding


def _make_correlation(session, website_id: int, event_id: int, related_event_id: int, *, relationship_type: str = "same_session") -> Correlation:
    correlation = Correlation(
        incident_id=None,
        event_id=event_id,
        related_event_id=related_event_id,
        relationship_type=relationship_type,
        strength=0.8,
    )
    session.add(correlation)
    session.commit()
    session.refresh(correlation)
    return correlation


def test_investigation_context_filters_by_website_and_sanitizes_sensitive_fields(investigation_db):
    with investigation_db() as session:
        user = _make_user(session, "ctx@example.com")
        site = _make_website(session, user.id, "ctx.example.com")
        other_site = _make_website(session, user.id, "other.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site.id, event_id="evt-1", session_id="s-1", timestamp=now)
        event_b = _make_event(session, site.id, event_id="evt-2", session_id="s-1", timestamp=now + timedelta(seconds=5), metadata={"page_url": "https://example.com/login?token=abc123"})
        _make_event(session, other_site.id, event_id="evt-3", session_id="s-2", timestamp=now)
        _make_finding(session, site.id, event_a.id, finding_type="suspicious_path")
        _make_finding(session, other_site.id, event_b.id, finding_type="suspicious_path")
        corr = _make_correlation(session, site.id, event_a.id, event_b.id, relationship_type="same_session")

        context = build_investigation_context(session, website_id=site.id, correlation_id=corr.id, max_events=10, max_findings=10, max_correlations=10)

        assert all(item["website_id"] == site.id for item in context["events"])
        assert all(item["website_id"] == site.id for item in context["findings"])
        assert context["correlations"][0]["relationship_type"] == "same_session"
        assert "abc123" not in str(context)


def test_start_investigation_creates_record_and_separates_fact_from_inference(investigation_db):
    with investigation_db() as session:
        user = _make_user(session, "owner@example.com")
        site = _make_website(session, user.id, "owner.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site.id, event_id="owner-1", session_id="s-9", timestamp=now)
        event_b = _make_event(session, site.id, event_id="owner-2", session_id="s-9", timestamp=now + timedelta(seconds=10), event_type="api_request")
        _make_finding(session, site.id, event_a.id, finding_type="suspicious_path")
        _make_finding(session, site.id, event_b.id, finding_type="ml_anomaly", agent_name="ml_anomaly_detector")
        corr = _make_correlation(session, site.id, event_a.id, event_b.id, relationship_type="rule_plus_ml")

        service = InvestigationService(session)
        result = service.start_investigation(user=user, website_id=site.id, correlation_id=corr.id)

        assert result["status"] in {"completed", "failed"}
        assert "facts" in result
        assert "inferences" in result
        assert result["confidence"] >= 0.0
        assert result["confidence"] <= 1.0


def test_unauthorized_website_investigation_is_rejected(investigation_db):
    with investigation_db() as session:
        owner = _make_user(session, "owner2@example.com")
        other_owner = _make_user(session, "other2@example.com")
        site = _make_website(session, owner.id, "secure.example.com")
        now = datetime.now(timezone.utc)
        event_a = _make_event(session, site.id, event_id="sec-1", session_id="s-1", timestamp=now)
        event_b = _make_event(session, site.id, event_id="sec-2", session_id="s-1", timestamp=now + timedelta(seconds=4))
        corr = _make_correlation(session, site.id, event_a.id, event_b.id, relationship_type="same_session")

        service = InvestigationService(session)
        with pytest.raises(PermissionError):
            service.start_investigation(user=other_owner, website_id=site.id, correlation_id=corr.id)


def test_invalid_evidence_reference_is_rejected(investigation_db):
    with investigation_db() as session:
        user = _make_user(session, "invalid@example.com")
        site = _make_website(session, user.id, "invalid.example.com")
        now = datetime.now(timezone.utc)
        event = _make_event(session, site.id, event_id="inv-1", session_id="s-1", timestamp=now)
        _make_correlation(session, site.id, event.id, event.id, relationship_type="same_session")

        service = InvestigationService(session)
        result = service.validate_output(
            {
                "summary": "X",
                "facts": [{"title": "Bad fact", "description": "desc", "classification": "fact", "confidence": 0.9, "evidence_references": [{"type": "event", "id": 999999}]}],
                "inferences": [],
                "uncertainties": [],
                "confidence": 0.7,
            },
            website_id=site.id,
        )

        assert result["status"] == "invalid"
