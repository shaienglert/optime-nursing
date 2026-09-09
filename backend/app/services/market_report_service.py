from __future__ import annotations

"""Auditable market-report read model.

The report is deliberately descriptive.  A missing number stays MISSING; it is
never converted to zero and is never used as facility-level evidence or ranking
input.  "Rooms" is represented as either senior-living units or SNF licensed beds
because combining those inventories would be misleading.
"""

from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.competitive_intelligence import MarketMetricObservation
from app.models.facility import Facility, FacilityLicenseRecord


REPORT_METRICS: List[Dict[str, str]] = [
    {"metric_key": "FACILITY_COUNT", "label": "Facilities", "unit": "facilities", "scope": "Licensed facility universe; segment-specific."},
    {"metric_key": "INVENTORY_UNITS", "label": "Senior-living units", "unit": "units", "scope": "Independent/assisted/memory-care inventory; not SNF beds."},
    {"metric_key": "LICENSED_CAPACITY", "label": "Licensed capacity", "unit": "beds_or_places", "scope": "State-reported licensed capacity by care segment; not apartment inventory."},
    {"metric_key": "OCCUPANCY_RATE", "label": "Occupancy", "unit": "percent", "scope": "Keep market, state and national series separate."},
    {"metric_key": "FALLS_MAJOR_INJURY", "label": "Falls with major injury", "unit": "percent", "scope": "CMS nursing-home measure; not a senior-living-wide measure."},
    {"metric_key": "HOSPITALIZATION_RATE", "label": "Hospitalization", "unit": "percent", "scope": "CMS nursing-home measure; not a senior-living-wide measure."},
    {"metric_key": "PIPELINE_UNITS", "label": "Units/beds under construction", "unit": "units_or_beds", "scope": "Verified project pipeline; do not include planned-only projects."},
    {"metric_key": "OLDER_ADULT_POPULATION_GROWTH", "label": "Older-adult population projection", "unit": "percent", "scope": "Age band must be stated, e.g. 65+ or 75+."},
]


def _licensed_nevada_inventory(db: Session) -> Dict[str, List[Dict[str, str]]]:
    """Derive only the Nevada state-registry portion already in our canonical DB.

    The output is intentionally scoped to *licensed* records.  It does not claim
    coverage of independent living, which normally has no equivalent statewide
    care licence and must be collected from another source.
    """
    rows = (
        db.query(
            FacilityLicenseRecord.state_care_type,
            func.count(func.distinct(FacilityLicenseRecord.facility_id)),
            func.coalesce(func.sum(Facility.beds), 0),
        )
        .join(Facility, Facility.id == FacilityLicenseRecord.facility_id)
        .filter(Facility.state == "NV", FacilityLicenseRecord.status == "VERIFIED")
        .group_by(FacilityLicenseRecord.state_care_type)
        .all()
    )
    if not rows:
        return {}
    total_facilities = 0
    total_beds = 0
    facilities = []
    beds = []
    for care_type, facility_count, bed_count in rows:
        segment = str(care_type or "UNCLASSIFIED")
        total_facilities += int(facility_count or 0)
        total_beds += int(bed_count or 0)
        facilities.append({"segment": segment, "value": str(int(facility_count or 0))})
        beds.append({"segment": segment, "value": str(int(bed_count or 0))})
    facilities.insert(0, {"segment": "ALL_LICENSED", "value": str(total_facilities)})
    beds.insert(0, {"segment": "ALL_LICENSED", "value": str(total_beds)})
    return {"FACILITY_COUNT": facilities, "LICENSED_CAPACITY": beds}


def market_report(db: Session, *, geography_key: str = "NEVADA") -> Dict[str, object]:
    comparison_geographies = [geography_key]
    if geography_key == "NEVADA":
        comparison_geographies.append("NATIONAL")
    rows = (
        db.query(MarketMetricObservation)
        .filter(MarketMetricObservation.geography_key.in_(comparison_geographies))
        .order_by(MarketMetricObservation.metric_key, MarketMetricObservation.captured_at.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault((row.metric_key, row.geography_key, row.segment, row.source_name), row)

    derived = _licensed_nevada_inventory(db) if geography_key == "NEVADA" else {}
    metrics = []
    for definition in REPORT_METRICS:
        matched = [row for (key, _geography, _segment, _source), row in latest.items() if key == definition["metric_key"]]
        if definition["metric_key"] in derived and not matched:
            metrics.append({
                **definition,
                "status": "AVAILABLE",
                "observations": [
                    {
                        **row,
                        "observed_period": "Current canonical registry import",
                        "source_name": "Nevada HCQC / ALiS public license registry",
                        "source_url": "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HF&PubliSearch=Y",
                        "evidence_status": "VERIFIED",
                        "source_scope": "Active Nevada state-licensed senior-care records imported into the canonical registry; excludes unlicensed independent living.",
                    }
                    for row in derived[definition["metric_key"]]
                ],
                "reason": None,
            })
            continue
        required_geographies = set(comparison_geographies)
        observed_geographies = {row.geography_key for row in matched}
        if not matched:
            metrics.append({
                **definition,
                "status": "MISSING",
                "observations": [],
                "reason": "No sourced observation has been collected for this geography and metric.",
            })
            continue
        metrics.append({
            **definition,
            # The executive scorecard compares Nevada with the United States.
            # Do not call a row complete merely because one geography happened
            # to have a value.  This makes source gaps operationally visible.
            "status": "AVAILABLE" if required_geographies.issubset(observed_geographies) else "PARTIAL",
            "observations": [
                {
                    "segment": f"{row.geography_label} · {row.segment}",
                    "value": row.value_text,
                    "observed_period": row.observed_period,
                    "source_name": row.source_name,
                    "source_url": row.source_url,
                    "evidence_status": row.evidence_status,
                    "source_scope": row.source_scope,
                }
                for row in matched
            ],
            "reason": None if required_geographies.issubset(observed_geographies) else (
                "Source-backed observation is missing for: "
                + ", ".join(sorted(required_geographies - observed_geographies))
                + "."
            ),
        })
    return {"geography_key": geography_key, "ranking_input": False, "metrics": metrics}
