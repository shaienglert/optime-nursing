from app.services.client_intent_runtime import intent_rank_key


def _row(
    name: str,
    *,
    gate: str = "PASS",
    care: str = "PRIMARY_FIT",
    nice=None,
    history=None,
    rating="UNKNOWN",
    reviews="UNKNOWN",
    known: int = 0,
    unknown: int = 0,
    canonical_type: str = "ASSISTED_LIVING_RFG",
    modalities=None,
    patient_match_score: float = 0.0,
    quality_safety_score: float = 0.0,
):
    return {
        "facility_name": name,
        "canonical_type": canonical_type,
        "housing_modalities": modalities or [],
        "care_setting_fit": {"status": care},
        "patient_match_score": patient_match_score,
        "quality_safety_score": quality_safety_score,
        "client_intent_fit": {
            "hard_gate": gate,
            "nice_match": list(nice or []),
            "nice_fit_scores": {},
            "public_reputation": {
                "rating": rating,
                "review_count": reviews,
            },
            "relevant_evidence_known_count": known,
            "relevant_evidence_unknown_count": unknown,
        },
        "regulatory_history": history or {},
    }


def test_verified_must_pass_beats_pending_even_if_pending_has_better_everything_else():
    verified = _row("Verified", gate="PASS", rating=3.0, reviews=5, known=1)
    pending = _row(
        "Pending",
        gate="PENDING_VERIFICATION",
        nice=["DINING_EXPERIENCE", "TRANSPORTATION_AND_OUTINGS"],
        rating=5.0,
        reviews=5000,
        known=50,
        patient_match_score=100.0,
        quality_safety_score=100.0,
    )
    assert intent_rank_key(verified) < intent_rank_key(pending)


def test_primary_care_setting_beats_possible_fit_before_nice_and_reputation():
    primary = _row("Primary", care="PRIMARY_FIT", rating=2.5, reviews=3)
    possible = _row(
        "Possible",
        care="POSSIBLE_FIT",
        nice=["DINING_EXPERIENCE", "TRANSPORTATION_AND_OUTINGS"],
        rating=5.0,
        reviews=5000,
        known=100,
    )
    assert intent_rank_key(primary) < intent_rank_key(possible)


def test_explicit_nice_fit_beats_regulatory_and_reputation_advantage():
    client_fit = _row(
        "Client Fit",
        nice=["DINING_EXPERIENCE"],
        history={"disciplinary_action": "Y", "latest_known_grade": "C", "grade_counts": {"C": 1}},
        rating=3.0,
        reviews=10,
    )
    generic_quality = _row(
        "Generic Quality",
        nice=[],
        history={"disciplinary_action": "N", "latest_known_grade": "A", "grade_counts": {"A": 10}},
        rating=5.0,
        reviews=5000,
    )
    assert intent_rank_key(client_fit) < intent_rank_key(generic_quality)


def test_regulatory_safety_precedes_public_reputation():
    safer = _row(
        "Safer",
        history={"disciplinary_action": "N", "latest_known_grade": "A", "grade_counts": {"A": 1}},
        rating=2.0,
        reviews=2,
    )
    popular_but_adverse = _row(
        "Popular But Adverse",
        history={"disciplinary_action": "Y", "latest_known_grade": "D", "grade_counts": {"D": 1}},
        rating=5.0,
        reviews=10000,
    )
    assert intent_rank_key(safer) < intent_rank_key(popular_but_adverse)


def test_public_reputation_precedes_evidence_completeness_when_prior_dimensions_tie():
    better_reputation = _row("Better Reputation", rating=4.8, reviews=200, known=1, unknown=20)
    more_documented = _row("More Documented", rating=4.2, reviews=5000, known=100, unknown=0)
    assert intent_rank_key(better_reputation) < intent_rank_key(more_documented)


def test_legacy_numeric_scores_cannot_change_final_rank_causality():
    baseline = _row("A", rating=4.0, reviews=100, patient_match_score=0.0, quality_safety_score=0.0)
    inflated_legacy = _row("B", rating=4.0, reviews=100, patient_match_score=999999.0, quality_safety_score=999999.0)
    # The only remaining difference is the deterministic facility-name tie-breaker.
    # Legacy numeric scores are intentionally absent from the final intent rank key.
    assert intent_rank_key(baseline)[:-1] == intent_rank_key(inflated_legacy)[:-1]
