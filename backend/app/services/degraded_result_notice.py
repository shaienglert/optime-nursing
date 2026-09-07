from __future__ import annotations

"""What a family is told when the hard criteria answered and the model did not.

The engine can reach a state where the MUST gate has produced eligible communities but the
model that weighs them against what this family actually said is unavailable. Two answers
were possible and both were wrong. Showing nothing hides work that was done correctly and
leaves a family staring at an empty screen with no explanation. Showing the shortlist
silently asserts a study that never happened, and this product's whole claim is that it
does not assert what it cannot support.

The third answer is to show the eligible set, refuse to order it, and say so. A set is a
weaker claim than a ranking and an honest one: every community here meets the requirements
you stated, and we have not yet compared them to each other for you.

The notice therefore carries three things a family can act on -- retry now, wait, or leave
an address and be sent the full report once the model is back -- and one thing they should
not have to ask for: the fact that this is not the normal answer.
"""

from typing import Any, Dict, List, Optional

NOTICE_VERSION = "degraded-result-notice-v1"

HEADLINE = "These communities meet your requirements. We have not yet studied them for you."

EXPLANATION = (
    "Every community listed here passed the requirements you told us about -- care level, "
    "budget and location. What has not run is the part that compares them against each "
    "other for your situation and explains why one would suit better than another. That "
    "step is temporarily unavailable, so the list below is in no particular order and no "
    "community here is being recommended over any other."
)

# Ordered by how quickly each helps. A retry costs nothing and often works; the emailed
# report is the option that survives the family closing the tab.
RECOVERY_ACTIONS: List[Dict[str, str]] = [
    {
        "action": "RETRY_NOW",
        "label": "Search again",
        "detail": "The interruption is often brief. Running the same search again may return the full comparison.",
    },
    {
        "action": "RETRY_LATER",
        "label": "Come back later",
        "detail": "If a retry does not help, the full report is usually available again within a few hours.",
    },
    {
        "action": "EMAIL_REPORT_WHEN_READY",
        "label": "Send me the full report when it is ready",
        "detail": "Leave an email address and we will run the complete study as soon as the service recovers, and send it to you. Nothing else is sent to that address.",
        "endpoint": "POST /decision-engine/deferred-report",
    },
]


def _reason_from_pipeline(pipeline: Dict[str, Any]) -> Optional[str]:
    ai = pipeline.get("ai_ranking") if isinstance(pipeline.get("ai_ranking"), dict) else {}
    fallback = str(ai.get("fallback_reason") or "").strip()
    return fallback or None


def build_degraded_notice(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the notice, or None when the answer is an ordinary one.

    Read from the canonical state rather than re-derived, so the notice cannot disagree
    with the state machine about whether this result is degraded.
    """
    decision = result.get("decision_intelligence")
    decision = decision if isinstance(decision, dict) else {}
    canonical = decision.get("canonical_decision_state")
    canonical = canonical if isinstance(canonical, dict) else {}

    if not canonical.get("is_degraded_result"):
        return None

    pipeline = decision.get("facility_selection_pipeline")
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    shown = len(result.get("results") or [])
    eligible = int(result.get("must_eligible_count") or 0) + int(result.get("must_pending_verification_count") or 0)

    return {
        "version": NOTICE_VERSION,
        "degraded": True,
        "headline": HEADLINE,
        "explanation": EXPLANATION,
        "what_ran": "HARD_CRITERIA_ONLY",
        "what_did_not_run": "COMPARATIVE_STUDY_AND_RANKING",
        # Stated so nothing downstream sorts this list and calls the order meaningful.
        "results_are_ordered": False,
        "ordering_note": "Listed in no particular order. Position carries no meaning.",
        "eligible_candidates": eligible,
        "shown_candidates": shown,
        "technical_reason": _reason_from_pipeline(pipeline),
        "recovery_actions": RECOVERY_ACTIONS,
        "governance": {
            "hardCriteriaWereApplied": True,
            "comparativeStudyWasNotPerformed": True,
            "noCandidateIsRecommendedOverAnother": True,
        },
    }


def attach_degraded_result_notice(result: Dict[str, Any]) -> Dict[str, Any]:
    notice = build_degraded_notice(result)
    if notice is None:
        # Absent rather than present-and-false: a caller that forgets to check the flag
        # should find nothing to render, not a notice quietly saying everything is fine.
        result.pop("degraded_result_notice", None)
        return result
    result["degraded_result_notice"] = notice
    return result


__all__ = ["attach_degraded_result_notice", "build_degraded_notice", "NOTICE_VERSION", "RECOVERY_ACTIONS"]
