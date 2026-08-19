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
        " north ": " n ",
        " south ": " s ",
        " east ": " e ",
        " west ": " w ",
    }.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


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


def get_provider_housing_evidence(row: Dict[str, Any]) -> Dict[str, Any]:
    name = _norm(row.get("facility_name") or row.get("name"))
    address = _norm_addr(row.get("address") or row.get("facility_address"))
    canonical_id = str(row.get("canonical_facility_id") or row.get("canonical_id") or "")
    result: Dict[str, Any] = {
        "matched": False,
        "housing_modalities": [],
        "provider_housing_evidence": None,
        "life_plan_primary_evidence": None,
    }

    for record in _provider_records():
        aliases = {_norm(record.get("community_name"))}
        aliases.update(_norm(value) for value in record.get("aliases") or [])
        if not name or name not in aliases:
            continue
        if not address or address != _norm_addr(record.get("address")):
            continue
        result["matched"] = True
        result["housing_modalities"] = list(record.get("housing_modalities") or [])
        result["provider_housing_evidence"] = {
            "source_url": record.get("primary_source_url") or "UNKNOWN",
            "summary": record.get("evidence_summary") or "UNKNOWN",
            "evidence": record.get("evidence") or {},
        }
        break

    for record in _life_plan_records():
        ids = {str(value) for value in record.get("canonical_facility_ids") or []}
        if canonical_id and canonical_id in ids:
            result["matched"] = True
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
        if evidence.get("provider_housing_evidence"):
            row["provider_housing_evidence"] = evidence["provider_housing_evidence"]
        if evidence.get("life_plan_primary_evidence"):
            row["life_plan_primary_evidence"] = evidence["life_plan_primary_evidence"]


__all__ = ["attach_provider_housing_evidence", "get_provider_housing_evidence"]
