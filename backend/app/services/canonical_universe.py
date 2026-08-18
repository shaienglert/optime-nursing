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
    f"las_vegas_runtime_v3/part{index:02}.b64" for index in range(12)
)
LAS_VEGAS_RUNTIME_PART_SHA256 = (
    "5b87a8400380f713456005e1a8769b64b800e1b203a6594229d6acbc76f579a4",
    "dcf8d61494bc11d6f9cf657060c902f198c7f0f51e8c12d3376c49898a562b38",
    "e16a4c19d75859abf07398cc264ac088fb5526a8829c281f9b7ac2b3f51ca3ef",
    "3377d5bb337203119532d6ec502986fdfffa377851ea2b5089e9d0aa1e6c5b4f",
    "5ad8362ce8ceb82f030f67f1be5674cdd73263e485c4c4f3df30d55c2a1e2d9b",
    "e128cf674810f59fff0c95c6392a021d2baeb34ecabfe46f4740b34b8b10d067",
    "b592731cbc21789cd1265ae7c5f819e45380760d590bf4ea9a36ec6dd7c900a4",
    "ae05c1ada66a29a26048df960799f3e8c6ce5f6c31b5acd10ac556c06351dbbb",
    "afcfc098e8a097ace531682fca26841acd0b79d84e04bad56819eeff774d9390",
    "eb0e3f39feb29b1a0363e83d4f304df0b291e8f92a124c27e3e2c558f851f6ce",
    "21743e81dcbbe52d6d79bd6cbed5e3f4c70858ed4c2519f732be4022630c0e50",
    "56e0a681bb0319965edfb1d31f7020d6fe3b6133fe6d13f9816e66ac9bc5a3df",
)
LAS_VEGAS_RUNTIME_PART_LENGTHS = (4500,) * 11 + (1936,)
LAS_VEGAS_RUNTIME_SHA256 = "1bd929d11a7defcbdc7489fbc1a7c83196bff8600c2480df5819bdcd3dcaf62b"
LAS_VEGAS_RUNTIME_CACHE = Path(tempfile.gettempdir()) / "optime-nevada-las-vegas-runtime-projection-v3.json"

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
        # Preserve compatibility only for isolated unit tests that inject the historical
        # filename. Production never falls back to the stale Nevada repo artifact.
        legacy = database_dir / "nevada_facility_universe_canonical.json"
        if database_dir != DATABASE_DIR and legacy.is_file():
            return legacy
        if require_exists:
            raise FileNotFoundError(
                "Pinned Las Vegas runtime projection part(s) missing: "
                + ", ".join(str(path) for path in missing)
            )
        return parts[0]

    target = (
        LAS_VEGAS_RUNTIME_CACHE
        if database_dir == DATABASE_DIR
        else database_dir / "nevada_las_vegas_runtime_projection_v3.json"
    )
    source_mtime = max(path.stat().st_mtime_ns for path in parts)
    if target.is_file() and target.stat().st_mtime_ns >= source_mtime:
        decoded = target.read_bytes()
        if hashlib.sha256(decoded).hexdigest() == LAS_VEGAS_RUNTIME_SHA256:
            return target

    try:
        part_texts: list[str] = []
        for index, path in enumerate(parts):
            text = path.read_text(encoding="utf-8").strip()
            if len(text) != LAS_VEGAS_RUNTIME_PART_LENGTHS[index]:
                raise ValueError(
                    f"runtime projection part {index:02} length mismatch: "
                    f"len={len(text)} expected={LAS_VEGAS_RUNTIME_PART_LENGTHS[index]}"
                )
            actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            expected_sha = LAS_VEGAS_RUNTIME_PART_SHA256[index]
            if actual_sha != expected_sha:
                raise ValueError(
                    f"runtime projection part {index:02} checksum mismatch: "
                    f"sha256={actual_sha} expected={expected_sha}"
                )
            part_texts.append(text)

        compressed = base64.b64decode("".join(part_texts), validate=True)
        decoded = gzip.decompress(compressed)
        actual_payload_sha = hashlib.sha256(decoded).hexdigest()
        if actual_payload_sha != LAS_VEGAS_RUNTIME_SHA256:
            raise ValueError(
                f"runtime projection checksum mismatch: "
                f"sha256={actual_payload_sha} expected={LAS_VEGAS_RUNTIME_SHA256}"
            )
        payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid pinned Las Vegas runtime projection: {exc}") from exc

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
        return _materialize_las_vegas_projection(
            database_dir=database_dir,
            require_exists=require_exists,
        )
    filename = MARKET_UNIVERSE_FILES.get(normalized)
    if not filename:
        supported = ", ".join(sorted({*MARKET_UNIVERSE_FILES, "las-vegas"}))
        raise ValueError(
            f"Unsupported canonical market '{normalized}'. Supported markets: {supported}"
        )
    path = database_dir / filename
    if require_exists and not path.is_file():
        raise FileNotFoundError(
            f"Canonical universe for market '{normalized}' is missing: {path}"
        )
    return path


def canonical_universe_source_label(market: str | None = None) -> str:
    raw_market = str(market or configured_canonical_market()).strip().lower()
    normalized = MARKET_ALIASES.get(raw_market, raw_market)
    if normalized == "las-vegas":
        return "database/las_vegas_runtime_v3/part*.b64"
    path = resolve_canonical_universe_path(normalized)
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)
