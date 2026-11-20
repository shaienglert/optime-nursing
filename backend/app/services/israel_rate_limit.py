"""Rate limits for public Israeli family actions (inquiries, bookings, messages, feedback).

Limits, per client address:
- new inquiries: 5 per hour, 15 per day; per facility: 3 per day from one address
- every facility: 30 new inquiries per hour from all addresses together (not spoofable)
- per inquiry link: 20 writes per hour (replies, visit requests, bookings, feedback)

Counts live in memory: one API instance, reset on restart. Good enough for the pilot;
a shared store is needed only if the API runs on several instances.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, Optional, Tuple

HOUR = 3600
DAY = 86400
RULES: Dict[str, Tuple[Tuple[int, int], ...]] = {
    "inquiry_ip": ((5, HOUR), (15, DAY)),
    "inquiry_ip_facility": ((3, DAY),),
    "inquiry_facility": ((30, HOUR),),
    "family_advice_ip": ((20, HOUR),),
    "family_advice_global": ((120, HOUR),),
    "token_write": ((20, HOUR),),
}
MESSAGE = "יותר מדי פניות בזמן קצר. אפשר לנסות שוב מאוחר יותר."

_lock = threading.Lock()
_hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def enabled() -> bool:
    return os.getenv("OOMNIK_RATE_LIMIT_DISABLED", "").strip() != "1"


def client_address(headers, fallback: Optional[str]) -> str:
    """The family's address. The Hebrew site's proxy passes it as x-oomnik-client-ip;
    direct callers are identified by Render's x-forwarded-for."""
    for name in ("x-oomnik-client-ip", "x-forwarded-for"):
        value = (headers.get(name) or "").split(",")[0].strip()
        if value:
            return value[:64]
    return fallback or "unknown"


def allowed(keys: Iterable[Tuple[str, str]], now: Optional[float] = None) -> bool:
    """True when every key is under its limits. Counts nothing."""
    return check(keys, now=now, record=False)


def record(keys: Iterable[Tuple[str, str]], now: Optional[float] = None) -> None:
    """Count one accepted action. Only successful actions are counted, so a family that
    fixes a form mistake is never locked out by its own retries."""
    if not enabled():
        return
    now = time.time() if now is None else now
    with _lock:
        for rule, key in keys:
            _hits[(rule, key)].append(now)


def check(keys: Iterable[Tuple[str, str]], now: Optional[float] = None, record: bool = True) -> bool:
    """True (and counted unless record=False) when every key is under its limits."""
    if not enabled():
        return True
    now = time.time() if now is None else now
    keys = list(keys)
    with _lock:
        for rule, key in keys:
            longest = max(window for _, window in RULES[rule])
            hits = _hits[(rule, key)]
            while hits and hits[0] <= now - longest:
                hits.popleft()
            for limit, window in RULES[rule]:
                if sum(1 for t in hits if t > now - window) >= limit:
                    return False
        if record:
            for rule, key in keys:
                _hits[(rule, key)].append(now)
    return True


def reset() -> None:
    with _lock:
        _hits.clear()
