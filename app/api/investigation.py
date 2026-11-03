from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.database.repositories import get_investigation_for_website, get_website_for_user, list_investigations_for_website
from app.investigation.models import Investigation
from app.investigation.schemas import InvestigationCreate, InvestigationResponse
from app.investigation.service import InvestigationService

router = APIRouter(prefix="/api", tags=["investigations"])


@router.get("/websites/{website_id}/investigations", response_model=list[InvestigationResponse])
def list_investigations_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvestigationResponse]:
    if get_website_for_user(db, user_id=current_user.id, website_id=website_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return [
        InvestigationResponse(
            id=item.id,
            website_id=item.website_id,
            correlation_id=item.correlation_id,
            investigation_id=item.investigation_id,
            title=item.title,
            status=item.status,
            summary=item.summary,
            confidence=item.confidence,
            facts=[],
            inferences=[],
            uncertainties=[],
            created_at=item.created_at.isoformat() if item.created_at else None,
            completed_at=item.completed_at.isoformat() if item.completed_at else None,
        )
        for item in list_investigations_for_website(db, website_id=website_id)
    ]


@router.post("/websites/{website_id}/investigations", response_model=InvestigationResponse)
def create_investigation_endpoint(
    website_id: int,
    payload: InvestigationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    if get_website_for_user(db, user_id=current_user.id, website_id=website_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    service = InvestigationService(db)
    try:
        result = service.start_investigation(user=current_user, website_id=website_id, correlation_id=payload.correlation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Investigation engine is not configured.") from exc

    return InvestigationResponse(
        id=result["id"],
        website_id=result["website_id"],
        correlation_id=result.get("correlation_id"),
        investigation_id=result["investigation_id"],
        title=f"Investigation for correlation {result.get('correlation_id')}",
        status=result["status"],
        summary=result.get("summary"),
        confidence=result.get("confidence", 0.0),
        facts=result.get("facts", []),
        inferences=result.get("inferences", []),
        uncertainties=result.get("uncertainties", []),
        created_at=result.get("created_at"),
        completed_at=result.get("completed_at"),
    )


@router.get("/websites/{website_id}/investigations/{investigation_id}", response_model=InvestigationResponse)
def get_investigation_endpoint(
    website_id: int,
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    if get_website_for_user(db, user_id=current_user.id, website_id=website_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    investigation = get_investigation_for_website(db, website_id=website_id, investigation_id=investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found.")

    return InvestigationResponse(
        id=investigation.id,
        website_id=investigation.website_id,
        correlation_id=investigation.correlation_id,
        investigation_id=investigation.investigation_id,
        title=investigation.title,
        status=investigation.status,
        summary=investigation.summary,
        confidence=investigation.confidence,
        facts=[],
        inferences=[],
        uncertainties=[],
        created_at=investigation.created_at.isoformat() if investigation.created_at else None,
        completed_at=investigation.completed_at.isoformat() if investigation.completed_at else None,
    )
