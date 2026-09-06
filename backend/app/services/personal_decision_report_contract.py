from __future__ import annotations

"""Fail-closed contract for user-facing Personal Decision Reports.

This module is intentionally deterministic and closed-world. It does not call an LLM,
web search, research service, or ranking service. A report may only render claims that
were explicitly approved upstream and tied to provenance already present in the case,
facility evidence, Research Institute, or canonical decision state.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class ClaimType(str, Enum):
    USER_INFORMATION = "USER_INFORMATION"
    VERIFIED_FACT = "VERIFIED_FACT"
    RESEARCH_FINDING = "RESEARCH_FINDING"
    ENGINE_CONCLUSION = "ENGINE_CONCLUSION"
    UNKNOWN = "UNKNOWN"


class ReportSection(str, Enum):
    YOUR_SITUATION = "YOUR_SITUATION"
    YOUR_ROLE = "YOUR_ROLE"
    WHAT_MATTERS = "WHAT_MATTERS"
    WHY_RECOMMENDATION = "WHY_RECOMMENDATION"
    WHY_THIS_PLACE = "WHY_THIS_PLACE"
    SUCCESSFUL_TRANSITION = "SUCCESSFUL_TRANSITION"
    BEFORE_YOU_DECIDE = "BEFORE_YOU_DECIDE"


@dataclass(frozen=True)
class ApprovedReportClaim:
    claim_id: str
    claim_type: ClaimType
    approved_text: str
    provenance_ids: tuple[str, ...]
    allowed_sections: tuple[ReportSection, ...]
    confidence: str | None = None


@dataclass(frozen=True)
class ReportClaimUse:
    claim_id: str
    section: ReportSection
    rendered_text: str


@dataclass(frozen=True)
class ReportContractResult:
    valid: bool
    violations: tuple[str, ...]


class ReportContractViolation(ValueError):
    pass


def _canonical_value(state: Mapping[str, Any], key: str) -> Any:
    value = state.get(key)
    return getattr(value, "value", value)


def validate_report_contract(
    *,
    approved_claims: Sequence[ApprovedReportClaim],
    claim_uses: Sequence[ReportClaimUse],
    canonical_state: Mapping[str, Any],
    report_decision: Mapping[str, Any],
) -> ReportContractResult:
    """Validate a proposed report against upstream authority.

    The validator is deliberately strict. Text is immutable: the renderer may choose
    which approved claims to show and where, but may not paraphrase factual,
    professional, research, decision, or UNKNOWN claims. Presentation-only prose must
    live outside the claim channel and cannot assert a material fact.
    """

    violations: list[str] = []
    by_id = {claim.claim_id: claim for claim in approved_claims}

    if len(by_id) != len(approved_claims):
        violations.append("duplicate approved claim_id")

    for claim in approved_claims:
        if not claim.claim_id.strip():
            violations.append("approved claim has empty claim_id")
        if not claim.approved_text.strip():
            violations.append(f"{claim.claim_id}: approved_text is empty")
        if not claim.provenance_ids:
            violations.append(f"{claim.claim_id}: material claim has no provenance")
        if not claim.allowed_sections:
            violations.append(f"{claim.claim_id}: no allowed report section")
        if claim.claim_type is ClaimType.RESEARCH_FINDING and not any(
            source.startswith("research:") for source in claim.provenance_ids
        ):
            violations.append(f"{claim.claim_id}: research finding lacks Research Institute provenance")
        if claim.claim_type is ClaimType.ENGINE_CONCLUSION and not any(
            source.startswith("decision:") for source in claim.provenance_ids
        ):
            violations.append(f"{claim.claim_id}: engine conclusion lacks decision provenance")

    for use in claim_uses:
        approved = by_id.get(use.claim_id)
        if approved is None:
            violations.append(f"{use.claim_id}: report used a claim outside the allowlist")
            continue
        if use.section not in approved.allowed_sections:
            violations.append(f"{use.claim_id}: claim used in unauthorized section {use.section.value}")
        if use.rendered_text != approved.approved_text:
            violations.append(f"{use.claim_id}: approved material claim was altered")

    # The report is a read-only projection of canonical authority. It may never
    # upgrade/downgrade finality, visibility, phase, or recommendation authority.
    protected_pairs = {
        "phase": "phase",
        "finality": "finality",
        "can_show_recommendations": "can_show_recommendations",
    }
    for report_key, canonical_key in protected_pairs.items():
        if report_key in report_decision:
            expected = _canonical_value(canonical_state, canonical_key)
            actual = report_decision.get(report_key)
            if actual != expected:
                violations.append(
                    f"report cannot override canonical {canonical_key}: {actual!r} != {expected!r}"
                )

    # UNKNOWN is immutable. Any UNKNOWN claim that is used must remain byte-for-byte
    # the approved UNKNOWN text; the equality check above enforces this. Additionally,
    # report metadata cannot claim that unresolved items were resolved locally.
    if report_decision.get("resolved_unknowns"):
        violations.append("report layer cannot resolve UNKNOWN evidence")

    if report_decision.get("ranking_recalculated") is True:
        violations.append("report layer cannot recalculate ranking")
    if report_decision.get("research_performed") is True:
        violations.append("report layer cannot perform research")

    return ReportContractResult(valid=not violations, violations=tuple(violations))


def enforce_report_contract(**kwargs: Any) -> None:
    """Fail closed: no report leaves the service when validation fails."""

    result = validate_report_contract(**kwargs)
    if not result.valid:
        raise ReportContractViolation("; ".join(result.violations))
