"""Reconstructed from the owner's ten descriptions, NOT the missing original fixtures."""
BASE = dict(relationship="Mom", ageGroup="80-84", memoryStatus="No", budget=6500, distanceFromFamily="Balanced location")
CASES = [
    ("independent_social", "Fully independent", "My mother is 82, fully independent and mentally alert. She wants a social community with activities in Las Vegas.", {}),
    ("bathing_dressing", "Needs assistance with bathing and dressing", "My mother needs help with bathing and dressing in Las Vegas. She has no dementia.", {}),
    ("falls_transfers", "Help with bathing", "My mother has had falls and needs one person to help her get in and out of bed and the shower in Las Vegas.", {}),
    ("mild_forgetfulness", "Help with medications", "My mother has mild forgetfulness and needs help with medications in Las Vegas.", {"memoryStatus": "Mild memory issues"}),
    ("dementia_wandering", "24/7 support required", "My mother has dementia, wanders, and needs a secure memory care unit in Las Vegas.", {"memoryStatus": "Significant memory issues"}),
    ("post_surgery_rehab", "Help with bathing", "My mother is recovering after hip surgery and needs physical therapy and occupational therapy in Las Vegas.", {}),
    ("dialysis", "Help with medications", "My father needs dialysis three times a week in Las Vegas. He needs help with medications.", {"relationship": "Dad"}),
    ("oxygen_wound", "Help with medications", "My mother uses continuous oxygen and has a pressure wound on her heel that needs daily dressing changes in Las Vegas.", {}),
    ("low_budget_medicaid", "Help with bathing", "My mother needs help with bathing in Las Vegas. Her budget is $3000 per month and Medicaid eligibility is pending.", {"budget": 3000, "medicaidStatus": "Application pending"}),
    ("couple_different_needs", "Help with bathing", "My parents are both 82 and live in Las Vegas. My father needs help with bathing and dressing. My mother is independent. They want to live together in the same apartment.", {"relationship": "Parents", "budget": 12000}),
]
