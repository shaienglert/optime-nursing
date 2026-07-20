import csv
import os
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.request import urlopen
import json

CMS_PROVIDER_DATASET_ID = "4pq5-n9py"
CMS_QUALITY_DATASET_ID = "djen-97ju"
CMS_INSPECTION_DATASET_ID = "r5ix-sfxw"
CMS_SURVEY_DATASET_ID = "svdt-c123"

CACHE_DIR = Path(__file__).resolve().parents[1] / "data"


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def get_distribution_url(dataset_id: str) -> str:
    meta_url = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{dataset_id}"
    with urlopen(meta_url) as response:
        payload = json.load(response)
    distributions = payload.get("distribution") or []
    if not distributions:
        raise RuntimeError(f"No distribution URL found for dataset {dataset_id}")
    return distributions[0]["downloadURL"]


def download_dataset(dataset_id: str, filename: str, force: bool = False) -> Path:
    ensure_cache_dir()
    output = CACHE_DIR / filename
    if output.exists() and not force:
        return output

    url = get_distribution_url(dataset_id)
    with urlopen(url) as response:
        output.write_bytes(response.read())
    return output


def iter_csv_rows(path: Path) -> Iterable[Dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "Not Available", "NA", "N/A", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Optional[str]) -> Optional[int]:
    converted = to_float(value)
    if converted is None:
        return None
    return int(round(converted))


def clip_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def stars_to_score(stars: Optional[int]) -> float:
    if stars is None:
        return 50.0
    return clip_0_100((stars / 5.0) * 100.0)


def invert_percent(value: Optional[float]) -> float:
    if value is None:
        return 50.0
    return clip_0_100(100.0 - value)


def normalize_hours(value: Optional[float], benchmark: float) -> float:
    if value is None or benchmark <= 0:
        return 50.0
    return clip_0_100((value / benchmark) * 100.0)


def inverse_count(value: Optional[float], max_bad: float) -> float:
    if value is None or max_bad <= 0:
        return 50.0
    return clip_0_100(100.0 - min(value, max_bad) / max_bad * 100.0)


def clean_state(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
