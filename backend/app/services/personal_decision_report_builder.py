from __future__ import annotations

"""Closed-world builder for the Personal Decision & Transition Report.

This module has no LLM, web, research, or ranking access. It reads only a
questionnaire_state + natural_language_query + an already-computed decision-engine
result (the same dict `run_patient_decision_engine` returns) and projects a subset of
that result into ApprovedReportClaim objects. It never adds a claim that isn't a direct,
traceable read of a field already present in that result -- it renders, it does not
research, decide, or interpret. Every produced payload is validated (fail-closed)
through personal_decision_report_contract.enforce_report_contract before it is returned.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from app.services.personal_decision_report_contract import (
    ApprovedReportClaim,
    ClaimType,
    ReportClaimUse,
    ReportSection,
    enforce_report_contract,
)


class UserRole(str, Enum):
    """A real decision-relevant parameter, not a wording toggle.

    Derived once from questionnaire_state["relationship"] and carried through the
    payload; presentation text is selected by role, it is never generated per-request.
    """

    SELF = "SELF"
    FAMILY_MEMBER = "FAMILY_MEMBER"
    OTHER = "OTHER"


_SELF_RELATIONSHIP_VALUES = {"self", "myself", "i am the resident", "me", "resident"}

_SITUATION_FIELD_LABELS = {
    "assistanceLevel": "Assistance needed",
    "memoryStatus": "Memory/cognitive status noted",
    "distanceFromFamily": "Preferred distance from family",
    "budget": "Monthly budget",
    "entranceFeeTolerance": "Willing to pay an entrance fee",
}


def derive_user_role(questionnaire_state: Mapping[str, Any]) -> UserRole:
    raw = str(questionnaire_state.get("relationship") or "").strip().lower()
    if not raw:
        return UserRole.OTHER
    if raw in _SELF_RELATIONSHIP_VALUES:
        return UserRole.SELF
    return UserRole.FAMILY_MEMBER


_ROLE_TEXT = {
    UserRole.SELF: "You are searching for care for yourself. The recommendations below reflect the needs and preferences you provided.",
    UserRole.FAMILY_MEMBER: "You are a family member helping with this decision. The recommendations below reflect the needs your relative has and the information you provided on their behalf.",
    UserRole.OTHER: "Your relationship to the person this search is for was not specified.",
}


@dataclass(frozen=True)
class CandidateReportView:
    canonical_facility_id: str
    facility_name: str
    rank_position: int | None
    match_band: str | None
    match_score: float | None
    claims: tuple[ApprovedReportClaim, ...]
    claim_uses: tuple[ReportClaimUse, ...]


@dataclass(frozen=True)
class PersonalReportPayload:
    user_role: UserRole
    report_ready: bool
    claims: tuple[ApprovedReportClaim, ...]
    claim_uses: tuple[ReportClaimUse, ...]
    candidates: tuple[CandidateReportView, ...]
    omitted_sections: tuple[str, ...]


def _claim(claim_id, claim_type, text, provenance_ids, sections, confidence=None):
    return ApprovedReportClaim(
        claim_id=claim_id,
        claim_type=claim_type,
        approved_text=text,
        provenance_ids=tuple(provenance_ids),
        allowed_sections=tuple(sections),
        confidence=confidence,
    )


def _use(claim: ApprovedReportClaim, section: ReportSection) -> ReportClaimUse:
    return ReportClaimUse(claim_id=claim.claim_id, section=section, rendered_text=claim.approved_text)


def _situation_claims(questionnaire_state: Mapping[str, Any]) -> list[ApprovedReportClaim]:
    claims: list[ApprovedReportClaim] = []
    for field_key, label in _SITUATION_FIELD_LABELS.items():
        value = questionnaire_state.get(field_key)
        if value in (None, ""):
            continue
        text = f"{label}: {value}"
        claims.append(
            _claim(
                f"case:{field_key}",
                ClaimType.USER_INFORMATION,
                text,
                [f"case:questionnaire.{field_key}"],
                [ReportSection.YOUR_SITUATION],
            )
        )
    return claims


def _role_claim(role: UserRole) -> ApprovedReportClaim:
    return _claim(
        "case:role",
        ClaimType.USER_INFORMATION,
        _ROLE_TEXT[role],
        ["case:questionnaire.relationship"],
        [ReportSection.YOUR_ROLE],
    )


def _what_matters_claims(needs: Sequence[Mapping[str, Any]]) -> list[ApprovedReportClaim]:
    claims: list[ApprovedReportClaim] = []
    for need in needs:
        if str(need.get("requirement_level") or "") not in {"REQUIRED", "HIGH"}:
            continue
        parameter_id = str(need.get("parameter_id") or "")
        need_text = str(need.get("need_text") or parameter_id)
        claims.append(
            _claim(
                f"decision:need.{parameter_id}",
                ClaimType.ENGINE_CONCLUSION,
                need_text,
                [f"decision:needs.{parameter_id}"],
                [ReportSection.WHAT_MATTERS],
            )
        )
    return claims


def _why_recommendation_claims(decision_intelligence: Mapping[str, Any]) -> list[ApprovedReportClaim]:
    claims: list[ApprovedReportClaim] = []
    strategy_universe = decision_intelligence.get("strategy_universe") or {}
    leading = strategy_universe.get("rank_one_strategy_ids") or []
    if leading:
        text = "Based on the needs identified, the leading care strategy is: " + ", ".join(leading) + "."
        claims.append(
            _claim(
                "decision:leading_strategy",
                ClaimType.ENGINE_CONCLUSION,
                text,
                ["decision:strategy_universe.rank_one_strategy_ids"],
                [ReportSection.WHY_RECOMMENDATION],
            )
        )
    finality = decision_intelligence.get("decision_finality")
    if finality:
        claims.append(
            _claim(
                "decision:finality",
                ClaimType.ENGINE_CONCLUSION,
                f"This recommendation's current status is: {finality}.",
                ["decision:canonical_decision_state.finality"],
                [ReportSection.WHY_RECOMMENDATION],
            )
        )
    return claims


def _candidate_claims(row: Mapping[str, Any]) -> tuple[list[ApprovedReportClaim], list[ApprovedReportClaim]]:
    """Returns (why_this_place_claims, before_you_decide_claims) for one ranked candidate."""

    facility_id = str(row.get("canonical_facility_id") or "")
    explanation = row.get("explanation") or {}
    fit_claims: list[ApprovedReportClaim] = []
    unknown_claims: list[ApprovedReportClaim] = []

    for index, text in enumerate(explanation.get("why_matches") or []):
        fit_claims.append(
            _claim(
                f"decision:{facility_id}.why_matches.{index}",
                ClaimType.ENGINE_CONCLUSION,
                str(text),
                [f"decision:candidate.{facility_id}.why_matches"],
                [ReportSection.WHY_THIS_PLACE],
            )
        )
    for index, text in enumerate(explanation.get("concerns") or []):
        fit_claims.append(
            _claim(
                f"decision:{facility_id}.concern.{index}",
                ClaimType.ENGINE_CONCLUSION,
                str(text),
                [f"decision:candidate.{facility_id}.concerns"],
                [ReportSection.WHY_THIS_PLACE],
            )
        )

    regulatory = row.get("regulatory_history") or {}
    latest_grade = regulatory.get("latest_known_grade")
    if latest_grade not in (None, "", "UNKNOWN"):
        source = regulatory.get("source_url") or "facility:regulatory_history"
        fit_claims.append(
            _claim(
                f"facility:{facility_id}.latest_grade",
                ClaimType.VERIFIED_FACT,
                f"Most recent inspection grade on file: {latest_grade}.",
                [source],
                [ReportSection.WHY_THIS_PLACE],
            )
        )

    for index, text in enumerate(explanation.get("needs_verification") or []):
        unknown_claims.append(
            _claim(
                f"decision:{facility_id}.needs_verification.{index}",
                ClaimType.UNKNOWN,
                str(text),
                [f"decision:candidate.{facility_id}.needs_verification"],
                [ReportSection.BEFORE_YOU_DECIDE],
            )
        )
    for index, parameter_id in enumerate(row.get("unknown_critical_needs") or []):
        unknown_claims.append(
            _claim(
                f"facility:{facility_id}.unknown.{parameter_id}",
                ClaimType.UNKNOWN,
                f"{parameter_id.replace('_', ' ').title()} has not been verified for this facility.",
                [f"facility:{facility_id}.{parameter_id}:UNKNOWN"],
                [ReportSection.BEFORE_YOU_DECIDE],
            )
        )
    return fit_claims, unknown_claims


def build_personal_decision_report(
    *,
    questionnaire_state: Mapping[str, Any],
    natural_language_query: str,
    decision_result: Mapping[str, Any],
    max_candidates: int = 3,
) -> PersonalReportPayload:
    del natural_language_query  # not read for claim content -- claims come from decision_result only

    profile = decision_result.get("patient_needs_profile") or {}
    decision_intelligence = profile.get("decision_intelligence") or decision_result.get("decision_intelligence") or {}
    canonical_state = decision_intelligence.get("canonical_decision_state") or {}
    can_show = bool(canonical_state.get("can_show_recommendations"))

    role = derive_user_role(questionnaire_state)
    claims: list[ApprovedReportClaim] = []
    uses: list[ReportClaimUse] = []
    omitted = ["SUCCESSFUL_TRANSITION"]  # no Research Institute claim source exists yet; never fabricated

    role_claim = _role_claim(role)
    claims.append(role_claim)
    uses.append(_use(role_claim, ReportSection.YOUR_ROLE))

    for claim in _situation_claims(questionnaire_state):
        claims.append(claim)
        uses.append(_use(claim, ReportSection.YOUR_SITUATION))

    for claim in _what_matters_claims(profile.get("needs") or []):
        claims.append(claim)
        uses.append(_use(claim, ReportSection.WHAT_MATTERS))

    for claim in _why_recommendation_claims(decision_intelligence):
        claims.append(claim)
        uses.append(_use(claim, ReportSection.WHY_RECOMMENDATION))

    candidates: list[CandidateReportView] = []
    if can_show:
        rows = list(decision_result.get("results") or [])[:max_candidates]
        for row in rows:
            fit_claims, unknown_claims = _candidate_claims(row)
            row_claims = fit_claims + unknown_claims
            row_uses = [
                _use(c, ReportSection.WHY_THIS_PLACE if c in fit_claims else ReportSection.BEFORE_YOU_DECIDE)
                for c in row_claims
            ]
            claims.extend(row_claims)
            uses.extend(row_uses)
            candidates.append(
                CandidateReportView(
                    canonical_facility_id=str(row.get("canonical_facility_id") or ""),
                    facility_name=str(row.get("facility_name") or ""),
                    rank_position=row.get("rank_position"),
                    match_band=row.get("match_band"),
                    match_score=row.get("match_score"),
                    claims=tuple(row_claims),
                    claim_uses=tuple(row_uses),
                )
            )
    else:
        reason = str(canonical_state.get("reason") or "More information is needed before a recommendation can be shown.")
        pending_claim = _claim(
            "decision:pending_reason",
            ClaimType.UNKNOWN,
            reason,
            ["decision:canonical_decision_state.reason"],
            [ReportSection.BEFORE_YOU_DECIDE],
        )
        claims.append(pending_claim)
        uses.append(_use(pending_claim, ReportSection.BEFORE_YOU_DECIDE))

    report_decision = {
        "phase": canonical_state.get("phase"),
        "finality": canonical_state.get("finality"),
        "can_show_recommendations": canonical_state.get("can_show_recommendations"),
        "resolved_unknowns": False,
        "ranking_recalculated": False,
        "research_performed": False,
    }

    enforce_report_contract(
        approved_claims=claims,
        claim_uses=uses,
        canonical_state=canonical_state,
        report_decision=report_decision,
    )

    return PersonalReportPayload(
        user_role=role,
        report_ready=can_show,
        claims=tuple(claims),
        claim_uses=tuple(uses),
        candidates=tuple(candidates),
        omitted_sections=tuple(omitted),
    )
