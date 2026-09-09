from __future__ import annotations

"""Official older-adult population projections for the market report.

This collector has a deliberately small source contract.  Nevada's official State
Demographer publishes its age-cohort projections as a yearly PDF; the U.S. Census
publishes a machine-readable national age projection file.  We store the published
2025-to-2030 change for ages 65+ and 75+ with both endpoints in source_scope.

The values are market context only.  They are not demand forecasts, facility
availability, placement estimates, or ranking inputs.
"""

import csv
import io
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional
from urllib.request import urlopen

from sqlalchemy.orm import Session

from app.models.competitive_intelligence import MarketMetricObservation

logger = logging.getLogger(__name__)

NEVADA_ASRHO_URL = "https://tax.nv.gov/wp-content/uploads/2025/09/2025-ASRHO-Estimates-and-Projections-Summary-2000-to-2044.pdf"
CENSUS_PROJECTIONS_URL = "https://www2.census.gov/programs-surveys/popproj/datasets/2023/2023-popproj/np2023_d5_mid.csv"
SOURCE_PERIOD = "2025 to 2030 projection"

# Transcribed from Nevada State Demographer's 2025 ASRHO summary, statewide
# "with group quarters" tables.  The PDF is the authoritative published source;
# retaining these source values in code avoids pretending it is a machine-readable
# feed while still making a fully reproducible calculation.
NEVADA_SOURCE_COUNTS = {
    "OLDER_ADULTS_65_PLUS": {"start": 545_569, "end": 610_754},
    "OLDER_ADULTS_75_PLUS": {"start": 221_330, "end": 260_265},
}


def _upsert(
    db: Session,
    *,
    geography_key: str,
    geography_label: str,
    segment: str,
    value: float,
    source_name: str,
    source_url: str,
    scope: str,
) -> None:
    row = (
        db.query(MarketMetricObservation)
        .filter(
            MarketMetricObservation.metric_key == "OLDER_ADULT_POPULATION_GROWTH",
            MarketMetricObservation.geography_key == geography_key,
            MarketMetricObservation.segment == segment,
            MarketMetricObservation.source_name == source_name,
        )
        .order_by(MarketMetricObservation.captured_at.desc())
        .first()
    )
    if row is None:
        db.add(
            MarketMetricObservation(
                metric_key="OLDER_ADULT_POPULATION_GROWTH",
                geography_key=geography_key,
                geography_label=geography_label,
                segment=segment,
                value_text=f"{value:.2f}",
                unit="percent",
                observed_period=SOURCE_PERIOD,
                source_name=source_name,
                source_url=source_url,
                evidence_status="VERIFIED",
                source_scope=scope[:240],
            )
        )
        return
    row.geography_label = geography_label
    row.value_text = f"{value:.2f}"
    row.unit = "percent"
    row.observed_period = SOURCE_PERIOD
    row.source_url = source_url
    row.source_scope = scope[:240]
    row.evidence_status = "VERIFIED"
    row.captured_at = datetime.now(timezone.utc)


def _growth(start: int, end: int) -> float:
    if start <= 0:
        raise ValueError("projection start count must be positive")
    return ((end / start) - 1) * 100


def _national_projection_counts(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, int]]:
    selected: Dict[int, Dict[str, int]] = {}
    for row in rows:
        # This is the total-U.S. series: all nativity, race/Hispanic origin and sex.
        if not (row.get("NATIVITY") == "1" and row.get("RACE_HISP") == "0" and row.get("SEX") == "0"):
            continue
        year = int(row.get("YEAR") or 0)
        if year not in {2025, 2030}:
            continue
        selected[year] = {
            "OLDER_ADULTS_65_PLUS": sum(int(row[f"POP_{age}"]) for age in range(65, 86)),
            "OLDER_ADULTS_75_PLUS": sum(int(row[f"POP_{age}"]) for age in range(75, 86)),
        }
    if set(selected) != {2025, 2030}:
        raise RuntimeError("Census national population projection is missing 2025 or 2030 total-U.S. rows")
    return {
        segment: {"start": selected[2025][segment], "end": selected[2030][segment]}
        for segment in ("OLDER_ADULTS_65_PLUS", "OLDER_ADULTS_75_PLUS")
    }


def _download_census_rows() -> Iterable[Dict[str, str]]:
    with urlopen(CENSUS_PROJECTIONS_URL, timeout=90) as response:
        payload = response.read()
    return csv.DictReader(io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8-sig", newline=""))


def collect_official_demographic_market_metrics(
    db: Session, *, census_rows: Optional[Iterable[Dict[str, str]]] = None
) -> Dict[str, object]:
    """Persist official 2025-to-2030 65+ and 75+ growth for Nevada and the U.S."""
    national = _national_projection_counts(census_rows if census_rows is not None else _download_census_rows())
    written = 0
    for geography_key, geography_label, source_name, source_url, counts in (
        ("NEVADA", "Nevada", "Nevada State Demographer", NEVADA_ASRHO_URL, NEVADA_SOURCE_COUNTS),
        ("NATIONAL", "United States", "U.S. Census Bureau", CENSUS_PROJECTIONS_URL, national),
    ):
        for segment, values in counts.items():
            _upsert(
                db,
                geography_key=geography_key,
                geography_label=geography_label,
                segment=segment,
                value=_growth(values["start"], values["end"]),
                source_name=source_name,
                source_url=source_url,
                scope=(
                    f"{segment.replace('_', ' ').replace('OLDER ADULTS ', '')} population: "
                    f"{values['start']:,} in 2025 to {values['end']:,} in 2030; "
                    "official population projection, not a senior-housing demand forecast."
                ),
            )
            written += 1
    db.commit()
    return {"source": "Nevada State Demographer + U.S. Census Bureau", "observations_written": written, "period": SOURCE_PERIOD}


def demographic_market_metrics_are_fresh(db: Session, *, max_age_days: int = 370) -> bool:
    rows = (
        db.query(MarketMetricObservation)
        .filter(
            MarketMetricObservation.metric_key == "OLDER_ADULT_POPULATION_GROWTH",
            MarketMetricObservation.geography_key.in_(("NEVADA", "NATIONAL")),
            MarketMetricObservation.segment.in_(("OLDER_ADULTS_65_PLUS", "OLDER_ADULTS_75_PLUS")),
        )
        .all()
    )
    found = {(row.geography_key, row.segment) for row in rows}
    required = {(geography, segment) for geography in ("NEVADA", "NATIONAL") for segment in ("OLDER_ADULTS_65_PLUS", "OLDER_ADULTS_75_PLUS")}
    newest = max((row.captured_at for row in rows if row.captured_at), default=None)
    if newest is not None and newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    return found == required and bool(newest and newest >= datetime.now(timezone.utc) - timedelta(days=max_age_days))


def start_demographic_market_metrics_scheduler() -> None:
    """Refresh only when the annual published projection snapshot becomes stale."""
    interval = max(24 * 60 * 60, int(os.getenv("OPTIME_DEMOGRAPHIC_METRICS_INTERVAL_SECONDS", str(365 * 24 * 60 * 60))))

    def _runner() -> None:
        from app.database import SessionLocal

        while True:
            try:
                with SessionLocal() as db:
                    if demographic_market_metrics_are_fresh(db):
                        logger.info("demographic_market_metrics_skipped reason=fresh")
                    else:
                        result = collect_official_demographic_market_metrics(db)
                        logger.info("demographic_market_metrics_cycle_completed observations=%s", result["observations_written"])
            except Exception:
                logger.exception("demographic_market_metrics_cycle_failed")
            time.sleep(interval)

    threading.Thread(target=_runner, name="optime-demographic-market-metrics", daemon=True).start()
