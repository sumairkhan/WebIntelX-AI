from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.processing.processor import process_pending_events

router = APIRouter(prefix="/api", tags=["processing"])


@router.post("/processing/run")
def run_processing(limit: int = 100, db: Session = Depends(get_db)) -> dict[str, int]:
    """Process pending events without implementing detection logic."""
    return process_pending_events(db, limit=limit)
