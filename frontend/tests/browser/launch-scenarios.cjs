const scenarios = {
  independent_mom: {
    story: 'My mother is 82 and fully independent. She lives in Las Vegas, enjoys music, gardening and regular social activities, speaks Hebrew and English, and wants a community with a clear future-care path. Her budget is up to $8,000 a month.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  memory_mom: {
    story: "My mother is 84 and has advancing Alzheimer's disease. She needs constant supervision, help with bathing, dressing, toileting and medication management, and she sometimes wanders at night. She lives in the Las Vegas Valley. She needs a secure memory-care setting with 24/7 staff. Her budget is about $5,000 per month and Medicaid eligibility is pending.",
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'SECURE_MEMORY_CARE_CONFIRMED', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    forbiddenMustKeys: ['SEMANTIC_FUTURE_CARE_PATH'],
    forbiddenVerifiedFacilities: ['Revel Vegas', 'STEWART PINES II SENIOR APTS'],
    requiredVisibleGaps: ['availability', 'pricing', 'medicaid'],
  },
  post_stroke_dad: {
    story: 'My father is 82 and recently had a stroke. He needs hands-on help with bathing, dressing and transfers, medication management, and PT, OT and speech therapy. We need the Las Vegas Valley and can spend up to $17,000 per month. He must have gluten-free meals.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  rehab_couple: {
    story: 'My parents want to remain together in Las Vegas. My father is recovering from spinal surgery and needs rehabilitation and temporary help with bathing and dressing for about three months; my mother is independent. They want one community that can support both of them.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability'],
  },
  independent_low_budget: {
    story: 'I am looking for my independent 76-year-old aunt in the Las Vegas Valley. She wants a social community and transportation, has a strict $3,500 monthly budget, and may apply for Medicaid later.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS'],
    requiredVisibleGaps: ['availability', 'pricing', 'medicaid'],
  },
  parkinsons_support: {
    story: 'My 79-year-old husband has Parkinson\'s. He is mentally alert but needs help with dressing, showering and medication timing, uses a walker, and needs a safe layout in the Las Vegas Valley. Our budget is $7,000 per month.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  dialysis_transport: {
    story: 'My 81-year-old father needs assistance with daily activities and transportation to dialysis three times a week. He needs medication support, lives near Henderson, and has a $7,500 monthly budget.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  hospice_family: {
    story: 'My mother is 88 and needs substantial daily assistance and medication management. Her doctor is discussing hospice. We need a calm Las Vegas Valley community that can coordinate with hospice and keep family closely involved. Budget is $9,000 monthly.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  celiac_assisted: {
    story: 'My 83-year-old mother needs help bathing and dressing but has no dementia. She has celiac disease and requires reliable gluten-free food with cross-contact precautions. We need Las Vegas and can spend $8,000 per month.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
  spanish_speaking_dad: {
    story: 'My 80-year-old father speaks mainly Spanish. He needs light daily assistance and medication reminders, wants frequent family visits and an active social setting in the Las Vegas Valley, with a budget of $6,000 per month.',
    expectedMustKeys: ['LICENSE_CURRENTLY_VALID', 'LAS_VEGAS', 'ADL_SUPPORT_AVAILABLE', 'MEDICATION_SUPPORT_AVAILABLE'],
    requiredVisibleGaps: ['availability', 'pricing'],
  },
};

function answerFor(question, scenario) {
  const text = question.toLowerCase();
  if (/city|area|location|market/.test(text)) return 'Las Vegas Valley';
  if (/budget|cost|monthly|afford|medicaid/.test(text)) return scenario.story.match(/\$[\d,]+[^.]*|Medicaid[^.]*/i)?.[0] || 'Use the budget and payment information in the story.';
  if (/memory|cognitive|dementia|alzheimer|wander/.test(text)) return /alzheimer|dementia|wander/i.test(scenario.story) ? 'Use the diagnosed memory and safety needs in the story.' : 'No diagnosed dementia unless the story says otherwise.';
  if (/care|support|adl|bathing|dressing|toilet|medication|supervision|rehab|therapy/.test(text)) return 'Use all care, medication, mobility and rehabilitation requirements stated in the story.';
  if (/safety|secure|night/.test(text)) return 'Use the safety requirements stated in the story; do not infer any additional requirement.';
  return 'No additional preference beyond the facts and requirements already described.';
}

module.exports = { scenarios, answerFor };
