from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"
LAS_VEGAS_RUNTIME_PART_NAMES = tuple(
    f"las_vegas_runtime_v2/part{index:02}.b64" for index in range(6)
)
LAS_VEGAS_RUNTIME_PART_SHA256 = (
    "b5c9e1647f7a702ab21e44c719355f30d329c66e230f7882c77ac1f065b52b6d",
    "538f1ea655ed543db3dcbb39ce0e974d83d2ebe33729953070e11c5d35fb9870",
    "1b448f458254ec08095807cca7c16aa2d9e0aff7945a35555d027110f694458d",
    "6529ab7fb9e7341c62c177e5c034545918291a3e222d24417b4de8c998a9944d",
    "0b68a88106b9adad9b5f1d394829e47c1003f74baeccc3520cd92cfc79a0c410",
    "deb181a63fc473c20710d6e3f9e65aea796626fc9b42f3686663121694f9092d",
)
LAS_VEGAS_RUNTIME_SHA256 = "bec25381d013cf39001fbdb8ab02d9c15b6a451a9e78dcedd1309178203346f4"
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
    value = str(
        os.getenv("OPTIME_CANONICAL_MARKET")
        or os.getenv("NEXT_PUBLIC_ASSESSMENT_REGION")
        or "las-vegas"
    ).strip().lower()
    return MARKET_ALIASES.get(value, value)


def _las_vegas_part_paths(database_dir: Path) -> tuple[Path, ...]:
    return tuple(database_dir / name for name in LAS_VEGAS_RUNTIME_PART_NAMES)


def _materialize_las_vegas_projection(*, database_dir: Path, require_exists: bool) -> Path:
    parts = _las_vegas_part_paths(database_dir)
    missing = [path for path in parts if not path.is_file()]
    if missing:
        legacy = database_dir / "nevada_facility_universe_canonical.json"
        if database_dir != DATABASE_DIR and legacy.is_file():
            return legacy
        if require_exists:
            raise FileNotFoundError(
                "Pinned Las Vegas runtime projection part(s) missing: "
                + ", ".join(str(path) for path in missing)
            )
        return parts[0]

    target = LAS_VEGAS_RUNTIME_CACHE if database_dir == DATABASE_DIR else database_dir / "nevada_las_vegas_runtime_projection.json"
    source_mtime = max(path.stat().st_mtime_ns for path in parts)
    if target.is_file() and target.stat().st_mtime_ns >= source_mtime:
        decoded = target.read_bytes()
        if hashlib.sha256(decoded).hexdigest() == LAS_VEGAS_RUNTIME_SHA256:
            return target

    try:
        part_texts = []
        for index, path in enumerate(parts):
            text = path.read_text(encoding="utf-8").strip()
            actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if actual_sha != LAS_VEGAS_RUNTIME_PART_SHA256[index]:
                raise ValueError(
                    f"runtime projection part {index:02} checksum mismatch: "
                    f"len={len(text)} sha256={actual_sha} expected={LAS_VEGAS_RUNTIME_PART_SHA256[index]}"
                )
            part_texts.append(text)
        encoded = "".join(part_texts)
        compressed = base64.b64decode(encoded, validate=True)
        decoded = gzip.decompress(compressed)
        if hashlib.sha256(decoded).hexdigest() != LAS_VEGAS_RUNTIME_SHA256:
            raise ValueError("runtime projection checksum mismatch")
        payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid pinned Las Vegas runtime projection parts: {exc}") from exc

    records = payload.get("records") or []
    if payload.get("record_count") != 364 or len(records) != 364:
        raise RuntimeError("Pinned Las Vegas runtime projection must contain exactly 364 Valley records")
    if payload.get("source_universe_record_count") != 517:
        raise RuntimeError("Pinned Las Vegas runtime projection source universe must contain 517 records")
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
    raw_market = str(market or configured_canonical_market()).strip().lower()
    normalized = MARKET_ALIASES.get(raw_market, raw_market)
    if normalized == "las-vegas":
        return "database/las_vegas_runtime_v2/part*.b64"
    path = resolve_canonical_universe_path(normalized)
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)
