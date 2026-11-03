from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Correlation, Event, Finding
from app.detection.utils import safe_evidence

SENSITIVE_QUERY_KEYS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "session",
    "jwt",
    "bearer",
}


@dataclass
class CorrelationSignal:
    event_id: int
    related_event_id: int
    relationship_type: str
    strength: float
    evidence: dict[str, Any] = field(default_factory=dict)
    incident_id: int | None = None

    def __post_init__(self) -> None:
        self.strength = max(0.0, min(1.0, float(self.strength)))


class CorrelationEngine:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def correlate_events(self, events: list[Event]) -> list[CorrelationSignal]:
        if not events:
            return []

        results: list[CorrelationSignal] = []
        seen: set[tuple[int, int, str]] = set()

        for index, left in enumerate(events):
            for right in events[index + 1 :]:
                if left.website_id != right.website_id:
                    continue
                if left.id == right.id:
                    continue

                for signal in self._evaluate_pair(left, right):
                    key = (signal.event_id, signal.related_event_id, signal.relationship_type)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(signal)
                    if self.session is not None:
                        self._persist_signal(signal)

        for signal in self._cluster_signals(events):
            key = (signal.event_id, signal.related_event_id, signal.relationship_type)
            if key in seen:
                continue
            seen.add(key)
            results.append(signal)
            if self.session is not None:
                self._persist_signal(signal)

        if self.session is not None:
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
        return results

    def _evaluate_pair(self, left: Event, right: Event) -> list[CorrelationSignal]:
        signals: list[CorrelationSignal] = []
        left_findings = self._find_findings_for_event(left)
        right_findings = self._find_findings_for_event(right)
        left_types = {item.finding_type for item in left_findings}
        right_types = {item.finding_type for item in right_findings}

        if self._same_session(left, right):
            delta = abs((left.timestamp - right.timestamp).total_seconds())
            if delta <= 300:
                strength = 0.8 if delta <= 60 else 0.65
                signals.append(
                    CorrelationSignal(
                        event_id=left.id,
                        related_event_id=right.id,
                        relationship_type="same_session",
                        strength=strength,
                        evidence=self._safe_evidence({
                            "session_id": left.session_id or right.session_id,
                            "website_id": left.website_id,
                            "seconds_apart": int(delta),
                        }),
                    )
                )

        if self._same_session(left, right) and left.timestamp != right.timestamp:
            delta = abs((left.timestamp - right.timestamp).total_seconds())
            if delta <= 300:
                direction = "before" if left.timestamp < right.timestamp else "after"
                signals.append(
                    CorrelationSignal(
                        event_id=left.id,
                        related_event_id=right.id,
                        relationship_type="temporal_sequence",
                        strength=0.7 if delta <= 60 else 0.55,
                        evidence=self._safe_evidence({
                            "direction": direction,
                            "seconds_apart": int(delta),
                            "event_types": [left.event_type, right.event_type],
                        }),
                    )
                )

        if left.event_type == right.event_type and self._same_session(left, right):
            signals.append(
                CorrelationSignal(
                    event_id=left.id,
                    related_event_id=right.id,
                    relationship_type="repeated_behavior",
                    strength=0.7,
                    evidence=self._safe_evidence({
                        "event_type": left.event_type,
                        "session_id": left.session_id,
                        "repeat_count": 2,
                    }),
                )
            )

        if self._has_agent_signal(left_findings, "detection_engine") and self._has_agent_signal(right_findings, "ml_anomaly_detector"):
            signals.append(
                CorrelationSignal(
                    event_id=left.id,
                    related_event_id=right.id,
                    relationship_type="rule_plus_ml",
                    strength=0.9,
                    evidence=self._safe_evidence({
                        "rule_findings": sorted({item.finding_type for item in left_findings}),
                        "ml_findings": sorted({item.finding_type for item in right_findings}),
                        "window_seconds": int(abs((left.timestamp - right.timestamp).total_seconds())),
                    }),
                )
            )
        elif self._has_agent_signal(left_findings, "ml_anomaly_detector") and self._has_agent_signal(right_findings, "detection_engine"):
            signals.append(
                CorrelationSignal(
                    event_id=left.id,
                    related_event_id=right.id,
                    relationship_type="rule_plus_ml",
                    strength=0.9,
                    evidence=self._safe_evidence({
                        "ml_findings": sorted({item.finding_type for item in left_findings}),
                        "rule_findings": sorted({item.finding_type for item in right_findings}),
                        "window_seconds": int(abs((left.timestamp - right.timestamp).total_seconds())),
                    }),
                )
            )

        cluster_signal = self._cluster_signal(left, right, left_findings, right_findings)
        if cluster_signal is not None:
            signals.append(cluster_signal)

        return signals

    def _cluster_signal(
        self,
        left: Event,
        right: Event,
        left_findings: list[Finding],
        right_findings: list[Finding],
    ) -> CorrelationSignal | None:
        if not self._same_session(left, right):
            return None

        suspicious_types = {"suspicious_path", "suspicious_user_agent", "high_request_frequency", "ml_anomaly"}
        combined_types = {item.finding_type for item in left_findings} | {item.finding_type for item in right_findings}
        if len(combined_types & suspicious_types) < 3:
            return None

        delta = abs((left.timestamp - right.timestamp).total_seconds())
        if delta > 300:
            return None

        return CorrelationSignal(
            event_id=left.id,
            related_event_id=right.id,
            relationship_type="suspicious_activity_cluster",
            strength=min(0.95, 0.7 + 0.08 * len(combined_types & suspicious_types)),
            evidence=self._safe_evidence({
                "session_id": left.session_id,
                "signals": sorted(combined_types & suspicious_types),
                "seconds_apart": int(delta),
            }),
        )

    def _cluster_signals(self, events: list[Event]) -> list[CorrelationSignal]:
        grouped: dict[tuple[int, str], list[Event]] = {}
        for event in events:
            if event.session_id is None:
                continue
            grouped.setdefault((event.website_id, event.session_id), []).append(event)

        signals: list[CorrelationSignal] = []
        suspicious_types = {"suspicious_path", "suspicious_user_agent", "high_request_frequency", "ml_anomaly"}

        for site_events in grouped.values():
            ordered = sorted(site_events, key=lambda event: event.timestamp)
            for start in range(len(ordered)):
                window: list[Event] = []
                signal_types: set[str] = set()
                for end in range(start, len(ordered)):
                    candidate = ordered[end]
                    window.append(candidate)
                    delta = (candidate.timestamp - ordered[start].timestamp).total_seconds()
                    if delta > 300:
                        break
                    for finding in self._find_findings_for_event(candidate):
                        if finding.finding_type in suspicious_types:
                            signal_types.add(finding.finding_type)
                    if len(signal_types) >= 3:
                        earliest = ordered[start]
                        latest = candidate
                        signals.append(
                            CorrelationSignal(
                                event_id=earliest.id,
                                related_event_id=latest.id,
                                relationship_type="suspicious_activity_cluster",
                                strength=min(0.95, 0.7 + 0.08 * len(signal_types)),
                                evidence=self._safe_evidence({
                                    "session_id": earliest.session_id,
                                    "signals": sorted(signal_types),
                                    "seconds_apart": int(delta),
                                }),
                            )
                        )
                        break
                if signals and signals[-1].event_id == ordered[start].id:
                    break

        return signals

    def _persist_signal(self, signal: CorrelationSignal) -> None:
        if self.session is None:
            return

        existing = self.session.execute(
            select(Correlation.id).where(
                Correlation.event_id == signal.event_id,
                Correlation.related_event_id == signal.related_event_id,
                Correlation.relationship_type == signal.relationship_type,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return

        row = Correlation(
            incident_id=signal.incident_id,
            event_id=signal.event_id,
            related_event_id=signal.related_event_id,
            relationship_type=signal.relationship_type,
            strength=signal.strength,
        )
        self.session.add(row)

    @staticmethod
    def _same_session(left: Event, right: Event) -> bool:
        if not left.session_id or not right.session_id:
            return False
        return left.website_id == right.website_id and left.session_id == right.session_id

    def _find_findings_for_event(self, event: Event) -> list[Finding]:
        if hasattr(event, "findings") and getattr(event, "findings"):
            return list(event.findings)
        if self.session is None or getattr(event, "id", None) is None:
            return []
        rows = self.session.execute(select(Finding).where(Finding.event_id == event.id)).scalars().all()
        return list(rows)

    @staticmethod
    def _has_agent_signal(findings: list[Finding], agent_name: str) -> bool:
        return any((item.agent_name or "") == agent_name for item in findings)

    @staticmethod
    def _safe_evidence(data: dict[str, Any]) -> dict[str, Any]:
        sanitized = safe_evidence(data)
        return CorrelationEngine._scrub_sensitive_values(sanitized)

    @staticmethod
    def _scrub_sensitive_values(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: CorrelationEngine._scrub_sensitive_values(item) for key, item in value.items()}
        if isinstance(value, list):
            return [CorrelationEngine._scrub_sensitive_values(item) for item in value]
        if isinstance(value, str):
            lowered = value.lower()
            if any(key in lowered for key in ["token", "secret", "password", "api_key", "authorization", "cookie", "jwt"]):
                return CorrelationEngine._redact_sensitive_url(value)
            return value
        return value

    @staticmethod
    def _redact_sensitive_url(value: str) -> str:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return "[REDACTED]"

        if not parsed.query:
            return value

        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        redacted_pairs = []
        for key, old_value in pairs:
            if key.lower() in SENSITIVE_QUERY_KEYS:
                redacted_pairs.append((key, "[REDACTED]"))
            else:
                redacted_pairs.append((key, old_value))

        return urlunsplit(parsed._replace(query=urlencode(redacted_pairs, doseq=True)))
