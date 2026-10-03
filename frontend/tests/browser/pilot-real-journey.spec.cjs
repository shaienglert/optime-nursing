const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

// Independent fixture oracle: every case below explicitly needs ADL and medication
// support. A ceiling below every such facility's price MUST produce no matches.
const fixtureEvidence = JSON.parse(zlib.gunzipSync(Buffer.from(fs.readFileSync(path.join(__dirname, '../../../database/synthetic_pilot/facility_parameter_evidence.json.gz.b64'), 'utf8'), 'base64'))).records;
const fixtureFacts = new Map();
for (const row of fixtureEvidence) {
  if (!fixtureFacts.has(row.canonical_facility_id)) fixtureFacts.set(row.canonical_facility_id, {});
  fixtureFacts.get(row.canonical_facility_id)[row.parameter_id] = row.value;
}
const minimumCarePrice = Math.min(...[...fixtureFacts.values()].filter(row => row.adl_support === 'YES' && row.medication_support === 'YES').map(row => row.current_price));

const scenarioStart = Number(process.env.OOMNIK_SCENARIO_START || 0);
const scenarioCount = Number(process.env.OOMNIK_SCENARIO_COUNT || 1);
const expectedCohort = Number(process.env.OOMNIK_EXPECTED_COHORT || 0);

// Golden personas. The answers are keyed by intake question id, validated against the live
// question graph by tests/golden-personas.test.ts (no browser), and written -- together
// with the oracle and the exact step sequence the graph produces -- to this fixture. The
// journey only replays it: no prompt patterns, no answers maintained here.
const PERSONAS = JSON.parse(fs.readFileSync(path.join(__dirname, '../../../backend/gold_examples/oomnik_golden_personas_v1.submissions.json'), 'utf8')).personas;

function scenarioFor(index) {
  const persona = PERSONAS[index];
  if (!persona) throw new Error(`No golden persona at index ${index}`);
  const answers = Object.fromEntries(persona.steps.filter((step) => step.answer !== null).map((step) => [step.id, step.answer]));
  const oracle = persona.oracle;
  return {
    persona,
    oracle,
    answers,
    id: persona.id,
    budget: oracle.budget,
    location: oracle.location,
    distance: oracle.distance,
    language: answers.language || 'English',
    medicalLanguage: answers.medicalLanguage || answers.language || 'English',
    diet: (answers.dietary || [])[0] || 'No restrictions / eats everything',
    futureCare: oracle.futureCare || answers.continuum || 'Preferred',
  };
}

/**
 * Replay a golden persona through the real intake, one question at a time.
 *
 * The question on screen is identified by its data-question-id, and answered from the
 * persona by that id and its kind. A question the persona has no answer for fails with
 * its id: the static validator should already have caught it, so reaching one here means
 * the browser shows a question the data model does not.
 */
async function answerInterview(page, scenario, maxSteps = 120) {
  const asked = [];
  for (let step = 0; step < maxSteps; step += 1) {
    if (/\/intake-confirmation(?:\?|$)/.test(page.url())) return asked;
    const summary = page.getByRole('heading', { name: /Here’s what I understood/i });
    if (await summary.isVisible().catch(() => false)) return asked;

    const heading = page.locator('main h1[data-question-id]').first();
    const visible = await heading.waitFor({ state: 'visible', timeout: 15_000 }).then(() => true).catch(() => false);
    if (!visible) {
      if (/\/intake-confirmation(?:\?|$)/.test(page.url()) || await summary.isVisible().catch(() => false)) return asked;
      throw new Error(`No intake question on screen after: ${asked.join(' > ')}`);
    }
    const id = await heading.getAttribute('data-question-id');
    const kind = await heading.getAttribute('data-question-kind');
    if (asked[asked.length - 1] === id) {
      await page.waitForURL(/\/intake-confirmation(?:\?|$)/, { timeout: 5_000 }).catch(() => {});
      if (/\/intake-confirmation(?:\?|$)/.test(page.url())) return asked;
      throw new Error(`Intake repeated question "${id}" without advancing`);
    }
    asked.push(id);
    const has = Object.prototype.hasOwnProperty.call(scenario.answers, id);
    const next = page.getByRole('button', { name: /^(Next →|See the summary →)$/ });
    if (!has) {
      const step = scenario.persona.steps.find((item) => item.id === id);
      if (step && !step.required) { await next.click(); continue; }
      throw new Error(`${scenario.id}: the browser asked "${id}", which the persona does not answer — run tests/golden-personas.test.ts`);
    }
    const value = scenario.answers[id];
    if (kind === 'single') {
      await page.getByRole('button', { name: String(value), exact: true }).click();
      continue; // a single choice advances on its own
    }
    if (kind === 'multi') {
      for (const option of value) await page.getByRole('button', { name: String(option), exact: true }).click();
    } else {
      const range = page.locator('main input[type="range"]');
      if (kind === 'number' && await range.count()) {
        await range.first().evaluate((el, v) => {
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(el, String(v));
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }, Number(value));
      } else {
        await page.locator('main input[type="text"], main input[type="number"], main textarea').first().fill(String(value));
      }
    }
    await next.click();
  }
  throw new Error('Intake did not reach the summary within the step budget');
}

test.describe('real synthetic-pilot customer journey', () => {
  test.setTimeout(900_000);

  for (let scenarioIndex = scenarioStart; scenarioIndex < scenarioStart + scenarioCount; scenarioIndex += 1) {
    const scenario = scenarioFor(scenarioIndex);
    const { oracle } = scenario;
    test(`${scenario.id} completes the real customer journey`, async ({ page }) => {
    page.setDefaultTimeout(15_000);
    const errors = [];
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });

    await page.goto('http://127.0.0.1:3000/intake', { waitUntil: 'networkidle' });

    const asked = await answerInterview(page, scenario);

    // The interview must ask one question at a time and never repeat itself.
    expect(new Set(asked).size).toBe(asked.length);
    expect(asked.length).toBeGreaterThan(20);
    // The browser must walk exactly the question graph the persona was validated against.
    expect(asked, `${scenario.id}: browser question sequence differs from the intake data model`).toEqual(scenario.persona.steps.map((step) => step.id));

    if (!/\/intake-confirmation(?:\?|$)/.test(page.url())) {
      await page.getByText('Yes — this reflects what I told Oomnik.').click();
      await page.getByRole('button', { name: 'Continue our conversation' }).click();
      await page.waitForURL(/\/(adaptive-interview|intake-confirmation)(?:\?|$)/, { timeout: 60_000 });
    }

    for (let turn = 0; turn < 25; turn += 1) {
      await page.waitForLoadState('domcontentloaded');
      const adaptivePrompt = await page.locator('main').innerText().catch(() => '');
      console.log('OOMNIK_ADAPTIVE_TURN', JSON.stringify({ scenario_id: scenario.id, turn, url: page.url(), prompt: adaptivePrompt.slice(0, 1200) }));
      const finalConfirmation = page.getByRole('button', { name: /I confirm—show recommendations/i });
      const continueReview = page.getByRole('button', { name: 'Continue our conversation', exact: true });
      let phase = 'LOADING';
      await expect.poll(async () => {
        const adaptive = /\/adaptive-interview(?:\?|$)/.test(page.url());
        const answer = page.getByLabel('Your answer');
        const option = page.locator('main section button').first();
        phase = await finalConfirmation.isVisible() && await finalConfirmation.isEnabled() ? 'READY'
          : await continueReview.isVisible() && await continueReview.isEnabled() ? 'CONTINUE_REVIEW'
          : adaptive && await answer.isVisible() && await answer.isEnabled() ? 'ANSWER'
          : adaptive && await option.isVisible() && await option.isEnabled() ? 'OPTION' : 'LOADING';
        return phase;
      }, { timeout: 60_000, message: 'Interview must expose a ready confirmation or a next action' }).not.toBe('LOADING');
      if (phase === 'READY') break;
      if (phase === 'CONTINUE_REVIEW') {
        await continueReview.click();
        continue;
      }
      // A runtime failure is not an interview option. Fail with the rendered
      // explanation instead of silently clicking Try again up to 25 times.
      const retry = page.getByRole('button', { name: 'Try again', exact: true });
      expect(await retry.count(), await page.locator('main').innerText()).toBe(0);
      const answerBox = page.getByLabel('Your answer');
      const continueButton = page.getByRole('button', { name: /^Continue$/ });
      if (await answerBox.count()) {
        await answerBox.fill(`Use the confirmed questionnaire facts: ${scenario.language} for daily life and social interaction, ${scenario.medicalLanguage} for medical discussions; budget $${scenario.budget} per month including all required care${oracle.couple ? ' and both residents, who must live together' : ''}; ${scenario.location} within ${scenario.distance} miles; ${scenario.diet === 'Kosher' ? 'kosher meals are required, a religious community is not required' : 'low sodium is a preference, not a mandatory clinical diet'}; future care ${scenario.futureCare.toLowerCase()}. No additional medical requirement beyond the questionnaire.`);
        await continueButton.click();
      } else {
        const offeredOption = page.locator('main section button').first();
        await expect(offeredOption).toBeVisible({ timeout: 30_000 });
        await offeredOption.click();
      }
      await page.waitForTimeout(500);
    }

    await expect(page.getByRole('heading', { name: /Please confirm what Oomnik understood/i })).toBeVisible({ timeout: 300_000 });
    const confirmRecommendations = page.getByRole('button', { name: /I confirm—show recommendations/i });
    await expect(confirmRecommendations, 'Needs profile must finish loading before confirmation').toBeEnabled({ timeout: 300_000 });
    const recommendationResponse = page.waitForResponse(
      (response) => response.url().includes('/decision-engine/recommendations')
        && response.request().method() === 'POST',
      { timeout: 720_000 },
    );
    await confirmRecommendations.click();
    await expect(page).toHaveURL(/\/results/, { timeout: 180_000 });

    const response = await recommendationResponse;
    expect(response.status()).toBe(200);
    const payload = await response.json();
    fs.mkdirSync(path.join(process.cwd(), 'pilot-results'), { recursive: true });
    fs.writeFileSync(path.join(process.cwd(), 'pilot-results', `${scenario.id}-decision.json`), `${JSON.stringify(payload, null, 2)}\n`);
    const results = payload.results || [];
    const dynamicModel = payload.decision_intelligence.dynamic_preference_model;
    expect(dynamicModel.preference_authority, JSON.stringify(payload.decision_intelligence.human_intelligence.semantic_ai)).toBe('QUOTED_STATEMENT_TRACES');
    expect(dynamicModel.preferences.every(pref => pref.source === 'semantic_ai.statements')).toBe(true);
    expect(dynamicModel.preferences.every(pref => !['Preference', 'Preferred', 'Nice to have', 'No preference'].includes(pref.client_expression))).toBe(true);
    expect(new Set(dynamicModel.preferences.map(pref => pref.preference_id)).size).toBe(dynamicModel.preferences.length);
    for (const item of results) {
      for (const preference of dynamicModel.preferences) {
        const assessment = item.dynamic_preference_fit.assessments.find(entry => entry.preference_id === preference.preference_id);
        expect(assessment).toBeDefined();
        if (assessment.status === 'UNKNOWN') {
          expect(assessment.provider_question_if_unknown).toContain(preference.client_expression);
          expect(assessment.provider_question_if_unknown).toContain(preference.semantic_meaning);
        }
      }
    }
    if (scenario.answers.activityImportance === 'Preference') {
      for (const activity of scenario.answers.activities || []) {
        expect(dynamicModel.preferences.filter(pref => pref.client_expression === activity).length,
          scenario.id + ': actual activity preference must have exactly one source obligation: ' + activity
            + ' | preferences=' + JSON.stringify(dynamicModel.preferences)
            + ' | statements=' + JSON.stringify(payload.decision_intelligence.human_intelligence.semantic_ai.result?.statements)).toBe(1);
      }
    }

    if (scenario.answers.nearbyImportance === 'Nice to have') {
      for (const place of scenario.answers.nearbyPlaces || []) {
        expect(dynamicModel.preferences.some(pref => pref.client_expression === place)).toBe(true);
      }
    }

    console.log('OOMNIK_PILOT_GATE_DIAGNOSTIC', JSON.stringify({
      scenario_id: scenario.id, budget: scenario.budget, result_count: results.length,
      must_eligible_count: payload.must_eligible_count,
      must_pending_verification_count: payload.must_pending_verification_count,
      canonical_decision_state: payload.decision_intelligence?.canonical_decision_state,
      must_gate: payload.decision_intelligence?.must_gate,
      semantic_facility_requirements: payload.decision_intelligence?.semantic_facility_requirements,
      needs: payload.patient_needs_profile?.needs?.map(need => ({ id: need.parameter_id, level: need.requirement_level, value: need.desired_value })),
    }));
    const classifiedCohort = payload.candidate_discovery?.total_facilities_classified;
    if (classifiedCohort !== undefined) expect([expectedCohort, 500]).toContain(classifiedCohort);
    expect(payload.total_candidates_scored).toBeGreaterThan(0);
    if (expectedCohort) expect(payload.total_candidates_scored).toBeLessThanOrEqual(expectedCohort);
    // Whether each oracle requirement became a MUST is graded by
    // backend/tests/test_golden_persona_decisions.py, from the same persona, against the
    // engine's real parameter ids. The browser checks the flow and the universal invariants.
    const budgetNeed = payload.patient_needs_profile.needs.find(item => item.parameter_id === 'current_price');
    expect(Number(budgetNeed.desired_value)).toBe(Number(scenario.budget));
    expect(Number.isFinite(minimumCarePrice)).toBe(true);
    // A verified option may be shown up to ten percent over the stated budget, labelled as
    // an exception and ranked after every in-budget option. Nothing further over is shown.
    // Golden contract: budget is strict first. Expansion is capped at +10% and
    // may only fill a shortlist after otherwise-qualified in-budget candidates.
    const expectedBudget = oracle.budget;
    expect(scenario.budget, `${scenario.id} fixture budget drifted from golden oracle`).toBe(expectedBudget);
    const budgetCeiling = expectedBudget * 1.1;
    if (budgetCeiling < minimumCarePrice) {
      expect(results).toHaveLength(0);
      await expect(page.getByText('I don’t have a verified recommendation to show yet. Missing information is still being distinguished from a confirmed mismatch.')).toBeVisible();
    } else if (results.length === 0) {
      // A price under budget does not verify another mandatory facility claim.
      // Semantic AI may correctly identify dietary safety or another client MUST
      // for which the pilot has no evidence. Require an explicit pending gate,
      // never silently call the empty result an affordable recommendation.
      expect(payload.pending_evidence_summary?.candidate_count).toBeGreaterThan(0);
      expect(payload.decision_intelligence?.canonical_decision_state?.must).toBe('PENDING');
      await expect(page.getByText(/communities need more evidence before I can recommend them/i)).toBeVisible();
      await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
    } else {
      await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
    }
    for (const item of results) {
      const price = Number(item.starting_monthly_price);
      if (!Number.isFinite(price)) continue;
      expect(price, `${item.canonical_facility_id} exceeds the ten-percent budget ceiling`).toBeLessThanOrEqual(budgetCeiling);
      expect(Boolean(item.budget_exception), `${item.canonical_facility_id} budget exception label`).toBe(price > scenario.budget);
    }
    const firstException = results.findIndex((item) => item.budget_exception);
    if (firstException >= 0) expect(results.slice(firstException).every((item) => item.budget_exception), 'in-budget options rank ahead of over-budget exceptions').toBe(true);
    // Universal golden invariants: a visible recommendation must have passed the
    // governed MUST gate; UNKNOWN evidence never becomes PASS, distance is a hard
    // limit when measurable, and no result may exceed the explicit +10% ceiling.
    expect(results.every((item) => item.must_eligibility === 'MUST_ELIGIBLE')).toBe(true);
    expect(results.every((item) => (item.client_intent_fit?.hard_gate || '').toUpperCase() === 'PASS')).toBe(true);
    expect(results.every((item) => (item.client_intent_fit?.must_unknown || []).length === 0)).toBe(true);
    expect(results.every((item) => item.synthetic_pilot === true)).toBe(true);
    expect(results.every((item) => String(item.canonical_facility_id || '').startsWith('PILOT-NV-'))).toBe(true);
    expect(errors.filter((message) => !/favicon/i.test(message))).toEqual([]);

    console.log('OOMNIK_REAL_PILOT_RESULT_BEGIN');
    const runResult = {
      scenario_id: scenario.id,
      scenario,
      total_candidates_scored: payload.total_candidates_scored,
      result_count: payload.result_count,
      candidate_discovery: payload.candidate_discovery,
      market_coverage_notice: payload.market_coverage_notice,
      top_results: results.slice(0, 10).map((item) => ({
        canonical_facility_id: item.canonical_facility_id,
        facility_name: item.facility_name,
        eligibility_status: item.eligibility_status,
        patient_match_score: item.patient_match_score,
        quality_safety_score: item.quality_safety_score,
        staffing_score: item.staffing_score,
        capability_depth_score: item.capability_depth_score,
        practical_fit_score: item.practical_fit_score,
        rank_position: item.rank_position,
        rank_tie_status: item.rank_tie_status,
      })),
    };
    fs.mkdirSync(path.join(process.cwd(), 'pilot-results'), { recursive: true });
    fs.writeFileSync(path.join(process.cwd(), 'pilot-results', `${scenario.id}.json`), `${JSON.stringify(runResult, null, 2)}\n`);
    console.log(JSON.stringify(runResult));
    console.log('OOMNIK_REAL_PILOT_RESULT_END');
    });
  }
});
