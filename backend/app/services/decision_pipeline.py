from __future__ import annotations

import re

"""Explicit composition of the existing governed decision stages.

One intake profile is built before matching and passed through the request.
This module owns orchestration, not ranking policy or fact interpretation.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

def _agency_matches_for_row(row: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    access = row.get("care_partner_access") if isinstance(row.get("care_partner_access"), dict) else {}
    if access.get("outside_care_allowed_verified") is not True:
        return []
    matches: list[dict[str, Any]] = []
    for option in result.get("care_partner_options") or []:
        if not isinstance(option, dict):
            continue
        fit = option.get("care_agency_fit") if isinstance(option.get("care_agency_fit"), dict) else {}
        hard_gate = str(fit.get("hard_gate") or "UNKNOWN").upper()
        matches.append({
            "canonical_agency_id": option.get("agency_id"),
            "agency_name": option.get("agency_name"),
            "verification_status": "VERIFIED" if hard_gate == "PASS" else "PARTIALLY_VERIFIED",
            "service_area_match": "LAS_VEGAS_VALLEY_SERVICE" in (fit.get("matched") or []),
            "can_cover_required_services": not any(str(reason).startswith("MISSING_") for reason in (fit.get("hard_fail_reasons") or [])),
            "services": [item for item in (fit.get("matched") or []) if item in {"BATHING_ASSISTANCE", "DRESSING_ASSISTANCE", "TRANSFER_ASSISTANCE"}],
            "minimum_hours": option.get("minimum_billable_hours", "UNKNOWN"),
            "estimated_hourly_rate": option.get("hourly_rate", "UNKNOWN"),
            "availability_status": option.get("availability_status", "UNKNOWN"),
            "material_unknowns": fit.get("material_unknowns") or [],
            "source": option.get("primary_source_url") or "Nevada PCA operational evidence",
        })
    return matches


def _reconcile_care_delivery_must(row: dict[str, Any], *, must_key: str, component_key: str, rule: str) -> None:
    """Shared by ADL and medication: a facility-side care-delivery MUST closes only when
    either in-house evidence or a *verified* external-agency match exists (see
    combined_care_solution_runtime.py's care_component / medication_component). Outside-care
    permission alone is never enough -- that would silently reintroduce the same
    unverified-evidence problem this session spent most of its time fixing elsewhere.
    """
    solution = row.get("combined_care_solution") if isinstance(row.get("combined_care_solution"), dict) else {}
    component = solution.get(component_key) if isinstance(solution.get(component_key), dict) else {}
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    if not fit or must_key not in set((fit.get("must_pass") or []) + (fit.get("must_unknown") or []) + (fit.get("must_fail") or [])):
        return
    passed = list(fit.get("must_pass") or [])
    unknown = list(fit.get("must_unknown") or [])
    failed = list(fit.get("must_fail") or [])
    for bucket in (passed, unknown, failed):
        while must_key in bucket:
            bucket.remove(must_key)
    coverage = str(component.get("combined_must_coverage") or "PENDING_VERIFICATION")
    if coverage == "PASS":
        passed.append(must_key)
    elif coverage == "FAIL":
        failed.append(must_key)
    else:
        unknown.append(must_key)
    fit["must_pass"] = passed
    fit["must_unknown"] = unknown
    fit["must_fail"] = failed
    fit["hard_gate"] = "FAIL" if failed else ("PENDING_VERIFICATION" if unknown else "PASS")
    fit.setdefault("care_delivery_gates", {})[must_key] = {
        "status": coverage,
        "delivery_model": component.get("delivery_model"),
        "reason": component.get("reason"),
        "rule": rule,
    }


def _reconcile_adl_must(row: dict[str, Any]) -> None:
    _reconcile_care_delivery_must(
        row,
        must_key="ADL_SUPPORT_AVAILABLE",
        component_key="care_component",
        rule="outside-care permission alone is not a care PASS; verified agency coverage is required",
    )


def _reconcile_medication_must(row: dict[str, Any]) -> None:
    _reconcile_care_delivery_must(
        row,
        must_key="MEDICATION_SUPPORT_AVAILABLE",
        component_key="medication_component",
        rule="outside-care permission alone is not a medication-support PASS; verified agency coverage is required",
    )


def _ranking_basis(row: dict[str, Any]) -> dict[str, Any]:
    """The specific, already-verified signals that actually separate this row from
    its neighbors in intent_rank_key's ordering -- rating, regulatory grade, and
    evidence completeness, not the flat needs-coverage match_score. Two rows can
    carry an identical match_score while ranking apart on these; without this field
    that gap was invisible to the client, who saw only a tied score with no visible
    reason for the order.
    """
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    reputation = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
    history = row.get("regulatory_history") if isinstance(row.get("regulatory_history"), dict) else {}
    return {
        "rating": reputation.get("rating", "UNKNOWN"),
        "review_count": reputation.get("review_count", "UNKNOWN"),
        "latest_regulatory_grade": history.get("latest_known_grade", "UNKNOWN"),
        "disciplinary_action_on_record": history.get("disciplinary_action", "UNKNOWN"),
        "nice_preferences_matched": len(fit.get("nice_match") or []),
        "verified_evidence_items": fit.get("relevant_evidence_known_count", 0),
    }



def _attach_room_pricing_truth(rows: list[dict[str, Any]]) -> None:
    """Attach room-level governed price truth before budget policy runs."""
    from app.database import SessionLocal
    from app.models.facility_room_offering import FacilityRoomType
    db=SessionLocal()
    try:
        identifiers = {str(row.get("canonical_facility_id")) for row in rows if row.get("canonical_facility_id")}
        if not identifiers:
            return
        try:
            rooms = db.query(FacilityRoomType).filter(FacilityRoomType.canonical_facility_id.in_(identifiers)).order_by(FacilityRoomType.id).all()
        except Exception as exc:
            if "facility_room_types" in str(exc) and ("no such table" in str(exc).lower() or "does not exist" in str(exc).lower()):
                db.rollback()
                return
            raise
        rooms_by_id = {}
        for room in rooms:
            rooms_by_id.setdefault(room.canonical_facility_id, []).append(room)
        for row in rows:
            cid=str(row.get("canonical_facility_id") or "")
            if not cid: continue
            rooms=rooms_by_id.get(cid, [])
            priced=[]
            for room in rooms:
                if room.monthly_price_cents is None: continue
                total=(room.monthly_price_cents or 0)+(room.care_fee_cents or 0)+(room.mandatory_monthly_fees_cents or 0)
                complete=room.care_fee_cents is not None and room.mandatory_monthly_fees_cents is not None
                priced.append({"room_type":room.room_type_name,"base_price":room.monthly_price_cents/100,"total_known_monthly_cost":total/100,"total_affordability_status":"KNOWN" if complete else "PENDING","pricing_qualifier":room.pricing_qualifier or "UNKNOWN","availability_status":room.availability_status,"final_availability_status":"REQUIRES_DIRECT_VERIFICATION"})
            row["room_pricing_options"]=priced
            known=[x for x in priced if x["total_affordability_status"]=="KNOWN"]
            if known:
                best=min(known,key=lambda x:x["total_known_monthly_cost"])
                row["starting_monthly_price"]=best["total_known_monthly_cost"]
                row["price_truth_basis"]="ROOM_TOTAL_KNOWN_MONTHLY_COST"
                row["total_affordability_status"]="KNOWN"
            elif priced:
                row["price_truth_basis"]="ROOM_BASE_ONLY_TOTAL_PENDING"
                row["total_affordability_status"]="PENDING"
    finally:
        db.close()

def _apply_combined_care_layer(result: dict[str, Any], questionnaire_state: dict[str, Any], natural_language_query: str, limit: int) -> dict[str, Any]:
    from app.services.client_intent_runtime import intent_rank_key
    from app.services.combined_care_solution_runtime import attach_combined_care_solutions

    rows = list(result.get("results") or [])
    _attach_room_pricing_truth(rows)
    for row in rows:
        row["external_care_agency_matches"] = _agency_matches_for_row(row, result)
    profile = result.get("patient_needs_profile") or {}
    summary = attach_combined_care_solutions(rows, questionnaire_state, natural_language_query, prepared_signals=profile.get("care_delivery_signals"))
    for row in rows:
        _reconcile_adl_must(row)
        _reconcile_medication_must(row)
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (*intent_rank_key(pair[1]), pair[0]))
    rows = [row for _, row in indexed]
    # intent_rank_key's last element is the facility-name tiebreaker used only to make
    # sort order deterministic -- it isn't a real signal, so two rows are a genuine
    # tie only if everything *before* that element matches.
    substantive_keys = [intent_rank_key(row)[:-1] for row in rows]
    for position, row in enumerate(rows, start=1):
        row["rank_position"] = position
        row["rank_display"] = f"#{position}"
        tied_indexes = [
            other for other, key in enumerate(substantive_keys)
            if other != position - 1 and key == substantive_keys[position - 1]
        ]
        row["rank_tie_status"] = "JOINT_RANK" if tied_indexes else "UNIQUE_RANK"
        row["tied_with"] = [rows[i].get("facility_name") for i in tied_indexes]
        row["ranking_basis"] = _ranking_basis(row)
        row.setdefault("explanation", {})["combined_care_solution"] = row.get("combined_care_solution") or {}
    # Final selection owns the display limit; late care reconciliation must see all rows.
    selected = rows
    result["results"] = selected
    result["result_count"] = len(selected)
    result["combined_care_solution_policy"] = summary
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    decision["combined_care_solution"] = summary
    must_gate = decision.get("must_gate") if isinstance(decision.get("must_gate"), dict) else {}
    must_gate["combined_care_delivery_enforced"] = True
    must_gate["combined_care_rule"] = "Outside-care permission alone does not satisfy ADL_SUPPORT_AVAILABLE or MEDICATION_SUPPORT_AVAILABLE; a verified agency match covering required services is required for each."
    decision["must_gate"] = must_gate
    decision["combined_solution_principle"] = "Rank the complete solution: housing environment and care delivery are separate. A preferred intimate/independent setting stays viable when outside care is permitted, but the care MUST closes only after a verified agency match covers the required services."
    result["decision_intelligence"] = decision
    return result


def _decision_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return profile.get("decision_intelligence") if isinstance(profile.get("decision_intelligence"), dict) else {}


def _canonical_client_complete(decision: dict[str, Any]) -> bool:
    from app.services.canonical_decision_state import canonical_client_is_complete

    return canonical_client_is_complete({"decision_intelligence": decision})


def _client_interview_blocked(client_complete: bool) -> bool:
    """Only unresolved client intent blocks matching; facility research is downstream work."""
    return not client_complete


def _mark_client_ready_for_research(decision: dict[str, Any], readiness: str) -> None:
    if readiness != "NEEDS_RESEARCH":
        return
    decision["client_decision_readiness"] = "READY"
    decision["facility_research_state"] = "RESEARCH_REQUIRED"
    decision["readiness_separation_rule"] = "Client readiness and facility evidence readiness are separate. Facility research never reopens a completed client interview."


def _classify_facilities_before_ranking(profile: dict[str, Any]) -> dict[str, Any]:
    """Classify the active market before client-readiness can block recommendation ranking.

    This is inventory discovery, not matching or ranking: it intentionally exposes no
    facility identities and makes no claim that a classified facility fits the client.
    """
    from app.services.facility_parameter_service import query_facility_knowledge_catalog

    need_ids = sorted({
        str(need.get("parameter_id") or "").strip()
        for need in (profile.get("needs") or [])
        if isinstance(need, dict)
        and str(need.get("requirement_level") or "").upper() in {"", "REQUIRED", "HIGH"}
        and str(need.get("parameter_id") or "") != "current_availability"
    })
    query = query_facility_knowledge_catalog(required_parameter_ids=need_ids)
    return {
        "status": "COMPLETED_PRE_RANKING",
        "catalog_version": query["catalog_version"],
        "total_facilities_classified": query["total_facilities_known"],
        "classification_counts": query["classification_counts"],
        "required_parameter_ids": query["required_parameter_ids"],
        "relevant_candidate_count": query["candidate_count"],
        "verified_capability_match_count": query["verified_capability_match_count"],
        "pending_verification_count": query["pending_verification_count"],
        "excluded_explicit_negative_count": query["excluded_explicit_negative_count"],
        "unknown_is_not_negative": True,
        "identities_hidden_pending_client_input": True,
        "rule": "The preclassified facility catalog is queried before client clarification; matching, ranking, and facility identities remain blocked.",
    }


def _blocked_interview_result(profile: dict[str, Any], readiness: str) -> dict[str, Any]:
    decision = _decision_from_profile(profile)
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    questions = human.get("adaptive_questions") or decision.get("adaptive_questions") or []
    semantic = human.get("semantic_ai") if isinstance(human.get("semantic_ai"), dict) else {}
    process_owner = {
        "owner": "SEMANTIC_AI_PROCESS_OWNER",
        "status": "ACTIVE" if semantic.get("status") == "CONSULTED_AND_VALIDATED" else semantic.get("status", "UNKNOWN"),
        "process_phase": "CLARIFICATION",
        "next_best_action": {
            "action": "ASK_CLIENT",
            "question": (questions[0].get("question") if questions and isinstance(questions[0], dict) else None),
        },
        "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
    }
    discovery = _classify_facilities_before_ranking(profile)
    blocked = {
        "patient_needs_profile": profile,
        "results": [],
        "result_count": 0,
        "total_candidates_scored": 0,
        "candidate_discovery": discovery,
        "availability_policy": "Recommendations are blocked until the governed AI interview has enough client evidence to begin research.",
        "care_setting_policy": {"status": "BLOCKED_PENDING_AI_INTERVIEW", "decision_intelligence": decision},
        "decision_intelligence": {
            **decision,
            "interview_owner": "SEMANTIC_AI",
            "process_owner": process_owner,
            "guardian_role": "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT",
        },
        "recommendation_audit_trace": {
            "blocked_before_facility_ranking": True,
            "facility_classification_completed": True,
            "reason": readiness,
            "adaptive_questions": questions,
            "semantic_ai": semantic,
            "process_owner": process_owner,
            "rule": "Only unresolved client intent may block facility matching. Facility research is downstream of a completed client interview.",
        },
    }
    from app.services.canonical_decision_state import apply_canonical_decision_state_authority
    return apply_canonical_decision_state_authority(blocked)


def _suppress_unverified_recommendations(result: dict[str, Any]) -> dict[str, Any]:
    from app.services.canonical_decision_state import canonical_can_show_recommendations

    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    if canonical_can_show_recommendations(result):
        return result
    candidate_count = len(result.get("results") or [])
    decision["research_candidate_count"] = candidate_count
    decision["recommendation_visibility_rule"] = "Canonical Decision State blocks candidate identities and ranking until its phase permits recommendation visibility."
    result["decision_intelligence"] = decision
    result["results"] = []
    result["result_count"] = 0
    result["availability_policy"] = "Facility candidates are being researched; recommendations remain hidden until the governed MUST gate passes."
    audit = result.get("recommendation_audit_trace") if isinstance(result.get("recommendation_audit_trace"), dict) else {}
    audit["recommendation_execution_allowed"] = False
    audit["blocked_before_recommendation_visibility"] = True
    audit["recommendations"] = []
    result["recommendation_audit_trace"] = audit
    return result


def _merge_funnel_fit(result: dict[str, Any]) -> None:
    from app.services.decision_funnel import merge_late_fit
    ledger = result.get("decision_funnel_ledger")
    if isinstance(ledger, list):
        merge_late_fit(ledger, result.get("results") or [])


def _attach_decision_funnel(result: dict[str, Any], decision_questionnaire: dict[str, Any]) -> list | None:
    """Mechanical funnel + zero-result classification (decision_funnel.py)."""
    from app.services.decision_funnel import build_funnel
    ledger = result.pop("decision_funnel_ledger", None)
    catalog = result.pop("decision_funnel_catalog", None)
    if not isinstance(ledger, list) or not isinstance(catalog, dict):
        return None
    decision = result.setdefault("decision_intelligence", {})
    intent = decision.get("client_intent") if isinstance(decision.get("client_intent"), dict) else {}
    must_order = [str(m.get("key") or "") for m in intent.get("must_haves") or []]
    budget = decision_questionnaire.get("budget")
    budget = float(budget) if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0 else None
    shown = len(result.get("results") or [])
    coverage = None
    if shown == 0:
        from app.services.must_evidence_sources import market_must_coverage
        coverage = market_must_coverage(must_order)
    result["decision_funnel"] = build_funnel(
        catalog=catalog,
        location_scope=result.get("location_scope") or {},
        ledger=ledger,
        must_order=must_order,
        budget=budget,
        shown_count=shown,
        requested_must_coverage=coverage,
    )
    return ledger


_PRIVATE_PRICE_BUDGET_SENTENCE = re.compile(
    r"No currently eligible pilot community in this result set fits the stated \$[\d,]+ monthly budget\. "
    r"The lowest verified starting price shown is \$[\d,]+; these are alternatives for review, not in-budget matches\.\s*"
)


def _reconcile_budget_notice(result: dict[str, Any], decision_questionnaire: dict[str, Any]) -> None:
    """The family-facing budget sentence must come from the same funding pathway the decision used.

    The core builds a private-price sentence before the pathway is known. When Medicaid is the
    pathway (owner rule), the budget is compared with the household's verified out-of-pocket cost,
    never the private-pay price, so that sentence would contradict the decision (it says nothing
    fits while the funnel says the relevant cost is still unverified). Replace it with the pathway
    statement; private-pay searches are untouched.
    """
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    intent = decision.get("client_intent") if isinstance(decision.get("client_intent"), dict) else {}
    if intent.get("funding_pathway") != "MEDICAID":
        return
    notice = str(result.get("market_coverage_notice") or "")
    notice = _PRIVATE_PRICE_BUDGET_SENTENCE.sub("", notice).strip()
    budget = decision_questionnaire.get("budget")
    if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0:
        notice = (notice + " " if notice else "") + (
            f"Because Medicaid is the funding pathway, your ${budget:,.0f} budget is compared with the "
            "household's out-of-pocket cost under Medicaid, not the private-pay price. That cost is not "
            "yet verified for these communities."
        )
    result["market_coverage_notice"] = notice or None


def _persist_selected_decision_audit(result: dict[str, Any], questionnaire_state: dict[str, Any], limit: int) -> dict[str, Any]:
    from app.services.decision_governance_runtime import attach_governed_knowledge_learning_and_audit

    selected = {row.get("canonical_facility_id"): row for row in result.get("results") or []}
    trace = result.get("recommendation_audit_trace") or {}
    trace["recommendations"] = [
        {**audit, "rank_position": selected[audit.get("canonical_facility_id")].get("rank_position")}
        for audit in trace.get("recommendations") or []
        if audit.get("canonical_facility_id") in selected
    ]
    result["recommendation_audit_trace"] = trace
    return attach_governed_knowledge_learning_and_audit(
        core=result, questionnaire_state=questionnaire_state, audit_limit=max(0, int(limit or 0)),
    )


def _attach_pipeline_trace(result: dict[str, Any]) -> dict[str, Any]:
    from app.services.decision_pipeline_trace import attach_decision_pipeline_trace
    return attach_decision_pipeline_trace(result)


def run_decision_pipeline(questionnaire_state: dict[str, Any], natural_language_query: str, limit: int, *, profile_builder: Callable, runner: Callable, prepared_profile: dict[str, Any] | None = None):
    from app.services.canonical_decision_state import apply_canonical_decision_state_authority

    stage_started = time.perf_counter()
    stage_timings: dict[str, float] = {}

    def _mark(stage_name: str, previous: float) -> float:
        now = time.perf_counter()
        stage_timings[stage_name] = round((now - previous) * 1000, 1)
        return now

    profile = prepared_profile if prepared_profile is not None else profile_builder(questionnaire_state=questionnaire_state, natural_language_query=natural_language_query)
    stage_started = _mark("build_patient_needs_profile_ms", stage_started)
    profile_readiness = "UNKNOWN"
    if isinstance(profile, dict):
        profile_decision = _decision_from_profile(profile)
        profile_complete = _canonical_client_complete(profile_decision)
        if _client_interview_blocked(profile_complete):
            logger.info("decision_pipeline_stage_timings_ms (blocked at profile) %s", stage_timings)
            return _attach_pipeline_trace(_blocked_interview_result(profile, "CANONICAL_CLIENT_INCOMPLETE"))
        human = profile_decision.get("human_intelligence") if isinstance(profile_decision.get("human_intelligence"), dict) else {}
        profile_readiness = str(human.get("decision_readiness") or "READY").upper()
        _mark_client_ready_for_research(profile_decision, profile_readiness)

    # The lower-level engine still scores the full Nevada market before it
    # ranks candidates. This cap applies only to the candidate pool that
    # reaches the expensive evidence and audit stages. Carrying hundreds of
    # rows through those stages wrote thousands of records for one family
    # search and could restart the production web worker.
    internal_limit = max(60, min(100, int(limit or 50)))
    # Cutover: conversation AI may read narrative upstream; decision engine gets structured facts only.
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
    # The profile builder already produced the canonical decision questionnaire from the
    # Structured Profile (interpreter output included). Every decision stage below reads
    # it -- never the raw questionnaire_state or the free text.
    canonical = profile.get("canonical_decision_questionnaire") if isinstance(profile, dict) else None
    if isinstance(canonical, dict):
        decision_questionnaire = dict(canonical)
    else:
        decision_profile = build_structured_profile(questionnaire_state)
        decision_questionnaire = materialize_questionnaire(decision_profile)
        if isinstance(questionnaire_state.get("questionnaireCompletion"), dict):
            decision_questionnaire["questionnaireCompletion"] = questionnaire_state["questionnaireCompletion"]
    result = runner(questionnaire_state=decision_questionnaire, natural_language_query="", limit=internal_limit, prepared_profile=profile, return_full_universe=True)
    stage_started = _mark("run_patient_decision_engine_deterministic_ms", stage_started)
    if not isinstance(result, dict):
        return result
    result = apply_canonical_decision_state_authority(result)
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    if _client_interview_blocked(_canonical_client_complete(decision)):
        runtime_profile = result.get("patient_needs_profile") if isinstance(result.get("patient_needs_profile"), dict) else profile
        logger.info("decision_pipeline_stage_timings_ms (blocked at result) %s", stage_timings)
        return _attach_pipeline_trace(_blocked_interview_result(runtime_profile or {}, "CANONICAL_CLIENT_INCOMPLETE"))
    human = decision.get("human_intelligence") if isinstance(decision.get("human_intelligence"), dict) else {}
    readiness = str(human.get("decision_readiness") or "READY").upper()
    _mark_client_ready_for_research(decision, readiness)

    from app.services.semantic_facility_requirements import apply_semantic_facility_requirements
    from app.services.ai_process_owner_guard_patch import attach_ai_process_owner_guarded
    from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline

    result = apply_semantic_facility_requirements(result, research_limit=max(60, internal_limit), questionnaire_state=decision_questionnaire)
    stage_started = _mark("apply_semantic_facility_requirements_ms", stage_started)
    decision = result.setdefault("decision_intelligence", {})
    decision["interview_owner"] = "SEMANTIC_AI"
    decision["guardian_role"] = "CONSTRAIN_VALIDATE_BLOCK_NOT_SCRIPT"
    result = _apply_combined_care_layer(result, decision_questionnaire, "", internal_limit)
    stage_started = _mark("apply_combined_care_layer_ms", stage_started)

    # Budget authority is centralized in must_ai_nice_pipeline.  Earlier stages may
    # expose price evidence but must not admit/remove candidates or decide how many
    # over-budget rows are needed.  This avoids the former duplicate "fill shortlist"
    # policy and preserves the owner rule: in-budget first, then all otherwise-eligible
    # candidates up to +10%, with transparent deviation.
    _merge_funnel_fit(result)
    completion = questionnaire_state.get("questionnaireCompletion") or {}
    accepted_changes = completion.get("oomnikerRelaxedPreferences") if isinstance(completion, dict) else None
    if accepted_changes:
        result = apply_must_ai_nice_pipeline(result, decision_questionnaire, "", limit,
                                            accepted_preference_changes=accepted_changes)
    else:
        result = apply_must_ai_nice_pipeline(result, decision_questionnaire, "", limit)
    stage_started = _mark("apply_must_ai_nice_pipeline_ms", stage_started)
    # Re-seal after the MUST/ranking stages before the process owner reads
    # phase or visibility.  Raw pipeline facts may change; control state may
    # only change through this authority boundary.
    result = apply_canonical_decision_state_authority(result)
    result = attach_ai_process_owner_guarded(result, questionnaire_state, natural_language_query)
    stage_started = _mark("attach_ai_process_owner_guarded_ms", stage_started)
    result = apply_canonical_decision_state_authority(result)
    result = _suppress_unverified_recommendations(result)
    result = _persist_selected_decision_audit(result, decision_questionnaire, limit)
    stage_started = _mark("persist_final_selection_audit_ms", stage_started)
    ledger = _attach_decision_funnel(result, decision_questionnaire)
    _reconcile_budget_notice(result, decision_questionnaire)
    from app.services.oomniker_optimizer import analyze_oomniker
    # Oomniker reads the same canonical profile, client intent and full candidate ledger
    # the decision used -- never the raw questionnaire -- so it can say which parameter
    # narrows supply and what changing it would do.
    decision = result.get("decision_intelligence") if isinstance(result.get("decision_intelligence"), dict) else {}
    oomniker_context = None
    if ledger is not None:
        oomniker_context = {
            "ledger": ledger,
            "client_intent": decision.get("client_intent") or {},
            "funnel": result.get("decision_funnel") or {},
            "location_scope": result.get("location_scope") or {},
            "preference_analysis": result.pop("oomniker_preference_analysis", {}),
        }
    result["oomniker"] = analyze_oomniker(dict(decision_questionnaire), list(result.get("results") or []), decision_context=oomniker_context)
    result = _attach_pipeline_trace(result)
    logger.info("decision_pipeline_stage_timings_ms %s total_ms=%s", stage_timings, round(sum(stage_timings.values()), 1))
    return result
