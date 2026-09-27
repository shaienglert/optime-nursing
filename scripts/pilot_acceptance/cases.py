"""The acceptance cases, and what a correct answer to each one looks like.

Every case states its expectation as something the pilot data can settle on its own, so a
run is graded against the catalog rather than against the engine's opinion of itself.

`never_archetypes` is the load-bearing half. Saying a dementia case should reach memory
care is easy; the failures that matter are the opposite kind -- a family asking for help
with bathing routed into skilled nursing, or mild forgetfulness routed into a locked
memory unit. Those are the ones that cost a family money and independence.

`questionnaire` carries answers to the client-owned questions a real interview would ask
for that situation (Medicare for a post-hospital case, for instance). Without them the
engine correctly refuses to expose any facility -- `identities_hidden_pending_client_input`
-- and the case cannot complete, which is a gap in the test, not in the product.
"""

BASE = {"distanceFromFamily": "Balanced location"}

# The eight archetypes in the pilot catalog, 25 communities each.
INDEPENDENT = {"INDEPENDENT_LIVING", "ACTIVE_ADULT_55_PLUS"}
RESIDENTIAL_CARE = {"ASSISTED_LIVING_RFG", "SMALL_GROUP_HOME", "CONTINUING_CARE"}
CLINICAL = {"SKILLED_NURSING", "REHABILITATION"}
MEMORY = {"MEMORY_CARE"}

CASES = {
    "01_independent_social": {
        "title": "Independent, wants social life",
        "questionnaire": {**BASE, "relationship": "Mom", "ageGroup": "75-79", "assistanceLevel": "Fully independent", "memoryStatus": "No", "budget": 4500},
        "query": "My mother is 77, fully independent and mentally sharp, recently widowed and lonely. She lives in Las Vegas and wants an active community with lots of social activities. Budget about $4,500 a month.",
        "min_recommendations": 1,
        "any_of_archetypes": INDEPENDENT,
        # Nobody who is fully independent should be shown a nursing home or a locked unit.
        "never_archetypes": CLINICAL | MEMORY,
    },
    "02_bathing_dressing": {
        "title": "Help with bathing and dressing only",
        "questionnaire": {**BASE, "relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 6500},
        "query": "My father is 84, lives in Las Vegas, is mentally alert and walks on his own. He needs help with bathing and dressing. No dementia.",
        "min_recommendations": 1,
        "any_of_archetypes": RESIDENTIAL_CARE,
        "never_archetypes": CLINICAL | MEMORY,
    },
    "03_falls_transfers": {
        "title": "Falls, needs help with transfers",
        "questionnaire": {**BASE, "relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 7000},
        "query": "My mother is 86 in Las Vegas. She has fallen twice this year, uses a walker, and needs one person to help her get in and out of bed and the shower. No dementia.",
        "min_recommendations": 1,
        "any_of_archetypes": RESIDENTIAL_CARE,
        "never_archetypes": MEMORY,
    },
    "04_mild_forgetfulness": {
        "title": "Mild forgetfulness, no dementia diagnosis",
        "questionnaire": {**BASE, "relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Help with medications", "memoryStatus": "Mild forgetfulness", "budget": 5500},
        "query": "My father is 82 in Las Vegas. He sometimes forgets appointments and needs reminders to take his pills, but he has no dementia diagnosis and does not wander.",
        "min_recommendations": 1,
        "any_of_archetypes": RESIDENTIAL_CARE,
        # Forgetting an appointment is not a dementia diagnosis. Routing this family into
        # memory care would sell them a locked unit they never asked for.
        "never_archetypes": MEMORY | CLINICAL,
    },
    "05_dementia_wandering": {
        "title": "Dementia with wandering",
        "questionnaire": {**BASE, "relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Help with bathing, 24/7 support required", "memoryStatus": "Significant memory issues", "budget": 8000},
        "query": "My mother has Alzheimer's and wanders at night; she tried to leave the house twice. She lives in Las Vegas and needs a secure memory care setting with 24/7 supervision.",
        "min_recommendations": 1,
        "any_of_archetypes": MEMORY,
        "never_archetypes": INDEPENDENT,
    },
    "06_rehab_after_hospital": {
        "title": "Rehabilitation after hospitalization",
        # Medicare and timing are what a real interview asks a post-hospital family; the
        # engine withholds every facility until they are answered.
        "questionnaire": {**BASE, "relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 9000, "medicareStatus": "Original Medicare", "moveTiming": "Within 30 days"},
        "query": "My father had hip surgery last week and is in the hospital in Las Vegas. He needs physical and occupational therapy for about six weeks before he can go home. No dementia.",
        "min_recommendations": 1,
        "any_of_archetypes": CLINICAL | {"CONTINUING_CARE"},
        "never_archetypes": INDEPENDENT | MEMORY,
    },
    "07_dialysis": {
        "title": "Dialysis three times a week",
        "questionnaire": {**BASE, "relationship": "Dad", "ageGroup": "75-79", "assistanceLevel": "Help with medications", "memoryStatus": "No", "budget": 7000},
        "query": "My father is on dialysis three times a week in Las Vegas and needs transportation to the dialysis center. He is mentally alert.",
        "min_recommendations": 1,
        "never_archetypes": MEMORY | INDEPENDENT,
    },
    "08_oxygen_wound": {
        "title": "Continuous oxygen and a wound",
        "questionnaire": {**BASE, "relationship": "Mom", "ageGroup": "85-89", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 8000},
        "query": "My mother in Las Vegas uses oxygen continuously for COPD and has a pressure wound on her heel that needs daily dressing changes.",
        "min_recommendations": 1,
        "never_archetypes": INDEPENDENT | MEMORY,
    },
    "09_low_budget_medicaid_pending": {
        "title": "Low budget, Medicaid pending",
        "questionnaire": {**BASE, "relationship": "Mom", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 3000},
        "query": "My mother in Las Vegas needs help with bathing and dressing. She can only afford about $3,000 a month and her Medicaid application is pending.",
        # No community in the pilot that provides ADL support costs $3,000 or less. The
        # right answer is to say so, not to present something unaffordable as a fit.
        "expect_no_match": True,
        "requires_market_coverage_notice": True,
    },
    "10_couple_different_needs": {
        "title": "Couple with different needs",
        "questionnaire": {**BASE, "relationship": "Parents", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "budget": 11000},
        "query": "My parents are both 82 and live in Las Vegas. My father needs help with bathing and dressing after a stroke; my mother is fully independent. They want to live together in the same apartment.",
        "min_recommendations": 1,
        "never_archetypes": MEMORY,
        "requires_couple_accepting": True,
    },
}
