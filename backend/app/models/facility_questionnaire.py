from typing import Dict, List

ANSWER_STATES: List[str] = ["YES", "NO", "UNKNOWN", "LIMITED"]

FACILITY_QUESTIONNAIRE_V1: Dict[str, List[Dict[str, str]]] = {
    "Medical": [
        {"key": "medical_24_7_nursing", "label": "24/7 nursing"},
        {"key": "medical_physician_availability", "label": "Physician availability"},
        {"key": "medical_memory_care", "label": "Memory care"},
    ],
    "Rehabilitation": [
        {"key": "rehab_speech_therapy", "label": "Speech therapy"},
        {"key": "rehab_physical_therapy", "label": "Physical therapy"},
        {"key": "rehab_occupational_therapy", "label": "Occupational therapy"},
        {"key": "rehab_stroke_support", "label": "Stroke rehabilitation"},
        {"key": "rehab_parkinson_support", "label": "Parkinson support"},
    ],
    "Dining": [
        {"key": "dining_gluten_free", "label": "Gluten free"},
        {"key": "dining_kosher", "label": "Kosher"},
        {"key": "dining_vegetarian", "label": "Vegetarian"},
        {"key": "dining_diabetic_meals", "label": "Diabetic meals"},
    ],
    "Lifestyle": [
        {"key": "lifestyle_movies", "label": "Movies"},
        {"key": "lifestyle_music", "label": "Music"},
        {"key": "lifestyle_gardening", "label": "Gardening"},
        {"key": "lifestyle_pool", "label": "Pool"},
        {"key": "lifestyle_fitness_center", "label": "Fitness center"},
        {"key": "lifestyle_religious_services", "label": "Religious services"},
        {"key": "lifestyle_transportation", "label": "Transportation"},
    ],
    "Housing": [
        {"key": "housing_kitchenette", "label": "Kitchenette"},
        {"key": "housing_balcony", "label": "Balcony"},
        {"key": "housing_studio", "label": "Studio"},
        {"key": "housing_one_bedroom", "label": "One bedroom"},
        {"key": "housing_pets_allowed", "label": "Pets allowed"},
    ],
    "Accessibility": [
        {"key": "accessibility_walker_support", "label": "Walker support"},
        {"key": "accessibility_wheelchair_access", "label": "Wheelchair accessibility"},
        {"key": "accessibility_fall_prevention", "label": "Fall prevention"},
        {"key": "accessibility_transfer_assistance", "label": "Transfer assistance"},
    ],
    "Future Care Continuum": [
        {"key": "continuum_assisted_living", "label": "Assisted living available"},
        {"key": "continuum_memory_care", "label": "Memory care available"},
        {"key": "continuum_skilled_nursing", "label": "Skilled nursing available"},
        {"key": "continuum_rehabilitation", "label": "Rehabilitation available"},
        {"key": "continuum_on_campus_progression", "label": "On-campus progression across care levels"},
    ],
}


def facility_questionnaire_v1_flat() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for section, questions in FACILITY_QUESTIONNAIRE_V1.items():
        for question in questions:
            items.append({
                "section": section,
                "key": question["key"],
                "label": question["label"],
            })
    return items
