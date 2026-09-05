from __future__ import annotations

"""Canonical decision-state model for OPTIME Nursing.

This module is intentionally shadow-only in its first migration phase: it derives one
normalized state from the current decision payload without changing production control
flow. The goal is to remove semantic overload from legacy fields such as
``decision_readiness``, ``recommendation_execution_allowed``, ``recommendation_visibility``
and ``decision_finality`` before any caller is migrated to use this state as authority.
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


class PreferenceState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


class DecisionFinality(str, Enum):
    NONE = "NONE"
    PROVISIONAL = "PROVISIONAL"
    FINAL = "FINAL"


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
        }

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
        payload["version"] = "canonical-decision-state-v1-shadow"
        return payload


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
    if status in {"AI_RANKED", "AI_BATCH_RANKED"}:
        return RankingState.COMPLETE
    if status in {"STARTED", "RUNNING", "IN_PROGRESS"}:
        return RankingState.RUNNING
    if status and status not in {"NO_MUST_ELIGIBLE_CANDIDATES", "DETERMINISTIC_FALLBACK"}:
        return RankingState.FAILED
    if pipeline.get("ai_ranking_fail_closed") is True:
        return RankingState.FAILED
    return RankingState.NOT_STARTED


def _system_failure(decision: Dict[str, Any], human: Dict[str, Any]) -> tuple[SystemHealth, str]:
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    semantic_status = _upper(semantic.get("status"))
    if semantic_status in {"FAILED", "REQUIRED_BUT_DISABLED"} and bool(semantic.get("required")):
        return SystemHealth.BLOCKED, f"required semantic AI unavailable: {semantic_status}"

    owner = decision.get("process_owner") if isinstance(decision.get("process_owner"), dict) else {}
    owner_status = _upper(owner.get("status"))
    if bool(owner.get("required")) and owner_status in {"FAILED", "REQUIRED_BUT_DISABLED"}:
        return SystemHealth.BLOCKED, f"required AI process owner unavailable: {owner_status}"

    pipeline = decision.get("facility_selection_pipeline")
    if isinstance(pipeline, dict) and pipeline.get("ai_ranking_fail_closed") is True:
        return SystemHealth.BLOCKED, "required AI ranking did not complete"

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
    # MUST_PENDING_VERIFICATION candidates are ranked together with MUST_ELIGIBLE ones
    # (see must_ai_nice_pipeline.py) rather than excluded, so a completed ranking can
    # cover either group. Only an explicit MUST_FAIL is excluded from ranking.
    rankable_count = eligible + pending

    if blockers:
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
            client=ClientState.COMPLETE,
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

    # Pending evidence is a research queue, not a veto on candidates that already
    # passed every MUST.  The former behaviour let one unresolved non-shortlisted
    # facility hide a successfully AI-ranked shortlist. Pending candidates are now
    # ranked alongside eligible ones (must_ai_nice_pipeline.py), so this route only
    # applies while that combined ranking has not completed yet -- once it has,
    # control falls through to the PROVISIONAL/FINAL_RECOMMENDATION branch below,
    # which shows them with an explicit per-candidate pending-verification note.
    if pending > 0 and eligible == 0 and ranking is not RankingState.COMPLETE:
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
    # The same now holds for MUST evidence: a candidate with an unresolved (not
    # failed) MUST item is ranked and shown on today's evidence, never hidden for it.
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
    elif state.phase is DecisionPhase.SYSTEM_BLOCKED:
        visibility, finality = "BLOCKED_SYSTEM", "BLOCKED_SYSTEM"
    else:
        visibility, finality = f"BLOCKED_{state.phase.value}", f"PENDING_{state.phase.value}"

    decision.update(
        recommendation_execution_allowed=state.can_show_recommendations,
        recommendation_visibility=visibility,
        decision_finality=finality,
        canonical_decision_state={
            **state.to_dict(),
            "legacy_conflicts": legacy_state_conflicts(state),
            "authoritative": True,
            "migration_rule": "phase-3: canonical state is the sole global decision-control writer",
        },
    )
    return result


__all__ = [
    "CanonicalDecisionState",
    "DecisionPhase",
    "apply_canonical_decision_state_authority",
    "attach_canonical_decision_state_shadow",
    "derive_canonical_decision_state",
    "legacy_state_conflicts",
]
