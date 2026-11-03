from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.database.models import Correlation, Event, Finding

VALID_CLASSIFICATIONS = {"fact", "inference"}
VALID_REFERENCE_TYPES = {"event", "finding", "correlation"}


def validate_evidence_references(references: list[dict[str, Any]], session: Session, website_id: int) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(references, list):
        return False, ["Evidence references must be a list."]

    for reference in references:
        if not isinstance(reference, dict):
            errors.append("Each reference must be a key-value object.")
            continue
        reference_type = str(reference.get("type", "")).lower()
        reference_id = reference.get("id")
        if reference_type not in VALID_REFERENCE_TYPES:
            errors.append(f"Unsupported evidence reference type: {reference_type}.")
            continue
        if not isinstance(reference_id, int):
            errors.append(f"Invalid {reference_type} reference id.")
            continue

        if reference_type == "event":
            record = session.get(Event, reference_id)
            if record is None or record.website_id != website_id:
                errors.append(f"Referenced event {reference_id} is invalid for website {website_id}.")
        elif reference_type == "finding":
            record = session.get(Finding, reference_id)
            if record is None or record.website_id != website_id:
                errors.append(f"Referenced finding {reference_id} is invalid for website {website_id}.")
        elif reference_type == "correlation":
            record = session.get(Correlation, reference_id)
            if record is None:
                errors.append(f"Referenced correlation {reference_id} does not exist.")
                continue
            event_record = session.get(Event, record.event_id)
            related_record = session.get(Event, record.related_event_id)
            if event_record is None or related_record is None or event_record.website_id != website_id or related_record.website_id != website_id:
                errors.append(f"Referenced correlation {reference_id} is invalid for website {website_id}.")

    return not errors, errors


def validate_investigation_output(payload: dict[str, Any], session: Session, website_id: int) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "invalid", "errors": ["Investigation output must be an object."]}

    errors: list[str] = []
    required = ["summary", "facts", "inferences", "uncertainties", "confidence"]
    for key in required:
        if key not in payload:
            errors.append(f"Missing field: {key}.")

    if "confidence" in payload:
        try:
            confidence = float(payload["confidence"]) 
        except (TypeError, ValueError):
            confidence = -1.0
        if not 0.0 <= confidence <= 1.0:
            errors.append("Confidence must be between 0.0 and 1.0.")

    for collection_name in ("facts", "inferences"):
        if collection_name in payload and not isinstance(payload[collection_name], list):
            errors.append(f"{collection_name} must be a list.")
            continue
        for item in payload.get(collection_name, []):
            if not isinstance(item, dict):
                errors.append(f"Each {collection_name[:-1]} item must be an object.")
                continue
            classification = str(item.get("classification", "")).lower()
            if classification not in VALID_CLASSIFICATIONS:
                errors.append(f"Invalid classification for {collection_name}: {classification!r}.")
            try:
                item_confidence = float(item.get("confidence", -1))
            except (TypeError, ValueError):
                item_confidence = -1.0
            if not 0.0 <= item_confidence <= 1.0:
                errors.append(f"Invalid confidence value inside {collection_name}: {item.get('confidence')!r}.")
            ok, ref_errors = validate_evidence_references(item.get("evidence_references", []), session, website_id)
            if not ok:
                errors.extend(ref_errors)

    if errors:
        return {"status": "invalid", "errors": errors}
    return {"status": "valid", "result": payload}
