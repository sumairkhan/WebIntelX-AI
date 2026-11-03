from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import Feedback, Incident, User
from app.database.repositories import create_feedback, get_website_for_user
from app.response.service import ResponseService

router = APIRouter(prefix="/api", tags=["response"])


@router.get("/websites/{website_id}/incidents/{incident_id}/recommendations")
def get_recommendations_endpoint(
    website_id: int,
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    incident = db.get(Incident, incident_id)
    if incident is None or incident.website_id != website_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    return ResponseService(db).build_recommendations(website_id, {"risk_level": incident.risk_level, "evidence": [incident.title]})


@router.post("/websites/{website_id}/incidents/{incident_id}/feedback")
def create_feedback_endpoint(
    website_id: int,
    incident_id: int,
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    incident = db.get(Incident, incident_id)
    if incident is None or incident.website_id != website_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    decision = str(payload.get("analyst_decision") or "needs_review").lower()
    if decision not in {"confirmed", "false_positive", "needs_review"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid analyst decision.")
    feedback = create_feedback(
        db,
        incident_id=incident.id,
        analyst_decision=decision,
        comment=str(payload.get("comment") or ""),
    )
    return {"id": feedback.id, "incident_id": feedback.incident_id, "analyst_decision": feedback.analyst_decision, "comment": feedback.comment}


@router.get("/websites/{website_id}/incidents/{incident_id}/feedback")
def list_feedback_endpoint(
    website_id: int,
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    incident = db.get(Incident, incident_id)
    if incident is None or incident.website_id != website_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    feedback_rows = db.query(Feedback).filter(Feedback.incident_id == incident.id).order_by(Feedback.created_at.desc()).all()
    return [{"id": item.id, "incident_id": item.incident_id, "analyst_decision": item.analyst_decision, "comment": item.comment} for item in feedback_rows]
