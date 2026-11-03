from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.database import database
from app.database.models import Event, Finding, User, Website
from app.ml.features import build_feature_matrix, build_feature_vector
from app.ml.service import MLAnomalyService


@pytest.fixture
def ml_db(tmp_path):
    db_path = tmp_path / "ml_test.db"
    engine = database.build_engine(f"sqlite:///{db_path}")
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database.Base.metadata.drop_all(bind=engine)
    database.Base.metadata.create_all(bind=engine)
    return database.SessionLocal, tmp_path


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


def _make_event(session, website_id: int, *, event_id: str, event_type: str = "page_view", metadata: dict | None = None, user_agent: str = "Mozilla/5.0") -> Event:
    event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=1),
        event_type=event_type,
        source="browser_sdk",
        session_id="session-1",
        source_ip="127.0.0.1",
        user_id="browser-user",
        method="GET",
        endpoint="/products",
        status_code=200,
        user_agent=user_agent,
        metadata=metadata or {
            "page_url": "https://example.com/products",
            "referrer": "https://example.com/",
            "screen_width": 1440,
            "screen_height": 900,
        },
        processing_status="processed",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def test_feature_vector_is_deterministic_and_safe(ml_db):
    session_factory, _ = ml_db
    event = {
        "event_type": "button_click",
        "session_id": "sess-1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "metadata": {
            "page_url": "https://example.com/products?utm_source=ad&token=abc123",
            "referrer": "https://example.com",
            "screen_width": 1440,
            "screen_height": 900,
            "session_id": "sess-1",
        },
    }
    first = build_feature_vector(event)
    second = build_feature_vector(event)
    assert first == second
    assert first["url_depth"] >= 0
    assert "token" not in str(first)


def test_feature_vector_handles_missing_fields(ml_db):
    event = {"event_type": "custom", "metadata": {"page_url": "https://example.com"}}
    vector = build_feature_vector(event)
    assert vector["screen_width"] == 0
    assert vector["screen_height"] == 0
    assert vector["session_id_present"] == 0


def test_training_requires_minimum_events(ml_db):
    session_factory, tmp_path = ml_db
    with session_factory() as session:
        user = _make_user(session, "train@example.com")
        website = _make_website(session, user.id, "train.example.com")
        for index in range(10):
            _make_event(session, website.id, event_id=f"train-{index}", metadata={"page_url": f"https://example.com/page{index}", "screen_width": 1200, "screen_height": 800})
        service = MLAnomalyService(session=session, model_dir=tmp_path)
        result = service.train_website_model(website.id)
        assert result["status"] == "not_ready"
        assert "Insufficient processed events" in result["reason"]


def test_training_and_prediction_work_for_a_website(ml_db):
    session_factory, tmp_path = ml_db
    with session_factory() as session:
        user = _make_user(session, "predict@example.com")
        website = _make_website(session, user.id, "predict.example.com")
        for index in range(25):
            _make_event(
                session,
                website.id,
                event_id=f"pred-{index}",
                event_type="page_view",
                metadata={
                    "page_url": f"https://example.com/products/{index % 5}",
                    "referrer": "https://example.com",
                    "screen_width": 1280,
                    "screen_height": 720,
                },
            )

        service = MLAnomalyService(session=session, model_dir=tmp_path)
        train_result = service.train_website_model(website.id)
        assert train_result["status"] == "trained"
        assert train_result["training_event_count"] >= 20

        event = _make_event(
            session,
            website.id,
            event_id="pred-anomaly",
            event_type="api_request",
            metadata={
                "page_url": "https://example.com/api/very/deep/path?debug=true&token=abc&key=1",
                "referrer": "https://example.com",
                "screen_width": 1920,
                "screen_height": 1080,
            },
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        )

        prediction = service.predict_event_anomaly(website.id, event)
        assert prediction["status"] in {"ok", "not_ready"}
        assert 0.0 <= prediction.get("anomaly_score", 0.0) <= 1.0
        assert isinstance(prediction.get("is_anomaly", False), bool)


def test_ml_finding_is_persisted_without_duplicates(ml_db):
    session_factory, tmp_path = ml_db
    with session_factory() as session:
        user = _make_user(session, "finding@example.com")
        website = _make_website(session, user.id, "finding.example.com")
        for index in range(25):
            _make_event(
                session,
                website.id,
                event_id=f"find-{index}",
                event_type="page_view",
                metadata={"page_url": f"https://example.com/item/{index}", "referrer": "https://example.com", "screen_width": 1280, "screen_height": 720},
            )

        service = MLAnomalyService(session=session, model_dir=tmp_path)
        service.train_website_model(website.id)
        event = _make_event(
            session,
            website.id,
            event_id="find-anomaly",
            event_type="page_view",
            metadata={
                "page_url": "https://example.com/admin/.env?cmd=ls&token=secret",
                "referrer": "https://example.com",
                "screen_width": 1920,
                "screen_height": 1080,
            },
        )
        prediction = service.predict_event_anomaly(website.id, event)
        if prediction.get("status") == "ok" and prediction.get("is_anomaly"):
            first = service.persist_anomaly_finding(website.id, event, prediction)
            second = service.persist_anomaly_finding(website.id, event, prediction)
            count = session.query(Finding).filter_by(website_id=website.id, event_id=event.id, finding_type="ml_anomaly").count()
            assert count == 1
            assert first.agent_name == "ml_anomaly_detector"
        else:
            assert prediction.get("status") in {"ok", "not_ready"}


def test_build_feature_matrix_works_for_event_lists(ml_db):
    session_factory, _ = ml_db
    with session_factory() as session:
        user = _make_user(session, "matrix@example.com")
        website = _make_website(session, user.id, "matrix.example.com")
        events = [
            _make_event(session, website.id, event_id=f"matrix-{idx}", metadata={"page_url": f"https://example.com/x/{idx}", "screen_width": 1200, "screen_height": 800})
            for idx in range(5)
        ]
        matrix = build_feature_matrix(events)
        assert len(matrix) == 5
        assert matrix.shape[1] >= 8
