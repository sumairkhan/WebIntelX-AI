from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User, Website
from app.database.repositories import get_website_for_user
from app.ml.service import MLAnomalyService

router = APIRouter(prefix="/api", tags=["ml"])


@router.post("/websites/{website_id}/ml/train")
def train_website_ml_model(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Train the per-website Isolation Forest model using processed events."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )

    service = MLAnomalyService(session=db)
    return service.train_website_model(website_id)
