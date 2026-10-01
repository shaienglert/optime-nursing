"""Contract: every CLIENT/SYSTEM MUST the intent can emit has its own evidence evaluator.

Invariant: a MUST with no evaluator falls into the generic UNKNOWN branch forever, so the
family gets zero recommendations even when governed evidence proves communities qualify
(found by golden persona 007: KOSHER_MEALS was emitted as a MUST but only the NICE branch
read the kosher evidence). Every emitted MUST key must be evaluated explicitly.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.client_intent_runtime import evaluate_candidate_intent

SOURCE = (Path(__file__).resolve().parents[1] / "app/services/client_intent_runtime.py").read_text()


def _must_loop_source() -> str:
    start = SOURCE.index('for must in intent.get("must_haves")')
    end = SOURCE.index('for nice in intent.get("nice_to_haves")', start)
    return SOURCE[start:end]


def test_every_emitted_must_key_has_an_explicit_evaluator():
    emitted = set(re.findall(r'add_must\(\s*"([A-Z_]+)"', SOURCE))
    loop = _must_loop_source()
    evaluated = set(re.findall(r'key == "([A-Z_]+)"', loop))
    evaluated |= {k for group in re.findall(r"key in \{([^}]*)\}", loop) for k in re.findall(r'"([A-Z_]+)"', group)}
    missing = sorted(emitted - evaluated)
    assert not missing, f"MUST keys with no evaluator (always UNKNOWN): {missing}"


def _fit(row):
    return evaluate_candidate_intent(row, {"must_haves": [{"key": "KOSHER_MEALS"}]})


def test_kosher_must_reads_the_governed_kosher_evidence():
    passed = _fit({"matched_needs": [{"parameter_id": "kosher"}]})
    assert "KOSHER_MEALS" in passed["must_pass"] and passed["hard_gate"] == "PASS"
    failed = _fit({"unmet_verified_needs": [{"parameter_id": "kosher"}]})
    assert "KOSHER_MEALS" in failed["must_fail"] and failed["hard_gate"] == "FAIL"
    unknown = _fit({})
    assert "KOSHER_MEALS" in unknown["must_unknown"] and unknown["hard_gate"] == "PENDING_VERIFICATION"
