from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.database import database


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
