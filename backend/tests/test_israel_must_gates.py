import json
import os
from unittest import mock

from app.services.canonical_universe import resolve_canonical_universe_path
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.israel_must_gates import functional_level_gate, moh_code_agreement_gate

RECORDS = {
    r["canonical_id"]: r
    for r in json.loads(resolve_canonical_universe_path("israel").read_text(encoding="utf-8"))["records"]
}
MOH_YES = RECORDS["IL-MOH-237U6"]  # MoH list, בהסכם=כן, wards unknown
WELFARE = RECORDS["IL-WEL-001"]  # Welfare home: independent/frail by regulatory scope only
PROTECTED_NURSING = RECORDS["IL-DM-031"]  # protected housing; list reports a nursing ward
MOH_NO = next(r for r in RECORDS.values() if r["licensing"]["moh_code_agreement"]["value"] == "NO")


def test_unknown_family_level_is_pending_everywhere():
    for row in (MOH_YES, WELFARE, PROTECTED_NURSING):
        assert functional_level_gate(row, None)[0] == "PENDING"


def test_ward_stated_in_source_passes():
    assert functional_level_gate(PROTECTED_NURSING, "NURSING") == ("PASS", "WARD_STATED_IN_SOURCE")


def test_regulatory_scope_can_exclude_but_never_qualify():
    assert functional_level_gate(WELFARE, "NURSING")[0] == "FAIL"
    assert functional_level_gate(WELFARE, "FRAIL")[0] == "PENDING"


def test_moh_institution_with_unknown_wards_is_pending():
    assert functional_level_gate(MOH_YES, "NURSING")[0] == "PENDING"


def test_moh_code_agreement_gate():
    assert moh_code_agreement_gate(MOH_YES)[0] == "PASS"
    assert moh_code_agreement_gate(MOH_NO)[0] == "FAIL"
    assert moh_code_agreement_gate(WELFARE)[0] == "PENDING"


def _intent(answers):
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
        return build_client_intent({"israelMarket": answers}, "", {}, {})


def test_israeli_intent_adds_musts_only_on_israel_market():
    keys = [m["key"] for m in _intent({"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE"})["must_haves"]]
    assert "IL_FUNCTIONAL_LEVEL" in keys and "IL_MOH_CODE_AGREEMENT" in keys
    with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}):
        nv = build_client_intent({"israelMarket": {"functionalLevel": "NURSING"}}, "", {}, {})
    assert not any(m["key"].startswith("IL_") for m in nv["must_haves"])


def test_private_funding_does_not_require_moh_agreement():
    keys = [m["key"] for m in _intent({"functionalLevel": "FRAIL", "fundingPathway": "PRIVATE"})["must_haves"]]
    assert "IL_MOH_CODE_AGREEMENT" not in keys


def test_shared_evaluator_applies_israeli_gates():
    intent = _intent({"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE"})
    assert evaluate_candidate_intent(MOH_NO, intent)["hard_gate"] == "FAIL"
    assert evaluate_candidate_intent(WELFARE, intent)["hard_gate"] == "FAIL"
    fit = evaluate_candidate_intent(MOH_YES, intent)
    # Agreement passes; ward and license validity are not in the source yet -> pending, not PASS.
    assert "IL_MOH_CODE_AGREEMENT" in fit["must_pass"]
    assert fit["hard_gate"] == "PENDING_VERIFICATION"
    assert set(fit["must_unknown"]) >= {"IL_FUNCTIONAL_LEVEL", "LICENSE_CURRENTLY_VALID"}
