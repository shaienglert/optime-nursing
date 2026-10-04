"""Shared existing questionnaire mappings; no new clinical policy."""

STRUCTURED_INTAKE_MAPPING_CONTRACT = {
    "assistanceLevel": {
        "Fully independent": {"classification": "NO_REQUIREMENT", "parameter_ids": []},
        "Light assistance": {"classification": "NEED", "parameter_ids": ["adl_support", "transfer_assistance"]},
        "Help with bathing": {"classification": "NEED", "parameter_ids": ["adl_support"]},
        "Help with dressing": {"classification": "NEED", "parameter_ids": ["adl_support"]},
        "Help with toileting": {"classification": "NEED", "parameter_ids": ["adl_support", "transfer_assistance"]},
        "Help with medications": {"classification": "NEED", "parameter_ids": ["medication_support"]},
        "Daytime supervision": {"classification": "NEED", "parameter_ids": ["adl_support", "transfer_assistance"]},
        "24/7 support required": {"classification": "NEED", "parameter_ids": ["adl_support", "transfer_assistance"]},
        "Skilled nursing care": {"classification": "NEED", "parameter_ids": ["skilled_nursing_capabilities", "nursing_24_7"]},
    },
    "medicalCareProfile.needs": {
        "Dialysis": {"classification": "NEED", "parameter_ids": ["dialysis_arrangements"]},
        "Oxygen": {"classification": "NEED", "parameter_ids": ["respiratory_trach_vent"]},
        "Wound care": {"classification": "NEED", "parameter_ids": ["wound_care"]},
        "Injections or infusions": {"classification": "NEED", "parameter_ids": ["medication_support"]},
        "Complex medication management": {"classification": "NEED", "parameter_ids": ["medication_support"]},
        "Complex chronic condition": {"classification": "NEED", "parameter_ids": ["adl_support"]},
        "Permanent medical equipment": {"classification": "NEED", "parameter_ids": ["adl_support"]},
        "Nursing supervision": {"classification": "NEED", "parameter_ids": ["nursing_24_7"]},
        "Other": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
    },
    "medicalCareProfile.mobilityMethod": {
        "Independent": {"classification": "NO_REQUIREMENT", "parameter_ids": []},
        "Cane": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "Walker": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "Wheelchair": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "Mostly in bed": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
    },
    "medicalCareProfile.transferAssistance": {
        "No": {"classification": "NO_REQUIREMENT", "parameter_ids": []},
        "One person": {"classification": "NEED", "parameter_ids": ["transfer_assistance"]},
        "Two people": {"classification": "NEED", "parameter_ids": ["transfer_assistance"]},
        "Mechanical lift": {"classification": "NEED", "parameter_ids": ["transfer_assistance"]},
        "Not sure": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
    },
    "medicalCareProfile.recentFalls": {
        "No": {"classification": "NO_REQUIREMENT", "parameter_ids": []},
        "One": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "More than one": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "Not sure": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
    },
    "medicalCareProfile.physicianCoordination": {
        "No": {"classification": "NO_REQUIREMENT", "parameter_ids": []},
        "Yes": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
        "Not sure": {"classification": "CONTEXT_ONLY", "parameter_ids": []},
    },
}


def assistance_parameters(value):
    """Exact structured selections, including the existing joined storage form."""
    selections = value if isinstance(value, list) else str(value or "").split(",")
    contract = STRUCTURED_INTAKE_MAPPING_CONTRACT["assistanceLevel"]
    return {parameter for selected in selections
            for parameter in contract.get(str(selected).strip(), {}).get("parameter_ids", [])}
