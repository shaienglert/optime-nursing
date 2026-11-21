"""Which facility rows belong to this deployment's market.

Each deployment serves exactly one market (OPTIME_CANONICAL_MARKET). Every
market except Israel keeps the historical Nevada scope unchanged, so the
existing pilot behaves exactly as before.
"""

from __future__ import annotations

from app.services.canonical_universe import configured_canonical_market

NEVADA_STATE_CODE = "NV"
ISRAEL_STATE_CODE = "IL"
ISRAEL_MARKET = "israel"
# Test deployment: same Israeli layer, synthetic facilities (never real ones).
ISRAEL_SYNTHETIC_MARKET = "israel-synthetic"
ISRAEL_MARKETS = {ISRAEL_MARKET, ISRAEL_SYNTHETIC_MARKET}


def is_israel_market(market: str | None = None) -> bool:
    return (market or configured_canonical_market()) in ISRAEL_MARKETS


def is_israel_synthetic_market(market: str | None = None) -> bool:
    return (market or configured_canonical_market()) == ISRAEL_SYNTHETIC_MARKET


def active_state_code(market: str | None = None) -> str:
    """The value stored in Facility.state for this deployment's market."""
    return ISRAEL_STATE_CODE if is_israel_market(market) else NEVADA_STATE_CODE
