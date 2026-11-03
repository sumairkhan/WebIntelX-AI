from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import (
    Correlation,
    Event,
    Feedback,
    Finding,
    Incident,
    IngestionCredential,
    User,
    Website,
)
from app.investigation.models import Investigation, InvestigationEvidence


def normalize_website_address(address: str) -> tuple[str, str]:
    """Return a normalized host[:port] and exact HTTP(S) origin."""
    value = (address or "").strip()
    if not value:
        raise ValueError("Website URL or domain is required.")

    if "://" not in value:
        candidate = urlsplit(f"//{value.lstrip('/')}")
        host = (candidate.hostname or "").lower().rstrip(".")
        try:
            is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = host == "localhost"
        value = f"{'http' if is_loopback else 'https'}://{value.lstrip('/')}"

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Enter a valid website URL or domain.") from exc

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Website URL must use HTTP or HTTPS and include a valid host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Website URL must not contain a username or password.")

    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Enter a valid website URL or domain.") from exc
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        labels = hostname.split(".")
        if any(
            not label
            or len(label) > 63
            or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
            for label in labels
        ):
            raise ValueError("Enter a valid website URL or domain.")

    scheme = parsed.scheme.lower()
    default_port = 80 if scheme == "http" else 443
    include_port = port is not None and port != default_port
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = f"{display_host}:{port}" if include_port else display_host
    return netloc, f"{scheme}://{netloc}"


def normalize_domain(domain: str) -> str:
    """Normalize a website address to its host and optional non-default port."""
    return normalize_website_address(domain)[0]


def create_website(
    session: Session,
    *,
    user_id: int,
    name: str,
    domain: str,
    status: str = "active",
) -> Website:
    normalized_domain, origin = normalize_website_address(domain)
    existing = session.execute(
        select(Website).where(Website.user_id == user_id, Website.domain == normalized_domain)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("A website with that domain already exists for this user.")

    website = Website(
        user_id=user_id,
        name=name.strip(),
        domain=normalized_domain,
        origin=origin,
        status=status,
    )
    session.add(website)
    session.commit()
    session.refresh(website)
    return website


def get_website_by_id(session: Session, website_id: int) -> Website | None:
    return session.get(Website, website_id)


def get_website_for_user(session: Session, *, user_id: int, website_id: int) -> Website | None:
    return session.execute(
        select(Website).where(Website.user_id == user_id, Website.id == website_id)
    ).scalar_one_or_none()


def list_websites_for_user(session: Session, user_id: int) -> list[Website]:
    return session.execute(select(Website).where(Website.user_id == user_id)).scalars().all()


def update_website(
    session: Session,
    website: Website,
    *,
    name: str | None = None,
    domain: str | None = None,
    status: str | None = None,
) -> Website:
    if name is not None:
        website.name = name.strip()

    if domain is not None:
        normalized_domain, origin = normalize_website_address(domain)
        duplicate = session.execute(
            select(Website).where(
                Website.user_id == website.user_id,
                Website.domain == normalized_domain,
                Website.id != website.id,
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise ValueError("A website with that domain already exists for this user.")
        website.domain = normalized_domain
        website.origin = origin

    if status is not None:
        website.status = status.strip().lower() or "active"

    session.add(website)
    session.commit()
    session.refresh(website)
    return website


def deactivate_website(session: Session, website: Website) -> Website:
    now = datetime.now(timezone.utc)
    website.status = "inactive"
    session.add(website)
    active_credentials = session.execute(
        select(IngestionCredential).where(
            IngestionCredential.website_id == website.id,
            IngestionCredential.status == "active",
        )
    ).scalars().all()
    for credential in active_credentials:
        credential.status = "revoked"
        credential.revoked_at = now
        session.add(credential)
    session.commit()
    session.refresh(website)
    return website


def list_events_for_website(session: Session, *, website_id: int, limit: int = 100) -> list[Event]:
    return session.execute(
        select(Event)
        .where(Event.website_id == website_id)
        .order_by(Event.timestamp.desc(), Event.id.desc())
        .limit(max(1, min(limit, 500)))
    ).scalars().all()


def get_latest_ingested_event(
    session: Session,
    *,
    website_id: int,
    credential_id: int,
) -> Event | None:
    return session.execute(
        select(Event)
        .where(
            Event.website_id == website_id,
            Event.ingestion_credential_id == credential_id,
        )
        .order_by(Event.created_at.desc(), Event.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def count_events_for_website(session: Session, *, website_id: int) -> int:
    return session.execute(
        select(func.count(Event.id)).where(Event.website_id == website_id)
    ).scalar_one()


def count_findings_for_website(session: Session, *, website_id: int) -> int:
    return session.execute(
        select(func.count(Finding.id)).where(Finding.website_id == website_id)
    ).scalar_one()


def has_active_credential_for_website(session: Session, *, website_id: int) -> bool:
    return get_active_credential_for_website(session, website_id=website_id) is not None


def get_active_credential_for_website(
    session: Session,
    *,
    website_id: int,
) -> IngestionCredential | None:
    return session.execute(
        select(IngestionCredential).where(
            IngestionCredential.website_id == website_id,
            IngestionCredential.status == "active",
        ).order_by(IngestionCredential.created_at.desc(), IngestionCredential.id.desc()).limit(1)
    ).scalar_one_or_none()


def create_ingestion_credential(
    session: Session,
    *,
    website_id: int,
    raw_credential: str,
    status: str = "active",
) -> IngestionCredential:
    from app.services.credentials import hash_ingestion_credential

    now = datetime.now(timezone.utc)
    active_credentials = session.execute(
        select(IngestionCredential).where(
            IngestionCredential.website_id == website_id,
            IngestionCredential.status == "active",
        )
    ).scalars().all()
    for existing in active_credentials:
        existing.status = "revoked"
        existing.revoked_at = now
        session.add(existing)

    credential = IngestionCredential(
        website_id=website_id,
        credential_hash=hash_ingestion_credential(raw_credential),
        status=status,
        rotated_at=None,
        revoked_at=None,
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)
    return credential


def list_ingestion_credentials(session: Session, *, website_id: int) -> list[IngestionCredential]:
    return session.execute(
        select(IngestionCredential)
        .where(IngestionCredential.website_id == website_id)
        .order_by(IngestionCredential.created_at.desc())
    ).scalars().all()


def get_ingestion_credential(
    session: Session,
    *,
    website_id: int,
    credential_id: int,
) -> IngestionCredential | None:
    return session.execute(
        select(IngestionCredential).where(
            IngestionCredential.website_id == website_id,
            IngestionCredential.id == credential_id,
        )
    ).scalar_one_or_none()


def get_active_credential_by_hash(
    session: Session,
    *,
    credential_hash: str,
) -> IngestionCredential | None:
    return session.execute(
        select(IngestionCredential).where(
            IngestionCredential.credential_hash == credential_hash,
            IngestionCredential.status == "active",
        )
    ).scalar_one_or_none()


def revoke_ingestion_credential(
    session: Session,
    credential: IngestionCredential,
) -> IngestionCredential:
    if credential.status != "revoked":
        credential.status = "revoked"
        credential.revoked_at = datetime.now(timezone.utc)
        session.add(credential)
        session.commit()
        session.refresh(credential)
    return credential


def rotate_ingestion_credential(
    session: Session,
    *,
    website_id: int,
    credential: IngestionCredential,
    new_raw_credential: str,
) -> IngestionCredential:
    now = datetime.now(timezone.utc)
    credential.status = "revoked"
    credential.revoked_at = now
    session.add(credential)

    new_credential = create_ingestion_credential(
        session,
        website_id=website_id,
        raw_credential=new_raw_credential,
        status="active",
    )
    new_credential.rotated_at = now
    session.add(new_credential)
    session.commit()
    session.refresh(new_credential)
    return new_credential


def create_event(
    session: Session,
    *,
    website_id: int,
    event_id: str,
    timestamp,
    event_type: str,
    source: str,
    source_ip: str | None,
    session_id: str | None,
    user_id: str | None,
    method: str | None,
    endpoint: str | None,
    status_code: int | None,
    user_agent: str | None,
    metadata: dict | None = None,
) -> Event:
    new_event = Event(
        website_id=website_id,
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        source=source,
        source_ip=source_ip,
        session_id=session_id,
        user_id=user_id,
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        user_agent=user_agent,
        metadata=metadata,
    )
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    return new_event


def create_events(session: Session, *, website_id: int, events: list[Event]) -> list[Event]:
    if not events:
        return []

    for event in events:
        event.website_id = website_id

    session.add_all(events)
    session.commit()
    for event in events:
        session.refresh(event)
    return events


def get_event(session: Session, event_id: str) -> Event | None:
    return session.execute(select(Event).where(Event.event_id == event_id)).scalar_one_or_none()


def get_event_by_event_id(session: Session, *, website_id: int, event_id: str) -> Event | None:
    return session.execute(
        select(Event).where(Event.website_id == website_id, Event.event_id == event_id)
    ).scalar_one_or_none()


def get_event_ids_for_website(session: Session, *, website_id: int, event_ids: list[str]) -> set[str]:
    if not event_ids:
        return set()

    rows = session.execute(
        select(Event.event_id).where(Event.website_id == website_id, Event.event_id.in_(event_ids))
    ).scalars().all()
    return set(rows)


def create_finding(
    session: Session,
    *,
    website_id: int,
    event_id: int,
    agent_name: str | None,
    finding_type: str,
    confidence: float,
    evidence: dict | None = None,
) -> Finding:
    finding = Finding(
        website_id=website_id,
        event_id=event_id,
        agent_name=agent_name,
        finding_type=finding_type,
        confidence=confidence,
        evidence=evidence,
    )
    session.add(finding)
    session.commit()
    session.refresh(finding)
    return finding


def create_incident(
    session: Session,
    *,
    website_id: int,
    incident_id: str,
    title: str,
    risk_level: str,
    risk_score: float,
    confidence: float,
    status: str,
) -> Incident:
    incident = Incident(
        website_id=website_id,
        incident_id=incident_id,
        title=title,
        risk_level=risk_level,
        risk_score=risk_score,
        confidence=confidence,
        status=status,
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def create_correlation(
    session: Session,
    *,
    incident_id: int | None,
    event_id: int,
    related_event_id: int,
    relationship_type: str,
    strength: float,
) -> Correlation:
    correlation = Correlation(
        incident_id=incident_id,
        event_id=event_id,
        related_event_id=related_event_id,
        relationship_type=relationship_type,
        strength=strength,
    )
    session.add(correlation)
    session.commit()
    session.refresh(correlation)
    return correlation


def create_feedback(
    session: Session,
    *,
    incident_id: int,
    analyst_decision: str,
    comment: str | None = None,
) -> Feedback:
    feedback = Feedback(
        incident_id=incident_id,
        analyst_decision=analyst_decision,
        comment=comment,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return feedback


def create_investigation(
    session: Session,
    *,
    website_id: int,
    correlation_id: int | None,
    investigation_id: str,
    title: str,
    status: str,
    summary: str | None,
    confidence: float,
) -> Investigation:
    investigation = Investigation(
        website_id=website_id,
        correlation_id=correlation_id,
        investigation_id=investigation_id,
        title=title,
        status=status,
        summary=summary,
        confidence=confidence,
    )
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def get_investigation_for_website(session: Session, *, website_id: int, investigation_id: str) -> Investigation | None:
    return session.execute(
        select(Investigation).where(Investigation.website_id == website_id, Investigation.investigation_id == investigation_id)
    ).scalar_one_or_none()


def list_investigations_for_website(session: Session, *, website_id: int) -> list[Investigation]:
    return session.execute(select(Investigation).where(Investigation.website_id == website_id)).scalars().all()


def update_investigation_status(
    session: Session,
    investigation: Investigation,
    *,
    status: str,
    summary: str | None = None,
    confidence: float | None = None,
) -> Investigation:
    investigation.status = status
    if summary is not None:
        investigation.summary = summary
    if confidence is not None:
        investigation.confidence = confidence
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def create_investigation_evidence(
    session: Session,
    *,
    investigation_id: int,
    evidence_type: str,
    source_type: str,
    source_id: int,
    classification: str,
    content: str | None,
    confidence: float,
) -> InvestigationEvidence:
    evidence = InvestigationEvidence(
        investigation_id=investigation_id,
        evidence_type=evidence_type,
        source_type=source_type,
        source_id=source_id,
        classification=classification,
        content=content,
        confidence=confidence,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


def get_investigation_evidence(session: Session, *, investigation_id: int) -> list[InvestigationEvidence]:
    return session.execute(select(InvestigationEvidence).where(InvestigationEvidence.investigation_id == investigation_id)).scalars().all()


def create_user(session: Session, *, email: str, password_hash: str, is_active: bool = True) -> User:
    user = User(email=email, password_hash=password_hash, is_active=is_active)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
