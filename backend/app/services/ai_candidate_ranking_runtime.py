from __future__ import annotations

"""Closed-world Semantic AI ranking for facilities that already passed every MUST.

Rules/Guardian decide MUST eligibility. The AI never changes eligibility and never
introduces a candidate. Small candidate sets are ranked in one closed-world request.
Large candidate sets are scored in parallel closed-world batches using one shared
0-100 rubric, then globally ordered by AI score with the governed deterministic key
used only as a stable tie-breaker. UNKNOWN is an information deficit, not negative
evidence.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import os
from typing import Any, Dict, List

from app.services.semantic_intent_ai import _default_transport
from app.services.semantic_preference_runtime import build_facility_claim_ledger

logger = logging.getLogger(__name__)


def _log_closed_world_mismatch(label: str, supplied: set[str], returned_ids: List[str]) -> None:
    returned = set(returned_ids)
    missing = supplied - returned
    extra = returned - supplied
    duplicates = len(returned_ids) - len(returned)
    logger.warning(
        "%s supplied=%s returned=%s missing=%s extra=%s duplicates=%s "
        "(missing_and_no_extra suggests truncation; extra suggests invented/hallucinated ids)",
        label,
        len(supplied),
        len(returned_ids),
        len(missing),
        len(extra),
        duplicates,
    )


def _ranking_packet(rows: List[Dict[str, Any]], *, claim_limit: int | None = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        ledger = build_facility_claim_ledger(row)
        claims = list(ledger.get("claims") or [])
        if claim_limit and len(claims) > claim_limit:
            # Keep a deterministic, broad sample across the complete governed ledger
            # rather than only the first fields. The full claim count remains visible
            # so missing evidence is never mistaken for negative evidence.
            step = max(1, len(claims) // claim_limit)
            sampled = claims[::step][:claim_limit]
            ledger = {**ledger, "claims": sampled, "total_governed_claim_count": len(claims), "packet_claim_count": len(sampled), "packet_mode": "DISTRIBUTED_GOVERNED_CLAIM_SAMPLE"}
        out.append({
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "must_eligibility": row.get("must_eligibility"),
            "care_setting_fit": row.get("care_setting_fit") or {},
            "public_reputation": fit.get("public_reputation") or {},
            "relevant_evidence_known_count": fit.get("relevant_evidence_known_count") or 0,
            "relevant_evidence_unknown_count": fit.get("relevant_evidence_unknown_count") or 0,
            "governed_claim_ledger": ledger,
        })
    return out


def _resolve_claim_limit() -> int:
    return max(30, min(160, int(os.getenv("OPTIME_AI_RANKING_CLAIMS_PER_CANDIDATE", "80"))))


def _claim_ids(row: Dict[str, Any]) -> set[str]:
    ledger = build_facility_claim_ledger(row)
    return {str(claim.get("claim_id")) for claim in ledger.get("claims") or [] if claim.get("claim_id")}


def _validated_citations(label: str, canonical_id: str, item: Dict[str, Any], valid_claim_ids: set[str]) -> tuple[List[str], List[str], bool]:
    """Citations are optional supporting detail, not the score/rank itself -- the
    contract already allows an empty list rather than a citation. So a fabricated
    claim_id is stripped and logged, not treated as grounds to discard the whole
    candidate's score. A closed-world violation (wrong candidate set) is a different,
    more serious kind of failure and is still handled by the caller as a hard fail.
    """
    drivers = [str(v) for v in item.get("rank_drivers") or []]
    risks = [str(v) for v in item.get("rank_risks") or []]
    clean_drivers = [claim_id for claim_id in drivers if claim_id in valid_claim_ids]
    clean_risks = [claim_id for claim_id in risks if claim_id in valid_claim_ids]
    invalid = [claim_id for claim_id in (*drivers, *risks) if claim_id not in valid_claim_ids]
    if invalid:
        logger.warning(
            "%s candidate=%s invalid_claim_ids=%s (a rank_driver/rank_risk cited a claim_id absent from this "
            "candidate's governed claim ledger -- stripped as a fabricated citation; score/rank retained)",
            label,
            canonical_id,
            invalid,
        )
    return clean_drivers, clean_risks, bool(invalid)


def _prompt(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any], claim_limit: int) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_AI_CANDIDATE_RANKER",
        "mission": "Rank only facilities that have already passed every deterministic MUST requirement, using the resident-specific semantic preference model plus supplied governed evidence.",
        "rules": [
            "Do not change MUST eligibility; every supplied candidate is MUST_ELIGIBLE.",
            "Rank all supplied candidate IDs exactly once and introduce no other facility.",
            "Use the dynamic_preference_model in human_context; do not rely on a fixed preference catalog.",
            "Use only supplied governed claim ledgers for facility facts; do not use generic brand assumptions or outside knowledge.",
            "Treat UNKNOWN as missing information, never as a negative fact and never as a positive fact.",
            "Negative verified regulatory or fit evidence may lower a candidate.",
            "A facility with missing preference evidence may be information-poor rather than a bad fit; explain that distinction.",
            "Explain the main governed evidence that distinguishes each candidate and explicitly identify information deficits.",
            "Do not invent price, availability, staffing, services, activities, reputation, or regulatory facts.",
            "For rank_drivers and rank_risks, cite only claim_id values that appear in that exact candidate's governed_claim_ledger; leave a list empty rather than inventing or guessing a citation.",
        ],
        "client_intent": client_intent,
        "human_context": human_context,
        "living_strategy": strategy,
        "must_eligible_candidates": _ranking_packet(rows, claim_limit=claim_limit),
        "required_output": {
            "ranked_candidates": [
                {
                    "canonical_facility_id": "string",
                    "reason": "string",
                    "information_deficits": ["string"],
                    "rank_drivers": ["claim_id from this candidate's governed_claim_ledger that supports its rank; may be empty"],
                    "rank_risks": ["claim_id from this candidate's governed_claim_ledger that is a concern or caveat; may be empty"],
                }
            ]
        },
    }


def _score_prompt(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any], claim_limit: int) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_AI_CANDIDATE_SCORER",
        "mission": "Score every supplied MUST_ELIGIBLE facility on one globally comparable resident-specific 0-100 fit scale. These batch scores will be merged with scores from other batches, so apply the rubric absolutely, not relatively within this batch.",
        "global_rubric": {
            "90_100": "Exceptionally strong fit supported by governed evidence across the resident's important preferences and relevant quality/safety dimensions, with few material information deficits.",
            "75_89": "Strong fit with meaningful governed support and manageable information deficits.",
            "55_74": "Plausible fit but mixed or incomplete governed support; important provider facts may still change the result.",
            "35_54": "Weakly supported fit or meaningful verified concerns, while still passing deterministic MUST requirements.",
            "0_34": "Very weak resident-specific fit because of verified negative evidence; never use missing evidence alone to justify a low score.",
        },
        "rules": [
            "Every candidate already passed deterministic MUST. Never change eligibility.",
            "Return every supplied canonical_facility_id exactly once and no other IDs.",
            "Use the same absolute 0-100 scale for every candidate; do not normalize scores to the current batch.",
            "Use the dynamic_preference_model in human_context and supplied governed evidence only.",
            "UNKNOWN is an information deficit, not negative evidence and not positive evidence.",
            "Verified regulatory, safety, care-setting or preference evidence may affect score.",
            "Do not invent facility facts or use outside/brand knowledge.",
            "For rank_drivers and rank_risks, cite only claim_id values that appear in that exact candidate's governed_claim_ledger; leave a list empty rather than inventing or guessing a citation.",
        ],
        "client_intent": client_intent,
        "human_context": human_context,
        "living_strategy": strategy,
        "must_eligible_candidates": _ranking_packet(rows, claim_limit=claim_limit),
        "required_output": {
            "scored_candidates": [
                {
                    "canonical_facility_id": "string",
                    "score": 0,
                    "reason": "string",
                    "information_deficits": ["string"],
                    "rank_drivers": ["claim_id from this candidate's governed_claim_ledger that supports its score; may be empty"],
                    "rank_risks": ["claim_id from this candidate's governed_claim_ledger that is a concern or caveat; may be empty"],
                }
            ]
        },
    }


def _validate(packet: Dict[str, Any], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    supplied = {str(row.get("canonical_facility_id") or "") for row in rows if row.get("canonical_facility_id")}
    ranked = packet.get("ranked_candidates") if isinstance(packet.get("ranked_candidates"), list) else []
    ids = [str(item.get("canonical_facility_id") or "") for item in ranked if isinstance(item, dict)]
    if len(ids) != len(supplied) or len(set(ids)) != len(ids) or set(ids) != supplied:
        _log_closed_world_mismatch("AI_CANDIDATE_RANKING_CLOSED_WORLD_VIOLATION", supplied, ids)
        raise RuntimeError("AI_CANDIDATE_RANKING_CLOSED_WORLD_VIOLATION")
    by_id = {str(row.get("canonical_facility_id")): row for row in rows}
    ordered: List[Dict[str, Any]] = []
    for position, item in enumerate(ranked, start=1):
        canonical_id = str(item.get("canonical_facility_id"))
        row = by_id[canonical_id]
        drivers, risks, citation_stripped = _validated_citations("AI_CANDIDATE_RANKING_INVALID_CLAIM_CITATION", canonical_id, item, _claim_ids(row))
        row["ai_ranking"] = {
            "status": "AI_RANKED",
            "rank": position,
            "reason": str(item.get("reason") or ""),
            "information_deficits": [str(v) for v in item.get("information_deficits") or []],
            "rank_drivers": drivers,
            "rank_risks": risks,
            "citation_validation": "PARTIAL" if citation_stripped else "FULL",
        }
        ordered.append(row)
    return ordered


def _validate_scores(packet: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    supplied = {str(row.get("canonical_facility_id") or "") for row in rows if row.get("canonical_facility_id")}
    scored = packet.get("scored_candidates") if isinstance(packet.get("scored_candidates"), list) else []
    ids = [str(item.get("canonical_facility_id") or "") for item in scored if isinstance(item, dict)]
    if len(ids) != len(supplied) or len(set(ids)) != len(ids) or set(ids) != supplied:
        _log_closed_world_mismatch("AI_CANDIDATE_SCORING_CLOSED_WORLD_VIOLATION", supplied, ids)
        raise RuntimeError("AI_CANDIDATE_SCORING_CLOSED_WORLD_VIOLATION")
    by_id = {str(row.get("canonical_facility_id")): row for row in rows}
    validated: Dict[str, Dict[str, Any]] = {}
    for item in scored:
        canonical_id = str(item.get("canonical_facility_id") or "")
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("AI_CANDIDATE_SCORING_INVALID_SCORE") from exc
        if score < 0 or score > 100:
            raise RuntimeError("AI_CANDIDATE_SCORING_INVALID_SCORE_RANGE")
        drivers, risks, citation_stripped = _validated_citations("AI_CANDIDATE_SCORING_INVALID_CLAIM_CITATION", canonical_id, item, _claim_ids(by_id[canonical_id]))
        validated[canonical_id] = {
            "score": round(score, 3),
            "reason": str(item.get("reason") or ""),
            "information_deficits": [str(v) for v in item.get("information_deficits") or []],
            "rank_drivers": drivers,
            "rank_risks": risks,
            "citation_validation": "PARTIAL" if citation_stripped else "FULL",
        }
    return validated


def _validated_ai_response(prompt: Dict[str, Any], rows: List[Dict[str, Any]], validate, *, output_key: str) -> tuple[Any, bool]:
    """Make one bounded repair attempt for an invalid closed-world AI response."""
    packet = _default_transport(prompt)
    try:
        return validate(packet, rows), False
    except RuntimeError as exc:
        error = str(exc)
        if not error.startswith("AI_CANDIDATE_"):
            raise
        candidate_ids = [str(row.get("canonical_facility_id")) for row in rows if row.get("canonical_facility_id")]
        retry_prompt = {
            **prompt,
            "contract_repair": {
                "previous_validation_error": error,
                "candidate_ids_required_exactly_once": candidate_ids,
                "instruction": (
                    f"Return a complete replacement `{output_key}` array containing exactly these IDs once each, "
                    "with no extras. Recheck every citation against that candidate's supplied ledger; use [] if uncertain."
                ),
            },
        }
        logger.warning("ai_candidate_ranking_contract_repair_attempt candidate_count=%s error=%s", len(candidate_ids), error)
        return validate(_default_transport(retry_prompt), rows), True


def _resolve_calibration_window() -> int:
    return max(0, min(40, int(os.getenv("OPTIME_AI_RANKING_CALIBRATION_WINDOW", "20"))))


def _resolve_calibration_margin() -> float:
    return max(0.0, min(20.0, float(os.getenv("OPTIME_AI_RANKING_CALIBRATION_MARGIN", "3.0"))))


def _calibration_window_end(ordered: List[Dict[str, Any]], window: int, margin: float) -> int:
    """Extend the strict top-N window to include any immediately-following candidate
    whose batch score is within `margin` points of the boundary score. A candidate
    scored 79.8 sitting just outside a window cut at 80.0 is not meaningfully worse
    than the one just inside it, and calibration should judge both in the same direct
    comparison rather than silently locking in whichever side of an arbitrary cutoff
    the batch scoring happened to place them on. Capped at 2x window so a long tail of
    similarly-scored candidates cannot balloon the calibration call's size.
    """
    if margin <= 0 or window >= len(ordered):
        return min(window, len(ordered))
    boundary_score = (ordered[window - 1].get("ai_ranking") or {}).get("global_score")
    if not isinstance(boundary_score, (int, float)):
        return window
    end = window
    hard_cap = min(len(ordered), window * 2)
    while end < hard_cap:
        score = (ordered[end].get("ai_ranking") or {}).get("global_score")
        if not isinstance(score, (int, float)) or score < boundary_score - margin:
            break
        end += 1
    return end


def _calibrate_top_candidates(
    ordered: List[Dict[str, Any]],
    client_intent: Dict[str, Any],
    human_context: Dict[str, Any],
    strategy: Dict[str, Any],
    claim_limit: int,
) -> None:
    """Batch scoring runs each batch as an independent LLM call sharing one absolute
    rubric, but separate calls are not perfectly calibrated to each other -- the same
    facility could plausibly score a few points differently in a different batch. This
    reruns one coherent, directly-comparative single-shot adjudication over the
    top-scored window plus any near-boundary candidates (the part of the order that is
    actually displayed and matters most), so every facility judged is compared against
    the same request instead of merged from independent batches. Mutates `ordered` in
    place on success. This is a quality refinement, never a required step: any failure
    (including a fabricated claim citation) leaves the original batch order untouched.
    """
    window = _resolve_calibration_window()
    if window <= 0 or len(ordered) <= window:
        return
    window_end = _calibration_window_end(ordered, window, _resolve_calibration_margin())
    top = ordered[:window_end]
    original_scores = {str(row.get("canonical_facility_id")): (row.get("ai_ranking") or {}).get("global_score") for row in top}
    try:
        packet = _default_transport(_prompt(top, client_intent, human_context, strategy, claim_limit))
        calibrated = _validate(packet, top)
    except Exception as exc:
        logger.warning("ai_ranking_calibration_failed candidate_count=%s error=%s", len(top), exc)
        return

    for position, row in enumerate(calibrated, start=1):
        canonical_id = str(row.get("canonical_facility_id"))
        row["ai_ranking"]["status"] = "AI_BATCH_SCORED_CALIBRATED"
        row["ai_ranking"]["rank"] = position
        row["ai_ranking"]["global_score"] = original_scores.get(canonical_id)
    ordered[:window_end] = calibrated


def _batch_ai_rank(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any], deterministic_fallback_key) -> List[Dict[str, Any]]:
    batch_size = max(4, min(30, int(os.getenv("OPTIME_AI_RANKING_BATCH_SIZE", "16"))))
    workers = max(1, min(10, int(os.getenv("OPTIME_AI_RANKING_MAX_WORKERS", "6"))))
    claim_limit = _resolve_claim_limit()
    batches = [rows[index:index + batch_size] for index in range(0, len(rows), batch_size)]
    scored_by_id: Dict[str, Dict[str, Any]] = {}

    def score_batch(batch: List[Dict[str, Any]], depth: int = 0) -> Dict[str, Dict[str, Any]]:
        """One batch/sub-batch's scoring attempt, with one contract-repair retry (see
        _validated_ai_response). If that still fails, the batch is split in half and
        each half retried independently rather than discarding every candidate in it --
        a single hard-to-score candidate should not erase its batch-mates' valid
        scores, and a whole batch should not erase every other batch's valid scores.
        Bottoms out at a single candidate: if that candidate still cannot be validated
        on its own, it is excluded from this ranking pass (never a fabricated score),
        which the caller surfaces as a closed-world gap rather than silently.
        """
        try:
            scored, _ = _validated_ai_response(_score_prompt(batch, client_intent, human_context, strategy, claim_limit), batch, _validate_scores, output_key="scored_candidates")
            return scored
        except Exception as exc:
            if len(batch) <= 1:
                logger.warning("ai_ranking_candidate_unrecoverable candidate_count=1 depth=%s error=%s", depth, exc)
                return {}
            mid = len(batch) // 2
            logger.warning("ai_ranking_batch_split_retry candidate_count=%s depth=%s error=%s", len(batch), depth, exc)
            left = score_batch(batch[:mid], depth + 1)
            right = score_batch(batch[mid:], depth + 1)
            return {**left, **right}

    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as executor:
        futures = [executor.submit(score_batch, batch) for batch in batches]
        for future in as_completed(futures):
            scored_by_id.update(future.result())

    expected_ids = {str(row.get("canonical_facility_id")) for row in rows}
    if not scored_by_id:
        _log_closed_world_mismatch("AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION", expected_ids, list(scored_by_id))
        raise RuntimeError("AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION")
    if set(scored_by_id) != expected_ids:
        missing = expected_ids - set(scored_by_id)
        logger.warning(
            "ai_batched_ranking_partial_coverage scored_count=%s missing_count=%s missing_ids=%s",
            len(scored_by_id), len(missing), sorted(missing)[:20],
        )
        _log_closed_world_mismatch("AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION", expected_ids, list(scored_by_id))
        raise RuntimeError(f"AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION:missing={len(missing)}_of_{len(expected_ids)}")

    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (-scored_by_id[str(pair[1].get("canonical_facility_id"))]["score"], *deterministic_fallback_key(pair[1]), pair[0]))
    ordered = [row for _, row in indexed]
    for position, row in enumerate(ordered, start=1):
        canonical_id = str(row.get("canonical_facility_id"))
        item = scored_by_id[canonical_id]
        row["ai_ranking"] = {
            "status": "AI_BATCH_SCORED",
            "rank": position,
            "global_score": item["score"],
            "reason": item["reason"],
            "information_deficits": item["information_deficits"],
            "rank_drivers": item["rank_drivers"],
            "rank_risks": item["rank_risks"],
            "citation_validation": item.get("citation_validation", "FULL"),
        }
    _calibrate_top_candidates(ordered, client_intent, human_context, strategy, claim_limit)
    return ordered


def rank_must_eligible_candidates(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any], deterministic_fallback_key) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not rows:
        return [], {"status": "NO_MUST_ELIGIBLE_CANDIDATES", "candidate_count": 0}

    enabled = os.getenv("OPTIME_SEMANTIC_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    required = os.getenv("OPTIME_AI_CANDIDATE_RANKING_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    batch_threshold = max(20, int(os.getenv("OPTIME_AI_RANKING_BATCH_THRESHOLD", "60")))

    if enabled:
        try:
            if len(rows) > batch_threshold:
                logger.info("ai_candidate_ranking_start mode=batched candidate_count=%s batch_threshold=%s", len(rows), batch_threshold)
                ordered = _batch_ai_rank(rows, client_intent, human_context, strategy, deterministic_fallback_key)
                calibrated_count = sum(1 for row in ordered if (row.get("ai_ranking") or {}).get("status") == "AI_BATCH_SCORED_CALIBRATED")
                return ordered, {
                    "status": "AI_BATCH_RANKED",
                    "candidate_count": len(ordered),
                    "closed_world_validated": True,
                    "evidence_model": "BATCHED_GOVERNED_CLAIM_LEDGER",
                    "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES",
                    "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE",
                    "batch_threshold": batch_threshold,
                    "calibration_window": _resolve_calibration_window(),
                    "calibrated_top_candidate_count": calibrated_count,
                }
            claim_limit = _resolve_claim_limit()
            single_shot_prompt = _prompt(rows, client_intent, human_context, strategy, claim_limit)
            logger.info(
                "ai_candidate_ranking_start mode=single_shot candidate_count=%s prompt_chars=%s claim_limit=%s",
                len(rows),
                len(json.dumps(single_shot_prompt, ensure_ascii=False)),
                claim_limit,
            )
            ordered, contract_repair_applied = _validated_ai_response(single_shot_prompt, rows, _validate, output_key="ranked_candidates")
            return ordered, {"status": "AI_RANKED", "candidate_count": len(ordered), "closed_world_validated": True, "contract_repair_applied": contract_repair_applied, "evidence_model": "GENERIC_GOVERNED_CLAIM_LEDGER", "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES", "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE"}
        except Exception as exc:
            fallback_reason = str(exc)
            logger.warning("ai_candidate_ranking_failed candidate_count=%s error=%s", len(rows), fallback_reason)
            if required:
                raise RuntimeError(f"AI_CANDIDATE_RANKING_REQUIRED_FAILED:{exc}") from exc
    else:
        fallback_reason = "OPTIME_SEMANTIC_AI_ENABLED is off"

    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (*deterministic_fallback_key(pair[1]), pair[0]))
    ordered = [row for _, row in indexed]
    for position, row in enumerate(ordered, start=1):
        row["ai_ranking"] = {
            "status": "DETERMINISTIC_FALLBACK",
            "rank": position,
            "reason": "Semantic AI ranking unavailable; governed deterministic ordering retained for continuity without inventing preference evidence.",
            "information_deficits": [str(pref.get("semantic_meaning") or "") for pref in ((human_context.get("dynamic_preference_model") or {}).get("preferences") or []) if str(pref.get("semantic_meaning") or "").strip()],
            "rank_drivers": [],
            "rank_risks": [],
        }
    return ordered, {"status": "DETERMINISTIC_FALLBACK" if not required else "REQUIRED_BUT_UNAVAILABLE", "candidate_count": len(ordered), "closed_world_validated": True, "evidence_model": "GENERIC_GOVERNED_CLAIM_LEDGER", "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES", "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE", "fallback_reason": fallback_reason}


def attach_nice_coverage(rows: List[Dict[str, Any]], client_intent: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy structured NICE audit only.

    The authoritative user-specific NICE coverage lives in semantic_preference_runtime.
    This function remains for migration diagnostics and backward-compatible audit data.
    """
    required = [str(item.get("key") or "") for item in client_intent.get("nice_to_haves") or [] if str(item.get("key") or "")]
    complete_ids: List[str] = []
    for row in rows:
        fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
        matches = {str(v) for v in fit.get("nice_match") or []}
        unknowns = {str(v) for v in fit.get("nice_unknown") or []}
        missing = [key for key in required if key not in matches and key not in unknowns]
        verified_match = [key for key in required if key in matches]
        unresolved = [key for key in required if key in unknowns or key in missing]
        if not required or len(verified_match) == len(required):
            status = "NICE_COMPLETE"
            if row.get("canonical_facility_id"):
                complete_ids.append(str(row.get("canonical_facility_id")))
        elif verified_match:
            status = "NICE_PARTIAL"
        else:
            status = "NICE_UNVERIFIED"
        row["nice_to_have_coverage"] = {"status": status, "required": required, "verified_match": verified_match, "unresolved": unresolved, "verified_match_count": len(verified_match), "required_count": len(required), "source": "LEGACY_STRUCTURED_NICE_AUDIT_ONLY"}
    return {"required_nice_to_have_count": len(required), "nice_complete_candidate_count": len(complete_ids), "nice_complete_candidate_ids": complete_ids, "authoritative": False, "client_message_mode": "AUDIT_ONLY", "verification_message": "Legacy structured NICE coverage is retained only for migration audit. Dynamic semantic preferences are authoritative."}


__all__ = ["rank_must_eligible_candidates", "attach_nice_coverage"]
