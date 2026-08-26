from __future__ import annotations

"""Deterministic MUST Guardian for Nursing V2.

The AI Process Owner defines the canonical requirement. The Guardian evaluates that
requirement against the canonical facility evidence state. It never ranks, invents
facts, parses user text, or turns missing evidence into NO.
"""

from typing import Any, Dict, List

from app.services.semantic_evidence_ai import CAPABILITY_SCHEMA


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _parameter_verdicts(facility_state: Dict[str, Any], parameter_ids: List[str]) -> List[Dict[str, Any]]:
    parameters = facility_state.get("parameters") if isinstance(facility_state.get("parameters"), dict) else {}
    out: List[Dict[str, Any]] = []
    for parameter_id in parameter_ids:
        row = parameters.get(parameter_id) if isinstance(parameters.get(parameter_id), dict) else {}
        raw = _upper(row.get("raw_value")) or "UNKNOWN"
        conflict = _upper(row.get("conflict_status")) == "CONFLICT"
        out.append(
            {
                "parameter_id": parameter_id,
                "value": "CONFLICT" if conflict else raw,
                "source": row.get("source"),
                "last_verified": row.get("last_verified"),
                "evidence_strength": row.get("evidence_strength"),
                "provenance": row.get("provenance") or {},
            }
        )
    return out


def _service_level_verdict(facility_state: Dict[str, Any], requirement: Dict[str, Any]) -> Dict[str, Any] | None:
    capability = _upper(requirement.get("capability_key"))
    schema = CAPABILITY_SCHEMA.get(capability)
    if not schema:
        return None
    service_levels = facility_state.get("semantic_service_levels") if isinstance(facility_state.get("semantic_service_levels"), dict) else {}
    evidence = service_levels.get(capability) if isinstance(service_levels.get(capability), dict) else None
    if not evidence:
        return {
            "status": "PENDING_VERIFICATION",
            "reason": "No governed semantic service-level evidence is available for this capability.",
            "capability": capability,
            "required_level": _upper(requirement.get("required_service_level")) or "UNKNOWN",
            "observed_level": "UNKNOWN",
            "evidence": None,
        }

    observed = _upper(evidence.get("level"))
    required = _upper(requirement.get("required_service_level"))
    levels = [str(value).upper() for value in schema.get("levels") or []]
    if observed not in levels:
        return {
            "status": "PENDING_VERIFICATION",
            "reason": "Observed semantic service level is outside the governed capability schema.",
            "capability": capability,
            "required_level": required or "UNKNOWN",
            "observed_level": observed or "UNKNOWN",
            "evidence": evidence,
        }
    if observed in {"NONE_OR_NOT_STATED", "UNKNOWN", ""}:
        return {
            "status": "PENDING_VERIFICATION",
            "reason": "The source did not establish the requested service level; absence of a statement is not a verified NO.",
            "capability": capability,
            "required_level": required or "UNKNOWN",
            "observed_level": observed,
            "evidence": evidence,
        }

    if not required or required == "UNKNOWN":
        sufficient = observed in {str(value).upper() for value in schema.get("must_sufficient_levels") or []}
        return {
            "status": "PASS" if sufficient else "PENDING_VERIFICATION",
            "reason": "Observed governed service level satisfies the generic capability requirement." if sufficient else "Observed level does not establish the generic governed MUST threshold.",
            "capability": capability,
            "required_level": "GOVERNED_GENERIC_THRESHOLD",
            "observed_level": observed,
            "evidence": evidence,
        }

    if required not in levels:
        # A novel required level cannot be silently translated by rules. The semantic
        # research layer must resolve it explicitly.
        return {
            "status": "PENDING_VERIFICATION",
            "reason": "Client-required service level is not represented by the governed closed capability schema; semantic verification is required.",
            "capability": capability,
            "required_level": required,
            "observed_level": observed,
            "evidence": evidence,
        }

    # Schema level order is weak -> strong for guarded service capabilities. A weaker
    # public statement never proves the stronger service is unavailable; it stays
    # pending rather than FAIL.
    sufficient = levels.index(observed) >= levels.index(required)
    return {
        "status": "PASS" if sufficient else "PENDING_VERIFICATION",
        "reason": "Observed service level meets or exceeds the client-required governed level." if sufficient else "Observed public evidence is weaker than the required service level; stronger capability remains unverified, not disproven.",
        "capability": capability,
        "required_level": required,
        "observed_level": observed,
        "evidence": evidence,
    }


def evaluate_canonical_must_v2(facility_state: Dict[str, Any], must_context: Dict[str, Any]) -> Dict[str, Any]:
    requirements = [row for row in must_context.get("requirements") or [] if isinstance(row, dict)]
    traces: List[Dict[str, Any]] = []
    passed: List[str] = []
    pending: List[str] = []
    failed: List[str] = []

    for requirement in requirements:
        requirement_id = str(requirement.get("requirement_id") or requirement.get("capability_key") or "").strip()
        capability = _upper(requirement.get("capability_key"))
        parameter_ids = [str(value) for value in requirement.get("evidence_parameter_ids") or [] if str(value)]
        semantic_needed = bool(requirement.get("semantic_evidence_needed", not parameter_ids))
        parameter_evidence = _parameter_verdicts(facility_state, parameter_ids)
        service_verdict = _service_level_verdict(facility_state, requirement)

        status = "PENDING_VERIFICATION"
        reason = "No governed evidence path has resolved this MUST."

        # Specific guarded service levels are authoritative when available. This avoids
        # a generic boolean YES overriding a narrower client requirement.
        if service_verdict is not None and (semantic_needed or _upper(requirement.get("required_service_level")) not in {"", "UNKNOWN"}):
            status = str(service_verdict["status"])
            reason = str(service_verdict["reason"])
        else:
            values = [str(item.get("value") or "UNKNOWN").upper() for item in parameter_evidence]
            if "CONFLICT" in values:
                status = "PENDING_VERIFICATION"
                reason = "Governed evidence sources conflict; the requirement cannot be finalized."
            elif any(value in {"YES", "TRUE", "AVAILABLE", "VERIFIED"} for value in values) and not semantic_needed:
                status = "PASS"
                reason = "A bound canonical parameter has positive governed evidence."
            elif values and all(value in {"NO", "FALSE", "NOT_AVAILABLE"} for value in values) and not semantic_needed:
                status = "FAIL"
                reason = "Every bound canonical parameter has explicit governed negative evidence."
            elif service_verdict is not None:
                status = str(service_verdict["status"])
                reason = str(service_verdict["reason"])

        if status == "PASS":
            passed.append(requirement_id)
        elif status == "FAIL":
            failed.append(requirement_id)
        else:
            pending.append(requirement_id)
            status = "PENDING_VERIFICATION"

        traces.append(
            {
                "requirement_id": requirement_id,
                "capability_key": capability,
                "client_expression": requirement.get("client_expression"),
                "required_service_level": requirement.get("required_service_level"),
                "status": status,
                "reason": reason,
                "parameter_evidence": parameter_evidence,
                "service_level_evidence": service_verdict,
                "semantic_evidence_needed": semantic_needed,
            }
        )

    gate = "FAIL" if failed else ("PENDING_VERIFICATION" if pending else "PASS")
    return {
        "status": gate,
        "pass": passed,
        "pending_verification": pending,
        "fail": failed,
        "requirement_trace": traces,
        "authoritative": True,
        "immutable_downstream": True,
        "guardian": "CANONICAL_MUST_GUARD_V2",
        "unknown_policy": "MISSING_OR_WEAKER_EVIDENCE_IS_PENDING_NOT_FAIL",
    }


__all__ = ["evaluate_canonical_must_v2"]
