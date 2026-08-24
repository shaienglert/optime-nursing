from __future__ import annotations

"""Guardian retry wrapper for the AI process owner.

The AI owns the process, but a phase/action that conflicts with the governed lifecycle
must be vetoed and returned to the AI once with an explicit correction packet instead
of leaving the process owner FAILED on the first model mismatch.
"""

from typing import Any, Dict

from app.services import ai_process_owner_runtime as _runtime


_RETRYABLE_GOVERNANCE_ERRORS = (
    "AI_PROCESS_OWNER_PHASE_MISMATCH",
    "AI_PROCESS_OWNER_PREMATURE_RECOMMENDATION",
    "AI_PROCESS_OWNER_RESEARCH_PHASE_CANNOT_RECOMMEND",
    "AI_PROCESS_OWNER_ACTION_BEFORE_EXECUTION_ALLOWED",
    "AI_PROCESS_OWNER_ACTION_WITH_MUST_FAIL",
    "AI_PROCESS_OWNER_CLARIFICATION_MUST_ASK_CLIENT",
    "AI_PROCESS_OWNER_FOLLOW_UP_PHASE_MUST_CONTINUE",
)


def _retryable(error: str) -> bool:
    return any(str(error or "").startswith(prefix) for prefix in _RETRYABLE_GOVERNANCE_ERRORS)


def attach_ai_process_owner_guarded(
    result: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
) -> Dict[str, Any]:
    decision = result.setdefault("decision_intelligence", {})
    prior_execution_allowed = decision.get("recommendation_execution_allowed")
    first = _runtime.attach_ai_process_owner(result, questionnaire_state, natural_language_query)
    decision = first.setdefault("decision_intelligence", {})
    owner = decision.get("process_owner") if isinstance(decision.get("process_owner"), dict) else {}
    error = str(owner.get("error") or "")
    if owner.get("status") != "FAILED" or not _retryable(error):
        return first

    expected_phase = _runtime._phase(first, questionnaire_state)
    prompt = _runtime._prompt(first, questionnaire_state, natural_language_query)
    prompt["guardian_veto"] = {
        "status": "RETRY_REQUIRED",
        "rejected_output_error": error,
        "expected_process_phase": expected_phase,
        "instruction": (
            "Your previous process decision was rejected by Guardian. Return the exact expected_process_phase. "
            "Do not present a final recommendation while research/verification is pending. In RESEARCH choose "
            "RESEARCH_FACILITY_FACTS or VERIFY_BEFORE_DECISION as appropriate; in CLARIFICATION choose ASK_CLIENT; "
            "in FOLLOW_UP choose FOLLOW_UP. Continue to own the process, but obey the governed lifecycle state."
        ),
    }
    prompt.setdefault("rules", []).append(
        f"GUARDIAN RETRY: process_phase must be exactly {expected_phase}; the previous output was rejected as {error}."
    )

    try:
        packet = _runtime._validate(
            _runtime._default_transport(prompt),
            first,
            questionnaire_state,
        )
        decision["process_owner"] = {
            "owner": "SEMANTIC_AI_PROCESS_OWNER",
            "status": "ACTIVE",
            "prior_process_state": _runtime._continuity_state(questionnaire_state),
            "guardian_retry_applied": True,
            "guardian_rejected_error": error,
            **packet,
        }
        if prior_execution_allowed is not None:
            decision["recommendation_execution_allowed"] = prior_execution_allowed
    except Exception as retry_exc:
        owner["guardian_retry_applied"] = True
        owner["guardian_retry_error"] = str(retry_exc)
        owner["guardian_expected_phase"] = expected_phase
        decision["process_owner"] = owner
    return first


__all__ = ["attach_ai_process_owner_guarded"]
