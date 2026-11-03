from __future__ import annotations

from app.risk.models import RiskAssessment, RiskFactor


class RiskCalculator:
    @staticmethod
    def calculate(payload: dict[str, object]) -> RiskAssessment:
        score = 0.0
        factors: list[RiskFactor] = []

        rule_findings = int(payload.get("rule_findings", 0) or 0)
        if rule_findings:
            contribution = min(rule_findings * 12.0, 30.0)
            score += contribution
            factors.append(RiskFactor("rule_detection", contribution, "Rule detections contributed to risk."))

        ml_anomaly = bool(payload.get("ml_anomaly", False))
        if ml_anomaly:
            score += 15.0
            factors.append(RiskFactor("ml_anomaly", 15.0, "ML anomaly model flagged unusual behavior."))

        correlations = int(payload.get("correlations", 0) or 0)
        if correlations:
            contribution = min(correlations * 12.0, 24.0)
            score += contribution
            factors.append(RiskFactor("correlation_strength", contribution, "Related events formed suspicious patterns."))

        investigation_confidence = float(payload.get("investigation_confidence", 0.0) or 0.0)
        if investigation_confidence:
            contribution = investigation_confidence * 20.0
            score += contribution
            factors.append(RiskFactor("investigation_confidence", contribution, "Investigation confidence increased confidence in the assessment."))

        threat_intel = payload.get("threat_intel") or {}
        if isinstance(threat_intel, dict):
            malicious = bool(threat_intel.get("malicious", False))
            if malicious:
                score += 25.0
                factors.append(RiskFactor("threat_intel", 25.0, "External intelligence labeled the indicator as malicious."))

        sensitive_activity = bool(payload.get("sensitive_endpoint_activity", False))
        if sensitive_activity:
            score += 18.0
            factors.append(RiskFactor("sensitive_activity", 18.0, "Sensitive endpoint activity increased the risk profile."))

        auth_failures = int(payload.get("authentication_failures", 0) or 0)
        if auth_failures:
            contribution = min(auth_failures * 4.0, 20.0)
            score += contribution
            factors.append(RiskFactor("authentication_failures", contribution, "Repeated authentication failures were observed."))

        score = max(0.0, min(100.0, score))

        if score >= 85:
            level = "critical"
        elif score >= 70:
            level = "high"
        elif score >= 40:
            level = "medium"
        else:
            level = "low"

        confidence = min(0.99, 0.45 + (score / 100.0) * 0.55)
        explanation = (
            "Risk was calculated from the observed suspicious behavior, automation signals, and any external intelligence. "
            "The score is deterministic and explainable rather than inferred from hidden heuristics."
        )

        return RiskAssessment(
            risk_score=score,
            risk_level=level,
            confidence=confidence,
            factors=factors,
            explanation=explanation,
        )
