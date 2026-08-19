from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_FILE = Path(__file__).resolve().parents[1] / "optime_nursing.db"
_SQLITE_FALLBACK = f"sqlite:///{DB_FILE.as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or _SQLITE_FALLBACK
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

_engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite:"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def database_runtime_status() -> dict[str, str]:
    if DATABASE_URL.startswith("sqlite:"):
        return {
            "backend": "sqlite",
            "durability": "LOCAL_FALLBACK",
            "source": "fallback",
        }
    if DATABASE_URL.startswith("postgresql:"):
        return {
            "backend": "postgresql",
            "durability": "PERSISTENT",
            "source": "DATABASE_URL",
        }
    return {
        "backend": "unknown",
        "durability": "UNKNOWN",
        "source": "DATABASE_URL" if os.getenv("DATABASE_URL") else "fallback",
    }
