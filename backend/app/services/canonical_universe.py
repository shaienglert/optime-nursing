from __future__ import annotations

import base64
import gzip
import json
import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"
LAS_VEGAS_RUNTIME_PROJECTION = DATABASE_DIR / "nevada_las_vegas_runtime_projection.json.gz.b64"
LAS_VEGAS_RUNTIME_CACHE = Path(tempfile.gettempdir()) / "optime-nevada-las-vegas-runtime-projection.json"

MARKET_UNIVERSE_FILES = {
    "florida": "florida_facility_universe_canonical.json",
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
    # Las Vegas is the active production market. Explicit environment configuration
    # still wins, so Florida remains reproducible for its own workflows/tests.
    value = str(
        os.getenv("OPTIME_CANONICAL_MARKET")
        or os.getenv("NEXT_PUBLIC_ASSESSMENT_REGION")
        or "las-vegas"
    ).strip().lower()
    return MARKET_ALIASES.get(value, value)


def _materialize_las_vegas_projection(*, database_dir: Path, require_exists: bool) -> Path:
    source = database_dir / LAS_VEGAS_RUNTIME_PROJECTION.name
    if not source.is_file():
        if require_exists:
            raise FileNotFoundError(f"Pinned Las Vegas runtime projection is missing: {source}")
        return source

    # For the repository database directory use /tmp so serverless/read-only filesystems
    # remain safe. Tests with an isolated database_dir receive a sibling materialization.
    target = LAS_VEGAS_RUNTIME_CACHE if database_dir == DATABASE_DIR else database_dir / "nevada_las_vegas_runtime_projection.json"
    source_mtime = source.stat().st_mtime_ns
    if target.is_file() and target.stat().st_mtime_ns >= source_mtime:
        return target

    try:
        compressed = base64.b64decode(source.read_text(encoding="utf-8").strip(), validate=True)
        decoded = gzip.decompress(compressed)
        payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid pinned Las Vegas runtime projection: {source}") from exc

    records = payload.get("records") or []
    if payload.get("record_count") != len(records) or len(records) <= 0:
        raise RuntimeError("Pinned Las Vegas runtime projection failed record-count validation")
    if any(str(row.get("state") or "").upper() != "NV" for row in records):
        raise RuntimeError("Pinned Las Vegas runtime projection contains non-Nevada records")
    if any(row.get("is_las_vegas_valley") is not True for row in records):
        raise RuntimeError("Pinned Las Vegas runtime projection contains non-Valley records")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(decoded)
    os.replace(temporary, target)
    return target


def resolve_canonical_universe_path(
    market: str | None = None,
    *,
    database_dir: Path = DATABASE_DIR,
    require_exists: bool = True,
) -> Path:
    configured = market or configured_canonical_market()
    normalized_input = str(configured).strip().lower()
    normalized = MARKET_ALIASES.get(normalized_input, normalized_input)

    if normalized == "las-vegas":
        return _materialize_las_vegas_projection(database_dir=database_dir, require_exists=require_exists)

    filename = MARKET_UNIVERSE_FILES.get(normalized)
    if not filename:
        supported = ", ".join(sorted({*MARKET_UNIVERSE_FILES, "las-vegas"}))
        raise ValueError(f"Unsupported canonical market '{normalized}'. Supported markets: {supported}")
    path = database_dir / filename
    if require_exists and not path.is_file():
        raise FileNotFoundError(f"Canonical universe for market '{normalized}' is missing: {path}")
    return path


def canonical_universe_source_label(market: str | None = None) -> str:
    normalized = MARKET_ALIASES.get(str(market or configured_canonical_market()).strip().lower(), str(market or configured_canonical_market()).strip().lower())
    if normalized == "las-vegas":
        return f"database/{LAS_VEGAS_RUNTIME_PROJECTION.name}"
    path = resolve_canonical_universe_path(normalized)
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)
