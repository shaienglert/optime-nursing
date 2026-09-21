"""Fixed parity cases. Personas mirror the repo's own tests plus edge cases."""

READY = {"decision_readiness": "READY", "next_question": None, "statements": []}
NEEDS_Q = {
    "decision_readiness": "NEEDS_CLARIFICATION",
    "next_question": "What would make the move feel most comfortable for him?",
    "statements": [],
}

HI_ANSWERED = {
    "personalityProfile": {"communitySizePreference": "Large community"},
    "familyProfile": {"socialInteractionNeed": "Helpful daily social contact"},
    "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
}

SON84 = {
    "relationship": "Dad",
    "ageGroup": "80-84",
    "assistanceLevel": "Needs assistance with bathing and dressing",
    "memoryStatus": "No",
    "budget": 6500,
    "distanceFromFamily": "Balanced location",
}

CASES = {
    "son84_ready": {
        "questionnaire": SON84,
        "query": "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing and meals. No dementia.",
    },
    "son84_ready_verified_rates": {
        "questionnaire": SON84,
        "query": "My father is 84, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing and meals. No dementia.",
        "verified_rates": True,
    },
    "son84_answered_hi": {
        "questionnaire": {**SON84, "humanIntelligenceV2": HI_ANSWERED},
        "query": "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing, meals and medication. No dementia.",
    },
    "interview_not_ready": {
        "questionnaire": SON84,
        "query": "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing and meals. No dementia.",
        "interview_ai": NEEDS_Q,
    },
    "mother90_social": {
        "questionnaire": {"relationship": "Mom", "ageGroup": "90+", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "distanceFromFamily": "Balanced location"},
        "query": "My mother is 90 and we are looking across the Las Vegas Valley. She is mentally alert, has no dementia, is mobile, but needs daily help with bathing, dressing and medication. She would like a friendly social environment and we want the least restrictive safe setting.",
    },
    "couple_rehab": {
        "questionnaire": {"relationship": "Dad", "ageGroup": "80+", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "distanceFromFamily": "Balanced location", "budget": 12000,
                          "humanIntelligenceV2": {"personalityProfile": {"communitySizePreference": "Large community"}, "familyProfile": {"socialInteractionNeed": "Very important"}}},
        "query": "A couple age 80+ wants to move to senior living in Las Vegas with lots of culture, classes and activities. The husband had spinal surgery and needs rehabilitation. He is expected to return to walking, but for the next 3 months he needs help with bathing and dressing. The wife is independent and they want to live together.",
    },
    "independent_couple": {
        "questionnaire": {"relationship": "Myself", "ageGroup": "80-84", "assistanceLevel": "Independent", "memoryStatus": "No", "distanceFromFamily": "Balanced location"},
        "query": "My husband and I are both over 80 and want independent senior living in Las Vegas. We are both healthy and independent and want lots of activities.",
    },
    "memory_care": {
        "questionnaire": {"relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Help with bathing, 24/7 support required", "memoryStatus": "Significant memory issues", "distanceFromFamily": "Balanced location", "budget": 8000},
        "query": "My mother has severe dementia requiring 24/7 supervision in a secure memory setting in Las Vegas.",
    },
    "skilled_nursing": {
        "questionnaire": {"relationship": "Dad", "ageGroup": "85-89", "assistanceLevel": "Needs extensive assistance", "memoryStatus": "No", "distanceFromFamily": "Balanced location", "budget": 12000},
        "query": "My father needs 24/7 skilled nursing in Las Vegas and is not looking for independent living. His monthly budget is $12,000.",
    },
    "clinical_dialysis": {
        "questionnaire": {"relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Help with medications", "memoryStatus": "No", "distanceFromFamily": "Balanced location"},
        "query": "My father lives in Las Vegas. He needs dialysis, daily wound care, and continuous oxygen.",
    },
    "budget_medicaid_pending": {
        "questionnaire": {"relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "distanceFromFamily": "Balanced location"},
        "query": "My mother lives in Las Vegas and needs help with bathing and dressing. Her budget is $5,000 per month and Medicaid eligibility is pending.",
    },
    "medicaid_negated_kosher": {
        "questionnaire": {"relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "distanceFromFamily": "Balanced location", "medicaidStatus": "Not eligible", "budget": 7000},
        "query": "My father lives in Las Vegas, keeps kosher and needs help with bathing and dressing. He has Medicare and is not applying for Medicaid.",
    },
    "henderson_city": {
        "questionnaire": {"relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 7000, "distanceFromFamily": "Balanced location", "city": "Henderson"},
        "query": "My mother is 87 and lives in Henderson, Nevada. She needs help with bathing, dressing and medication. No dementia. We want a place in Henderson close to family.",
    },
    "empty_input": {
        "questionnaire": {},
        "query": "",
    },
    "pilot_son84": {
        "market": "synthetic-pilot",
        "questionnaire": SON84,
        "query": "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing and meals. No dementia.",
    },
    "pilot_memory": {
        "market": "synthetic-pilot",
        "questionnaire": {"relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Help with bathing, 24/7 support required", "memoryStatus": "Significant memory issues", "distanceFromFamily": "Balanced location", "budget": 8000},
        "query": "My mother has severe dementia requiring 24/7 supervision in a secure memory setting in Las Vegas.",
    },
    "pilot_stroke_rehab": {
        "market": "synthetic-pilot",
        "questionnaire": {"relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "distanceFromFamily": "Balanced location", "budget": 9000},
        "query": "My father had a stroke, needs physical, occupational and speech therapy, help with bathing, dressing and transfers, and medication management in Las Vegas. No dementia.",
    },
}
