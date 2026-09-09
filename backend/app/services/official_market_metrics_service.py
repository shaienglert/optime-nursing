from __future__ import annotations

"""Official, reproducible market metrics.

This collector deliberately has a narrow source contract: CMS Provider Information
and CMS Nursing Home Quality Measures.  Both are public national datasets and cover
*skilled nursing facilities only*.  They must never be stretched into claims about
all senior living or independent living.

Each stored observation carries the source URL, period, geography and source scope.
The report reader may therefore show a real number, or MISSING, but never an
unlabelled estimate.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import os
import threading
import time
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.competitive_intelligence import MarketMetricObservation
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    CMS_QUALITY_DATASET_ID,
    clean_state,
    download_dataset,
    iter_csv_rows,
    to_float,
    to_int,
)

logger = logging.getLogger(__name__)
CMS_PROVIDER_LANDING = f"https://data.cms.gov/provider-data/dataset/{CMS_PROVIDER_DATASET_ID}"
CMS_QUALITY_LANDING = f"https://data.cms.gov/provider-data/dataset/{CMS_QUALITY_DATASET_ID}"
SOURCE_SCOPE = "CMS Nursing Home data only (Medicare/Medicaid-certified skilled nursing facilities); excludes assisted living, memory care and independent living."


def _upsert(
    db: Session,
    *,
    metric_key: str,
    geography_key: str,
    geography_label: str,
    value_text: str,
    unit: str,
    observed_period: str,
    source_name: str,
    source_url: str,
    source_scope: str = SOURCE_SCOPE,
    segment: str = "SKILLED_NURSING",
) -> None:
    row = (
        db.query(MarketMetricObservation)
        .filter(
            MarketMetricObservation.metric_key == metric_key,
            MarketMetricObservation.geography_key == geography_key,
            MarketMetricObservation.segment == segment,
            MarketMetricObservation.source_name == source_name,
        )
        .order_by(MarketMetricObservation.captured_at.desc())
        .first()
    )
    if row is None:
        row = MarketMetricObservation(
            metric_key=metric_key,
            geography_key=geography_key,
            geography_label=geography_label,
            segment=segment,
            value_text=value_text,
            unit=unit,
            observed_period=observed_period,
            source_name=source_name,
            source_url=source_url,
            evidence_status="VERIFIED",
            source_scope=source_scope,
        )
        db.add(row)
        return
    row.geography_label = geography_label
    row.value_text = value_text
    row.unit = unit
    row.observed_period = observed_period
    row.source_url = source_url
    row.source_scope = source_scope
    row.evidence_status = "VERIFIED"
    row.captured_at = datetime.now(timezone.utc)


def _provider_aggregates(rows: Iterable[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, int]], str, int]:
    result = {"NATIONAL": {"facilities": 0, "beds": 0}, "NEVADA": {"facilities": 0, "beds": 0}}
    seen: set[str] = set()
    period = "CMS current published dataset"
    row_count = 0
    for row in rows:
        row_count += 1
        period = period if period != "CMS current published dataset" else str(row.get("Processing Date") or row.get("Last Updated") or period).strip()
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        if not ccn or ccn in seen:
            continue
        seen.add(ccn)
        result["NATIONAL"]["facilities"] += 1
        result["NATIONAL"]["beds"] += to_int(row.get("Number of Certified Beds")) or 0
        if clean_state(row.get("State")) == "NV":
            result["NEVADA"]["facilities"] += 1
            result["NEVADA"]["beds"] += to_int(row.get("Number of Certified Beds")) or 0
    return result, period, row_count


def _measure_family(description: str) -> Optional[str]:
    text = description.lower()
    if "fall" in text and "major injury" in text:
        return "FALLS_MAJOR_INJURY"
    if "hospitalization" in text or "rehospitalization" in text:
        return "HOSPITALIZATION_RATE"
    return None


def _quality_aggregates(rows: Iterable[Dict[str, str]]) -> Tuple[Dict[Tuple[str, str], Tuple[float, int, str, str]], int]:
    """Return one transparent arithmetic mean per metric/geography.

    CMS quality measures can be percentages or rates.  We preserve the published
    measure description in source_scope and infer the unit only when the label says
    percentage; otherwise it remains SOURCE_REPORTED_RATE.
    """
    values: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    periods: Dict[Tuple[str, str, str], str] = {}
    row_count = 0
    for row in rows:
        row_count += 1
        metric = _measure_family(str(row.get("Measure Description") or ""))
        value = to_float(row.get("Four Quarter Average Score"))
        if not metric or value is None:
            continue
        geography = "NEVADA" if clean_state(row.get("State")) == "NV" else "NATIONAL"
        description = str(row.get("Measure Description") or "").strip()
        key = (metric, geography, description)
        values[key].append(value)
        periods[key] = str(row.get("Measure Period") or "CMS four-quarter average").strip()

    chosen: Dict[Tuple[str, str], Tuple[float, int, str, str]] = {}
    for (metric, geography, description), numbers in values.items():
        key = (metric, geography)
        candidate = (sum(numbers) / len(numbers), len(numbers), description, periods[(metric, geography, description)])
        # Keep the most-covered CMS measure if several similarly named measures exist.
        if key not in chosen or candidate[1] > chosen[key][1]:
            chosen[key] = candidate
    return chosen, row_count


def collect_cms_market_metrics(
    db: Session,
    *,
    provider_rows: Optional[Iterable[Dict[str, str]]] = None,
    quality_rows: Optional[Iterable[Dict[str, str]]] = None,
) -> Dict[str, object]:
    """Collect and persist official national and Nevada SNF market metrics.

    Injectable rows keep tests hermetic; production reads CMS's current published
    distributions.  A failed source raises before commit, so a partial refresh can
    never overwrite a previously sourced number with an empty result.
    """
    provider_stream = provider_rows if provider_rows is not None else iter_csv_rows(
        download_dataset(CMS_PROVIDER_DATASET_ID, "market_cms_provider_information.csv", force=True)
    )
    quality_stream = quality_rows if quality_rows is not None else iter_csv_rows(
        download_dataset(CMS_QUALITY_DATASET_ID, "market_cms_quality_measures.csv", force=True)
    )

    aggregate, provider_period, provider_row_count = _provider_aggregates(provider_stream)
    for geography, label in (("NATIONAL", "United States"), ("NEVADA", "Nevada")):
        data = aggregate[geography]
        _upsert(db, metric_key="FACILITY_COUNT", geography_key=geography, geography_label=label, value_text=str(data["facilities"]), unit="facilities", observed_period=provider_period, source_name="CMS Provider Information", source_url=CMS_PROVIDER_LANDING)
        _upsert(db, metric_key="LICENSED_CAPACITY", geography_key=geography, geography_label=label, value_text=str(data["beds"]), unit="beds", observed_period=provider_period, source_name="CMS Provider Information", source_url=CMS_PROVIDER_LANDING)

    quality, quality_row_count = _quality_aggregates(quality_stream)
    for (metric, geography), (value, count, description, period) in quality.items():
        unit = "percent" if "percent" in description.lower() or "%" in description else "source_reported_rate"
        label = "United States" if geography == "NATIONAL" else "Nevada"
        _upsert(
            db,
            metric_key=metric,
            geography_key=geography,
            geography_label=label,
            value_text=f"{value:.2f}",
            unit=unit,
            observed_period=period or "CMS four-quarter average",
            source_name="CMS Nursing Home Quality Measures",
            source_url=CMS_QUALITY_LANDING,
            source_scope=f"{SOURCE_SCOPE} Published measure: {description}. Arithmetic mean across {count} reporting facilities; not a population-weighted rate.",
        )
    db.commit()
    return {
        "source": "CMS",
        "provider_rows": provider_row_count,
        "quality_rows": quality_row_count,
        "observations_written": 4 + len(quality),
        "provider_source_url": CMS_PROVIDER_LANDING,
        "quality_source_url": CMS_QUALITY_LANDING,
    }


def cms_market_metrics_are_fresh(db: Session, *, max_age_days: int = 28) -> bool:
    required = {"FACILITY_COUNT", "LICENSED_CAPACITY", "FALLS_MAJOR_INJURY", "HOSPITALIZATION_RATE"}
    rows = (
        db.query(MarketMetricObservation)
        .filter(
            MarketMetricObservation.geography_key.in_(("NEVADA", "NATIONAL")),
            MarketMetricObservation.source_name.in_(("CMS Provider Information", "CMS Nursing Home Quality Measures")),
        )
        .all()
    )
    observed = {(row.metric_key, row.geography_key) for row in rows}
    if any((metric, geography) not in observed for metric in required for geography in ("NEVADA", "NATIONAL")):
        return False
    newest = max((row.captured_at for row in rows if row.captured_at), default=None)
    if newest is not None and newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    return bool(newest and newest >= datetime.now(timezone.utc) - timedelta(days=max_age_days))


def start_official_market_metrics_scheduler() -> None:
    """Refresh public CMS metrics at most monthly, outside request handling."""
    interval = max(24 * 60 * 60, int(os.getenv("OPTIME_OFFICIAL_MARKET_METRICS_INTERVAL_SECONDS", str(30 * 24 * 60 * 60))))

    def _runner() -> None:
        from app.database import SessionLocal

        while True:
            try:
                with SessionLocal() as db:
                    if cms_market_metrics_are_fresh(db):
                        logger.info("official_market_metrics_skipped reason=fresh")
                    else:
                        result = collect_cms_market_metrics(db)
                        logger.info("official_market_metrics_cycle_completed observations=%s", result["observations_written"])
            except Exception:
                logger.exception("official_market_metrics_cycle_failed")
            time.sleep(interval)

    threading.Thread(target=_runner, name="optime-official-market-metrics", daemon=True).start()
