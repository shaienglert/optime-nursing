// Fictional acceptance cases for the isolated 200-facility pilot only.
const scenarios = {
  "independent_social": {
    "story": "My mother is 77, fully independent and lonely after losing her husband. She wants social activities and meals in a large community in Las Vegas. She needs no help with bathing, dressing or medication. Monthly budget $5000.",
    "budget": 5000,
    "assistance": "Fully independent",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "bathing_dressing": {
    "story": "My mother is 86 and needs daily help bathing and dressing. She walks independently and has no dementia. We need assisted living in Las Vegas within 30 days. Monthly budget $6500.",
    "budget": 6500,
    "assistance": "Help with bathing, Help with dressing",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "falls_transfers": {
    "story": "My father is 83, has fallen three times this month and needs one-person assistance transferring from bed to chair and into the shower. He uses a walker. No dementia. Las Vegas, monthly budget $7500.",
    "budget": 7500,
    "assistance": "Help with bathing",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "mild_memory_reminders": {
    "story": "My father is 78, forgets appointments and needs reminders to take pills, but takes them himself. No dementia diagnosis and no complex medication management. He dresses and bathes independently. Las Vegas monthly budget $6000.",
    "budget": 6000,
    "assistance": "Light assistance",
    "memory": "Occasionally forgetful",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "dementia_wandering": {
    "story": "My mother is 87, has diagnosed dementia and wanders outside. She needs a secure memory care unit with supervision around the clock, help dressing and medication assistance. She has no skilled nursing procedures. Las Vegas monthly budget $8500.",
    "budget": 8500,
    "assistance": "Daytime supervision",
    "memory": "Significant memory issues",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS",
      "SECURE_MEMORY_CARE_CONFIRMED"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ]
  },
  "post_surgery_rehab": {
    "story": "My father is 82 and needs short-term rehabilitation after hip replacement, physical and occupational therapy. He has Original Medicare. Discharge is in five days. No swallowing or speech problem, no dementia. Las Vegas. Private-pay budget up to $8000 monthly if needed.",
    "budget": 8000,
    "assistance": "Light assistance",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "dialysis": {
    "story": "My father is 76 and receives dialysis three times every week at his existing Las Vegas dialysis center. He needs reliable transport to and from treatment and light assistance with daily activities. No dementia. Monthly budget $7500.",
    "budget": 7500,
    "assistance": "Light assistance",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "oxygen_wound": {
    "story": "My father is 81 and uses oxygen by nasal cannula, not a ventilator and no tracheostomy. He has a wound requiring daily skilled dressing changes and help bathing. Las Vegas monthly budget $9500.",
    "budget": 9500,
    "assistance": "Help with bathing",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "medicaid_pending": {
    "story": "My mother is 84 and needs help bathing and dressing. Her budget is $3000 monthly and Medicaid is pending, not approved. We cannot pay more. No dementia. We need care in Las Vegas.",
    "budget": 3000,
    "assistance": "Help with bathing, Help with dressing",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  },
  "couple_no_dementia": {
    "story": "My parents are 81 and 83 and want to live together in the same apartment in Las Vegas. My father needs help bathing, my mother is fully independent. Neither has dementia. They do not want a CCRC entrance-fee contract. Their combined monthly budget is $11000.",
    "budget": 11000,
    "assistance": "Help with bathing",
    "memory": "No",
    "expectedMustKeys": [
      "LICENSE_CURRENTLY_VALID",
      "LAS_VEGAS",
      "COUPLE_CORESIDENCE"
    ],
    "requiredVisibleGaps": [
      "availability",
      "pricing"
    ],
    "forbiddenMustKeys": [
      "SECURE_MEMORY_CARE_CONFIRMED"
    ]
  }
};

function answerFor(question, scenario) {
  const q = question.toLowerCase();
  if (/medicare/.test(q)) return /original medicare/i.test(scenario.story) ? 'Original Medicare' : 'Not sure';
  if (/medicaid/.test(q)) return /medicaid.*pending/i.test(scenario.story) ? 'Medicaid pending, not approved' : 'Not sure';
  if (/budget|afford|monthly|cost/.test(q)) return 'Up to $' + scenario.budget + ' per month';
  if (/entrance fee|ccrc/.test(q)) return /do not want a ccrc/i.test(scenario.story) ? 'No entrance fee contract' : 'Not sure';
  if (/city|location|area|market/.test(q)) return 'Las Vegas Valley';
  if (/memory|dementia|cognitive|wander/.test(q)) return scenario.memory + '. Use the facts in the original story.';
  if (/move timing|when.*move|how soon/.test(q)) return /five days/.test(scenario.story) ? 'Discharge in five days' : /30 days/.test(scenario.story) ? 'Within 30 days' : 'Not sure';
  if (/care|bathing|dressing|medication|support|therapy|rehab/.test(q)) return scenario.story;
  return 'Not sure';
}
module.exports = { scenarios, answerFor };
