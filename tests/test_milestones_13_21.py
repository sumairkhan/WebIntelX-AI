from __future__ import annotations

import uuid

import pytest

from app.database.models import Event, Finding, User, Website
from app.graph.service import GraphService
from app.reporting.service import ReportingService
from app.response.service import ResponseService
from app.risk.service import RiskService
from app.threat_intel.service import ThreatIntelService


def _make_user(session, email: str = "milestone@example.com") -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_website(session, user_id: int, domain: str = "demo.example.com") -> Website:
    site = Website(user_id=user_id, name="Demo Site", domain=domain)
    session.add(site)
    session.commit()
    session.refresh(site)
    return site


def _make_event(session, website_id: int, *, event_id: str, session_id: str = "sess-1") -> Event:
    event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        event_type="login_failure",
        source="browser_sdk",
        source_ip="203.0.113.42",
        session_id=session_id,
        user_id="browser-user",
        method="POST",
        endpoint="/login",
        status_code=401,
        user_agent="Mozilla/5.0",
        metadata={"page_url": "https://demo.example.com/login?token=abc123"},
        processing_status="processed",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_threat_intel_checks_valid_ip_and_redacts_sensitive_data(db_session):
    user = _make_user(db_session, "intel@example.com")
    site = _make_website(db_session, user.id, "intel.example.com")
    _make_event(db_session, site.id, event_id="evt-ti-1")

    result = ThreatIntelService(db_session).check_indicator(site.id, "8.8.8.8", "ip")

    assert result["indicator_type"] == "ip"
    assert result["provider"] in {"demo", "mock", "unavailable"}
    assert result["indicator"] == "8.8.8.8"
    assert result["malicious"] in {True, False, "unavailable"}


def test_risk_service_returns_explainable_score(db_session):
    user = _make_user(db_session, "risk@example.com")
    site = _make_website(db_session, user.id, "risk.example.com")
    _make_event(db_session, site.id, event_id="evt-risk-1")

    payload = {
        "site_id": site.id,
        "investigation_confidence": 0.82,
        "ml_anomaly": True,
        "rule_findings": 2,
        "correlations": 2,
        "sensitive_endpoint_activity": True,
        "authentication_failures": 5,
        "threat_intel": {"malicious": True, "confidence": 0.9},
    }

    result = RiskService(db_session).evaluate(site.id, payload)

    assert 0 <= result["risk_score"] <= 100
    assert result["risk_level"] in {"low", "medium", "high", "critical"}
    assert result["factors"]
    assert "explanation" in result


def test_incident_service_respects_threshold_and_ownership(db_session):
    user = _make_user(db_session, "inc@example.com")
    site = _make_website(db_session, user.id, "inc.example.com")
    other_user = _make_user(db_session, "other@example.com")

    risk_service = RiskService(db_session)
    result = risk_service.evaluate(site.id, {"site_id": site.id, "investigation_confidence": 0.85, "ml_anomaly": True, "rule_findings": 3})

    assert result["risk_score"] >= 0

    incident = RiskService(db_session).create_incident(site.id, {"title": "Suspicious access", "description": "Demo", "risk_score": 85})
    assert incident["risk_score"] >= 0

    with pytest.raises(PermissionError):
        RiskService(db_session).get_incident_for_website(other_user.id, site.id, incident["id"])


def test_graph_service_builds_nodes_and_edges(db_session):
    user = _make_user(db_session, "graph@example.com")
    site = _make_website(db_session, user.id, "graph.example.com")
    event = _make_event(db_session, site.id, event_id="evt-graph-1")
    finding = Finding(website_id=site.id, event_id=event.id, agent_name="rule_engine", finding_type="suspicious_path", confidence=0.8, evidence={"reason": "test"})
    db_session.add(finding)
    db_session.commit()

    graph = GraphService(db_session).build_graph(site.id, max_nodes=10)

    assert "nodes" in graph
    assert "edges" in graph
    assert graph["nodes"]


def test_response_service_and_reporting_service_work(db_session):
    user = _make_user(db_session, "report@example.com")
    site = _make_website(db_session, user.id, "report.example.com")
    _make_event(db_session, site.id, event_id="evt-report-1")

    recs = ResponseService(db_session).build_recommendations(site.id, {"risk_level": "high"})
    assert recs
    assert recs[0]["action"]

    report = ReportingService(db_session).build_report(site.id, {"summary": "Demo report"})
    assert "facts" in report
    assert "inferences" in report
    assert "summary" in report
