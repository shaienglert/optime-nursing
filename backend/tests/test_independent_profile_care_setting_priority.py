from app.services.client_intent_runtime import intent_rank_key


def _row(name: str, canonical_type: str, modalities=None, care_status="POSSIBLE_FIT"):
    return {
        "facility_name": name,
        "canonical_type": canonical_type,
        "housing_modalities": modalities or [],
        "care_setting_fit": {"status": care_status},
        "client_intent_fit": {
            "hard_gate": "PASS",
            "nice_match": [],
            "nice_fit_scores": {},
            "public_reputation": {},
            "relevant_evidence_known_count": 0,
            "relevant_evidence_unknown_count": 0,
        },
        "regulatory_history": {},
    }


def test_independent_living_ranks_above_small_rfg_for_independent_client():
    il = _row("Revel Vegas", "INDEPENDENT_LIVING", ["INDEPENDENT_LIVING"], "PRIMARY_FIT")
    rfg = _row("Small Group Home", "ASSISTED_LIVING_RFG", [], "POSSIBLE_FIT")
    assert intent_rank_key(il) < intent_rank_key(rfg)


def test_verified_il_modality_promotes_hybrid_rfg_product_fit():
    hybrid = _row("Las Ventanas at Summerlin", "ASSISTED_LIVING_RFG", ["INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"], "POSSIBLE_FIT")
    rfg = _row("Small Group Home", "ASSISTED_LIVING_RFG", [], "POSSIBLE_FIT")
    assert intent_rank_key(hybrid) < intent_rank_key(rfg)


def test_il_modality_does_not_override_insufficient_setting_for_care_needs():
    unsafe_il = _row("Independent Living Only", "INDEPENDENT_LIVING", ["INDEPENDENT_LIVING"], "INSUFFICIENT_SETTING")
    assisted = _row("Appropriate Assisted Living", "ASSISTED_LIVING_RFG", [], "PRIMARY_FIT")
    assert intent_rank_key(assisted) < intent_rank_key(unsafe_il)
