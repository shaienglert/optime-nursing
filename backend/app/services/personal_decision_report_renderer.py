from __future__ import annotations

"""Deterministic renderer for governed Personal Decision Reports.

No LLM is used. The renderer only groups byte-identical approved claim text that has
already passed the report contract.
"""

from typing import Any

from app.services.personal_decision_report_builder import PersonalReportPayload


SECTION_TITLES = {
    "YOUR_SITUATION": "Your Situation",
    "YOUR_ROLE": "Your Role in This Decision",
    "WHAT_MATTERS": "What Matters Most",
    "WHY_RECOMMENDATION": "Why This Recommendation",
    "WHY_THIS_PLACE": "Why This Place",
    "SUCCESSFUL_TRANSITION": "Preparing for a Successful Transition",
    "BEFORE_YOU_DECIDE": "What We Still Don't Know",
}


def render_personal_report(payload: PersonalReportPayload) -> dict[str, Any]:
    claims = {claim.claim_id: claim for claim in payload.approved_claims}
    sections: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}

    for use in payload.claim_uses:
        claim = claims[use.claim_id]
        key = use.section.value
        grouped.setdefault(key, []).append({
            "claim_id": claim.claim_id,
            "text": use.rendered_text,
            "claim_type": claim.claim_type.value,
            "provenance_ids": list(claim.provenance_ids),
            "confidence": claim.confidence,
        })

    for key, title in SECTION_TITLES.items():
        if grouped.get(key):
            sections.append({"section": key, "title": title, "claims": grouped[key]})

    return {
        "report_type": "PERSONAL_DECISION_AND_TRANSITION_REPORT",
        "report_version": "v1-closed-world",
        "decision": {
            "phase": payload.canonical_decision.get("phase"),
            "finality": payload.canonical_decision.get("finality"),
            "can_show_recommendations": payload.canonical_decision.get("can_show_recommendations"),
        },
        "sections": sections,
    }
