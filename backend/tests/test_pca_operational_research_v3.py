from scripts.enrich_nevada_pca_operational_primary_sources_v3 import UNKNOWN, extract_extended_positive_facts


def test_extended_facts_are_positive_only_and_preserve_unknown():
    facts = extract_extended_positive_facts(
        "We provide post-surgical hospital-to-home support, overnight care, live-in care, "
        "registered nurse oversight, backup caregiver coverage, accept long-term care insurance, "
        "VA benefits and private pay. Minimum 12 hours per week."
    )
    assert facts["post_surgical_care"] is True
    assert facts["overnight_care_available"] is True
    assert facts["live_in_care_available"] is True
    assert facts["registered_nurse_oversight"] is True
    assert facts["backup_caregiver_available"] is True
    assert facts["long_term_care_insurance_verified"] is True
    assert facts["va_benefit_support_verified"] is True
    assert facts["private_pay_verified"] is True
    assert facts["minimum_weekly_hours"] == 12
    assert facts["medicaid_service_verified"] == UNKNOWN


def test_absence_never_becomes_false():
    facts = extract_extended_positive_facts("Personalized home care for older adults.")
    for key, value in facts.items():
        assert value == UNKNOWN, (key, value)
