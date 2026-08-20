from app.services.combined_care_solution_runtime import build_combined_care_solution
from app.services.facility_service_delivery_runtime import get_facility_service_delivery_evidence


def test_vista_park_has_three_meals_and_outside_care_path():
    row = {
        "canonical_facility_id": "NV-PROVIDER-IL-VISTA-PARK",
        "facility_name": "Vista Park Retirement Community",
        "canonical_type": "INDEPENDENT_LIVING",
        "housing_modalities": ["INDEPENDENT_LIVING"],
        "address": "4190 W Farm Rd",
        "city": "North Las Vegas",
        "state": "NV",
    }
    evidence = get_facility_service_delivery_evidence(row)
    assert evidence["matched"] is True
    assert evidence["meal_delivery"]["meals_per_day"] == 3
    assert evidence["meal_delivery"]["meal_plan_included"] is True
    assert evidence["personal_care_delivery"]["outside_care_allowed"] is True
    solution = build_combined_care_solution(row, {}, "Needs one hour of bathing and dressing after surgery")
    assert solution["meal_component"]["meals_per_day"] == 3
    assert solution["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
    assert solution["care_component"]["agency_relationship_type"] == "OUTSIDE_AGENCY_ALLOWED"


def test_revel_dining_credits_do_not_become_three_meals():
    row = {
        "canonical_facility_id": "NV-PROVIDER-IL-REVEL-VEGAS",
        "facility_name": "Revel Vegas",
        "canonical_type": "INDEPENDENT_LIVING",
        "housing_modalities": ["INDEPENDENT_LIVING"],
        "address": "4940 S Conquistador St",
        "city": "Las Vegas",
        "state": "NV",
    }
    solution = build_combined_care_solution(row, {}, "Three meals and help with bathing")
    assert solution["meal_component"]["meal_plan_model"] == "MONTHLY_DINING_CREDITS"
    assert solution["meal_component"]["meals_per_day"] == "UNKNOWN"
    assert solution["care_component"]["external_care_allowed"] == "UNKNOWN"


def test_las_ventanas_keeps_flexible_dining_count_unknown():
    row = {
        "canonical_facility_id": "NV-LIC-4000-AGC-31",
        "facility_name": "Las Ventanas at Summerlin",
        "canonical_type": "ASSISTED_LIVING_RFG",
        "housing_modalities": ["INDEPENDENT_LIVING", "LIFE_PLAN_CCRC", "ASSISTED_LIVING"],
        "address": "10401 W Charleston Blvd",
        "city": "Las Vegas",
        "state": "NV",
    }
    solution = build_combined_care_solution(row, {}, "Needs meals and personal care")
    assert solution["meal_component"]["meal_plan_model"] == "FLEXIBLE_DINING_POINTS"
    assert solution["meal_component"]["meals_per_day"] == "UNKNOWN"
    assert solution["delivery_model"] == "FACILITY_IN_HOUSE"
