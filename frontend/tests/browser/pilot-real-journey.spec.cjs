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

// Golden acceptance oracle: these cases intentionally cover distinct decision contracts.
// They replace accidental combinatorial variation with explicit expected behavior.
const GOLDEN_ORACLE = {
  "pilot-001": { care: ["INDEPENDENT_LIVING","ASSISTED_LIVING"], forbidden: ["MEMORY_CARE_ONLY","SKILLED_NURSING_ONLY","REHABILITATION_ONLY"], budget: 5000, location: "Las Vegas", distance: "10", futureCare: "Preferred" },
  "pilot-002": { care: ["ASSISTED_LIVING","CONTINUING_CARE"], required: ["adl_support","medication_support"], budget: 6000, location: "Henderson", distance: "10", availability: "REQUIRED" },
  "pilot-003": { care: ["MEMORY_CARE"], required: ["memory_care","wandering_safety"], forbidden: ["INDEPENDENT_LIVING"], budget: 7000, location: "Las Vegas", distance: "20" },
  "pilot-004": { care: ["REHABILITATION","SKILLED_NURSING"], required: ["rehabilitation"], forbidden: ["INDEPENDENT_LIVING","MEMORY_CARE_ONLY"], budget: 7000, location: "Las Vegas", distance: "20" },
  "pilot-005": { care: ["ASSISTED_LIVING","CONTINUING_CARE"], required: ["couple_coresidence","adl_support"], budget: 8000, location: "Henderson", distance: "20", couple: true },
  "pilot-006": { care: ["ASSISTED_LIVING","SMALL_GROUP_HOME"], required: ["adl_support","medicaid_pathway"], budget: 3000, location: "Las Vegas", distance: "30", medicaid: "REQUIRED" },
  "pilot-007": { care: ["ASSISTED_LIVING","CONTINUING_CARE"], required: ["adl_support","kosher"], preferred: ["hebrew"], budget: 6500, location: "Las Vegas", distance: "30" },
  "pilot-008": { care: ["INDEPENDENT_LIVING","ASSISTED_LIVING"], forbidden: ["MEMORY_CARE_ONLY"], preferred: ["social_fit","nearby_places"], budget: 5000, location: "Las Vegas", distance: "30" },
  "pilot-009": { care: ["SKILLED_NURSING","ASSISTED_LIVING"], required: ["dialysis","wound_care"], budget: 7500, location: "Las Vegas", distance: "20" },
  "pilot-010": { care: ["CONTINUING_CARE"], required: ["continuum_of_care"], forbidden: ["INDEPENDENT_LIVING_ONLY","ASSISTED_LIVING_ONLY"], budget: 9900, location: "Las Vegas", distance: "50", futureCare: "Required" },
};


function scenarioFor(index) {
  const id = `pilot-${String(index + 1).padStart(3, '0')}`;
  const oracle = GOLDEN_ORACLE[id];
  if (!oracle) throw new Error(`Missing golden oracle for ${id}`);
  const base = {
    id, relationship: 'Mom', age: '80-84', budget: oracle.budget,
    moveTiming: '1-3 months', attitude: 'Cautious but open', social: 'Weekly',
    community: 'No preference', activities: ['Music', 'Classes'],
    concerns: ['Independence', 'Daily routine'], diet: 'Low sodium',
    futureCare: oracle.futureCare || 'Preferred', distance: oracle.distance,
    location: oracle.location,
  };
  const overrides = {
    "pilot-001": { relationship: "Mom", age: "75-79", social: "Daily", community: "Large and active", activities: ["Music","Cultural activities"] },
    "pilot-002": { relationship: "Dad", age: "80-84", moveTiming: "Within 30 days" },
    "pilot-003": { relationship: "Dad", age: "80-84", community: "Small and familiar", memory: "Significant memory issues", medical: "No" },
    "pilot-004": { relationship: "Dad", age: "80-84", moveTiming: "Immediately", recentHospital: "Yes", medical: "Yes", medicalRoutine: ["Complex chronic condition"] },
    "pilot-005": { relationship: "Couple", age: "80-84", community: "Medium", couple: true },
    "pilot-006": { relationship: "Mom", age: "80-84", moveTiming: "Within 30 days", medicaid: "Application pending" },
    "pilot-007": { relationship: "Grandma", age: "80-84", activities: ["Religious life","Cultural activities"], diet: "Kosher", language: "Hebrew", medicalLanguage: "Hebrew" },
    "pilot-008": { relationship: "Mom", age: "75-79", social: "Daily", community: "Large and active", activities: ["Exercise","Classes"] },
    "pilot-009": { relationship: "Dad", age: "75-79", moveTiming: "Within 30 days", medical: "Yes", medicalRoutine: ["Dialysis","Wound care"] },
    "pilot-010": { relationship: "Myself", age: "70-74", moveTiming: "Planning ahead", futureCare: "Required" },
  };
  return { ...base, ...(overrides[id] || {}) };
}

/**
 * Drive the intake one question at a time.
 *
 * The intake asks a single question per step and decides the next one from the answers so
 * far, so the spec cannot click a fixed list of buttons: it has to read the question on
 * screen and answer that. `answers` maps a prompt pattern to what to do. A single-choice
 * answer advances by itself; anything else needs "Next".
 */
async function answerInterview(page, answers, maxSteps = 120) {
  const asked = [];
  for (let step = 0; step < maxSteps; step += 1) {
    if (/\/intake-confirmation(?:\?|$)/.test(page.url())) return asked;
    const summary = page.getByRole('heading', { name: /Here’s what I understood/i });
    if (await summary.isVisible().catch(() => false)) return asked;

    const heading = page.locator('main h1').first();
    await heading.waitFor({ state: 'visible' });
    const prompt = (await heading.innerText()).trim();
    if (asked[asked.length - 1] === prompt) {
      await page.waitForURL(/\/intake-confirmation(?:\?|$)/, { timeout: 5_000 }).catch(() => {});
      if (/\/intake-confirmation(?:\?|$)/.test(page.url())) return asked;
      throw new Error(`Intake repeated a question without advancing: ${prompt}`);
    }

    const entry = answers.find(([pattern]) => pattern.test(prompt));
    if (!entry) throw new Error(`No answer configured for intake question: "${prompt}"`);
    const [, action] = entry;

    if (action.choose) {
      const choice = page.getByRole('button', { name: action.choose, exact: true });
      await choice.waitFor({ state: 'visible', timeout: 2_000 }).catch(() => {});
      if (/\/intake-confirmation(?:\?|$)/.test(page.url())) return asked;
      asked.push(prompt);
      await choice.click();
      continue; // a single choice advances on its own
    }
    asked.push(prompt);
    if (action.select) {
      for (const option of action.select) await page.getByRole('button', { name: option, exact: true }).click();
    }
    if (action.fill !== undefined) {
      const range = page.locator('main input[type="range"]');
      if (await range.count()) {
        const slider = range.first();
        const min = Number(await slider.getAttribute('min') || 1);
        const max = Number(await slider.getAttribute('max') || 15000);
        const step = Number(await slider.getAttribute('step') || 1);
        const requested = Number(action.fill);
        const snapped = Math.min(max, Math.max(min, requested));
        await slider.evaluate((el, value) => {
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(el, String(value));
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }, snapped);
      } else {
        await page.locator('main input[type="text"], main input[type="number"]').first().fill(String(action.fill));
      }
    }
    await page.getByRole('button', { name: /^(Next →|See the summary →)$/ }).click();
  }
  throw new Error('Intake did not reach the summary within the step budget');
}

test.describe('real synthetic-pilot customer journey', () => {
  test.setTimeout(900_000);

  for (let scenarioIndex = scenarioStart; scenarioIndex < scenarioStart + scenarioCount; scenarioIndex += 1) {
    const scenario = scenarioFor(scenarioIndex);
    const oracle = GOLDEN_ORACLE[scenario.id];
    if (!oracle) throw new Error(`Missing golden oracle for ${scenario.id}`);
    test(`${scenario.id} completes the real customer journey`, async ({ page }) => {
    page.setDefaultTimeout(15_000);
    const errors = [];
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });

    await page.goto('http://127.0.0.1:3000/intake', { waitUntil: 'networkidle' });

    const asked = await answerInterview(page, [
      [/Who are we finding the right place for\?/i, { choose: scenario.relationship }],
      [/About how old/i, { choose: scenario.age }],
      [/Which part of the Las Vegas Valley would you prefer\?/i, { choose: scenario.location }],
      [/How far is still close enough\?/i, { choose: scenario.distance }],
      [/What kind of help makes everyday life easier\?/i, { select: ['Help with bathing', 'Help with dressing', 'Help with medications'] }],
      [/usually get around\?/i, { choose: 'Independent' }],
      [/getting up, sitting down, or transferring\?/i, { choose: 'No' }],
      [/falls in the last six months\?/i, { choose: 'No' }],
      [/changes in memory or confusion lately\?/i, { choose: scenario.memory || 'No' }],
      [/wandering or getting lost\?/i, { choose: scenario.id === 'pilot-003' ? 'Yes' : 'No' }],
      [/ongoing medical care the community/i, { choose: scenario.medical || 'No' }],
      [/Which of these are part of the current routine\?/i, { select: scenario.medicalRoutine || [] }],
      [/How often is dialysis needed\?/i, { fill: 'three times weekly' }],
      [/Which of these are part of the current routine\?/i, { select: scenario.id === 'pilot-009' ? ['Dialysis','Wound care'] : scenario.id === 'pilot-004' ? ['Physical therapy'] : [] }],
      [/hospital stay recently\?/i, { choose: scenario.recentHospital || 'No' }],
      [/Medicaid situation\?/i, { choose: scenario.medicaid || 'Not eligible' }],
      [/What monthly budget would feel comfortable\?/i, { fill: scenario.budget }],
      [/When would you ideally like the move to happen\?/i, { choose: scenario.moveTiming }],
      [/feel about the idea of moving\?/i, { choose: scenario.attitude }],
      [/How social would/i, { choose: scenario.social }],
      [/What kind of community would feel most comfortable\?/i, { choose: scenario.community }],
      [/genuinely enjoy doing\?/i, { select: scenario.activities }],
      [/What would you like to have nearby\?/i, { select: ["Parks & walking paths"] }],
      [/How important is it to be close to these places\?/i, { choose: "Nice to have" }],
      [/specific person or place it would be important to stay close to\?/i, { choose: "No specific destination" }],
      [/hate for .* to lose after the move\?/i, { select: scenario.concerns }],
      [/Anything specific we should preserve\?/i, { fill: `${scenario.id}: preserve familiar routines and preferred activities.` }],
      [/What language feels most natural day to day\?/i, { choose: scenario.language || 'English' }],
      [/language.*medical|medical.*language/i, { fill: scenario.medicalLanguage || scenario.language || 'English' }],
      [/language.*medical|medical.*language/i, { choose: scenario.language || 'English' }],
      [/food preferences or requirements/i, { select: [scenario.diet] }],
      [/religious or faith community be important\?/i, { choose: 'No' }],
      [/pet need to move with/i, { choose: 'No' }],
      [/leave the community and go out on/i, { choose: 'Yes' }],
      [/need parking at the community\?/i, { choose: 'No' }],
      [/provide more care later/i, { choose: scenario.futureCare }],
      [/How broadly would you like me to search\?/i, { choose: 'Show me both approaches' }],
    ]);

    // The interview must ask one question at a time and never repeat itself.
    expect(new Set(asked).size).toBe(asked.length);
    expect(asked.length).toBeGreaterThan(20);
    expect(asked[0]).toMatch(/Who are we finding the right place for\?/i);
    expect(asked[1]).toMatch(/About how old/i);
    expect(asked[2]).toMatch(/Which part of the Las Vegas Valley would you prefer\?/i);

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
        await answerBox.fill(`Use the confirmed questionnaire facts: English for daily life, medical discussions and social interaction; budget $${scenario.budget} per month including all required care${oracle.couple ? ' and both residents, who must live together' : ''}; ${scenario.location} within ${scenario.distance} miles; ${scenario.diet === 'Kosher' ? 'kosher meals are required, a religious community is not required' : 'low sodium is a preference, not a mandatory clinical diet'}; future care ${scenario.futureCare.toLowerCase()}. No additional medical requirement beyond the questionnaire.`);
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
    const results = payload.results || [];
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
    if (classifiedCohort !== undefined) expect([expectedCohort, 200]).toContain(classifiedCohort);
    expect(payload.total_candidates_scored).toBeGreaterThan(0);
    if (expectedCohort) expect(payload.total_candidates_scored).toBeLessThanOrEqual(expectedCohort);
    const needsById = new Map((payload.patient_needs_profile?.needs || []).map((item) => [item.parameter_id, item]));
    const intentMust = new Set([
      ...((payload.decision_intelligence?.client_intent?.must_have_parameter_ids) || []),
      ...((payload.decision_intelligence?.client_intent?.must_haves) || []).flatMap((x) => [x?.parameter_id, x?.key]).filter(Boolean),
    ].map(String));
    for (const requiredId of (oracle.required || [])) {
      const need = needsById.get(requiredId);
      const inNeeds = need && ['HIGH','REQUIRED','MUST'].includes(String(need.requirement_level || '').toUpperCase());
      const aliases = { couple_coresidence: ['couple_coresidence','coresidence','couple'], medicaid_pathway: ['medicaid_pathway','medicaid'], continuum_of_care: ['continuum_of_care','continuum','future_care'] }[requiredId] || [requiredId];
      const inIntent = [...intentMust].some((x) => aliases.some((alias) => x.toLowerCase().includes(alias)));
      expect(Boolean(inNeeds || inIntent), `${scenario.id} must preserve required need ${requiredId} in canonical needs or client intent`).toBe(true);
    }
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
