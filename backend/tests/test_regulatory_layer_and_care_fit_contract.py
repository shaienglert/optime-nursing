"""Contracts for the two approved findings (owner, 2026-10-01).

Finding 1: care-setting fit comes from capability (regulation -> verified evidence ->
UNKNOWN), never from facility type alone; a facility that verifiably provides every
required care capability can never be labelled INSUFFICIENT_SETTING.

Finding 2: one Regulatory/Quality Evidence Layer; no composite score; a measure separates
candidates only when all of them have it from the same source; otherwise a true tie; name,
order or index never decide rank.
"""
from __future__ import annotations

import itertools

from app.services import decision_engine_evidence as governed
from app.services.regulatory_quality_layer import rank_with_evidence_layer


def _q(**measures):
    return {parameter: {"value": value, "source_family": "SRC"} for parameter, value in measures.items()}


def _row(fid, name=None, **measures):
    return {"canonical_facility_id": fid, "facility_name": name or fid, "regulatory_quality_evidence": _q(**measures), "client_intent_fit": {}}


def _positions(rows):
    ranked = rank_with_evidence_layer(rows, lambda r: (0,))
    signatures = []
    for row in ranked:
        if row["rank_group_signature"] not in signatures:
            signatures.append(row["rank_group_signature"])
    return {row["canonical_facility_id"]: signatures.index(row["rank_group_signature"]) for row in ranked}


def test_measure_missing_for_one_member_is_not_a_basis_for_the_group():
    pos = _positions([_row("A", inspection_rating=4.5), _row("B")])
    assert pos["A"] == pos["B"]


def test_shared_measure_separates_in_its_own_direction():
    pos = _positions([_row("A", deficiency_count=7), _row("B", deficiency_count=2), _row("C", deficiency_count=2)])
    assert pos["B"] == pos["C"] < pos["A"]


def test_same_measure_from_different_sources_is_not_compared():
    a = _row("A", inspection_rating=5)
    b = _row("B", inspection_rating=2)
    b["regulatory_quality_evidence"]["inspection_rating"]["source_family"] = "OTHER"
    pos = _positions([a, b])
    assert pos["A"] == pos["B"]


def test_name_and_input_order_never_change_rank():
    base = [_row("A", "Zeta", deficiency_count=3), _row("B", "Alpha", deficiency_count=3), _row("C", "Mid", deficiency_count=1)]
    expected = _positions([dict(r) for r in base])
    for order in itertools.permutations(base):
        renamed = [{**r, "facility_name": f"x{i}"} for i, r in enumerate(order)]
        assert _positions(renamed) == expected


def test_verified_care_capabilities_are_never_insufficient_whatever_the_type():
    context = {"care_need_ids": ["adl_support", "dialysis_arrangements", "wound_care"]}
    for canonical_type in ("ASSISTED_LIVING_RFG", "SKILLED_NURSING", "UNKNOWN_TYPE"):
        fit = governed._care_setting_fit(
            context,
            {"canonical_type": canonical_type, "matched_needs": [{"parameter_id": p} for p in context["care_need_ids"]]},
            {},
        )
        assert fit["status"] in {"PRIMARY_FIT", "OVERLEVEL"}, (canonical_type, fit)


def test_verified_missing_capability_is_insufficient_and_unknown_is_possible():
    context = {"care_need_ids": ["dialysis_arrangements"]}
    assert governed._care_setting_fit(context, {"canonical_type": "SKILLED_NURSING", "unmet_verified_needs": [{"parameter_id": "dialysis_arrangements"}]}, {})["status"] == "INSUFFICIENT_SETTING"
    assert governed._care_setting_fit(context, {"canonical_type": "SKILLED_NURSING"}, {})["status"] == "POSSIBLE_FIT"
