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
    questionnaireCompletion: {
      mandatoryComplete: true,
      conditionalFollowUpsComplete: true,
      clientSummaryConfirmed: false,
      confirmedAt: '',
    },
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
  const interviewState = (complete = false) => ({
    authoritative: true,
    client: complete ? 'COMPLETE' : 'INCOMPLETE',
    phase: complete ? 'MUST_EVALUATION' : 'CLIENT_INPUT_REQUIRED',
    can_show_recommendations: false,
  });
  if (signals.length === 0) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        canonical_decision_state: interviewState(),
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
  return {
    intake_profile_id: 'test-server-profile',
    needs: [{ parameter_id: 'adl', need_text: 'Bathing assistance', requirement_level: 'REQUIRED' }],
    decision_intelligence: {
      decision_readiness: 'READY',
      canonical_decision_state: interviewState(true),
      adaptive_questions: [],
    },
  };
}

const decisionResponse = {
  decision_intelligence: {
    canonical_decision_state: { authoritative: true, client: 'COMPLETE', system: 'READY' },
  },
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
      ai_ranking: { reason: 'Medication support is not verified.', information_deficits: ['ADL support is not verified.'] },
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

async function mockBackend(page, recommendations = decisionResponse, profileFactory = profileFor) {
  await page.route('**/api/backend/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/decision-engine/patient-needs-profile')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profileFactory(route.request().postDataJSON())) });
    }
    if (url.includes('/human-intelligence/adaptive-response')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    }
    if (url.includes('/decision-engine/recommend')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(recommendations) });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

async function seedQuestionnaire(page) {
  await page.addInitScript((state) => {
    window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify(state));
  }, questionnaireState());
}

test('invalid AI packet does not hide a canonical budget recovery question', async ({ page }) => {
  await mockBackend(page, decisionResponse, body => {
    const profile = profileFor(body);
    if (body?.questionnaire_state?.humanIntelligenceV2?.scoringEngine?.adaptiveSignals?.length) return profile;
    profile.decision_intelligence.canonical_decision_state.system = 'BLOCKED';
    profile.decision_intelligence.adaptive_questions = [];
    profile.decision_intelligence.human_intelligence = {
      semantic_ai: { enabled: true, status: 'FAILED', error: 'SEMANTIC_AI_READY_WITH_MISSING_MINIMUM_DIMENSIONS' },
      readiness_guardian: { selected_fact_key: 'monthly_budget', fallback_reason: 'SEMANTIC_AI_UNAVAILABLE' },
      adaptive_questions: [{ question_key: 'budget-recovery', question: 'What is your monthly budget?',
        target_fact_key: 'monthly_budget', question_owner: 'DETERMINISTIC_CANONICAL_FALLBACK', answer_options: ['Not sure'] }],
    };
    return profile;
  });
  await seedQuestionnaire(page);
  await page.goto('http://127.0.0.1:3000/adaptive-interview');
  await expect(page.getByText('What is your monthly budget?', { exact: true })).toBeVisible();
  await expect(page.getByText(/We could not verify our understanding/)).toHaveCount(0);
  await page.getByRole('button', { name: 'Not sure', exact: true }).click();
  await expect(page).toHaveURL(/\/intake-confirmation/);
  const saved = await page.evaluate(() => JSON.parse(sessionStorage.getItem('optime.questionnaire.session')));
  expect(saved.budget).toBe(0);
  expect(saved.humanIntelligenceV2.scoringEngine.adaptiveSignals[0].answer).toBe('Not sure');
});

test('server-owned intake asks only the missing question and preserves explicit answers', async ({ page }) => {
  await mockBackend(page);
  await seedQuestionnaire(page);
  await page.goto('http://127.0.0.1:3000/adaptive-interview');

  await expect(page.getByText('What city or area should we search in for Mom?')).toHaveCount(0);
  await expect(page.getByText('What monthly housing-and-care budget are you comfortable with?')).toHaveCount(0);
  await expect(page.getByText('Would Mom prefer a quieter setting or a more active social environment?')).toBeVisible();

  await page.getByRole('button', { name: 'More active' }).click();
  await expect(page).toHaveURL(/\/intake-confirmation\?next=/);
  await expect(page.getByRole('heading', { name: /Please confirm what Oomnik understood/i })).toBeVisible();
  await expect(page.getByText('Bathing assistance', { exact: true })).toBeVisible();
  const recommendations = page.waitForRequest(request => request.url().includes('/decision-engine/recommendations'));
  await page.getByRole('button', { name: /I confirm—show recommendations/i }).click();
  await expect(page).toHaveURL(/\/results/);
  expect(new URL(page.url()).search).toBe('');
  expect((await recommendations).postDataJSON().intake_profile_id).toBe('test-server-profile');
});

test('results default view is readable and does not expose internal evidence jargon', async ({ page }) => {
  await mockBackend(page);
  const confirmed = questionnaireState();
  confirmed.questionnaireCompletion.clientSummaryConfirmed = true;
  confirmed.questionnaireCompletion.confirmedAt = '2026-09-17T00:00:00.000Z';
  await page.addInitScript((state) => {
    window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify(state));
  }, confirmed);
  await page.goto('http://127.0.0.1:3000/results');

  await expect(page.getByRole('heading', { name: /Here’s where I’d start for Mom/i })).toBeVisible();
  await expect(page.getByText('Verified Community')).toBeVisible();
  await expect(page.getByText('Community Still Under Review')).toBeVisible();
  await expect(page.getByText('Meets verified must-haves')).toBeVisible();
  await expect(page.getByText('Bathing and dressing support is verified.')).toBeVisible();
  await expect(page.getByText('Medication support is not verified.')).toHaveCount(0);
  await expect(page.getByText('ADL support is not verified.')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'See detailed comparison' })).toBeVisible();
  await expect(page.getByText(/CMS Placeholder/i)).toHaveCount(0);
  await expect(page.getByText(/POTENTIALLY_ELIGIBLE/i)).toHaveCount(0);
  await expect(page.getByText(/^Not verified$/i)).toHaveCount(0);
});

test('price research is visible without pretending it is a recommendation', async ({ page }) => {
  await mockBackend(page, {
    ...decisionResponse, results: [], result_count: 0,
    price_research_candidates: [{ canonical_facility_id: 'price-only', facility_name: 'Research Community',
      status: 'PRICE_NOT_VERIFIED_NOT_A_RECOMMENDATION', passed_requirement_count: 3 }],
  });
  const confirmed = questionnaireState();
  confirmed.questionnaireCompletion.clientSummaryConfirmed = true;
  await page.addInitScript(state => window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify(state)), confirmed);
  await page.goto('http://127.0.0.1:3000/results');
  await expect(page.getByRole('heading', { name: 'Price not verified — not a recommendation' })).toBeVisible();
  await expect(page.getByText('Research Community', { exact: true })).toBeVisible();
  await expect(page.getByText(/We cannot confirm affordability/)).toBeVisible();
  await expect(page.getByText('Meets verified must-haves')).toHaveCount(0);
  await expect(page.getByText(/obtain a current written quote/)).toBeVisible();
});


test('results follow-up preserves the answer and returns to confirmation', async ({ page }) => {
  await mockBackend(page);
  const confirmed = questionnaireState();
  confirmed.questionnaireCompletion.clientSummaryConfirmed = true;
  await page.addInitScript((state) => {
    window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify(state));
  }, confirmed);
  await page.route('**/api/backend/decision-engine/recommendations', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      ...decisionResponse,
      decision_intelligence: profileFor({}).decision_intelligence,
    }) });
  });
  await page.goto('http://127.0.0.1:3000/results');
  await expect(page.getByRole('heading', { name: 'One more detail before we recommend places' })).toBeVisible();
  await expect(page.getByText('Would Mom prefer a quieter setting or a more active social environment?')).toBeVisible();
  await expect(page.getByText('Verified Community', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'More active', exact: true }).click();
  await expect(page).toHaveURL(/\/intake-confirmation\?next=/);
  const persisted = await page.evaluate(() => JSON.parse(window.sessionStorage.getItem('optime.questionnaire.session')));
  expect(persisted.notes).toBe(confirmed.notes);
  expect(persisted.questionnaireCompletion.clientSummaryConfirmed).toBe(false);
  expect(persisted.humanIntelligenceV2.scoringEngine.adaptiveSignals).toEqual(expect.arrayContaining([
    expect.objectContaining({ questionKey: 'new-fact', answer: 'More active' }),
  ]));
});

test('direct adaptive-interview access is blocked until the structured questionnaire is complete', async ({ page }) => {
  await mockBackend(page);
  await page.addInitScript(() => {
    window.sessionStorage.setItem('optime.questionnaire.session', JSON.stringify({
      relationship: '', ageGroup: '', assistanceLevel: '', memoryStatus: '', budget: 0,
      referenceLocationValue: '', referenceAddress: '', notes: '',
      humanIntelligenceV2: {
        personalityProfile: { communitySizePreference: '' },
        familyProfile: { socialInteractionNeed: '', griefSupportInterest: '', widowStatus: '' },
        socialProfile: { preferredSocialIntensity: '' },
        transitionRiskProfile: { attitudeTowardMove: '' },
        languageProfile: { preferredSpokenLanguage: '', nativeLanguage: '' },
        culturalProfile: { religionImportance: '' },
        scoringEngine: { adaptiveSignals: [] },
      },
    }));
  });

  await page.goto('http://127.0.0.1:3000/adaptive-interview');
  await expect(page).toHaveURL(/\/intake$/);
  await expect(page.getByRole('heading', { name: 'Who are we finding the right place for?' })).toBeVisible();
  await expect(page.getByRole('heading')).toHaveCount(1);
  await expect(page.getByText('Is there any ongoing medical care the community would need to provide or coordinate?')).toHaveCount(0);

  await page.getByRole('button', { name: 'Mom', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'About how old are they?' })).toBeVisible();
  await expect(page.getByRole('heading')).toHaveCount(1);
});
