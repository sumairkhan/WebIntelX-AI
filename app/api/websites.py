from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from datetime import datetime, timezone

from app.database.models import Finding, User, Website
from app.database.repositories import (
    create_website,
    deactivate_website,
    count_events_for_website,
    count_findings_for_website,
    get_active_credential_for_website,
    get_latest_ingested_event,
    get_website_for_user,
    has_active_credential_for_website,
    list_events_for_website,
    list_websites_for_user,
    normalize_domain,
    update_website,
)
from app.schemas.database import EventResponse, FindingResponse, WebsiteCreate, WebsiteResponse, WebsiteTelemetryResponse, WebsiteUpdate

router = APIRouter(prefix="/api", tags=["websites"])


@router.post("/websites", response_model=WebsiteResponse)
def create_website_endpoint(
    payload: WebsiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Website:
    """Create a website owned by the authenticated user."""
    try:
        website = create_website(
            db,
            user_id=current_user.id,
            name=payload.name,
            domain=payload.domain,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A website with that domain already exists for this user.",
        ) from exc

    return website


@router.get("/websites", response_model=list[WebsiteResponse])
def list_websites_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Website]:
    """Return only websites belonging to the authenticated user."""
    return list_websites_for_user(db, current_user.id)


@router.get("/websites/{website_id}", response_model=WebsiteResponse)
def get_website_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Website:
    """Return one website if it belongs to the authenticated user."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )
    return website


@router.get("/websites/{website_id}/events", response_model=list[EventResponse])
def list_website_events_endpoint(
    website_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return list_events_for_website(db, website_id=website_id, limit=limit)


@router.get("/websites/{website_id}/telemetry", response_model=WebsiteTelemetryResponse)
def website_telemetry_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebsiteTelemetryResponse:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    active_credential_record = get_active_credential_for_website(db, website_id=website_id)
    active_credential = active_credential_record is not None
    latest_event = (
        get_latest_ingested_event(
            db,
            website_id=website_id,
            credential_id=active_credential_record.id,
        )
        if active_credential_record is not None
        else None
    )
    telemetry_received = False
    if latest_event is not None:
        created_at = latest_event.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        telemetry_received = 0 <= age_seconds <= 5 * 60
    connected = website.status == "active" and active_credential and telemetry_received
    return WebsiteTelemetryResponse(
        event_count=count_events_for_website(db, website_id=website_id),
        finding_count=count_findings_for_website(db, website_id=website_id),
        active_credential=active_credential,
        connected=connected,
        sdk_detected=telemetry_received,
        telemetry_received=telemetry_received,
        ingestion_working=connected,
        last_event=latest_event,
    )


@router.get("/websites/{website_id}/findings", response_model=list[FindingResponse])
def list_website_findings_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Finding]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return db.execute(
        select(Finding).where(Finding.website_id == website_id).order_by(Finding.created_at.desc())
    ).scalars().all()


@router.patch("/websites/{website_id}", response_model=WebsiteResponse)
def update_website_endpoint(
    website_id: int,
    payload: WebsiteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Website:
    """Update a website only when it belongs to the authenticated user."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )

    try:
        updated = update_website(
            db,
            website,
            name=payload.name,
            domain=payload.domain,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return updated


@router.delete("/websites/{website_id}", response_model=WebsiteResponse)
def deactivate_website_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Website:
    """Deactivate a website without deleting the database record."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )

    return deactivate_website(db, website)
