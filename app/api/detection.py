from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Event
from app.detection.engine import DetectionEngine

router = APIRouter(prefix="/api", tags=["detection"])


@router.post("/internal/detection/run")
def run_internal_detection(
    payload: dict[str, Any] | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run deterministic detection rules against one event or a list of events."""
    engine = DetectionEngine()
    body = payload or {}

    if "event_id" in body:
        event = db.query(Event).filter_by(event_id=str(body["event_id"])).first()
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        result = engine.detect_event(event, db)
        return {"processed": len(result), "results": [item.as_dict() for item in result]}

    if "events" in body and isinstance(body["events"], list):
        results = engine.detect_events(body["events"], db)
        return {"processed": len(results), "results": [item.as_dict() for item in results]}

    return {"processed": 0, "results": []}
