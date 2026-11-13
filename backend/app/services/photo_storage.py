"""Storage for facility photographs uploaded through the provider portal.

Files live on a local directory set by ``OPTIME_UPLOAD_DIR``. On Render that directory
must be a mounted persistent disk (for example ``/var/data``); without one, uploads
survive only until the next deploy or restart. ``storage_status()`` reports which case
applies so the portal never claims durability it does not have.

Every upload is decoded and re-encoded as JPEG. That rejects anything that is not a real
image, caps the size, applies the camera's rotation, and strips EXIF metadata (which can
carry the GPS location of the phone that took the picture).
"""

from __future__ import annotations

import io
import os
import re
import uuid
from pathlib import Path
from typing import Dict

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_EDGE_PX = 1600
JPEG_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
MEDIA_PREFIX = "/media/"
PHOTO_DIR = "facility_photos"
_NAME_RE = re.compile(r"^[0-9a-f]{32}\.jpg$")

Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS


def upload_root() -> Path:
    configured = os.getenv("OPTIME_UPLOAD_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "uploads"


def storage_status() -> Dict[str, object]:
    return {
        "upload_dir_configured": bool(os.getenv("OPTIME_UPLOAD_DIR", "").strip()),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
    }


def _normalise(data: bytes) -> bytes:
    if not data:
        raise ValueError("הקובץ ריק.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("הקובץ גדול מדי (עד 10MB).")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in ALLOWED_FORMATS:
            raise ValueError("אפשר להעלות רק תמונות JPG, PNG או WEBP.")
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            image.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX))
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as error:
        raise ValueError("הקובץ אינו תמונה תקינה.") from error


def store_facility_photo(facility_id: int, data: bytes) -> str:
    """Save a normalised JPEG and return its public URL path (``/media/...``)."""
    jpeg = _normalise(data)
    name = f"{uuid.uuid4().hex}.jpg"
    folder = upload_root() / PHOTO_DIR / str(int(facility_id))
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f".{name}.tmp"
    tmp.write_bytes(jpeg)
    tmp.replace(folder / name)
    return f"{MEDIA_PREFIX}{PHOTO_DIR}/{int(facility_id)}/{name}"


def resolve_media_path(facility_id: int, name: str) -> Path:
    if not _NAME_RE.match(name):
        raise FileNotFoundError(name)
    path = upload_root() / PHOTO_DIR / str(int(facility_id)) / name
    if not path.is_file():
        raise FileNotFoundError(name)
    return path


def media_url(facility_id: int, name: str) -> str:
    return f"{MEDIA_PREFIX}{PHOTO_DIR}/{int(facility_id)}/{name}"
