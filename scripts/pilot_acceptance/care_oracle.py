"""Independent pilot care-path proof; never reads the engine's fit verdict.

Owner approved service/program interpretation of care on 2026-10-02 (option 2).
This grades fictional fixture evidence only. Facility category is not a proof.
Existing case-specific licensing, cost, availability and forbidden-placement
contracts remain separate and cannot be overridden by this evaluator.
"""
from __future__ import annotations

from functools import lru_cache

from scripts.pilot_acceptance.oracle import _load


PATHS = {
    "INDEPENDENT_LIVING": (),
    "ASSISTED_LIVING": (("parameter", "adl_support"), ("service", "adl_support_verified")),
    "SMALL_GROUP_HOME": (("parameter", "adl_support"), ("service", "adl_support_verified")),
    "MEMORY_CARE": (("parameter", "memory_care"), ("parameter", "dementia_alz_programs"),
                    ("provider", "medical_memory_care"), ("provider", "continuum_memory_care")),
    "SKILLED_NURSING": (("parameter", "skilled_nursing_capabilities"), ("parameter", "nursing_24_7"),
                        ("service", "nursing_support_verified"), ("service", "physician_coordination_verified"),
                        ("provider", "medical_24_7_nursing")),
    "REHABILITATION": (("parameter", "pt"), ("parameter", "ot"), ("parameter", "therapy_staffing"),
                       ("parameter", "nursing_24_7"), ("service", "nursing_support_verified"),
                       ("service", "physician_coordination_verified"), ("provider", "continuum_rehabilitation")),
    "CONTINUING_CARE": (("service", "continuum_of_care_verified"), ("provider", "continuum_on_campus_progression")),
}


@lru_cache(maxsize=1)
def evidence():
    indexes = []
    for name, key in [("facility_parameter_evidence.json.gz.b64", "parameter_id"),
                      ("provider_capabilities.json.gz.b64", "capability")]:
        index = {}
        for row in _load(name):
            index.setdefault((row.get("canonical_facility_id"), row.get(key)), []).append(row)
        indexes.append(index)
    return tuple(indexes)


def _proof(kind, key, record, parameters, providers):
    fid = record.get("canonical_id") or record.get("canonical_facility_id")
    if kind == "service":
        payload = record.get("pilot_service_evidence") or {}
        provenance = payload.get("provenance") or {}
        rows = [payload] if (record.get("synthetic_pilot") is True
               and payload.get("source") == "SYNTHETIC_PILOT_SERVICE_FIXTURE"
               and provenance.get("synthetic_pilot") is True
               and provenance.get("not_real_world_evidence") is True) else []
        value_key = key
    else:
        records = parameters if kind == "parameter" else providers
        rows = records.get((fid, key), []) if isinstance(records, dict) else [r for r in records
                if r.get("canonical_facility_id") == fid
                and r.get("parameter_id" if kind == "parameter" else "capability") == key]
        value_key = "value"
    if any(r.get("conflict_status", "NONE") != "NONE" for r in rows):
        return {"kind": kind, "key": key, "state": "UNKNOWN", "sources": [], "reason": "conflicting evidence"}
    valid = [r for r in rows if r.get("canonical_facility_id") == fid
             and r.get("verification_status") == "VERIFIED" and r.get("source")
             and r.get("conflict_status", "NONE") == "NONE"]
    values = {str(r.get(value_key)).upper() for r in valid}
    positive = {"TRUE"} if kind == "service" else {"YES"}
    negative = {"FALSE"} if kind == "service" else {"NO", "LIMITED"}
    if values & positive and values & negative:
        state = "UNKNOWN"
    elif values & positive:
        state = "PASS"
    elif values & negative:
        state = "FAIL"
    else:
        state = "UNKNOWN"
    return {"kind": kind, "key": key, "state": state,
            "sources": [{"source": r.get("source"), "value": r.get(value_key),
                         "scope": r.get("scope"), "verified_at": r.get("last_verified") or r.get("verified_at")}
                        for r in valid]}


def evaluate_care(expected, record, parameters=None, providers=None):
    if parameters is None or providers is None:
        frozen_parameters, frozen_providers = evidence()
        parameters = frozen_parameters if parameters is None else parameters
        providers = frozen_providers if providers is None else providers
    unknown = set(expected) - set(PATHS)
    if unknown:
        return {"state": "FAIL", "error": f"unimplemented oracle.care values: {sorted(unknown)}", "paths": {}}
    paths = {}
    for path in sorted(expected):
        checks = [_proof(kind, key, record, parameters, providers) for kind, key in PATHS[path]]
        if path == "INDEPENDENT_LIVING":
            # Explicit housing modality is information about the offered housing,
            # not a capability inferred from the building's category/title.
            modalities = set(record.get("housing_modalities") or [])
            checks.append({"kind": "housing", "key": "housing_modalities",
                           "state": "PASS" if modalities & {"INDEPENDENT_LIVING", "ACTIVE_ADULT_55+"} else "UNKNOWN"})
        if path == "SMALL_GROUP_HOME":
            capacity = record.get("licensed_capacity")
            checks.append({"kind": "size", "key": "licensed_capacity",
                           "state": "UNKNOWN" if not isinstance(capacity, (int, float)) else "PASS" if 0 < capacity <= 16 else "FAIL"})
        states = {c["state"] for c in checks}
        paths[path] = {"state": "FAIL" if "FAIL" in states else "UNKNOWN" if "UNKNOWN" in states else "PASS", "checks": checks}
    states = {p["state"] for p in paths.values()}
    state = "PASS" if not expected or "PASS" in states else "UNKNOWN" if "UNKNOWN" in states else "FAIL"
    return {"state": state, "paths": paths}
