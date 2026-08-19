from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "provider_housing_primary_evidence.json"
LIFE_PLAN_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "life_plan_primary_evidence.json"


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _norm_addr(value: Any) -> str:
    text = f" {_norm(value)} "
    for source, target in {
        " street ": " st ",
        " road ": " rd ",
        " avenue ": " ave ",
        " boulevard ": " blvd ",
        " drive ": " dr ",
        " lane ": " ln ",
        " court ": " ct ",
        " place ": " pl ",
        " highway ": " hwy ",
        " parkway ": " pkwy ",
        " north ": " n ",
        " south ": " s ",
        " east ": " e ",
        " west ": " w ",
    }.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def _zip(value: Any) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits[:5]


def _street_key(value: Any) -> str:
    text = _norm_addr(value)
    if not text:
        return ""
    # Ignore apartment/suite/unit suffixes while retaining the street number and name.
    text = re.split(r"\s+(?:apt|apartment|suite|ste|unit|building|bldg|#)\s*", text, maxsplit=1)[0]
    return text.strip()


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"records": []}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _provider_records() -> list[Dict[str, Any]]:
    return list(_read(PROVIDER_PATH).get("records") or [])


@lru_cache(maxsize=1)
def _life_plan_records() -> list[Dict[str, Any]]:
    return list(_read(LIFE_PLAN_PATH).get("records") or [])


def _same_market(row: Dict[str, Any], record: Dict[str, Any]) -> bool:
    row_city = _norm(row.get("city"))
    row_state = _norm(row.get("state"))
    record_city = _norm(record.get("city"))
    record_state = _norm(record.get("state"))
    if row_city and record_city and row_city != record_city:
        return False
    if row_state and record_state and row_state != record_state:
        return False
    return True


def _provider_identity_matches(row: Dict[str, Any], record: Dict[str, Any], canonical_id: str, name: str, address: str) -> bool:
    if not _same_market(row, record):
        return False
    governed_ids = {str(value) for value in record.get("canonical_facility_ids") or []}
    if canonical_id and canonical_id in governed_ids:
        return True

    aliases = {_norm(record.get("community_name"))}
    aliases.update(_norm(value) for value in record.get("aliases") or [])
    record_address = _norm_addr(record.get("address"))
    if address and record_address and address == record_address:
        return True
    if _street_key(address) and _street_key(address) == _street_key(record_address):
        return True

    exact_name_match = bool(name and name in aliases)
    if not exact_name_match:
        return False
    row_zip = _zip(row.get("zip") or row.get("postal_code"))
    record_zip = _zip(record.get("zip"))
    if row_zip and record_zip:
        return row_zip == record_zip
    # Exact governed provider name/alias within the same city/state is accepted
    # when one side lacks ZIP, but a conflicting street number is not.
    row_number = (address.split(" ", 1)[0] if address else "")
    record_number = (record_address.split(" ", 1)[0] if record_address else "")
    return not (row_number and record_number and row_number.isdigit() and record_number.isdigit() and row_number != record_number)


def get_provider_housing_evidence(row: Dict[str, Any]) -> Dict[str, Any]:
    name = _norm(row.get("facility_name") or row.get("name"))
    address = _norm_addr(row.get("address") or row.get("facility_address"))
    canonical_id = str(row.get("canonical_facility_id") or row.get("canonical_id") or "")
    canonical_type = str(row.get("canonical_type") or "UNKNOWN").upper()
    result: Dict[str, Any] = {
        "matched": False,
        "housing_modalities": [],
        "provider_housing_evidence": None,
        "provider_aliases": [],
        "life_plan_primary_evidence": None,
        "campus_group_id": None,
    }

    for record in _provider_records():
        if not _provider_identity_matches(row, record, canonical_id, name, address):
            continue
        result["matched"] = True
        result["provider_aliases"] = [str(record.get("community_name") or "")] + [str(value) for value in record.get("aliases") or []]

        # Provider lifestyle evidence describes the residential community, not a
        # skilled-nursing license component on the same campus. Keep the SNF row
        # available for rehab/continuum evidence, but do not let campus lifestyle
        # claims turn the SNF component into a duplicate lifestyle recommendation.
        if canonical_type != "SKILLED_NURSING":
            result["housing_modalities"] = list(record.get("housing_modalities") or [])
            result["provider_housing_evidence"] = {
                "community_name": record.get("community_name") or "UNKNOWN",
                "aliases": [str(value) for value in record.get("aliases") or []],
                "address": record.get("address") or "UNKNOWN",
                "city": record.get("city") or "UNKNOWN",
                "state": record.get("state") or "UNKNOWN",
                "zip": record.get("zip") or "UNKNOWN",
                "source_url": record.get("primary_source_url") or "UNKNOWN",
                "summary": record.get("evidence_summary") or "UNKNOWN",
                "evidence": record.get("evidence") or {},
            }
        break

    for record in _life_plan_records():
        ids = {str(value) for value in record.get("canonical_facility_ids") or []}
        if canonical_id and canonical_id in ids:
            result["matched"] = True
            result["campus_group_id"] = record.get("campus_group_id") or None
            modalities = list(result.get("housing_modalities") or [])
            for modality in record.get("modalities") or []:
                if modality not in modalities:
                    modalities.append(modality)
            result["housing_modalities"] = modalities
            result["life_plan_primary_evidence"] = {
                "community_name": record.get("community_name") or "UNKNOWN",
                "operator_name": record.get("operator_name") or "UNKNOWN",
                "source_url": record.get("primary_source_url") or "UNKNOWN",
                "independent_living_source_url": record.get("independent_living_source_url") or "UNKNOWN",
                "rehabilitation_source_url": record.get("rehabilitation_source_url") or "UNKNOWN",
                "summary": record.get("evidence_summary") or "UNKNOWN",
            }
            break

    return result


def attach_provider_housing_evidence(rows: list[Dict[str, Any]]) -> None:
    for row in rows:
        evidence = get_provider_housing_evidence(row)
        if not evidence.get("matched"):
            continue
        modalities = list(row.get("housing_modalities") or [])
        for modality in evidence.get("housing_modalities") or []:
            if modality not in modalities:
                modalities.append(modality)
        if modalities:
            row["housing_modalities"] = modalities
        if evidence.get("campus_group_id"):
            row["campus_group_id"] = evidence["campus_group_id"]
        if evidence.get("provider_housing_evidence"):
            provider = evidence["provider_housing_evidence"]
            row["provider_housing_evidence"] = provider
            aliases = [str(value) for value in row.get("aliases") or []]
            for alias in evidence.get("provider_aliases") or []:
                if alias and alias not in aliases:
                    aliases.append(alias)
            if aliases:
                row["aliases"] = aliases
            community_name = str(provider.get("community_name") or "").strip()
            if community_name:
                row.setdefault("licensed_facility_name", row.get("facility_name") or row.get("name") or "UNKNOWN")
                row["facility_name"] = community_name
            provider_address = str(provider.get("address") or "").strip()
            if provider_address and provider_address.upper() != "UNKNOWN":
                row.setdefault("licensed_address", row.get("address") or row.get("facility_address") or "UNKNOWN")
                row["address"] = provider_address
            for key in ("city", "state", "zip"):
                value = str(provider.get(key) or "").strip()
                if value and value.upper() != "UNKNOWN":
                    row[key] = value
        if evidence.get("life_plan_primary_evidence"):
            row["life_plan_primary_evidence"] = evidence["life_plan_primary_evidence"]


__all__ = ["attach_provider_housing_evidence", "get_provider_housing_evidence"]
