from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_ingestion_credential() -> str:
    """Create a secure, website-scoped ingestion credential."""
    return "wix_ing_" + secrets.token_urlsafe(32)


def hash_ingestion_credential(raw_credential: str) -> str:
    """Hash a raw credential for storage in the database."""
    return hashlib.sha256(raw_credential.encode("utf-8")).hexdigest()


def verify_ingestion_credential(raw_credential: str, stored_hash: str) -> bool:
    """Verify the raw credential matches the stored hash without timing leaks."""
    return hmac.compare_digest(hash_ingestion_credential(raw_credential), stored_hash)
