from __future__ import annotations


class RecommendationBuilder:
    @staticmethod
    def build(risk_level: str, evidence: list[str] | None = None) -> list[dict[str, object]]:
        evidence = evidence or []
        if risk_level.lower() == "critical":
            return [
                {
                    "action": "Escalate the suspicious activity to an analyst for immediate review",
                    "reason": "The evidence set indicates severe and repeated suspicious behavior.",
                    "priority": "high",
                    "evidence": evidence or ["repeated suspicious behavior", "authentication failures"],
                },
                {
                    "action": "Review affected authentication and session logs",
                    "reason": "This helps confirm whether a credential or session was abused.",
                    "priority": "high",
                    "evidence": evidence,
                },
            ]
        if risk_level.lower() == "high":
            return [
                {
                    "action": "Review the suspicious session and sensitive endpoints",
                    "reason": "The pattern suggests user or credential misuse.",
                    "priority": "high",
                    "evidence": evidence or ["sensitive endpoint access"],
                },
                {
                    "action": "Increase monitoring for the affected website",
                    "reason": "Additional telemetry will confirm whether the pattern continues.",
                    "priority": "medium",
                    "evidence": evidence,
                },
            ]
        return [
            {
                "action": "Continue monitoring the activity pattern",
                "reason": "The available evidence is suspicious but not yet conclusive.",
                "priority": "medium",
                "evidence": evidence or ["limited evidence"],
            }
        ]
