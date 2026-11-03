from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.security import hash_password, validate_password, verify_password
from app.database.models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email address, case-insensitive for the normal flow."""
    normalized_email = email.strip().lower()
    return db.query(User).filter(User.email == normalized_email).first()


def register_user(db: Session, email: str, password: str) -> User:
    """Create a new user record with a hashed password."""
    normalized_email = email.strip().lower()
    validate_password(password)

    if get_user_by_email(db, normalized_email):
        raise ValueError("Email already registered.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password using the stored hash."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
