from __future__ import annotations

"""Closed-world NICE verification over canonical V2 facility evidence."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from typing import Any, Callable, Dict, List

from app.services.semantic_intent_ai import _default_transport


Transport = Callable[[Dict[str, Any]], Dict[str, Any]]


def _claim_id(prefix: str, key: str, value: Any) -> str:
    digest = hashlib.sha256(f"{prefix}|{key}|{value}".encode("utf-8")).hexdigest()[:18]
    return f"claim:{digest}"


def build_canonical_claim_ledger_v2(row: Dict[str, Any]) -> Dict[str, Any]:
    claims: List[Dict[str, Any]] = []
    parameters = row.get("parameters") if isinstance(row.get("parameters"), dict) else {}
    for parameter_id in sorted(parameters):
        item = parameters.get(parameter_id) if isinstance(parameters.get(parameter_id), dict) else {}
        value = item.get("raw_value")
        normalized = str(value or "UNKNOWN").strip().upper()
        if value in (None, "") or normalized == "UNKNOWN" or str(item.get("conflict_status") or "").upper() == "CONFLICT":
            continue
        claims.append(
            {
                "claim_id": _claim_id("parameter", parameter_id, value),
                "claim_type": "PARAMETER",
                "key": parameter_id,
                "value": value,
                "source": item.get("source"),
                "last_verified": item.get("last_verified"),
                "evidence_strength": item.get("evidence_strength"),
            }
        )

    service_levels = row.get("semantic_service_levels") if isinstance(row.get("semantic_service_levels"), dict) else {}
    for capability in sorted(service_levels):
        item = service_levels.get(capability) if isinstance(service_levels.get(capability), dict) else {}
        level = str(item.get("level") or "UNKNOWN").upper()
        if level in {"", "UNKNOWN", "NONE_OR_NOT_STATED"}:
            continue
        claims.append(
            {
                "claim_id": _claim_id("service", capability, level),
                "claim_type": "SEMANTIC_SERVICE_LEVEL",
                "key": capability,
                "value": level,
                "source": item.get("source"),
                "source_url": item.get("source_url"),
                "observed_at": item.get("observed_at"),
            }
        )

    return {
        "canonical_facility_id": row.get("canonical_facility_id"),
        "facility_name": row.get("facility_name"),
        "claims": claims,
        "claim_count": len(claims),
        "source_model": "CANONICAL_FACILITY_EVIDENCE_STATE_V2",
    }


def _nice_requirements(client_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        requirement
        for requirement in client_state.get("requirements") or []
        if isinstance(requirement, dict)
        and str(requirement.get("importance") or "").upper() == "NICE"
        and str(requirement.get("knowledge_state") or "KNOWN").upper() == "KNOWN"
    ]


def _prompt(row: Dict[str, Any], client_state: Dict[str, Any]) -> Dict[str, Any]:
    nice = _nice_requirements(client_state)
    return {
        "role": "OPTIME_NURSING_CANONICAL_NICE_VERIFIER_V2",
        "mission": "Verify each resident NICE requirement against one facility's closed canonical evidence ledger.",
        "rules": [
            "Return exactly one assessment for every supplied NICE requirement_id.",
            "MATCH or MISMATCH requires at least one supporting_claim_id from the supplied ledger.",
            "If the supplied claims do not specifically resolve the requirement, return UNKNOWN.",
            "Do not use outside knowledge, brand assumptions or generic expectations.",
            "A broad category does not prove a narrow preference unless the cited claim entails it.",
            "UNKNOWN is not MISMATCH.",
            "Never change MUST eligibility or AI ranking.",
        ],
        "nice_requirements": nice,
        "facility_ledger": build_canonical_claim_ledger_v2(row),
        "required_output": {
            "assessments": [
                {
                    "requirement_id": "req:id",
                    "status": "MATCH|MISMATCH|UNKNOWN",
                    "supporting_claim_ids": ["claim:id"],
                    "reason": "concise reason",
                    "provider_question_if_unknown": "string|null",
                }
            ]
        },
    }


def _validate(packet: Dict[str, Any], row: Dict[str, Any], client_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    requirements = _nice_requirements(client_state)
    expected = {str(item.get("requirement_id")) for item in requirements}
    ledger = build_canonical_claim_ledger_v2(row)
    valid_claims = {str(item.get("claim_id")) for item in ledger.get("claims") or []}
    assessments = packet.get("assessments") if isinstance(packet.get("assessments"), list) else []
    ids = [str(item.get("requirement_id") or "") for item in assessments if isinstance(item, dict)]
    if len(ids) != len(expected) or len(set(ids)) != len(ids) or set(ids) != expected:
        raise RuntimeError("V2_NICE_CLOSED_WORLD_REQUIREMENT_VIOLATION")

    out: List[Dict[str, Any]] = []
    for item in assessments:
        requirement_id = str(item.get("requirement_id"))
        status = str(item.get("status") or "UNKNOWN").upper()
        if status not in {"MATCH", "MISMATCH", "UNKNOWN"}:
            raise RuntimeError(f"V2_NICE_INVALID_STATUS:{requirement_id}")
        supporting = [str(value) for value in item.get("supporting_claim_ids") or []]
        if any(claim_id not in valid_claims for claim_id in supporting):
            raise RuntimeError(f"V2_NICE_UNKNOWN_CLAIM:{requirement_id}")
        if status in {"MATCH", "MISMATCH"} and not supporting:
            raise RuntimeError(f"V2_NICE_ASSERTION_WITHOUT_EVIDENCE:{requirement_id}")
        if status == "UNKNOWN":
            supporting = []
        out.append(
            {
                "requirement_id": requirement_id,
                "status": status,
                "supporting_claim_ids": supporting,
                "reason": str(item.get("reason") or "").strip(),
                "provider_question_if_unknown": str(item.get("provider_question_if_unknown") or "").strip() or None,
            }
        )
    return out


def verify_top_nice_canonical_v2(
    rows: List[Dict[str, Any]],
    client_state: Dict[str, Any],
    *,
    transport: Transport = _default_transport,
) -> List[Dict[str, Any]]:
    nice = _nice_requirements(client_state)
    if not rows:
        return []
    if not nice:
        for row in rows:
            row["nice_verification"] = {"status": "NO_NICE_REQUIREMENTS", "assessments": [], "match_count": 0, "unknown_count": 0, "mismatch_count": 0}
        return rows

    max_workers = max(1, min(10, int(os.getenv("OPTIME_V2_NICE_MAX_WORKERS", "8"))))
    by_index: Dict[int, List[Dict[str, Any]]] = {}

    def verify(index: int, row: Dict[str, Any]):
        return index, _validate(transport(_prompt(row, client_state)), row, client_state)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(rows))) as executor:
        futures = [executor.submit(verify, index, row) for index, row in enumerate(rows)]
        for future in as_completed(futures):
            index, assessments = future.result()
            by_index[index] = assessments

    for index, row in enumerate(rows):
        assessments = by_index[index]
        matches = sum(1 for item in assessments if item["status"] == "MATCH")
        mismatches = sum(1 for item in assessments if item["status"] == "MISMATCH")
        unknowns = sum(1 for item in assessments if item["status"] == "UNKNOWN")
        if matches == len(assessments):
            status = "NICE_COMPLETE"
        elif matches:
            status = "NICE_PARTIAL"
        elif mismatches and not unknowns:
            status = "NICE_MISMATCH"
        else:
            status = "NICE_UNVERIFIED"
        row["nice_verification"] = {
            "status": status,
            "assessments": assessments,
            "match_count": matches,
            "mismatch_count": mismatches,
            "unknown_count": unknowns,
            "required_count": len(assessments),
            "verification_model": "CANONICAL_CLOSED_WORLD_V2",
        }
    return rows


__all__ = ["build_canonical_claim_ledger_v2", "verify_top_nice_canonical_v2"]
