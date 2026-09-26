from app.services.facility_parameter_service import _best_evidence_row


def test_newer_verified_evidence_beats_older_broader_scope():
    best = _best_evidence_row([
        {"value": "YES", "scope": "FACILITY", "confidence": "HIGH", "last_verified": "2025-01-01", "verification_status": "VERIFIED", "conflict_status": "NO_CONFLICT"},
        {"value": "NO", "scope": "PROGRAM", "confidence": "HIGH", "last_verified": "2026-09-01", "verification_status": "VERIFIED", "conflict_status": "NO_CONFLICT"},
    ])
    assert best["value"] == "NO"


def test_stale_evidence_cannot_become_hard_yes():
    best = _best_evidence_row([
        {"value": "YES", "scope": "FACILITY", "confidence": "HIGH", "last_verified": "2024-01-01", "verification_status": "VERIFIED", "freshness_status": "STALE", "conflict_status": "NO_CONFLICT"},
    ])
    assert best["value"] == "UNKNOWN"


def test_unresolved_conflict_cannot_become_hard_no():
    best = _best_evidence_row([
        {"value": "NO", "scope": "FACILITY", "confidence": "HIGH", "last_verified": "2026-09-01", "verification_status": "VERIFIED", "conflict_status": "CONFLICT"},
    ])
    assert best["value"] == "UNKNOWN"


def test_unverified_evidence_cannot_become_hard_fact():
    best = _best_evidence_row([
        {"value": "YES", "scope": "FACILITY", "confidence": "HIGH", "last_verified": "2026-09-01", "verification_status": "NOT_VERIFIED", "conflict_status": "NO_CONFLICT"},
    ])
    assert best["value"] == "UNKNOWN"
