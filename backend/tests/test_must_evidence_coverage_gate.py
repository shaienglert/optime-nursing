"""Coverage Gate (owner rule 2026-10-01).

Every SYSTEM/CLIENT MUST the engine can emit must (1) declare its evidence source, (2) have
that source loaded by the decision core, and (3) have at least one facility in the pilot
market with a known value from it. Otherwise a zero result is a readiness gap of the
catalog, not "no suitable communities".
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

from app.services.must_evidence_sources import MUST_EVIDENCE_PARAMETER_IDS, MUST_EVIDENCE_SOURCES, market_must_coverage

ROOT = Path(__file__).resolve().parents[2]
INTENT_SOURCE = (ROOT / "backend/app/services/client_intent_runtime.py").read_text()


def test_every_emittable_must_declares_an_evidence_source():
    emitted = set(re.findall(r'add_must\(\s*"([A-Z_]+)"', INTENT_SOURCE)) | {"MEDICAID_PATHWAY_REQUIRED"}
    assert sorted(emitted - set(MUST_EVIDENCE_SOURCES)) == []


def test_decision_core_loads_every_must_evidence_parameter():
    core = (ROOT / "backend/app/services/decision_engine_core.py").read_text()
    assert "*MUST_EVIDENCE_PARAMETER_IDS," in core
    assert {"secured_units", "medicaid_attributes", "kosher"} <= MUST_EVIDENCE_PARAMETER_IDS


def test_pilot_market_has_evidence_for_every_must():
    with patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"}, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache

        refresh_runtime_cache("must-coverage-gate")
        report = market_must_coverage()
    gaps = {key: item for key, item in report.items() if item["status"] != "COVERED"}
    assert not gaps, f"pilot market is not ready: {gaps}"
