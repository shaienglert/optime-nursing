from __future__ import annotations

import copy
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.services.facility_parameter_service import (
    get_facility_parameter_table,
    get_runtime_cache_status,
    get_runtime_metadata,
)
from app.services.patient_decision_engine import _eligibility_from_needs, _score_result


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _snapshot_version(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


class ActiveFacilitySnapshotStore:
    def __init__(
        self,
        *,
        active_snapshot_version: str,
        last_successful_refresh: str,
        facility_tables: Iterable[Dict[str, Any]],
        stale_after_days: int = 180,
    ) -> None:
        self.active_snapshot_version = active_snapshot_version
        self.last_successful_refresh = last_successful_refresh
        self.stale_after_days = stale_after_days
        self._facilities: Dict[str, Dict[str, Any]] = {}
        self._facility_refresh_counts: Dict[str, int] = {}
        self._parameter_refresh_counts: Dict[str, Dict[str, int]] = {}
        self._recommendation_count = 0
        self._network_request_count = 0
        self._profile_rebuild_count = 0

        for table in facility_tables:
            canonical_id = str(table["canonical_facility_id"])
            record = copy.deepcopy(table)
            record["facility_snapshot_version"] = _snapshot_version(
                {
                    "active_snapshot_version": active_snapshot_version,
                    "canonical_facility_id": canonical_id,
                    "rows": record.get("rows") or [],
                }
            )
            record["last_successful_refresh"] = last_successful_refresh
            record["changed_parameters"] = []
            record["unchanged_parameters_reused"] = len(record.get("rows") or [])
            record["refresh_count"] = 0
            self._update_parameter_health(record)
            self._facilities[canonical_id] = record
            self._facility_refresh_counts[canonical_id] = 0
            self._parameter_refresh_counts[canonical_id] = {}

    @classmethod
    def from_active_runtime(
        cls,
        *,
        facility_ids: Iterable[str],
        parameter_ids: Optional[Iterable[str]] = None,
        stale_after_days: int = 180,
    ) -> "ActiveFacilitySnapshotStore":
        runtime_meta = get_runtime_metadata()
        cache_status = get_runtime_cache_status()
        selected_parameter_ids = set(parameter_ids or [])
        tables = []
        for canonical_id in facility_ids:
            table = get_facility_parameter_table(str(canonical_id), include_evidence_records=False)
            if selected_parameter_ids:
                table["rows"] = [
                    row for row in table.get("rows") or [] if row.get("parameter_id") in selected_parameter_ids
                ]
            tables.append(table)

        last_refresh = str(
            runtime_meta.get("runtime_timestamp")
            or cache_status.get("loaded_at")
            or _utc_now_iso()
        )
        return cls(
            active_snapshot_version=str(runtime_meta.get("runtime_version") or "unknown"),
            last_successful_refresh=last_refresh,
            facility_tables=tables,
            stale_after_days=stale_after_days,
        )

    def _update_parameter_health(self, record: Dict[str, Any]) -> None:
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=self.stale_after_days)
        stale = []
        missing = []
        for row in record.get("rows") or []:
            parameter_id = str(row.get("parameter_id") or "")
            if row.get("raw_value") in {None, "UNKNOWN"}:
                missing.append(parameter_id)
                continue
            last_verified = _parse_timestamp(row.get("last_verified"))
            if last_verified is None or last_verified < stale_cutoff:
                stale.append(parameter_id)
        record["stale_parameters"] = sorted(stale)
        record["missing_parameters"] = sorted(missing)

    def facility_object_identity(self, canonical_facility_id: str) -> int:
        return id(self._facilities[canonical_facility_id])

    def apply_source_update(
        self,
        *,
        canonical_facility_id: str,
        parameter_updates: Dict[str, Dict[str, Any]],
        refreshed_at: Optional[str] = None,
        source_update_id: str = "simulated-source-update",
    ) -> Dict[str, Any]:
        if canonical_facility_id not in self._facilities:
            raise KeyError(canonical_facility_id)
        if not parameter_updates:
            raise ValueError("parameter_updates must not be empty")

        refreshed_at = refreshed_at or _utc_now_iso()
        previous = self._facilities[canonical_facility_id]
        updated = copy.deepcopy(previous)
        rows_by_parameter = {str(row.get("parameter_id")): row for row in updated.get("rows") or []}
        unknown_parameters = sorted(set(parameter_updates).difference(rows_by_parameter))
        if unknown_parameters:
            raise KeyError(f"Parameters are not present in active facility snapshot: {unknown_parameters}")

        changed_parameters = []
        for parameter_id, changes in parameter_updates.items():
            row = rows_by_parameter[parameter_id]
            before = copy.deepcopy(row)
            row.update(copy.deepcopy(changes))
            row["last_verified"] = changes.get("last_verified") or refreshed_at
            if row != before:
                changed_parameters.append(parameter_id)
                parameter_counts = self._parameter_refresh_counts[canonical_facility_id]
                parameter_counts[parameter_id] = int(parameter_counts.get(parameter_id) or 0) + 1

        if not changed_parameters:
            raise ValueError("Source update did not change any active parameter")

        previous_active_version = self.active_snapshot_version
        self.active_snapshot_version = _snapshot_version(
            {
                "previous_active_snapshot_version": previous_active_version,
                "canonical_facility_id": canonical_facility_id,
                "source_update_id": source_update_id,
                "refreshed_at": refreshed_at,
                "changed_parameters": changed_parameters,
                "rows": updated.get("rows") or [],
            }
        )
        updated["facility_snapshot_version"] = _snapshot_version(
            {
                "previous_facility_snapshot_version": previous["facility_snapshot_version"],
                "source_update_id": source_update_id,
                "refreshed_at": refreshed_at,
                "changed_parameters": changed_parameters,
                "rows": updated.get("rows") or [],
            }
        )
        updated["last_successful_refresh"] = refreshed_at
        updated["changed_parameters"] = sorted(changed_parameters)
        updated["unchanged_parameters_reused"] = len(updated.get("rows") or []) - len(changed_parameters)
        self._facility_refresh_counts[canonical_facility_id] += 1
        updated["refresh_count"] = self._facility_refresh_counts[canonical_facility_id]
        self._update_parameter_health(updated)
        self._facilities[canonical_facility_id] = updated
        self.last_successful_refresh = refreshed_at

        return {
            "source_update_id": source_update_id,
            "previous_active_snapshot_version": previous_active_version,
            "active_snapshot_version": self.active_snapshot_version,
            "affected_facilities": [canonical_facility_id],
            "changed_parameters": sorted(changed_parameters),
            "unchanged_facilities_reused": sorted(
                facility_id for facility_id in self._facilities if facility_id != canonical_facility_id
            ),
        }

    def recommend(self, *, needs: List[Dict[str, Any]], limit: int = 10) -> Dict[str, Any]:
        start = time.perf_counter()
        results = []
        for canonical_id, facility in self._facilities.items():
            row_by_parameter = {
                str(row.get("parameter_id")): row for row in facility.get("rows") or []
            }
            eligibility = _eligibility_from_needs(needs, row_by_parameter)
            scoring = _score_result(needs, eligibility)
            results.append(
                {
                    "canonical_facility_id": canonical_id,
                    "facility_name": facility.get("facility_name"),
                    "eligibility_status": eligibility["eligibility_status"],
                    "match_score": scoring["match_score"],
                    "snapshot_version": facility["facility_snapshot_version"],
                    "active_snapshot_version": self.active_snapshot_version,
                    "last_successful_refresh": facility["last_successful_refresh"],
                    "changed_parameters_since_previous_snapshot": list(facility["changed_parameters"]),
                    "unchanged_parameters_reused": int(facility["unchanged_parameters_reused"]),
                    "stale_parameters": list(facility["stale_parameters"]),
                    "missing_parameters": list(facility["missing_parameters"]),
                }
            )

        eligibility_order = {
            "ELIGIBLE": 0,
            "POTENTIALLY_ELIGIBLE": 1,
            "INSUFFICIENT_EVIDENCE": 2,
            "INELIGIBLE": 3,
        }
        results.sort(
            key=lambda item: (
                eligibility_order.get(str(item["eligibility_status"]), 99),
                -float(item["match_score"]),
                str(item["canonical_facility_id"]),
            )
        )
        response_time_ms = round((time.perf_counter() - start) * 1000, 3)
        for result in results:
            result["recommendation_response_time_ms"] = response_time_ms

        self._recommendation_count += 1
        return {
            "active_snapshot_version": self.active_snapshot_version,
            "snapshot_only": True,
            "internet_crawl_performed": False,
            "facility_profiles_rebuilt": False,
            "recommendation_response_time_ms": response_time_ms,
            "results": results[:limit],
        }

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "active_snapshot_version": self.active_snapshot_version,
            "last_successful_refresh": self.last_successful_refresh,
            "facility_refresh_counts": dict(self._facility_refresh_counts),
            "parameter_refresh_counts": copy.deepcopy(self._parameter_refresh_counts),
            "recommendation_count": self._recommendation_count,
            "network_request_count": self._network_request_count,
            "profile_rebuild_count": self._profile_rebuild_count,
        }