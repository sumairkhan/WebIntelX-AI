from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.investigation.agents import build_agent_specs
from app.investigation.tasks import build_tasks


def _fallback_result(context: dict[str, Any]) -> dict[str, Any]:
    events = context.get("events", [])
    findings = context.get("findings", [])
    correlations = context.get("correlations", [])

    fact_references: list[dict[str, Any]] = []
    if events:
        fact_references.append({"type": "event", "id": events[0]["id"]})
    if findings:
        fact_references.append({"type": "finding", "id": findings[0]["id"]})
    if correlations:
        fact_references.append({"type": "correlation", "id": correlations[0]["id"]})

    fact_desc = "The investigation context contains suspicious activity records within the selected website and session context."
    facts = [
        {
            "title": "Observations in the selected evidence set",
            "description": fact_desc,
            "classification": "fact",
            "finding_type": "timeline_observation",
            "confidence": 0.9,
            "evidence_references": fact_references[:3],
        }
    ]

    inferences = [
        {
            "title": "Possible suspicious behavioral pattern",
            "description": "The available sequence of events and findings is consistent with a suspicious activity pattern but does not confirm a successful compromise.",
            "classification": "inference",
            "finding_type": "behavioral_hypothesis",
            "confidence": 0.72,
            "evidence_references": [{"type": "correlation", "id": correlations[0]["id"]}] if correlations else [],
        }
    ]

    uncertainties = [
        "The available evidence does not confirm whether unauthorized access occurred.",
        "Additional telemetry would be required to confirm the exact user impact.",
    ]

    return {
        "summary": "The investigation found a bounded set of suspicious events, findings, and correlations consistent with a suspicious pattern, but no direct evidence of confirmed compromise.",
        "facts": facts,
        "inferences": inferences,
        "uncertainties": uncertainties,
        "confidence": 0.76,
        "evidence": [ref for ref in fact_references[:3]],
    }


def _build_configured_llm(crewai):
    provider = settings.llm_provider.strip().lower()
    model_name = settings.llm_model.strip()
    if not provider or not model_name or not settings.llm_api_key:
        return None

    model = model_name if "/" in model_name else f"{provider}/{model_name}"
    options = {
        "model": model,
        "api_key": settings.llm_api_key,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    if settings.llm_base_url.strip():
        options["base_url"] = settings.llm_base_url.strip()
    return crewai.LLM(**options)


def run_investigation_crew(context: dict[str, Any]) -> dict[str, Any]:
    if not getattr(settings, "crewai_enabled", False):
        return _fallback_result(context)
    if not getattr(settings, "llm_provider", "") or not getattr(settings, "llm_model", "") or not getattr(settings, "llm_api_key", ""):
        return _fallback_result(context)

    try:
        import crewai  # type: ignore
    except Exception:
        return _fallback_result(context)

    try:
        llm = _build_configured_llm(crewai)
        if llm is None:
            return _fallback_result(context)
        agent_specs = build_agent_specs()
        tasks = build_tasks(context)
        if hasattr(crewai, "Agent") and hasattr(crewai, "Crew") and hasattr(crewai, "Task"):
            agents = [
                crewai.Agent(
                    role=agent.role,
                    goal=agent.goal,
                    backstory=agent.backstory,
                    llm=llm,
                    verbose=False,
                    allow_delegation=False,
                )
                for agent in agent_specs
            ]
            crew_tasks = [
                crewai.Task(
                    description=task.description,
                    expected_output=task.expected_output,
                    agent=agents[index % len(agents)] if index < len(agents) else agents[0],
                    context=task.context,
                )
                for index, task in enumerate(tasks)
            ]
            crew = crewai.Crew(agents=agents, tasks=crew_tasks, verbose=False)
            crew_result = crew.kickoff()
            if isinstance(crew_result, dict):
                return crew_result
            if hasattr(crew_result, "model_dump"):
                return crew_result.model_dump()
            return str(crew_result)
    except Exception:
        return _fallback_result(context)

    return _fallback_result(context)
