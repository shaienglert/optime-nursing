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

function scenarioFor(index) {
  const pick = (values, offset = 0) => values[(index + offset) % values.length];
  return {
    id: `pilot-${String(index + 1).padStart(3, '0')}`,
    relationship: pick(['Mom', 'Dad', 'Grandma', 'Grandpa', 'Spouse', 'Myself', 'Relative', 'Friend']),
    age: pick(['60-64', '65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95+'], 3),
    budget: 3600 + ((index * 700) % 10500),
    moveTiming: pick(['Immediately', 'Within 30 days', '1-3 months', '3-6 months', 'Planning ahead']),
    attitude: pick(['Wants to move', 'Positive', 'Cautious but open', 'Anxious', 'Resistant'], 1),
    social: pick(['Daily', 'Several times weekly', 'Weekly', 'Occasionally', 'Very little'], 2),
    community: pick(['Small and familiar', 'Medium', 'Large and active', 'Quiet', 'No preference'], 3),
    activities: [pick(['Music', 'Movies', 'Games', 'Exercise', 'Outdoor activities']), pick(['Religious life', 'Cultural activities', 'Classes', 'Volunteering'], 2)],
    concerns: [pick(['Good food', 'Privacy', 'Independence', 'Social life', 'Proximity to family']), pick(['Daily routine', 'Space for visitors', 'A pet', 'Transportation'], 1)],
    diet: pick(['Vegetarian', 'Vegan', 'Low sodium', 'Diabetic', 'Gluten free']),
    futureCare: pick(['Required', 'Preferred', 'Not important', 'Not sure'], 1),
    distance: pick(['10', '20', '30', '50', '100'], 2),
  };
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
    const summary = page.getByRole('heading', { name: /Here’s what I understood/i });
    if (await summary.isVisible().catch(() => false)) return asked;

    const heading = page.locator('main h1').first();
    await heading.waitFor({ state: 'visible' });
    const prompt = (await heading.innerText()).trim();
    asked.push(prompt);

    const entry = answers.find(([pattern]) => pattern.test(prompt));
    if (!entry) throw new Error(`No answer configured for intake question: "${prompt}"`);
    const [, action] = entry;

    if (action.choose) {
      await page.getByRole('button', { name: action.choose, exact: true }).click();
      continue; // a single choice advances on its own
    }
    if (action.select) {
      for (const option of action.select) await page.getByRole('button', { name: option, exact: true }).click();
    }
    if (action.fill !== undefined) {
      await page.locator('main input[type="text"], main input[type="number"]').first().fill(String(action.fill));
    }
    await page.getByRole('button', { name: /^(Next →|See the summary →)$/ }).click();
  }
  throw new Error('Intake did not reach the summary within the step budget');
}

test.describe('real synthetic-pilot customer journey', () => {
  test.setTimeout(900_000);

  for (let scenarioIndex = scenarioStart; scenarioIndex < scenarioStart + scenarioCount; scenarioIndex += 1) {
    const scenario = scenarioFor(scenarioIndex);
    test(`${scenario.id} completes the real customer journey`, async ({ page }) => {
    page.setDefaultTimeout(15_000);
    const errors = [];
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });

    await page.goto('http://127.0.0.1:3000/intake', { waitUntil: 'networkidle' });

    const asked = await answerInterview(page, [
      [/Who are we finding the right place for\?/i, { choose: scenario.relationship }],
      [/About how old are they\?/i, { choose: scenario.age }],
      [/What kind of help makes everyday life easier\?/i, { select: ['Help with bathing', 'Help with dressing', 'Help with medications'] }],
      [/How do they usually get around\?/i, { choose: 'Independent' }],
      [/getting up, sitting down, or transferring\?/i, { choose: 'No' }],
      [/falls in the last six months\?/i, { choose: 'No' }],
      [/changes in memory or confusion lately\?/i, { choose: 'No' }],
      [/ongoing medical care the community/i, { choose: 'No' }],
      [/hospital stay recently\?/i, { choose: 'No' }],
      [/Medicaid situation\?/i, { choose: 'Not eligible' }],
      [/What monthly budget would feel comfortable\?/i, { fill: scenario.budget }],
      [/When would you ideally like the move to happen\?/i, { choose: scenario.moveTiming }],
      [/How do they feel about the idea of moving\?/i, { choose: scenario.attitude }],
      [/How social would they like everyday life to be\?/i, { choose: scenario.social }],
      [/What kind of community would feel most comfortable\?/i, { choose: scenario.community }],
      [/What do they genuinely enjoy doing\?/i, { select: scenario.activities }],
      [/hate for them to lose after the move\?/i, { select: scenario.concerns }],
      [/Anything specific we should preserve\?/i, { fill: `${scenario.id}: preserve familiar routines and preferred activities.` }],
      [/What language feels most natural day to day\?/i, { choose: 'English' }],
      [/food preferences or requirements/i, { select: [scenario.diet] }],
      [/religious or faith community be important\?/i, { choose: 'No' }],
      [/Would a pet need to move with them\?/i, { choose: 'No' }],
      [/Can they go out independently\?/i, { choose: 'Yes' }],
      [/What worries them most about moving\?/i, { fill: 'Losing familiar routines' }],
      [/Will they need parking at the community\?/i, { choose: 'No' }],
      [/provide more care later/i, { choose: scenario.futureCare }],
      [/How broadly would you like me to search\?/i, { choose: 'Show me both approaches' }],
      [/staying near a particular area or person matter\?/i, { choose: 'Yes' }],
      [/address or area should I measure from\?/i, { fill: 'Las Vegas, NV' }],
      [/How far would still feel close enough\?/i, { choose: scenario.distance }],
    ]);

    // The interview must ask one question at a time and never repeat itself.
    expect(new Set(asked).size).toBe(asked.length);
    expect(asked.length).toBeGreaterThan(20);

    await page.getByText('Yes — this reflects what I told Oomnik.').click();
    await page.getByRole('button', { name: 'Continue our conversation' }).click();
    await page.waitForURL(/\/(adaptive-interview|intake-confirmation)(?:\?|$)/, { timeout: 60_000 });

    for (let turn = 0; turn < 25; turn += 1) {
      await page.waitForLoadState('domcontentloaded');
      const adaptivePrompt = await page.locator('main').innerText().catch(() => '');
      console.log('OOMNIK_ADAPTIVE_TURN', JSON.stringify({ scenario_id: scenario.id, turn, url: page.url(), prompt: adaptivePrompt.slice(0, 1200) }));
      const finalConfirmation = page.getByRole('button', { name: /I confirm—show recommendations/i });
      await Promise.race([
        finalConfirmation.waitFor({ state: 'visible', timeout: 300_000 }),
        page.getByLabel('Your answer').waitFor({ state: 'visible', timeout: 300_000 }),
        page.locator('main section button').first().waitFor({ state: 'visible', timeout: 300_000 }),
      ]).catch(() => {});
      if (await finalConfirmation.isVisible()) break;
      // A runtime failure is not an interview option. Fail with the rendered
      // explanation instead of silently clicking Try again up to 25 times.
      const retry = page.getByRole('button', { name: 'Try again', exact: true });
      expect(await retry.count(), await page.locator('main').innerText()).toBe(0);
      const answerBox = page.getByLabel('Your answer');
      const continueButton = page.getByRole('button', { name: /^Continue$/ });
      if (await answerBox.count()) {
        await answerBox.fill('No additional requirement; use the confirmed questionnaire answers.');
        await continueButton.click();
      } else {
        const offeredOption = page.locator('main section button').first();
        await expect(offeredOption).toBeVisible({ timeout: 30_000 });
        await offeredOption.click();
      }
      await page.waitForTimeout(500);
    }

    await expect(page.getByRole('heading', { name: /Please confirm what Oomnik understood/i })).toBeVisible({ timeout: 300_000 });
    const recommendationResponse = page.waitForResponse(
      (response) => response.url().includes('/decision-engine/recommendations')
        && response.request().method() === 'POST',
      { timeout: 720_000 },
    );
    await page.getByRole('button', { name: /I confirm—show recommendations/i }).click();
    await expect(page).toHaveURL(/\/results/, { timeout: 180_000 });

    const response = await recommendationResponse;
    expect(response.status()).toBe(200);
    const payload = await response.json();
    const results = payload.results || [];
    const classifiedCohort = payload.candidate_discovery?.total_facilities_classified;
    if (classifiedCohort !== undefined) expect([expectedCohort, 200]).toContain(classifiedCohort);
    expect(payload.total_candidates_scored).toBeGreaterThan(0);
    if (expectedCohort) expect(payload.total_candidates_scored).toBeLessThanOrEqual(expectedCohort);
    const budgetNeed = payload.patient_needs_profile.needs.find(item => item.parameter_id === 'current_price');
    expect(budgetNeed.desired_value).toBe(scenario.budget);
    expect(Number.isFinite(minimumCarePrice)).toBe(true);
    if (scenario.budget < minimumCarePrice) {
      expect(results).toHaveLength(0);
      await expect(page.getByText('I don’t have a verified recommendation to show yet. Missing information is still being distinguished from a confirmed mismatch.')).toBeVisible();
    } else {
      expect(results.length).toBeGreaterThan(0);
      await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
    }
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
