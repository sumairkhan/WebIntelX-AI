from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.database.repositories import get_website_for_user
from app.risk.service import RiskService

router = APIRouter(prefix="/api", tags=["risk"])


@router.post("/websites/{website_id}/risk/evaluate")
def evaluate_risk_endpoint(
    website_id: int,
    payload: dict[str, object],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return RiskService(db).evaluate(website_id, payload)
