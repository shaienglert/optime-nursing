import copy
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
MOH_YES = RECORDS["IL-MOH-237U6"]  # MoH list says בהסכם=כן; facility not registered
WELFARE = RECORDS["IL-WEL-001"]
PROTECTED_NURSING = RECORDS["IL-DM-031"]  # list reports a nursing ward; facility not registered


def _registered(row, *, departments=None, levels=None, moh_agreement=None):
    row = copy.deepcopy(row)
    supplied = lambda v: {"value": v, "status": "STATED", "source": "facility_portal", "basis": "FACILITY_SUPPLIED"}
    if departments is not None:
        row["care_capabilities"]["departments"] = supplied(departments)
    if levels is not None:
        row["care_capabilities"]["functional_levels_served"] = supplied(levels)
    if moh_agreement is not None:
        row["licensing"]["moh_code_agreement"] = supplied(moh_agreement)
    return row


def test_list_data_alone_never_decides_a_gate():
    for row in (MOH_YES, WELFARE, PROTECTED_NURSING):
        assert functional_level_gate(row, "NURSING")[0] == "PENDING"
        assert moh_code_agreement_gate(row)[0] == "PENDING"


def test_facility_supplied_data_decides():
    nursing = _registered(WELFARE, departments=["סיעודית"], moh_agreement="YES")
    assert functional_level_gate(nursing, "NURSING")[0] == "PASS"
    assert functional_level_gate(nursing, "COGNITIVE_FRAIL")[0] == "FAIL"
    assert moh_code_agreement_gate(nursing)[0] == "PASS"
    assert moh_code_agreement_gate(_registered(WELFARE, moh_agreement="NO"))[0] == "FAIL"


def test_unknown_family_level_is_pending():
    assert functional_level_gate(_registered(WELFARE, levels=["FRAIL"]), None)[0] == "PENDING"


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
    assert evaluate_candidate_intent(MOH_YES, intent)["hard_gate"] == "PENDING_VERIFICATION"
    refuses = _registered(MOH_YES, levels=["FRAIL"], moh_agreement="YES")
    assert evaluate_candidate_intent(refuses, intent)["hard_gate"] == "FAIL"
    fits = _registered(MOH_YES, departments=["סיעודית"], moh_agreement="YES")
    fit = evaluate_candidate_intent(fits, intent)
    assert {"IL_FUNCTIONAL_LEVEL", "IL_MOH_CODE_AGREEMENT"} <= set(fit["must_pass"])


def test_israeli_answers_survive_the_structured_profile():
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

    answers = {"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE", "city": "חיפה", "maxDistanceKm": 20}
    restored = materialize_questionnaire(build_structured_profile({"israelMarket": answers}))
    assert restored["israelMarket"] == answers
