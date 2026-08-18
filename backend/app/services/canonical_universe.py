from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"

MARKET_UNIVERSE_FILES = {
    "florida": "florida_facility_universe_canonical.json",
    "las-vegas": "nevada_facility_universe_canonical.json",
    "nevada": "nevada_facility_universe_canonical.json",
}

MARKET_ALIASES = {
    "fl": "florida",
    "miami": "florida",
    "nv": "nevada",
    "las vegas": "las-vegas",
    "las_vegas": "las-vegas",
    "las-vegas-nevada": "las-vegas",
}


def configured_canonical_market() -> str:
    # Nevada / Las Vegas is the active production market for OPTIME Nursing now.
    # Explicit environment configuration always wins, so Florida remains reproducible
    # with OPTIME_CANONICAL_MARKET=florida when running its workflows/tests.
    value = str(
        os.getenv("OPTIME_CANONICAL_MARKET")
        or os.getenv("NEXT_PUBLIC_ASSESSMENT_REGION")
        or "las-vegas"
    ).strip().lower()
    return MARKET_ALIASES.get(value, value)


def resolve_canonical_universe_path(
    market: str | None = None,
    *,
    database_dir: Path = DATABASE_DIR,
    require_exists: bool = True,
) -> Path:
    configured = market or configured_canonical_market()
    normalized_input = str(configured).strip().lower()
    normalized = MARKET_ALIASES.get(normalized_input, normalized_input)
    filename = MARKET_UNIVERSE_FILES.get(normalized)
    if not filename:
        supported = ", ".join(sorted(MARKET_UNIVERSE_FILES))
        raise ValueError(f"Unsupported canonical market '{normalized}'. Supported markets: {supported}")
    path = database_dir / filename
    if require_exists and not path.is_file():
        raise FileNotFoundError(f"Canonical universe for market '{normalized}' is missing: {path}")
    return path


def canonical_universe_source_label(market: str | None = None) -> str:
    path = resolve_canonical_universe_path(market)
    return path.relative_to(REPO_ROOT).as_posix()
