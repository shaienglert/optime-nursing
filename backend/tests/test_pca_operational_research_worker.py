from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich_nevada_pca_operational_primary_sources import (  # noqa: E402
    UNKNOWN,
    extract_operational_facts,
    identity_matches,
)


def test_extracts_only_explicit_operational_facts():
    text = """
    We provide bathing, dressing assistance, safe transfers and mobility assistance.
    Medication reminders and meal preparation are available. We are available 24/7.
    Our caregivers are W-2 employees and complete criminal background checks.
    Visits have a 3-hour minimum. Spanish and Tagalog caregivers are available.
    """
    facts = extract_operational_facts(text)
    assert facts["bathing_assistance"] is True
    assert facts["dressing_assistance"] is True
    assert facts["transfer_assistance"] is True
    assert facts["medication_reminders"] is True
    assert facts["meal_preparation"] is True
    assert facts["minimum_billable_hours"] == 3
    assert facts["minimum_visit_minutes"] == UNKNOWN
    assert facts["employment_model"] == "W2_EMPLOYEES"
    assert facts["background_check_verified"] is True
    assert facts["availability_status"] == "24_7_SERVICE_AVAILABLE"
    assert facts["languages"] == ["Spanish", "Tagalog"]


def test_published_rate_does_not_become_requested_schedule_rate():
    text = "Care starts at $32.50 per hour for schedules of 25 weekly hours."
    facts = extract_operational_facts(text)
    assert facts["published_hourly_rate_candidates"][0]["amount_usd_per_hour"] == 32.50
    assert facts["hourly_rate_for_requested_schedule"] == UNKNOWN


def test_generic_marketing_does_not_invent_operational_terms():
    facts = extract_operational_facts("Compassionate licensed home care for seniors in Nevada.")
    assert facts["bathing_assistance"] is False
    assert facts["dressing_assistance"] is False
    assert facts["transfer_assistance"] is False
    assert facts["minimum_billable_hours"] == UNKNOWN
    assert facts["employment_model"] == UNKNOWN
    assert facts["liability_insurance_verified"] == UNKNOWN
    assert facts["background_check_verified"] == UNKNOWN
    assert facts["fixed_caregiver_possible"] == UNKNOWN


def test_identity_can_match_exact_phone_even_with_brand_variation():
    task = {
        "agency_name": "RIGHT AT HOME LAS VEGAS",
        "city": "LAS VEGAS",
        "address": "6757 W CHARLESTON BLVD",
        "phone": "702-367-3400",
        "license_number": "9703-PCS-7",
    }
    text = "Right at Home | 6757 W. Charleston Blvd, Las Vegas NV | (702) 367-3400"
    assert identity_matches(text, task) is True


def test_similar_name_without_location_phone_address_or_license_is_not_identity():
    task = {
        "agency_name": "SUNRISE PERSONAL CARE",
        "city": "LAS VEGAS",
        "address": "100 MAIN ST",
        "phone": "702-555-1234",
        "license_number": "9999-PCS-1",
    }
    assert identity_matches("Sunrise Personal Care serving Phoenix Arizona", task) is False
