from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InvestigationTask:
    name: str
    description: str
    expected_output: str
    context: dict[str, Any] = field(default_factory=dict)


def build_tasks(context: dict[str, Any]) -> list[InvestigationTask]:
    return [
        InvestigationTask(
            name="evidence_analysis",
            description="Review the event, finding, and correlation records for the selected website context and identify directly supported facts.",
            expected_output="Structured list of fact-based claims with evidence references.",
            context=context,
        ),
        InvestigationTask(
            name="behavior_analysis",
            description="Compare repeated behavior, session continuity, and temporal ordering to describe visible patterns without over-claiming.",
            expected_output="Behavioral assessment with uncertainty noted.",
            context=context,
        ),
        InvestigationTask(
            name="attack_chain_analysis",
            description="Describe possible stages of suspicious activity using evidence-backed inferences only.",
            expected_output="Inference-based chain hypotheses with explicit uncertainty and supporting references.",
            context=context,
        ),
        InvestigationTask(
            name="final_synthesis",
            description="Combine all outputs into a concise investigation summary that distinguishes facts from inference and closes with uncertainty.",
            expected_output="Final structured investigation result with summary, facts, inferences, uncertainties, and confidence.",
            context=context,
        ),
    ]
