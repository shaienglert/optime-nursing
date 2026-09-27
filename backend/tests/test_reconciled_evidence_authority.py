from app.services.facility_parameter_service import _best_evidence_row


def test_taxonomy_inference_cannot_prove_hard_capability():
    best = _best_evidence_row([{"value":"YES","scope":"FACILITY","confidence":"HIGH","last_verified":"2026-09-01","evidence_strength":"TAXONOMY_INFERRED","conflict_status":"NONE"}])
    assert best["value"] == "UNKNOWN"


def test_regulatory_evidence_without_legacy_verification_status_remains_eligible():
    best = _best_evidence_row([{"value":"YES","scope":"FACILITY","confidence":"HIGH","last_verified":"2026-09-01","evidence_strength":"REGULATORY_VERIFIED","conflict_status":"NONE"}])
    assert best["value"] == "YES"


def test_stale_or_conflicting_evidence_cannot_be_hard_fact():
    for extra in ({"freshness_status":"STALE"},{"conflict_status":"CONFLICT"}):
        row={"value":"YES","scope":"FACILITY","confidence":"HIGH","last_verified":"2026-09-01","evidence_strength":"REGULATORY_VERIFIED","conflict_status":"NONE",**extra}
        assert _best_evidence_row([row])["value"] == "UNKNOWN"
