from __future__ import annotations

"""Single source of governed per-row evidence payloads.

Before this module existed, client_intent_runtime.py and combined_care_solution_runtime.py
each had their own separately-written function that read the same underlying row fields
(agent_person_fit_evidence, provider_housing_evidence, life_plan_primary_evidence) into a
flat list of payload dicts for MUST-gate and care-delivery checks to scan. They had quietly
diverged: one synthesized rehab_verified/pt_ot_verified/continuum_of_care_verified flags from
life-plan evidence, the other passed the raw life-plan dict through unchanged (which carries
none of those keys, so any future check for them there would silently see nothing). No
production check had tripped over it yet, but it is the same "two disagreeing sources of
truth for one fact" shape as the medication-evidence bug this was extracted alongside. Every
reader of agent/provider/life-plan evidence should call agent_and_provider_payloads() here
instead of re-deriving its own reading of these fields.
"""

from typing import Any, Dict, List


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def agent_only_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten only agent-sourced evidence for one candidate row.

    Kept separate from agent_and_provider_payloads() because some callers (e.g.
    public-reputation fallback) intentionally trust only agent research, not
    provider/life-plan evidence, for certain facts.
    """
    agent_evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    return [item.get("payload") for item in agent_evidence if isinstance(item, dict) and isinstance(item.get("payload"), dict)]


def agent_and_provider_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten agent-sourced, provider-verified, and life-plan evidence for one
    candidate row into a single list of payload dicts, in a stable order
    (agent evidence first, then provider evidence, then life-plan-derived flags).
    """
    out: List[Dict[str, Any]] = list(agent_only_payloads(row))

    provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
    provider_evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else None
    if provider_evidence:
        out.append(provider_evidence)

    life_plan = row.get("life_plan_primary_evidence") if isinstance(row.get("life_plan_primary_evidence"), dict) else {}
    if life_plan:
        direct: Dict[str, Any] = {}
        if str(life_plan.get("rehabilitation_source_url") or "").startswith("http"):
            direct["rehab_verified"] = True
            direct["pt_ot_verified"] = True
        modalities = {_upper(value) for value in row.get("housing_modalities") or []}
        if "LIFE_PLAN_CCRC" in modalities:
            direct["continuum_of_care_verified"] = True
        if direct:
            out.append(direct)

    return out


__all__ = ["agent_only_payloads", "agent_and_provider_payloads"]
