"""Audited additive-only source-accounting parity metadata.

This is not a ranking/eligibility waiver. Only three diagnostic keys are allowed
when introduced into the established decision-intelligence accounting envelope.
"""
from __future__ import annotations

PREFIX = ".decision_intelligence.human_intelligence.user_statement_accounting."
VALUES = {
    "coverage_basis": "STATEMENT_CLASSIFICATION_ONLY",
    "semantic_coverage_percent": None,
    "semantic_coverage_status": "NOT_INDEPENDENTLY_VERIFIED",
}


def is_additive_coverage_metadata(path: str, kind: str, old, new) -> bool:
    if kind != "added" or old is not None or not path.startswith("$."):
        return False
    if path.count(PREFIX) != 1:
        return False
    tail = path.split(PREFIX, 1)[1]
    if tail not in VALUES:
        return False
    return type(new) is type(VALUES[tail]) and new == VALUES[tail]
