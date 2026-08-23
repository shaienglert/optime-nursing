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


def test_independent_living_modality_ranks_above_small_rfg_for_independent_client():
    il = _row("Revel Vegas", "INDEPENDENT_LIVING", ["INDEPENDENT_LIVING"], "PRIMARY_FIT")
    rfg = _row("Small Group Home", "ASSISTED_LIVING_RFG", [], "POSSIBLE_FIT")
    assert intent_rank_key(il) < intent_rank_key(rfg)


def test_hybrid_rfg_with_verified_independent_living_modality_is_primary_product_fit():
    hybrid = _row("Las Ventanas at Summerlin", "ASSISTED_LIVING_RFG", ["INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"], "POSSIBLE_FIT")
    rfg = _row("Small Group Home", "ASSISTED_LIVING_RFG", [], "POSSIBLE_FIT")
    assert intent_rank_key(hybrid) < intent_rank_key(rfg)
