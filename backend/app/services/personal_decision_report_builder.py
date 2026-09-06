from __future__ import annotations

"""Closed-world Personal Decision Report payload builder.

The builder does not research, rank, infer missing facility facts, or call an LLM.
It projects already-governed case/result data into approved report claims and then
runs the fail-closed report contract before returning anything to a renderer.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.services.canonical_decision_state import derive_canonical_decision_state
from app.services.personal_decision_report_contract import (
    ApprovedReportClaim, ClaimType, ReportClaimUse, ReportSection, enforce_report_contract,
)
from app.services.personal_decision_report_sections import normalize_report_sections


@dataclass(frozen=True)
class PersonalReportPayload:
    canonical_decision: Mapping[str, Any]
    approved_claims: tuple[ApprovedReportClaim, ...]
    claim_uses: tuple[ReportClaimUse, ...]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _claim(*, claim_id: str, claim_type: ClaimType, text: str, provenance: Sequence[str], sections: Sequence[ReportSection], confidence: str | None = None) -> ApprovedReportClaim | None:
    text = _text(text)
    provenance = tuple(_text(x) for x in provenance if _text(x))
    if not text or not provenance:
        return None
    return ApprovedReportClaim(claim_id=claim_id, claim_type=claim_type, approved_text=text, provenance_ids=provenance, allowed_sections=tuple(sections), confidence=confidence)


def build_personal_report_payload(result: Mapping[str, Any], *, case_claims: Sequence[Mapping[str, Any]] = (), research_claims: Sequence[Mapping[str, Any]] = (), facility_claims: Sequence[Mapping[str, Any]] = ()) -> PersonalReportPayload:
    """Build a renderable report using only explicit upstream authority."""
    canonical = derive_canonical_decision_state(dict(result)).to_dict()
    approved: list[ApprovedReportClaim] = []

    decision_reason = _claim(claim_id="decision:canonical-reason", claim_type=ClaimType.ENGINE_CONCLUSION, text=canonical.get("reason"), provenance=("decision:canonical",), sections=(ReportSection.WHY_RECOMMENDATION,))
    if decision_reason:
        approved.append(decision_reason)

    for i, row in enumerate(case_claims):
        claim = _claim(
            claim_id=_text(row.get("claim_id")) or f"case:{i}", claim_type=ClaimType.USER_INFORMATION,
            text=row.get("text"), provenance=tuple(row.get("provenance_ids") or ()),
            sections=normalize_report_sections(row.get("allowed_sections") or (), ReportSection.YOUR_SITUATION),
        )
        if claim:
            approved.append(claim)

    for i, row in enumerate(research_claims):
        provenance = tuple(row.get("provenance_ids") or ())
        if not provenance or not all(_text(p).startswith("research:") for p in provenance):
            continue
        claim = _claim(
            claim_id=_text(row.get("claim_id")) or f"research:{i}", claim_type=ClaimType.RESEARCH_FINDING,
            text=row.get("approved_text") or row.get("text"), provenance=provenance,
            sections=normalize_report_sections(row.get("allowed_sections") or (), ReportSection.SUCCESSFUL_TRANSITION),
            confidence=_text(row.get("confidence")) or None,
        )
        if claim:
            approved.append(claim)

    for i, row in enumerate(facility_claims):
        verified, unknown = row.get("verified") is True, row.get("unknown") is True
        if not verified and not unknown:
            continue
        default = ReportSection.BEFORE_YOU_DECIDE if unknown else ReportSection.WHY_THIS_PLACE
        claim = _claim(
            claim_id=_text(row.get("claim_id")) or f"facility:{i}",
            claim_type=ClaimType.UNKNOWN if unknown else ClaimType.VERIFIED_FACT,
            text=row.get("approved_text") or row.get("text"), provenance=tuple(row.get("provenance_ids") or ()),
            sections=normalize_report_sections(row.get("allowed_sections") or (), default),
        )
        if claim:
            approved.append(claim)

    uses = tuple(ReportClaimUse(claim_id=c.claim_id, section=c.allowed_sections[0], rendered_text=c.approved_text) for c in approved)
    report_decision = {
        "phase": canonical.get("phase"), "finality": canonical.get("finality"),
        "can_show_recommendations": canonical.get("can_show_recommendations"),
        "ranking_recalculated": False, "research_performed": False, "resolved_unknowns": [],
    }
    enforce_report_contract(approved_claims=approved, claim_uses=uses, canonical_state=canonical, report_decision=report_decision)
    return PersonalReportPayload(canonical_decision=canonical, approved_claims=tuple(approved), claim_uses=uses)
