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


def _prompt(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
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
        ],
        "client_intent": client_intent,
        "human_context": human_context,
        "living_strategy": strategy,
        "must_eligible_candidates": _ranking_packet(rows),
        "required_output": {"ranked_candidates": [{"canonical_facility_id": "string", "reason": "string", "information_deficits": ["string"]}]},
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
        ],
        "client_intent": client_intent,
        "human_context": human_context,
        "living_strategy": strategy,
        "must_eligible_candidates": _ranking_packet(rows, claim_limit=claim_limit),
        "required_output": {"scored_candidates": [{"canonical_facility_id": "string", "score": 0, "reason": "string", "information_deficits": ["string"]}]},
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
        row["ai_ranking"] = {"status": "AI_RANKED", "rank": position, "reason": str(item.get("reason") or ""), "information_deficits": [str(v) for v in item.get("information_deficits") or []]}
        ordered.append(row)
    return ordered


def _validate_scores(packet: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    supplied = {str(row.get("canonical_facility_id") or "") for row in rows if row.get("canonical_facility_id")}
    scored = packet.get("scored_candidates") if isinstance(packet.get("scored_candidates"), list) else []
    ids = [str(item.get("canonical_facility_id") or "") for item in scored if isinstance(item, dict)]
    if len(ids) != len(supplied) or len(set(ids)) != len(ids) or set(ids) != supplied:
        _log_closed_world_mismatch("AI_CANDIDATE_SCORING_CLOSED_WORLD_VIOLATION", supplied, ids)
        raise RuntimeError("AI_CANDIDATE_SCORING_CLOSED_WORLD_VIOLATION")
    validated: Dict[str, Dict[str, Any]] = {}
    for item in scored:
        canonical_id = str(item.get("canonical_facility_id") or "")
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("AI_CANDIDATE_SCORING_INVALID_SCORE") from exc
        if score < 0 or score > 100:
            raise RuntimeError("AI_CANDIDATE_SCORING_INVALID_SCORE_RANGE")
        validated[canonical_id] = {"score": round(score, 3), "reason": str(item.get("reason") or ""), "information_deficits": [str(v) for v in item.get("information_deficits") or []]}
    return validated


def _batch_ai_rank(rows: List[Dict[str, Any]], client_intent: Dict[str, Any], human_context: Dict[str, Any], strategy: Dict[str, Any], deterministic_fallback_key) -> List[Dict[str, Any]]:
    batch_size = max(4, min(30, int(os.getenv("OPTIME_AI_RANKING_BATCH_SIZE", "16"))))
    workers = max(1, min(10, int(os.getenv("OPTIME_AI_RANKING_MAX_WORKERS", "6"))))
    claim_limit = max(30, min(160, int(os.getenv("OPTIME_AI_RANKING_CLAIMS_PER_CANDIDATE", "80"))))
    batches = [rows[index:index + batch_size] for index in range(0, len(rows), batch_size)]
    scored_by_id: Dict[str, Dict[str, Any]] = {}

    def score_batch(batch: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        packet = _default_transport(_score_prompt(batch, client_intent, human_context, strategy, claim_limit))
        return _validate_scores(packet, batch)

    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as executor:
        futures = [executor.submit(score_batch, batch) for batch in batches]
        for future in as_completed(futures):
            scored_by_id.update(future.result())

    expected_ids = {str(row.get("canonical_facility_id")) for row in rows}
    if set(scored_by_id) != expected_ids:
        _log_closed_world_mismatch("AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION", expected_ids, list(scored_by_id))
        raise RuntimeError("AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION")

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
        }
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
                return ordered, {
                    "status": "AI_BATCH_RANKED",
                    "candidate_count": len(ordered),
                    "closed_world_validated": True,
                    "evidence_model": "BATCHED_GOVERNED_CLAIM_LEDGER",
                    "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES",
                    "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE",
                    "batch_threshold": batch_threshold,
                }
            single_shot_prompt = _prompt(rows, client_intent, human_context, strategy)
            logger.info(
                "ai_candidate_ranking_start mode=single_shot candidate_count=%s prompt_chars=%s (no claim_limit applied on this path)",
                len(rows),
                len(json.dumps(single_shot_prompt, ensure_ascii=False)),
            )
            ordered = _validate(_default_transport(single_shot_prompt), rows)
            return ordered, {"status": "AI_RANKED", "candidate_count": len(ordered), "closed_world_validated": True, "evidence_model": "GENERIC_GOVERNED_CLAIM_LEDGER", "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES", "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE"}
        except Exception as exc:
            logger.warning("ai_candidate_ranking_failed candidate_count=%s error=%s", len(rows), exc)
            if required:
                raise RuntimeError(f"AI_CANDIDATE_RANKING_REQUIRED_FAILED:{exc}") from exc

    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (*deterministic_fallback_key(pair[1]), pair[0]))
    ordered = [row for _, row in indexed]
    for position, row in enumerate(ordered, start=1):
        row["ai_ranking"] = {
            "status": "DETERMINISTIC_FALLBACK",
            "rank": position,
            "reason": "Semantic AI ranking unavailable; governed deterministic ordering retained for continuity without inventing preference evidence.",
            "information_deficits": [str(pref.get("semantic_meaning") or "") for pref in ((human_context.get("dynamic_preference_model") or {}).get("preferences") or []) if str(pref.get("semantic_meaning") or "").strip()],
        }
    return ordered, {"status": "DETERMINISTIC_FALLBACK" if not required else "REQUIRED_BUT_UNAVAILABLE", "candidate_count": len(ordered), "closed_world_validated": True, "evidence_model": "GENERIC_GOVERNED_CLAIM_LEDGER", "preference_model": "DYNAMIC_SEMANTIC_PREFERENCES", "unknown_policy": "INFORMATION_DEFICIT_NOT_NEGATIVE"}


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
