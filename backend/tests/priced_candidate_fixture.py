"""Explicit synthetic prices for downstream strategy tests, never production data."""
from copy import deepcopy


def priced_payloads(payloads, monthly_price=2800):
    """Supply a numeric candidate price while preserving the real budget gate.

    These tests isolate downstream strategy/serialization. A published-rates flag
    alone cannot serve as their affordability fixture. Do not mock the comparator
    or use this helper in budget/MUST verification tests.
    """
    def read(row):
        row["starting_monthly_price"] = monthly_price
        return deepcopy(payloads)

    return read
