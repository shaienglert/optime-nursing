from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException, Query


ADMIN_SECRET_ENV = "OPTIME_ADMIN_SECRET"
ADMIN_SECRET_HEADER = "X-OPTIME-Admin-Secret"


def verify_admin_secret(provided_secret: Optional[str]) -> None:
    expected_secret = os.getenv(ADMIN_SECRET_ENV, "").strip()
    if not expected_secret:
        raise HTTPException(status_code=403, detail="Admin operations are disabled")
    if not provided_secret or not secrets.compare_digest(provided_secret, expected_secret):
        raise HTTPException(status_code=403, detail="Admin authorization required")


def require_admin_secret(
    x_optime_admin_secret: Optional[str] = Header(default=None, alias=ADMIN_SECRET_HEADER),
) -> None:
    verify_admin_secret(x_optime_admin_secret)


def require_admin_for_refresh(
    refresh: bool = Query(default=False),
    x_optime_admin_secret: Optional[str] = Header(default=None, alias=ADMIN_SECRET_HEADER),
) -> None:
    if refresh:
        verify_admin_secret(x_optime_admin_secret)