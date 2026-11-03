from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from app.auth.security import create_access_token
from app.auth.service import authenticate_user, register_user
from app.database.database import get_db
from app.database.models import User

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=UserResponse)
def register_user_endpoint(
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> User:
    """Register a new user account using a hashed password."""
    try:
        user = register_user(db, payload.email, payload.password)
    except ValueError as exc:
        detail = str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    return user


@router.post("/auth/login", response_model=TokenResponse)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a bearer token."""
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/auth/me", response_model=UserResponse)
def get_current_user_endpoint(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user profile for the current JWT identity."""
    return current_user
