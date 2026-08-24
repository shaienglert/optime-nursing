const { test, expect } = require('@playwright/test');

function questionnaireState() {
  return {
    relationship: 'Mom',
    ageGroup: '90-94',
    assistanceLevel: 'Help with bathing',
    memoryStatus: 'No',
    budget: 8000,
    referenceLocationValue: 'Las Vegas Valley',
    referenceAddress: '',
    notes: 'Mom needs help with bathing and dressing and enjoys classical music and social company.',
    humanIntelligenceV2: {
      personalityProfile: { communitySizePreference: '' },
      familyProfile: { socialInteractionNeed: '', griefSupportInterest: '', widowStatus: '' },
      socialProfile: { preferredSocialIntensity: '' },
      transitionRiskProfile: { attitudeTowardMove: '' },
      languageProfile: { preferredSpokenLanguage: '', nativeLanguage: '' },
      culturalProfile: { religionImportance: '' },
      scoringEngine: { adaptiveSignals: [] },
    },
  };
}

function profileFor(body) {
  const signals = body?.questionnaire_state?.humanIntelligenceV2?.scoringEngine?.adaptiveSignals || [];
  if (signals.length === 0) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        adaptive_questions: [{
          question_key: 'known-location',
          question: 'What city or area should we search in for Mom?',
          target_fact_key: 'market_location',
          information_gain: 'HIGH',
        }],
      },
    };
  }
  if (signals.length === 1) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        adaptive_questions: [{
          question_key: 'known-budget',
          question: 'What monthly housing-and-care budget are you comfortable with?',
          target_fact_key: 'monthly_budget',
          information_gain: 'HIGH',
        }],
      },
    };
  }
  if (signals.length === 2) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        adaptive_questions: [{
          question_key: 'new-fact',
          question: 'Would Mom prefer a quieter setting or a more active social environment?',
          target_fact_key: 'environment_preference_not_already_known',
          information_gain: 'HIGH',
          answer_options: ['Quieter', 'More active', 'No preference'],
        }],
      },
    };
  }
  return { decision_intelligence: { decision_readiness: 'READY', adaptive_questions: [] } };
}

const decisionResponse = {
  patient_needs_profile: { needs: [], need_tags: [], priority_parameter_ids: [] },
  result_count: 2,
  total_candidates_scored: 20,
  results: [
    {
      canonical_facility_id: 'A', facility_name: 'Verified Community', city: 'Las Vegas', state: 'NV',
      eligibility_status: 'ELIGIBLE', match_score: 90, patient_match_score: 90, match_band: 'STRONG_MATCH',
      matched_needs: [], unmet_verified_needs: [], unknown_critical_needs: [], preference_matches: [], evidence_certainty: 80,
      evidence_confidence: 80, quality_safety_score: 80, staffing_score: 75, capability_depth_score: 80,
      patient_relevant_outcomes_score: 80, practical_fit_score: 80, domain_breakdown: {},
      explanation: { why_matches: ['Bathing and dressing support is verified.'], needs_verification: ['Current availability should be confirmed.'], concerns: [], eligibility_reasons: [], availability_note: '', location_note: '' },
      parameter_badges: [], comparison_parameter_ids: [],
    },
    {
      canonical_facility_id: 'B', facility_name: 'Community Still Under Review', city: 'Henderson', state: 'NV',
      eligibility_status: 'POTENTIALLY_ELIGIBLE', match_score: 70, patient_match_score: 70, match_band: 'GOOD_MATCH',
      matched_needs: [], unmet_verified_needs: [], unknown_critical_needs: [], preference_matches: [], evidence_certainty: 45,
      evidence_confidence: 45, quality_safety_score: null, staffing_score: null, capability_depth_score: null,
      patient_relevant_outcomes_score: null, practical_fit_score: null, domain_breakdown: {},
      explanation: { why_matches: [], needs_verification: ['Medication management is not verified.'], concerns: [], eligibility_reasons: [], availability_note: '', location_note: '' },
      parameter_badges: [], comparison_parameter_ids: [],
    },
  ],
};

async function mockBackend(page) {
  await page.route('**/api/backend/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/decision-engine/patient-needs-profile')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profileFor(route.request().postDataJSON())) });
    }
    if (url.includes('/human-intelligence/adaptive-response')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    }
    if (url.includes('/decision-engine/recommend')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(decisionResponse) });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

async function seedQuestionnaire(page) {
  await page.addInitScript((state) => {
    window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify(state));
  }, questionnaireState());
}

test('AI silently consumes questionnaire facts and only asks genuinely missing information', async ({ page }) => {
  await mockBackend(page);
  await seedQuestionnaire(page);
  await page.goto('http://127.0.0.1:3000/adaptive-interview');

  await expect(page.getByText('What city or area should we search in for Mom?')).toHaveCount(0);
  await expect(page.getByText('What monthly housing-and-care budget are you comfortable with?')).toHaveCount(0);
  await expect(page.getByText('Would Mom prefer a quieter setting or a more active social environment?')).toBeVisible();

  await page.getByRole('button', { name: 'More active' }).click();
  await expect(page).toHaveURL(/\/results/);
});

test('results default view is readable and does not expose internal evidence jargon', async ({ page }) => {
  await mockBackend(page);
  await seedQuestionnaire(page);
  await page.goto('http://127.0.0.1:3000/results');

  await expect(page.getByRole('heading', { name: /The strongest options for Mom/i })).toBeVisible();
  await expect(page.getByText('Verified Community')).toBeVisible();
  await expect(page.getByText('Community Still Under Review')).toBeVisible();
  await expect(page.getByText('Meets verified must-haves')).toBeVisible();
  await expect(page.getByRole('link', { name: 'See detailed comparison' })).toBeVisible();
  await expect(page.getByText(/CMS Placeholder/i)).toHaveCount(0);
  await expect(page.getByText(/POTENTIALLY_ELIGIBLE/i)).toHaveCount(0);
  await expect(page.getByText(/^Not verified$/i)).toHaveCount(0);
});
