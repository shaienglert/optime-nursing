from __future__ import annotations

"""AI-owned ranking over every canonical MUST-eligible Nursing facility.

Every eligible candidate is AI-scored under one absolute resident-specific rubric.
Large universes are processed in parallel batches for latency, but no eligible facility
is removed before AI scoring. A final AI adjudication orders the leading set.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


Transport = Callable[[Dict[str, Any]], Dict[str, Any]]


def _compact_facility_packet(row: Dict[str, Any]) -> Dict[str, Any]:
    must = row.get("authoritative_must") if isinstance(row.get("authoritative_must"), dict) else {}
    if str(must.get("status") or "").upper() != "PASS":
        raise RuntimeError("V2_AI_RANKER_RECEIVED_NON_PASS_CANDIDATE")

    parameters = row.get("parameters") if isinstance(row.get("parameters"), dict) else {}
    known: List[Dict[str, Any]] = []
    unknown: List[str] = []
    conflicts: List[str] = []
    for parameter_id in sorted(parameters):
        item = parameters.get(parameter_id) if isinstance(parameters.get(parameter_id), dict) else {}
        value = item.get("raw_value")
        normalized = str(value or "UNKNOWN").strip().upper()
        if str(item.get("conflict_status") or "").upper() == "CONFLICT":
            conflicts.append(parameter_id)
            continue
        if value in (None, "") or normalized == "UNKNOWN":
            unknown.append(parameter_id)
            continue
        known.append(
            {
                "parameter_id": parameter_id,
                "value": value,
                "source": item.get("source"),
                "last_verified": item.get("last_verified"),
                "evidence_strength": item.get("evidence_strength"),
            }
        )

    service_levels = []
    for capability, item in sorted((row.get("semantic_service_levels") or {}).items()):
        if not isinstance(item, dict):
            continue
        service_levels.append(
            {
                "capability": capability,
                "level": item.get("level"),
                "confidence": item.get("confidence"),
                "source": item.get("source"),
                "source_url": item.get("source_url"),
                "observed_at": item.get("observed_at"),
            }
        )

    return {
        "canonical_facility_id": row.get("canonical_facility_id"),
        "facility_name": row.get("facility_name"),
        "city": row.get("city"),
        "state": row.get("state"),
        "canonical_type": row.get("canonical_type"),
        "housing_modalities": row.get("housing_modalities") or [],
        "authoritative_must": must,
        "known_parameters": known,
        "unknown_parameter_ids": unknown,
        "conflicting_parameter_ids": conflicts,
        "semantic_service_levels": service_levels,
        "evidence_summary": {
            "known_parameter_count": len(known),
            "unknown_parameter_count": len(unknown),
            "conflict_count": len(conflicts),
            "agent_evidence_record_count": int(row.get("agent_evidence_record_count") or 0),
        },
    }


def _client_packet(client_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "canonical_facts": client_state.get("canonical_facts") or [],
        "requirements": client_state.get("requirements") or [],
        "strategy_candidates": client_state.get("strategy_candidates") or [],
        "statement_accounting": client_state.get("statement_accounting") or [],
        "governance": client_state.get("governance") or {},
    }


def _score_prompt(rows: List[Dict[str, Any]], client_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_CANONICAL_AI_SCORER_V2",
        "mission": "Score every supplied MUST-PASS facility on one absolute resident-specific 0-100 fit scale using the complete compact canonical evidence packet. Scores from different batches must be directly comparable.",
        "global_rubric": {
            "90_100": "Exceptional resident-specific fit: strong governed evidence across important NICE preferences and relevant quality/lifestyle dimensions with very few material unresolved facts.",
            "75_89": "Strong fit: meaningful governed support with manageable unresolved NICE/provider details.",
            "55_74": "Plausible fit: mixed or incomplete preference/quality evidence, but no verified MUST failure.",
            "35_54": "Weak fit because of verified negative preference/quality evidence, not merely missing information.",
            "0_34": "Very weak resident-specific fit due to material verified negative evidence while still technically passing MUST.",
        },
        "rules": [
            "Every supplied facility already passed every authoritative MUST. You may never re-decide or contradict MUST eligibility.",
            "Return every supplied canonical_facility_id exactly once and no other ID.",
            "Use the same absolute scale across every batch; never normalize relative to batch peers.",
            "Use all supplied known canonical parameters and semantic service levels that are relevant to this resident.",
            "UNKNOWN means information deficit, never positive or negative evidence.",
            "Do not infer brand quality, services, price, activities, reputation or availability from outside knowledge.",
            "A missing NICE fact may reduce confidence/completeness but is not evidence of mismatch.",
            "unresolved_requirement_ids may include NICE requirements or unresolved non-MUST facts, but may never include a requirement that authoritative_must lists as PASS.",
        ],
        "canonical_client_state": _client_packet(client_state),
        "facilities": [_compact_facility_packet(row) for row in rows],
        "required_output": {
            "scored_candidates": [
                {
                    "canonical_facility_id": "string",
                    "score": 0,
                    "reason": "concise governed-evidence explanation",
                    "unresolved_requirement_ids": ["requirement_id"],
                    "information_deficits": ["concise string"],
                }
            ]
        },
    }


def _validate_scores(packet: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    expected = {str(row.get("canonical_facility_id")) for row in rows}
    supplied_by_id = {str(row.get("canonical_facility_id")): row for row in rows}
    scored = packet.get("scored_candidates") if isinstance(packet.get("scored_candidates"), list) else []
    actual = [str(item.get("canonical_facility_id") or "") for item in scored if isinstance(item, dict)]
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or set(actual) != expected:
        raise RuntimeError("V2_AI_SCORING_CLOSED_WORLD_VIOLATION")

    validated: Dict[str, Dict[str, Any]] = {}
    for item in scored:
        canonical_id = str(item.get("canonical_facility_id"))
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("V2_AI_SCORING_INVALID_SCORE") from exc
        if score < 0 or score > 100:
            raise RuntimeError("V2_AI_SCORING_SCORE_OUT_OF_RANGE")
        row = supplied_by_id[canonical_id]
        must = row.get("authoritative_must") if isinstance(row.get("authoritative_must"), dict) else {}
        passed_ids = {str(value) for value in must.get("pass") or []}
        unresolved_ids = {str(value) for value in item.get("unresolved_requirement_ids") or []}
        overlap = passed_ids.intersection(unresolved_ids)
        if overlap:
            raise RuntimeError("V2_AI_SCORING_CONTRADICTS_MUST_PASS:" + ",".join(sorted(overlap)))
        validated[canonical_id] = {
            "score": round(score, 3),
            "reason": str(item.get("reason") or "").strip(),
            "unresolved_requirement_ids": sorted(unresolved_ids),
            "information_deficits": [str(value) for value in item.get("information_deficits") or []],
        }
    return validated


def _adjudication_prompt(rows: List[Dict[str, Any]], client_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "OPTIME_NURSING_CANONICAL_AI_FINAL_ADJUDICATOR_V2",
        "mission": "Order the leading AI-scored MUST-PASS facilities for this specific resident. Use canonical evidence and the globally comparable scores; resolve close scores using resident-specific NICE evidence and evidence quality, never by changing MUST status.",
        "rules": [
            "Return every supplied canonical_facility_id exactly once.",
            "Never change authoritative MUST status.",
            "Use supplied canonical evidence only.",
            "UNKNOWN is uncertainty, not mismatch.",
            "Do not invent facts.",
        ],
        "canonical_client_state": _client_packet(client_state),
        "leading_candidates": [
            {
                **_compact_facility_packet(row),
                "global_ai_score": (row.get("ai_ranking") or {}).get("global_score"),
                "global_ai_reason": (row.get("ai_ranking") or {}).get("reason"),
            }
            for row in rows
        ],
        "required_output": {
            "ordered_candidate_ids": ["canonical_facility_id"],
            "reasons_by_id": {"canonical_facility_id": "concise reason"},
        },
    }


def _validate_adjudication(packet: Dict[str, Any], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expected = {str(row.get("canonical_facility_id")) for row in rows}
    ids = [str(value) for value in packet.get("ordered_candidate_ids") or []]
    if len(ids) != len(expected) or len(set(ids)) != len(ids) or set(ids) != expected:
        raise RuntimeError("V2_AI_ADJUDICATION_CLOSED_WORLD_VIOLATION")
    reasons = packet.get("reasons_by_id") if isinstance(packet.get("reasons_by_id"), dict) else {}
    by_id = {str(row.get("canonical_facility_id")): row for row in rows}
    ordered: List[Dict[str, Any]] = []
    for position, canonical_id in enumerate(ids, start=1):
        row = by_id[canonical_id]
        ranking = row.get("ai_ranking") if isinstance(row.get("ai_ranking"), dict) else {}
        row["ai_ranking"] = {
            **ranking,
            "status": "AI_GLOBAL_RANKED",
            "rank": position,
            "final_reason": str(reasons.get(canonical_id) or ranking.get("reason") or ""),
        }
        ordered.append(row)
    return ordered


def rank_all_canonical_must_eligible_v2(
    rows: List[Dict[str, Any]],
    client_state: Dict[str, Any],
    *,
    transport: Transport = _default_transport,
) -> List[Dict[str, Any]]:
    if not rows:
        return []

    batch_size = max(10, min(60, int(os.getenv("OPTIME_V2_AI_RANKING_BATCH_SIZE", "40"))))
    workers = max(1, min(12, int(os.getenv("OPTIME_V2_AI_RANKING_MAX_WORKERS", "8"))))
    adjudication_size = max(5, min(20, int(os.getenv("OPTIME_V2_AI_ADJUDICATION_SIZE", "12"))))
    batches = [rows[index:index + batch_size] for index in range(0, len(rows), batch_size)]
    scores: Dict[str, Dict[str, Any]] = {}

    def score_batch(batch: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return _validate_scores(transport(_score_prompt(batch, client_state)), batch)

    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as executor:
        futures = [executor.submit(score_batch, batch) for batch in batches]
        for future in as_completed(futures):
            scores.update(future.result())

    expected_ids = {str(row.get("canonical_facility_id")) for row in rows}
    if set(scores) != expected_ids:
        raise RuntimeError("V2_NOT_ALL_MUST_ELIGIBLE_AI_SCORED")

    indexed = list(enumerate(rows))
    indexed.sort(key=lambda pair: (-scores[str(pair[1].get("canonical_facility_id"))]["score"], pair[0]))
    globally_scored = [row for _, row in indexed]
    for position, row in enumerate(globally_scored, start=1):
        item = scores[str(row.get("canonical_facility_id"))]
        row["ai_ranking"] = {
            "status": "AI_BATCH_SCORED",
            "rank": position,
            "global_score": item["score"],
            "reason": item["reason"],
            "unresolved_requirement_ids": item["unresolved_requirement_ids"],
            "information_deficits": item["information_deficits"],
            "all_must_eligible_ai_scored": True,
        }

    leading = globally_scored[: min(adjudication_size, len(globally_scored))]
    if len(leading) > 1:
        leading = _validate_adjudication(transport(_adjudication_prompt(leading, client_state)), leading)
        leading_ids = {str(row.get("canonical_facility_id")) for row in leading}
        tail = [row for row in globally_scored if str(row.get("canonical_facility_id")) not in leading_ids]
        globally_scored = leading + tail
        for position, row in enumerate(globally_scored, start=1):
            ranking = row.get("ai_ranking") if isinstance(row.get("ai_ranking"), dict) else {}
            ranking["rank"] = position
            row["ai_ranking"] = ranking
    else:
        globally_scored[0]["ai_ranking"]["status"] = "AI_GLOBAL_RANKED"

    return globally_scored


__all__ = ["rank_all_canonical_must_eligible_v2"]
