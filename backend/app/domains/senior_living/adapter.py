"""Adapter between the current Senior Living decision payloads and OPTIME Core.

The adapter is deliberately one-way at this stage: it translates existing
Senior Living outputs into neutral contracts without changing production
selection, ordering, scoring, or explanations.
"""

from __future__ import annotations

from typing import Any, Mapping

from app.core.contracts import (
    AuditTrace,
    ClarificationQuestion,
    DecisionOption,
    DecisionParty,
    EligibilityStatus,
    EvidenceRecord,
    EvidenceState,
    Explanation,
    PairEvaluation,
    Requirement,
    RequirementEvaluation,
    RequirementLevel,
    TradeOff,
)


_REQUIREMENT_LEVEL_MAP = {
    "REQUIRED": RequirementLevel.MUST,
    "HIGH": RequirementLevel.IMPORTANT,
    "MEDIUM": RequirementLevel.IMPORTANT,
    "PREFERENCE": RequirementLevel.NICE_TO_HAVE,
}

_ELIGIBILITY_MAP = {
    "ELIGIBLE": EligibilityStatus.ELIGIBLE,
    "POTENTIALLY_ELIGIBLE": EligibilityStatus.ELIGIBLE_WITH_UNKNOWNS,
    "INSUFFICIENT_EVIDENCE": EligibilityStatus.ELIGIBLE_WITH_UNKNOWNS,
    "INELIGIBLE": EligibilityStatus.NOT_ELIGIBLE,
}


def requirement_from_patient_need(need: Mapping[str, Any]) -> Requirement:
    raw_level = str(need.get("requirement_level") or "PREFERENCE").upper()
    return Requirement(
        requirement_id=str(need.get("parameter_id") or "UNKNOWN"),
        label=str(need.get("need_text") or need.get("parameter_id") or "Unknown requirement"),
        level=_REQUIREMENT_LEVEL_MAP.get(raw_level, RequirementLevel.NICE_TO_HAVE),
        desired_value=need.get("desired_value"),
        acceptable_values=tuple(need.get("acceptable_values") or ()),
        source=str(need.get("user_evidence_source") or "UNKNOWN"),
        rationale=str(need.get("need_text") or ""),
    )


def party_from_patient_profile(profile: Mapping[str, Any], party_id: str = "CURRENT_CASE") -> DecisionParty:
    return DecisionParty(
        party_id=party_id,
        party_type="SENIOR_LIVING_SEEKER",
        attributes={
            "profile_key": profile.get("profile_key"),
            "location_city": profile.get("location_city"),
            "need_tags": tuple(profile.get("need_tags") or ()),
        },
    )


def option_from_facility_result(result: Mapping[str, Any]) -> DecisionOption:
    option_id = str(result.get("canonical_facility_id") or result.get("facility_id") or "UNKNOWN")
    return DecisionOption(
        option_id=option_id,
        option_type="SENIOR_LIVING_FACILITY",
        label=str(result.get("facility_name") or option_id),
        attributes={
            "city": result.get("city"),
            "state": result.get("state"),
            "canonical_type": result.get("canonical_type"),
        },
    )


def _evidence_state(status: str) -> EvidenceState:
    normalized = status.upper()
    if normalized == "MATCH":
        return EvidenceState.YES
    if normalized in {"GAP", "VERIFIED_GAP"}:
        return EvidenceState.NO
    if normalized == "LIMITED":
        return EvidenceState.LIMITED
    if normalized == "CONFLICTING":
        return EvidenceState.CONFLICTING
    return EvidenceState.UNKNOWN


def _requirement_evaluations(result: Mapping[str, Any]) -> tuple[RequirementEvaluation, ...]:
    eligibility = result.get("eligibility") or {}
    groups = [
        ("matched_needs", True),
        ("unmet_verified_needs", False),
        ("unknown_critical_needs", None),
        ("unknown_noncritical_needs", None),
    ]
    rows: list[RequirementEvaluation] = []
    seen: set[str] = set()

    for group_name, matched in groups:
        for item in eligibility.get(group_name) or ():
            requirement_id = str(item.get("parameter_id") or "UNKNOWN")
            if requirement_id in seen:
                continue
            seen.add(requirement_id)
            status = str(item.get("status") or ("MATCH" if matched else "UNKNOWN"))
            evidence = EvidenceRecord(
                option_id=str(result.get("canonical_facility_id") or "UNKNOWN"),
                requirement_id=requirement_id,
                state=_evidence_state(status),
                value=item.get("raw_value"),
                source=str(item.get("source") or "UNKNOWN"),
                explanation=str(item.get("reason") or item.get("need_text") or ""),
            )
            rows.append(
                RequirementEvaluation(
                    requirement_id=requirement_id,
                    state=evidence.state,
                    matched=matched,
                    explanation=evidence.explanation,
                    evidence=(evidence,),
                )
            )
    return tuple(rows)


def _explanation(result: Mapping[str, Any]) -> Explanation:
    raw = result.get("explanation") or {}
    questions = tuple(
        ClarificationQuestion(
            question_id=f"Q-{index + 1}",
            target_party="OPTION_PROVIDER",
            question=str(question),
            reason="Missing or unverified information",
        )
        for index, question in enumerate(raw.get("questions_to_confirm") or raw.get("questions") or ())
    )
    return Explanation(
        why_presented=tuple(raw.get("why_this_facility") or raw.get("why_presented") or ()),
        advantages=tuple(raw.get("strengths") or raw.get("advantages") or ()),
        disadvantages=tuple(raw.get("trade_offs") or raw.get("disadvantages") or ()),
        unknowns=tuple(raw.get("unknowns") or ()),
        questions=questions,
    )


def pair_evaluation_from_patient_result(
    profile: Mapping[str, Any],
    result: Mapping[str, Any],
    party_id: str = "CURRENT_CASE",
) -> PairEvaluation:
    status = str(result.get("eligibility_status") or "INSUFFICIENT_EVIDENCE")
    trade_off_texts = tuple((result.get("explanation") or {}).get("trade_offs") or ())
    return PairEvaluation(
        party=party_from_patient_profile(profile, party_id=party_id),
        option=option_from_facility_result(result),
        eligibility=_ELIGIBILITY_MAP.get(status, EligibilityStatus.ELIGIBLE_WITH_UNKNOWNS),
        requirement_evaluations=_requirement_evaluations(result),
        explanation=_explanation(result),
        trade_offs=tuple(
            TradeOff(subject="option", benefit="", cost=str(text))
            for text in trade_off_texts
        ),
        audit=AuditTrace(
            rules_applied=("senior_living_legacy_decision_engine",),
            evidence_sources=tuple(result.get("evidence_sources") or ()),
            warnings=tuple(result.get("warnings") or ()),
        ),
    )
