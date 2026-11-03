from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.database import get_db
from app.schemas.ingestion import IngestionRequest, IngestionResponse
from app.services.ingestion_service import ingestion_rate_limiter, process_event_batch, resolve_active_credential

router = APIRouter(prefix="/api", tags=["ingestion"])


@router.post("/ingest/events", response_model=IngestionResponse)
def ingest_events(
    payload: IngestionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> IngestionResponse:
    """Validate and store SDK event batches for the website associated with the ingestion credential."""
    if len(payload.events) > settings.ingestion_max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Batch too large.",
        )

    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{payload.credential}"
    if not ingestion_rate_limiter.allow(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many ingestion requests.",
        )

    try:
        credential = resolve_active_credential(db, payload.credential)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ingestion credential",
        ) from exc
    website = credential.website

    origin = request.headers.get("origin")
    if origin:
        from app.database.repositories import normalize_website_address

        try:
            request_origin = normalize_website_address(origin)[1]
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin is not registered for this ingestion credential.",
            ) from exc
        if website.origin != request_origin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin is not registered for this ingestion credential.",
            )

    accepted_count, duplicates_count, _ = process_event_batch(
        db,
        website_id=website.id,
        events=payload.events,
        credential_id=credential.id,
    )

    return IngestionResponse(
        success=True,
        accepted=accepted_count,
        duplicates=duplicates_count,
        rejected=0,
    )
