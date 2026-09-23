from __future__ import annotations

"""Canonical decision-state model for OPTIME Nursing.

All recommendation control decisions must be read from ``canonical_decision_state``.
The older readiness, execution, visibility and finality fields are compatibility mirrors
only; they may be emitted for older clients, but they are never decision authorities.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Iterable


class DecisionPhase(str, Enum):
    CLIENT_INPUT_REQUIRED = "CLIENT_INPUT_REQUIRED"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    MUST_EVALUATION = "MUST_EVALUATION"
    AI_RANKING = "AI_RANKING"
    PREFERENCE_VERIFICATION = "PREFERENCE_VERIFICATION"
    PROVISIONAL_RECOMMENDATION = "PROVISIONAL_RECOMMENDATION"
    FINAL_RECOMMENDATION = "FINAL_RECOMMENDATION"
    # The MUST gate ran and produced eligible candidates, but the model that weighs them
    # against what this family said did not. They are shown as a set, never as an order,
    # with the degradation stated on the result rather than inferred from a missing field.
    UNRANKED_ELIGIBLE_SET = "UNRANKED_ELIGIBLE_SET"
    SYSTEM_BLOCKED = "SYSTEM_BLOCKED"


class ClientState(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    COMPLETE = "COMPLETE"


class EvidenceState(str, Enum):
    MATERIAL_GAPS = "MATERIAL_GAPS"
    SUFFICIENT = "SUFFICIENT"


class MustState(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PENDING = "PENDING"
    PASS = "PASS"
    NO_ELIGIBLE_CANDIDATES = "NO_ELIGIBLE_CANDIDATES"


class RankingState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    # The model was unavailable and the hard criteria carried the result on their own.
    # Distinct from NOT_STARTED, which is what the fallback used to collapse into, and
    # distinct from COMPLETE, which would claim a weighing that never happened.
    UNAVAILABLE_HARD_CRITERIA_ONLY = "UNAVAILABLE_HARD_CRITERIA_ONLY"


class PreferenceState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


class DecisionFinality(str, Enum):
    NONE = "NONE"
    PROVISIONAL = "PROVISIONAL"
    FINAL = "FINAL"
    # Not a weaker PROVISIONAL: provisional means ranked but awaiting verification, this
    # means never ranked at all. Collapsing the two would let a degraded answer be read as
    # an ordinary one that simply needs confirming.
    DEGRADED_UNRANKED = "DEGRADED_UNRANKED"


class SystemHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CanonicalDecisionState:
    phase: DecisionPhase
    client: ClientState
    evidence: EvidenceState
    must: MustState
    ranking: RankingState
    preferences: PreferenceState
    finality: DecisionFinality
    system: SystemHealth
    next_action: str
    reason: str
    legacy_readiness: str
    legacy_recommendation_execution_allowed: bool | None
    legacy_recommendation_visibility: str
    legacy_decision_finality: str

    @property
    def can_show_recommendations(self) -> bool:
        return self.phase in {
            DecisionPhase.PROVISIONAL_RECOMMENDATION,
            DecisionPhase.FINAL_RECOMMENDATION,
            DecisionPhase.UNRANKED_ELIGIBLE_SET,
        }

    @property
    def is_degraded_result(self) -> bool:
        """True when the candidates shown passed the hard criteria and nothing more.

        Every caller that renders a shortlist must branch on this. A degraded set carries
        no order, so presenting it as "best first" would assert work the system did not do.
        """
        return self.phase is DecisionPhase.UNRANKED_ELIGIBLE_SET

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["phase"] = self.phase.value
        payload["client"] = self.client.value
        payload["evidence"] = self.evidence.value
        payload["must"] = self.must.value
        payload["ranking"] = self.ranking.value
        payload["preferences"] = self.preferences.value
        payload["finality"] = self.finality.value
        payload["system"] = self.system.value
        payload["can_show_recommendations"] = self.can_show_recommendations
        payload["is_degraded_result"] = self.is_degraded_result
        payload["version"] = "canonical-decision-state-v2-authority"
        payload["authoritative"] = True
        return payload


class CanonicalDecisionStateError(RuntimeError):
    """Raised when a control boundary receives a payload not sealed by the authority."""


def canonical_state_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the authoritative state or fail closed.

    Control-flow callers must not silently fall back to legacy fields.  Requiring the
    authoritative marker makes a missing finalization step observable instead of letting
    a stale compatibility mirror decide whether a family sees recommendations.
    """

    decision = _decision_payload(result)
    state = decision.get("canonical_decision_state")
    if not isinstance(state, dict) or state.get("authoritative") is not True:
        raise CanonicalDecisionStateError("CANONICAL_DECISION_STATE_NOT_AUTHORITATIVE")
    return state


def canonical_can_show_recommendations(result: Dict[str, Any]) -> bool:
    return canonical_state_payload(result).get("can_show_recommendations") is True


def canonical_client_is_complete(result: Dict[str, Any]) -> bool:
    return _upper(canonical_state_payload(result).get("client")) == ClientState.COMPLETE.value


def canonical_is_final(result: Dict[str, Any]) -> bool:
    return _upper(canonical_state_payload(result).get("finality")) == DecisionFinality.FINAL.value


def _upper(value: Any, default: str = "") -> str:
    text = str(value or default).strip().upper()
    return text


def _decision_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    value = result.get("decision_intelligence")
    return value if isinstance(value, dict) else {}


def _human_payload(decision: Dict[str, Any]) -> Dict[str, Any]:
    value = decision.get("human_intelligence")
    return value if isinstance(value, dict) else {}


def _material_client_blockers(human: Dict[str, Any]) -> list[Dict[str, Any]]:
    policy = human.get("canonical_gap_policy")
    if isinstance(policy, dict) and policy.get("authority") == "DETERMINISTIC_POLICY":
        # Both Guardian and source-backed semantic gaps have already been governed
        # here. Reading only Guardian rows silently discarded semantic conflicts.
        return [row for row in policy.get("assessments") or [] if isinstance(row, dict) and row.get("classification") == "BLOCKING"]
    guardian = human.get("readiness_guardian")
    if not isinstance(guardian, dict):
        return []
    blockers = guardian.get("client_owned_blockers")
    return [row for row in blockers or [] if isinstance(row, dict)]


def _candidate_rows(result: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [row for row in result.get("results") or [] if isinstance(row, dict)]


def _pending_must_count(result: Dict[str, Any], decision: Dict[str, Any]) -> int:
    explicit = result.get("must_pending_verification_count")
    if isinstance(explicit, int):
        return explicit
    gate = decision.get("must_gate") if isinstance(decision.get("must_gate"), dict) else {}
    explicit = gate.get("pending_verification")
    if isinstance(explicit, int):
        return explicit
    count = 0
    for row in _candidate_rows(result):
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        if _upper(fit.get("hard_gate")) == "PENDING_VERIFICATION":
            count += 1
    return count


def _must_counts(result: Dict[str, Any], decision: Dict[str, Any]) -> tuple[int, int, int]:
    gate = decision.get("must_gate") if isinstance(decision.get("must_gate"), dict) else {}

    def read(name: str, result_name: str) -> int:
        value = result.get(result_name)
        if isinstance(value, int):
            return value
        value = gate.get(name)
        return value if isinstance(value, int) else 0

    return (
        read("eligible", "must_eligible_count"),
        read("pending_verification", "must_pending_verification_count"),
        read("rejected", "must_rejected_count"),
    )


def _preference_counts(decision: Dict[str, Any]) -> tuple[int, int]:
    """Raw (nice_complete_candidate_count, verification_required_count), independent
    of the collapsed COMPLETE/PARTIAL state -- callers that need to distinguish "at
    least one candidate is ready to show" from "every checked candidate is fully
    resolved" read these directly rather than the binary PreferenceState.
    """
    pipeline = decision.get("facility_selection_pipeline")
    if not isinstance(pipeline, dict):
        return 0, 0
    dynamic = pipeline.get("dynamic_preferences")
    if not isinstance(dynamic, dict):
        return 0, 0
    return int(dynamic.get("nice_complete_candidate_count") or 0), int(dynamic.get("verification_required_count") or 0)


def _preference_state(decision: Dict[str, Any]) -> PreferenceState:
    pipeline = decision.get("facility_selection_pipeline")
    if not isinstance(pipeline, dict):
        return PreferenceState.NOT_STARTED
    dynamic = pipeline.get("dynamic_preferences")
    if not isinstance(dynamic, dict):
        return PreferenceState.NOT_STARTED
    preference_count = int(dynamic.get("preference_count") or 0)
    if preference_count == 0:
        return PreferenceState.COMPLETE
    complete, verification_required = _preference_counts(decision)
    if complete > 0 and verification_required == 0:
        return PreferenceState.COMPLETE
    return PreferenceState.PARTIAL


def _ranking_state(decision: Dict[str, Any]) -> RankingState:
    pipeline = decision.get("facility_selection_pipeline")
    if not isinstance(pipeline, dict):
        return RankingState.NOT_STARTED
    ai = pipeline.get("ai_ranking") if isinstance(pipeline.get("ai_ranking"), dict) else {}
    status = _upper(ai.get("status"))
    # DETERMINISTIC_THIN_EVIDENCE_WATERFALL (must_ai_nice_pipeline.py) is a
    # deliberate, complete ranking -- AI judgment is skipped because the candidate
    # pool has no NICE preferences and no known rating/grade/disciplinary record for
    # it to differentiate on, not because ranking failed or is unavailable.
    if status in {"AI_RANKED", "AI_BATCH_RANKED", "DETERMINISTIC_THIN_EVIDENCE_WATERFALL"}:
        return RankingState.COMPLETE
    if status in {"STARTED", "RUNNING", "IN_PROGRESS"}:
        return RankingState.RUNNING
    # DETERMINISTIC_FALLBACK was deliberately excluded from the FAILED set below -- it is
    # not a failure -- but nothing then claimed it, so it fell through to NOT_STARTED and a
    # completed MUST gate was hidden behind "requires validated AI ranking". 374 eligible
    # candidates, nothing shown, and no message saying why.
    if status in {"DETERMINISTIC_FALLBACK", "REQUIRED_BUT_UNAVAILABLE", "AI_RANKING_ERROR", "FAILED"}:
        return RankingState.UNAVAILABLE_HARD_CRITERIA_ONLY
    if status and status not in {"NO_MUST_ELIGIBLE_CANDIDATES"}:
        return RankingState.FAILED
    if pipeline.get("ai_ranking_fail_closed") is True:
        return RankingState.FAILED
    return RankingState.NOT_STARTED


def _system_failure(decision: Dict[str, Any], human: Dict[str, Any]) -> tuple[SystemHealth, str]:
    # Optional ranking failure does not erase established client facts. Failed
    # narrative extraction is different: there is no established intake to match.
    intake = human.get("intake_resolution") or {}
    if intake.get("status") == "UNAVAILABLE" and intake.get("narrative_extraction_required") is True:
        return SystemHealth.BLOCKED, "narrative intake interpretation unavailable; preserve answers and retry"
    return SystemHealth.HEALTHY, ""


def derive_canonical_decision_state(result: Dict[str, Any]) -> CanonicalDecisionState:
    """Derive the proposed state machine from today's payload without mutating it.

    This adapter deliberately treats legacy fields as observations, not authority. When
    legacy fields conflict, material client blockers, governed MUST counts and validated
    AI-ranking status take precedence so the divergence is visible in shadow telemetry.
    """

    decision = _decision_payload(result)
    human = _human_payload(decision)
    legacy_readiness = _upper(human.get("decision_readiness") or decision.get("decision_readiness"), "UNKNOWN")
    legacy_execution = decision.get("recommendation_execution_allowed")
    if not isinstance(legacy_execution, bool):
        legacy_execution = None
    legacy_visibility = _upper(decision.get("recommendation_visibility"), "UNKNOWN")
    legacy_finality = _upper(decision.get("decision_finality"), "UNKNOWN")

    blockers = _material_client_blockers(human)
    system, system_reason = _system_failure(decision, human)
    eligible, pending, rejected = _must_counts(result, decision)
    ranking = _ranking_state(decision)
    preferences = _preference_state(decision)
    # Unverified MUSTs remain research candidates; only verified passes can rank.
    rankable_count = eligible

    if blockers and system is not SystemHealth.BLOCKED:
        return CanonicalDecisionState(
            phase=DecisionPhase.CLIENT_INPUT_REQUIRED,
            client=ClientState.INCOMPLETE,
            evidence=EvidenceState.MATERIAL_GAPS,
            must=MustState.NOT_EVALUATED,
            ranking=RankingState.NOT_STARTED,
            preferences=PreferenceState.NOT_STARTED,
            finality=DecisionFinality.NONE,
            system=SystemHealth.HEALTHY,
            next_action="ASK_CLIENT",
            reason="material client-owned blockers remain unresolved",
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    if system is SystemHealth.BLOCKED:
        return CanonicalDecisionState(
            phase=DecisionPhase.SYSTEM_BLOCKED,
            client=ClientState.INCOMPLETE,
            evidence=EvidenceState.MATERIAL_GAPS if pending else EvidenceState.SUFFICIENT,
            must=MustState.PENDING if pending else (MustState.PASS if eligible else MustState.NOT_EVALUATED),
            ranking=ranking,
            preferences=preferences,
            finality=DecisionFinality.NONE,
            system=SystemHealth.BLOCKED,
            next_action="RECOVER_SYSTEM",
            reason=system_reason,
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    # Ranking cannot turn missing MUST evidence into a verified pass.
    if pending > 0 and eligible == 0:
        return CanonicalDecisionState(
            phase=DecisionPhase.EVIDENCE_COLLECTION,
            client=ClientState.COMPLETE,
            evidence=EvidenceState.MATERIAL_GAPS,
            must=MustState.PENDING,
            ranking=RankingState.NOT_STARTED,
            preferences=PreferenceState.NOT_STARTED,
            finality=DecisionFinality.NONE,
            system=SystemHealth.HEALTHY,
            next_action="RESEARCH_PROVIDER_EVIDENCE",
            reason=f"{pending} candidate(s) still have unresolved MUST evidence",
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    if rankable_count == 0 and (rejected > 0 or legacy_readiness in {"READY", "NEEDS_RESEARCH"}):
        return CanonicalDecisionState(
            phase=DecisionPhase.MUST_EVALUATION,
            client=ClientState.COMPLETE,
            evidence=EvidenceState.SUFFICIENT,
            must=MustState.NO_ELIGIBLE_CANDIDATES,
            ranking=RankingState.NOT_STARTED,
            preferences=PreferenceState.NOT_STARTED,
            finality=DecisionFinality.NONE,
            system=SystemHealth.HEALTHY,
            next_action="EXPAND_OR_REVISE_STRATEGY",
            reason="MUST evaluation produced no eligible candidate",
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    # Hard criteria carried the result. Show the eligible set, do not order it, and say
    # plainly that the deep work did not run -- a family is better served by "these twelve
    # meet your requirements, we could not study them today" than by an empty screen.
    #
    # Only genuinely eligible candidates are shown, and the pending ones are dropped from
    # the list rather than blocking it. The normal path does display a pending candidate
    # with a note, but only because the model assessed it first; here nothing assessed
    # anything, and a family who needs medication support must not be sent to communities
    # whose ability to provide it is merely unknown. Requiring pending==0 to degrade was the
    # first attempt and it was too blunt: an ADL search with 350 eligible and 24 unverified
    # hid all 350. Excluding the 24 keeps the safety property without discarding the work.
    if eligible > 0 and ranking is RankingState.UNAVAILABLE_HARD_CRITERIA_ONLY:
        return CanonicalDecisionState(
            phase=DecisionPhase.UNRANKED_ELIGIBLE_SET,
            client=ClientState.COMPLETE,
            evidence=EvidenceState.SUFFICIENT,
            must=MustState.PASS,
            ranking=ranking,
            preferences=PreferenceState.NOT_STARTED,
            finality=DecisionFinality.DEGRADED_UNRANKED,
            system=SystemHealth.DEGRADED,
            next_action="SHOW_UNRANKED_ELIGIBLE_SET_WITH_DEGRADATION_NOTICE",
            reason=(
                f"{eligible} candidate(s) meet the stated hard criteria; the ranking model "
                "was unavailable, so they are shown unordered and unstudied"
                + (f", and {pending} unverified candidate(s) are withheld" if pending else "")
            ),
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    if rankable_count > 0 and ranking is not RankingState.COMPLETE:
        return CanonicalDecisionState(
            phase=DecisionPhase.AI_RANKING,
            client=ClientState.COMPLETE,
            evidence=EvidenceState.SUFFICIENT,
            must=MustState.PASS if pending == 0 else MustState.PENDING,
            ranking=ranking,
            preferences=PreferenceState.NOT_STARTED,
            finality=DecisionFinality.NONE,
            system=SystemHealth.HEALTHY,
            next_action="RUN_AI_RANKING",
            reason=f"{rankable_count} MUST-pass or pending-verification candidate(s) require validated AI ranking",
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    # NICE preferences are a ranking/labeling signal, not a visibility gate: more
    # confirmed matches can only raise a candidate's standing (via finality, or via
    # ranking elsewhere) -- their absence never blocks a validated MUST-pass,
    # fully-ranked shortlist from being shown. PREFERENCE_VERIFICATION is therefore
    # unreachable once rankable_count>0 and ranking is complete; preferences only
    # decide FINAL vs PROVISIONAL below, never whether anything is shown at all.
    # Pending MUST candidates stay in the research queue.
    if rankable_count > 0 and ranking is RankingState.COMPLETE:
        finality = DecisionFinality.FINAL if preferences is PreferenceState.COMPLETE and pending == 0 else DecisionFinality.PROVISIONAL
        phase = DecisionPhase.FINAL_RECOMMENDATION if finality is DecisionFinality.FINAL else DecisionPhase.PROVISIONAL_RECOMMENDATION
        return CanonicalDecisionState(
            phase=phase,
            client=ClientState.COMPLETE,
            evidence=EvidenceState.SUFFICIENT if finality is DecisionFinality.FINAL else EvidenceState.MATERIAL_GAPS,
            must=MustState.PASS if pending == 0 else MustState.PENDING,
            ranking=RankingState.COMPLETE,
            preferences=preferences,
            finality=finality,
            system=SystemHealth.HEALTHY,
            next_action="SHOW_FINAL_RECOMMENDATION" if finality is DecisionFinality.FINAL else "SHOW_PROVISIONAL_RECOMMENDATION",
            reason="validated MUST gate and AI ranking are complete",
            legacy_readiness=legacy_readiness,
            legacy_recommendation_execution_allowed=legacy_execution,
            legacy_recommendation_visibility=legacy_visibility,
            legacy_decision_finality=legacy_finality,
        )

    return CanonicalDecisionState(
        phase=DecisionPhase.CLIENT_INPUT_REQUIRED,
        client=ClientState.INCOMPLETE,
        evidence=EvidenceState.MATERIAL_GAPS,
        must=MustState.NOT_EVALUATED,
        ranking=RankingState.NOT_STARTED,
        preferences=PreferenceState.NOT_STARTED,
        finality=DecisionFinality.NONE,
        system=SystemHealth.DEGRADED,
        next_action="RESOLVE_STATE_AMBIGUITY",
        reason="legacy payload does not contain enough governed state to advance safely",
        legacy_readiness=legacy_readiness,
        legacy_recommendation_execution_allowed=legacy_execution,
        legacy_recommendation_visibility=legacy_visibility,
        legacy_decision_finality=legacy_finality,
    )


def legacy_state_conflicts(state: CanonicalDecisionState) -> list[str]:
    """Return shadow diagnostics for contradictions in legacy state fields."""

    conflicts: list[str] = []
    if state.phase is DecisionPhase.CLIENT_INPUT_REQUIRED and state.legacy_readiness in {"READY", "NEEDS_RESEARCH"}:
        conflicts.append("LEGACY_READINESS_ADVANCES_WITH_CLIENT_BLOCKERS")
    if state.can_show_recommendations and state.legacy_recommendation_execution_allowed is False:
        conflicts.append("LEGACY_EXECUTION_BLOCKS_CANONICAL_RECOMMENDATION")
    if not state.can_show_recommendations and state.legacy_recommendation_execution_allowed is True and state.phase is not DecisionPhase.AI_RANKING:
        conflicts.append("LEGACY_EXECUTION_ALLOWS_PREMATURE_RECOMMENDATION")
    if not state.can_show_recommendations and "VISIBLE" in state.legacy_recommendation_visibility:
        conflicts.append("LEGACY_VISIBILITY_SHOWS_PREMATURE_RECOMMENDATION")
    if state.phase is DecisionPhase.SYSTEM_BLOCKED and "PROVISIONAL" in state.legacy_decision_finality:
        conflicts.append("LEGACY_FINALITY_PROVISIONAL_DURING_SYSTEM_FAILURE")
    return conflicts


def attach_canonical_decision_state_shadow(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach shadow state diagnostics without changing any existing control field."""

    state = derive_canonical_decision_state(result)
    decision = result.setdefault("decision_intelligence", {})
    decision["canonical_decision_state_shadow"] = {
        **state.to_dict(),
        "legacy_conflicts": legacy_state_conflicts(state),
        "authoritative": False,
        "migration_rule": "shadow-only: no production behavior may depend on this field yet",
    }
    return result


def apply_canonical_decision_state_authority(result: Dict[str, Any]) -> Dict[str, Any]:
    """Make Canonical Decision State the sole writer of global decision controls.

    Evidence and research services contribute facts, counters and ranking outcomes. They
    must not decide whether recommendations may execute or be visible.
    """

    state = derive_canonical_decision_state(result)
    decision = result.setdefault("decision_intelligence", {})
    if state.phase is DecisionPhase.FINAL_RECOMMENDATION:
        visibility, finality = "FINAL_RECOMMENDATION_VISIBLE", "FINAL"
    elif state.phase is DecisionPhase.PROVISIONAL_RECOMMENDATION:
        visibility, finality = "PROVISIONAL_RANKING_VISIBLE", "PROVISIONAL_PENDING_PREFERENCE_VERIFICATION"
    elif state.phase is DecisionPhase.UNRANKED_ELIGIBLE_SET:
        # Visible, and named so no legacy reader mistakes it for a ranking. Falling through
        # to the generic branch below would have produced BLOCKED_UNRANKED_ELIGIBLE_SET
        # while execution_allowed said True -- a payload contradicting itself.
        visibility, finality = "UNRANKED_ELIGIBLE_SET_VISIBLE", "DEGRADED_UNRANKED"
    elif state.phase is DecisionPhase.SYSTEM_BLOCKED:
        visibility, finality = "BLOCKED_SYSTEM", "BLOCKED_SYSTEM"
    else:
        visibility, finality = f"BLOCKED_{state.phase.value}", f"PENDING_{state.phase.value}"

    # Owner-approved research visibility is separate from recommendation authority.
    # Rebuild on every seal: a later client/system blocker must remove stale names.
    research = []
    if state.client is ClientState.COMPLETE and state.system is not SystemHealth.BLOCKED:
        seen = set()
        for row in result.get("must_pending_verification_candidates") or []:
            if not isinstance(row, dict):
                continue
            identifier = str(row.get("canonical_facility_id") or "").strip()
            name = str(row.get("facility_name") or "").strip()
            if not identifier or not name or identifier in seen:
                continue
            if set(row.get("must_unknown") or []) != {"SEMANTIC_BUDGET_VERIFICATION"} or row.get("must_fail"):
                continue
            # Intent checks cannot erase an unmet/unknown clinical capability.
            if row.get("eligibility_status") != "ELIGIBLE":
                continue
            # A known amount (including one above budget) is not a missing price.
            if row.get("starting_monthly_price") not in (None, ""):
                continue
            seen.add(identifier)
            research.append({
                "canonical_facility_id": identifier,
                "facility_name": name,
                "status": "PRICE_NOT_VERIFIED_NOT_A_RECOMMENDATION",
                "passed_requirement_count": len(set(row.get("must_pass") or [])),
                "synthetic_pilot": row.get("synthetic_pilot") is True,
            })
    research.sort(key=lambda row: (row["facility_name"].casefold(), row["canonical_facility_id"]))
    result["price_research_candidates"] = research
    decision["price_research_visibility"] = "UNRANKED_RESEARCH_ONLY" if research else "HIDDEN"

    if state.can_show_recommendations:
        # Enforce the MUST gate even if an upstream ranking returns pending rows.
        rows = result.get("results")
        if isinstance(rows, list):
            verified = [
                row for row in rows
                if not (isinstance(row, dict) and _upper(row.get("must_eligibility")) == "MUST_PENDING_VERIFICATION")
            ]
            if len(verified) != len(rows):
                result["results"] = verified
                result["result_count"] = len(verified)

    decision.update(
        recommendation_execution_allowed=state.can_show_recommendations,
        recommendation_visibility=visibility,
        decision_finality=finality,
        canonical_decision_state={
            **state.to_dict(),
            "legacy_conflicts": legacy_state_conflicts(state),
            "authoritative": True,
            "migration_rule": "canonical state is the sole global decision-control authority; legacy fields are read-only compatibility mirrors",
        },
    )
    return result


__all__ = [
    "CanonicalDecisionState",
    "CanonicalDecisionStateError",
    "DecisionPhase",
    "apply_canonical_decision_state_authority",
    "attach_canonical_decision_state_shadow",
    "canonical_can_show_recommendations",
    "canonical_client_is_complete",
    "canonical_is_final",
    "canonical_state_payload",
    "derive_canonical_decision_state",
    "legacy_state_conflicts",
]
