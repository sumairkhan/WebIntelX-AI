from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Event, Finding
from app.database.repositories import create_finding
from app.detection.models import DetectionResult
from app.detection.rules import default_rules
from app.detection.utils import load_detection_config, safe_evidence


class DetectionEngine:
    def __init__(self, rules: list[Any] | None = None, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()
        self.rules = rules or default_rules(self.config)

    def _coerce_event(self, event: Any) -> dict[str, Any]:
        if isinstance(event, dict):
            return event
        if hasattr(event, "metadata"):
            metadata = event.metadata or {}
            if isinstance(metadata, dict):
                raw = dict(metadata)
            else:
                raw = {"value": metadata}
            return {
                "event_id": event.event_id,
                "website_id": event.website_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else event.timestamp,
                "session_id": event.session_id,
                "source": event.source,
                "user_agent": event.user_agent,
                "method": event.method,
                "endpoint": event.endpoint,
                "status_code": event.status_code,
                "metadata": raw,
            }
        raise TypeError("Unsupported event type for detection evaluation.")

    def evaluate(self, event: Any, history: list[Any] | None = None) -> list[DetectionResult]:
        normalized_event = self._coerce_event(event)
        normalized_history = [self._coerce_event(item) for item in (history or [])]
        results: list[DetectionResult] = []
        for rule in self.rules:
            results.extend(rule.evaluate(normalized_event, normalized_history))
        return self.deduplicate(results)

    def evaluate_many(self, events: list[Any]) -> list[DetectionResult]:
        if not events:
            return []
        normalized_events = [self._coerce_event(item) for item in events]
        results: list[DetectionResult] = []
        for index, event in enumerate(normalized_events):
            history = normalized_events[:index] + normalized_events[index + 1 :]
            results.extend(self.evaluate(event, history=history))
        return self.deduplicate(results)

    @staticmethod
    def deduplicate(results: list[DetectionResult]) -> list[DetectionResult]:
        seen: set[tuple[int | str | None, str | None, str]] = set()
        unique: list[DetectionResult] = []
        for result in results:
            key = (result.website_id, result.event_id, result.rule_name)
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return unique

    def persist_findings(self, session: Session, results: list[DetectionResult]) -> list[Finding]:
        stored: list[Finding] = []
        for result in results:
            if result.website_id is None:
                continue
            event_record = None
            if result.event_id is not None:
                if isinstance(result.event_id, int):
                    event_record = session.execute(select(Event).where(Event.id == result.event_id)).scalar_one_or_none()
                else:
                    event_record = session.execute(select(Event).where(Event.event_id == str(result.event_id))).scalar_one_or_none()

            if event_record is None:
                continue

            existing = session.execute(
                select(Finding.id).where(
                    Finding.website_id == result.website_id,
                    Finding.event_id == event_record.id,
                    Finding.agent_name == "detection_engine",
                    Finding.finding_type == result.finding_type,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue

            finding = create_finding(
                session,
                website_id=int(result.website_id),
                event_id=int(event_record.id),
                agent_name="detection_engine",
                finding_type=result.finding_type,
                confidence=float(result.confidence),
                evidence=safe_evidence({
                    "rule_name": result.rule_name,
                    "severity": result.severity,
                    "reason": result.reason,
                    **result.evidence,
                }),
            )
            stored.append(finding)
        return stored

    def detect_event(self, event: Any, session: Session | None = None) -> list[DetectionResult]:
        results = self.evaluate(event)
        if session is not None:
            self.persist_findings(session, results)
        return results

    def detect_events(self, events: list[Any], session: Session | None = None) -> list[DetectionResult]:
        results = self.evaluate_many(events)
        if session is not None:
            self.persist_findings(session, results)
        return results


def detect_event(event: Any, session: Session | None = None, config: dict[str, Any] | None = None) -> list[DetectionResult]:
    return DetectionEngine(config=config).detect_event(event, session)


def detect_events(events: list[Any], session: Session | None = None, config: dict[str, Any] | None = None) -> list[DetectionResult]:
    return DetectionEngine(config=config).detect_events(events, session)
