from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.database.repositories import get_website_for_user
from app.threat_intel.schemas import ThreatIntelCheckRequest, ThreatIntelCheckResponse
from app.threat_intel.service import ThreatIntelService

router = APIRouter(prefix="/api", tags=["threat-intel"])


@router.post("/websites/{website_id}/threat-intelligence/check", response_model=ThreatIntelCheckResponse)
def check_indicator_endpoint(
    website_id: int,
    payload: ThreatIntelCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ThreatIntelCheckResponse:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    try:
        result = ThreatIntelService(db).check_indicator(website_id, payload.indicator, payload.indicator_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ThreatIntelCheckResponse(**result)
