from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import Incident, User
from app.database.repositories import create_incident, get_website_for_user
from app.risk.service import RiskService

router = APIRouter(prefix="/api", tags=["incidents"])


class IncidentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user: User, website_id: int, payload: dict[str, object]) -> dict[str, object]:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        score = float(payload.get("risk_score", 0.0) or 0.0)
        incident = create_incident(
            self.session,
            website_id=website_id,
            incident_id=f"inc-{abs(hash(str(payload.get('title', 'incident')))) % 1000000}",
            title=str(payload.get("title") or "New suspicious activity"),
            risk_level=str(payload.get("risk_level") or "medium"),
            risk_score=max(0.0, min(100.0, score)) / 100.0,
            confidence=float(payload.get("confidence", 0.5) or 0.5),
            status=str(payload.get("status") or "open"),
        )
        return {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "website_id": incident.website_id,
            "title": incident.title,
            "risk_level": incident.risk_level,
            "risk_score": round(float(incident.risk_score) * 100.0, 2),
            "confidence": incident.confidence,
            "status": incident.status,
        }

    def list_for_website(self, user: User, website_id: int) -> list[dict[str, object]]:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        incidents = self.session.query(Incident).filter(Incident.website_id == website_id).order_by(Incident.created_at.desc()).all()
        return [
            {
                "id": incident.id,
                "incident_id": incident.incident_id,
                "website_id": incident.website_id,
                "title": incident.title,
                "risk_level": incident.risk_level,
                "risk_score": round(float(incident.risk_score) * 100.0, 2),
                "confidence": incident.confidence,
                "status": incident.status,
            }
            for incident in incidents
        ]

    def get(self, user: User, website_id: int, incident_id: int) -> dict[str, object]:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        incident = self.session.get(Incident, incident_id)
        if incident is None or incident.website_id != website_id:
            raise ValueError("Incident not found.")
        return {
            "id": incident.id,
            "incident_id": incident.incident_id,
            "website_id": incident.website_id,
            "title": incident.title,
            "risk_level": incident.risk_level,
            "risk_score": round(float(incident.risk_score) * 100.0, 2),
            "confidence": incident.confidence,
            "status": incident.status,
        }

    def update(self, user: User, website_id: int, incident_id: int, payload: dict[str, object]) -> dict[str, object]:
        website = get_website_for_user(self.session, user_id=user.id, website_id=website_id)
        if website is None:
            raise PermissionError("Website not found or not owned by the current user.")
        incident = self.session.get(Incident, incident_id)
        if incident is None or incident.website_id != website_id:
            raise ValueError("Incident not found.")
        if "status" in payload:
            status_value = str(payload["status"]).lower()
            if status_value not in {"open", "investigating", "resolved", "dismissed"}:
                raise ValueError("Invalid incident status.")
            incident.status = status_value
        if "title" in payload and payload["title"]:
            incident.title = str(payload["title"])
        if "risk_level" in payload and payload["risk_level"]:
            incident.risk_level = str(payload["risk_level"])
        self.session.add(incident)
        self.session.commit()
        self.session.refresh(incident)
        return self.get(user, website_id, incident.id)


@router.post("/websites/{website_id}/incidents")
def create_incident_endpoint(
    website_id: int,
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = IncidentService(db)
    try:
        return service.create(current_user, website_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/websites/{website_id}/incidents")
def list_incidents_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    service = IncidentService(db)
    try:
        return service.list_for_website(current_user, website_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/websites/{website_id}/incidents/{incident_id}")
def get_incident_endpoint(
    website_id: int,
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = IncidentService(db)
    try:
        return service.get(current_user, website_id, incident_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/websites/{website_id}/incidents/{incident_id}")
def update_incident_endpoint(
    website_id: int,
    incident_id: int,
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = IncidentService(db)
    try:
        return service.update(current_user, website_id, incident_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
