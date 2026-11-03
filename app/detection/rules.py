from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.detection.base import DetectionRule
from app.detection.models import DetectionResult
from app.detection.utils import (
    extract_event_path,
    extract_query_params,
    load_detection_config,
    match_path,
    normalize_user_agent,
    safe_evidence,
    event_session_key,
)


class SuspiciousPathRule(DetectionRule):
    name = "suspicious_path"
    finding_type = "suspicious_path"
    severity = "high"
    confidence = 0.90

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        path = extract_event_path(event)
        if not path:
            return []
        for pattern in self.config.get("suspicious_paths", []):
            if match_path(pattern, path):
                return [
                    DetectionResult(
                        rule_name=self.name,
                        finding_type=self.finding_type,
                        confidence=self.confidence,
                        severity=self.severity,
                        reason="Observed suspicious path matched a configured detection pattern.",
                        evidence=safe_evidence({"path": path, "matched_pattern": pattern, "rule_name": self.name}),
                        event_id=event.get("event_id"),
                        website_id=event.get("website_id"),
                    )
                ]
        return []


class SensitiveEndpointAccessRule(DetectionRule):
    name = "sensitive_endpoint_access"
    finding_type = "sensitive_endpoint_access"
    severity = "low"
    confidence = 0.60

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        path = extract_event_path(event)
        if not path:
            return []
        for endpoint in self.config.get("sensitive_endpoints", []):
            if match_path(endpoint, path):
                return [
                    DetectionResult(
                        rule_name=self.name,
                        finding_type=self.finding_type,
                        confidence=self.confidence,
                        severity=self.severity,
                        reason="Observed access to a sensitive administrative or authentication endpoint.",
                        evidence=safe_evidence({"path": path, "matched_endpoint": endpoint}),
                        event_id=event.get("event_id"),
                        website_id=event.get("website_id"),
                    )
                ]
        return []


class RepeatedAuthenticationFailureRule(DetectionRule):
    name = "repeated_authentication_failure"
    finding_type = "repeated_authentication_failure"
    severity = "medium"
    confidence = 0.85

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def _is_failure(self, event: dict[str, Any]) -> bool:
        event_type = str(event.get("event_type") or "").lower()
        status_code = event.get("status_code")
        endpoint = str(event.get("endpoint") or (event.get("metadata") or {}).get("endpoint") or "").lower()
        if "auth" in event_type and "fail" in event_type:
            return True
        if status_code == 401:
            return True
        if "login" in endpoint or "signin" in endpoint or "auth" in endpoint:
            return "fail" in event_type or status_code == 401
        return False

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        session_id = event_session_key(event)
        timeframe = (history or []) + [event]
        failures = []
        for candidate in timeframe:
            if not self._is_failure(candidate):
                continue
            if event_session_key(candidate) != session_id:
                continue
            failures.append(candidate)

        threshold = int(self.config.get("auth_failure_threshold", 5))
        window_seconds = int(self.config.get("auth_failure_window_seconds", 300))
        if len(failures) < threshold:
            return []

        now = datetime.now(timezone.utc)
        relevant = []
        for item in failures:
            try:
                timestamp = item.get("timestamp")
                if isinstance(timestamp, str):
                    if timestamp.endswith("Z"):
                        timestamp = timestamp[:-1] + "+00:00"
                    parsed = datetime.fromisoformat(timestamp)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    if (now - parsed.astimezone(timezone.utc)).total_seconds() <= window_seconds:
                        relevant.append(item)
            except (TypeError, ValueError):
                continue

        if len(relevant) < threshold:
            return []

        return [
            DetectionResult(
                rule_name=self.name,
                finding_type=self.finding_type,
                confidence=self.confidence,
                severity=self.severity,
                reason="Observed repeated authentication failures within the configured window.",
                evidence=safe_evidence({
                    "failure_count": len(relevant),
                    "window_seconds": window_seconds,
                    "session_id": session_id,
                    "threshold": threshold,
                }),
                event_id=event.get("event_id"),
                website_id=event.get("website_id"),
            )
        ]


class SuspiciousUserAgentRule(DetectionRule):
    name = "suspicious_user_agent"
    finding_type = "suspicious_user_agent"
    severity = "medium"
    confidence = 0.90

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        user_agent = normalize_user_agent(event.get("user_agent") or (event.get("metadata") or {}).get("user_agent") or (event.get("metadata") or {}).get("userAgent"))
        if not user_agent:
            return []
        lower_agent = user_agent.lower()
        for indicator in self.config.get("suspicious_user_agents", []):
            if indicator.lower() in lower_agent:
                return [
                    DetectionResult(
                        rule_name=self.name,
                        finding_type=self.finding_type,
                        confidence=self.confidence,
                        severity=self.severity,
                        reason="Matched a configured scanner or automated tooling indicator in the user-agent string.",
                        evidence=safe_evidence({"user_agent": user_agent, "matched_indicator": indicator, "rule_name": self.name}),
                        event_id=event.get("event_id"),
                        website_id=event.get("website_id"),
                    )
                ]
        return []


class HighRequestFrequencyRule(DetectionRule):
    name = "high_request_frequency"
    finding_type = "high_request_frequency"
    severity = "medium"
    confidence = 0.75

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        if not history:
            return []

        threshold = int(self.config.get("request_frequency_threshold", 30))
        window_seconds = int(self.config.get("request_frequency_window_seconds", 60))
        session_id = event_session_key(event)
        if not session_id:
            return []

        relevant = []
        for candidate in history:
            if event_session_key(candidate) != session_id:
                continue
            candidate_ts = candidate.get("timestamp")
            try:
                if isinstance(candidate_ts, str):
                    if candidate_ts.endswith("Z"):
                        candidate_ts = candidate_ts[:-1] + "+00:00"
                    parsed = datetime.fromisoformat(candidate_ts)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() <= window_seconds:
                        relevant.append(candidate)
            except (TypeError, ValueError):
                continue

        if len(relevant) < threshold:
            return []

        return [
            DetectionResult(
                rule_name=self.name,
                finding_type=self.finding_type,
                confidence=self.confidence,
                severity=self.severity,
                reason="Observed a high event rate within the configured time window for the same session.",
                evidence=safe_evidence({
                    "session_id": session_id,
                    "event_count": len(relevant),
                    "window_seconds": window_seconds,
                    "threshold": threshold,
                }),
                event_id=event.get("event_id"),
                website_id=event.get("website_id"),
            )
        ]


class SuspiciousQueryParameterRule(DetectionRule):
    name = "suspicious_query_parameter"
    finding_type = "suspicious_query_parameter"
    severity = "medium"
    confidence = 0.70

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        query_params = extract_query_params(event)
        if not query_params:
            return []
        path = extract_event_path(event)
        for key in self.config.get("suspicious_query_parameters", []):
            if key.lower() in {k.lower() for k in query_params.keys()}:
                return [
                    DetectionResult(
                        rule_name=self.name,
                        finding_type=self.finding_type,
                        confidence=self.confidence,
                        severity=self.severity,
                        reason="Observed a suspicious query parameter name that matches a configured administrative or command pattern.",
                        evidence=safe_evidence({"parameter_name": key, "path": path, "rule_name": self.name}),
                        event_id=event.get("event_id"),
                        website_id=event.get("website_id"),
                    )
                ]
        return []


class UnusualHttpMethodRule(DetectionRule):
    name = "unusual_http_method"
    finding_type = "unusual_http_method"
    severity = "low"
    confidence = 0.60

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_detection_config()

    def evaluate(self, event: dict[str, Any], history: list[dict[str, Any]] | None = None) -> list[DetectionResult]:
        method = str(event.get("method") or "").upper()
        if not method:
            return []
        if method in {"GET", "POST"}:
            return []
        if method in {item.upper() for item in self.config.get("unusual_methods", [])}:
            return [
                DetectionResult(
                    rule_name=self.name,
                    finding_type=self.finding_type,
                    confidence=self.confidence,
                    severity=self.severity,
                    reason="Observed an unusual HTTP method outside the normal browser request pattern.",
                    evidence=safe_evidence({"method": method}),
                    event_id=event.get("event_id"),
                    website_id=event.get("website_id"),
                )
            ]
        return []


def default_rules(config: dict[str, Any] | None = None) -> list[DetectionRule]:
    config = config or load_detection_config()
    return [
        SuspiciousPathRule(config),
        SensitiveEndpointAccessRule(config),
        RepeatedAuthenticationFailureRule(config),
        SuspiciousUserAgentRule(config),
        HighRequestFrequencyRule(config),
        SuspiciousQueryParameterRule(config),
        UnusualHttpMethodRule(config),
    ]
