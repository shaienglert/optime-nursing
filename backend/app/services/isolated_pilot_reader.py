"""Read the isolated, fictional Neon pilot catalog; never touch the application DB.

Opt-in only: OOMNIK_PILOT_SOURCE=neon and OOMNIK_PILOT_DATABASE_URL.
This URL must point to the isolated synthetic pilot database, NOT DATABASE_URL.
"""
from __future__ import annotations

import os
from sqlalchemy import create_engine, text


def read_isolated_pilot():
    if os.getenv("OOMNIK_PILOT_SOURCE") != "neon":
        raise RuntimeError("Isolated Neon pilot source is not enabled")
    url = os.getenv("OOMNIK_PILOT_DATABASE_URL", "").strip()
    if not url or url == os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError("A separate OOMNIK_PILOT_DATABASE_URL is required")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url.startswith("postgresql://"):
        raise RuntimeError("Isolated pilot must use PostgreSQL")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 8})
    try:
        with engine.connect() as connection:
            # The dataset is deliberately synthetic; refuse to mix real facility records.
            facilities = [row[0] for row in connection.execute(text(
                "SELECT payload FROM public.oomnik_pilot_facilities ORDER BY (payload->>'pilot_exposure_order')::integer"
            ))]
            evidence = [row[0] for row in connection.execute(text(
                "SELECT payload FROM public.oomnik_pilot_evidence ORDER BY id"
            ))]
            if len(facilities) != 500 or not all(
                row.get("synthetic_pilot") is True for row in facilities
            ):
                raise RuntimeError("Pilot identity/count check failed")
            ids = [str(row.get("canonical_id") or "") for row in facilities]
            if len(set(ids)) != 500 or not all(ids):
                raise RuntimeError("Pilot canonical identities are invalid")
            if not evidence or any(
                str(row.get("canonical_facility_id") or "") not in set(ids)
                for row in evidence
            ):
                raise RuntimeError("Pilot evidence integrity check failed")
            return facilities, evidence
    finally:
        engine.dispose()
