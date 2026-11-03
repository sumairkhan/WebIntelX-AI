from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import IngestionCredential, User
from app.database.repositories import (
    create_ingestion_credential,
    get_ingestion_credential,
    get_website_for_user,
    list_ingestion_credentials,
    revoke_ingestion_credential,
    rotate_ingestion_credential,
)
from app.schemas.credential import CredentialCreateResponse, CredentialResponse
from app.services.credentials import generate_ingestion_credential

router = APIRouter(prefix="/api", tags=["credentials"])


@router.post("/websites/{website_id}/credentials", response_model=CredentialCreateResponse)
def create_credential(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CredentialCreateResponse:
    """Create a new website-scoped ingestion credential for the authenticated user."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    if website.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot create credentials for an inactive website.")

    raw_credential = generate_ingestion_credential()
    credential = create_ingestion_credential(db, website_id=website_id, raw_credential=raw_credential)

    return CredentialCreateResponse(
        id=credential.id,
        website_id=credential.website_id,
        credential=raw_credential,
        status=credential.status,
        created_at=credential.created_at,
    )


@router.get("/websites/{website_id}/credentials", response_model=list[CredentialResponse])
def list_credentials(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IngestionCredential]:
    """Return credential metadata for a website owned by the authenticated user."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    return list_ingestion_credentials(db, website_id=website_id)


@router.get(
    "/websites/{website_id}/credentials/{credential_id}",
    response_model=CredentialResponse,
)
def get_credential(
    website_id: int,
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestionCredential:
    """Return credential metadata for a website-owned credential."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    credential = get_ingestion_credential(db, website_id=website_id, credential_id=credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found.")

    return credential


@router.post(
    "/websites/{website_id}/credentials/{credential_id}/rotate",
    response_model=CredentialCreateResponse,
)
def rotate_credential(
    website_id: int,
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CredentialCreateResponse:
    """Rotate a credential while preserving the old record as revoked history."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    if website.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot rotate credentials for an inactive website.")

    credential = get_ingestion_credential(db, website_id=website_id, credential_id=credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found.")

    new_raw_credential = generate_ingestion_credential()
    rotated_credential = rotate_ingestion_credential(
        db,
        website_id=website_id,
        credential=credential,
        new_raw_credential=new_raw_credential,
    )

    return CredentialCreateResponse(
        id=rotated_credential.id,
        website_id=rotated_credential.website_id,
        credential=new_raw_credential,
        status=rotated_credential.status,
        created_at=rotated_credential.created_at,
    )


@router.post(
    "/websites/{website_id}/credentials/{credential_id}/revoke",
    response_model=CredentialResponse,
)
def revoke_credential(
    website_id: int,
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestionCredential:
    """Revoke an existing website credential without deleting the record."""
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    credential = get_ingestion_credential(db, website_id=website_id, credential_id=credential_id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found.")

    return revoke_ingestion_credential(db, credential)
