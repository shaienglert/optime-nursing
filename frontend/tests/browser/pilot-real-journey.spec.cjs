const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

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

function question(page, text) {
  return page.getByText(text, { exact: true }).locator('..');
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
    await expect(page.getByRole('heading', { name: /Let’s get to know the person behind the decision\./i })).toBeVisible();

    await page.getByRole('button', { name: scenario.relationship, exact: true }).click();
    await page.getByRole('button', { name: scenario.age, exact: true }).click();
    await page.getByRole('button', { name: 'Help with bathing', exact: true }).click();
    await page.getByRole('button', { name: 'Help with dressing', exact: true }).click();
    await page.getByRole('button', { name: 'Help with medications', exact: true }).click();
    await question(page, 'How do they usually get around?').getByRole('button', { name: 'Independent', exact: true }).click();
    await question(page, 'Do they need help getting up, sitting down, or transferring?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Have there been any falls in the last six months?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Have you noticed any changes in memory or confusion lately?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Is there any ongoing medical care the community would need to provide or coordinate?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Has there been a hospital stay recently?').getByRole('button', { name: 'No', exact: true }).click();
    await page.getByRole('button', { name: 'Not eligible', exact: true }).click();

    await page.locator('input[type="range"]').evaluate((element, budget) => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(element, String(budget));
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }, scenario.budget);
    await expect(page.locator('input[type="range"]')).toHaveValue(String(scenario.budget));
    await page.getByRole('button', { name: scenario.moveTiming, exact: true }).click();
    await page.getByRole('button', { name: scenario.attitude, exact: true }).click();
    await page.getByRole('button', { name: scenario.social, exact: true }).click();
    await page.getByRole('button', { name: scenario.community, exact: true }).click();
    for (const activity of scenario.activities) await page.getByRole('button', { name: activity, exact: true }).click();
    for (const concern of scenario.concerns) await page.getByRole('button', { name: concern, exact: true }).click();
    await page.getByLabel('Anything specific we should preserve?').fill(`${scenario.id}: preserve familiar routines and preferred activities.`);
    await page.getByRole('button', { name: 'English', exact: true }).click();
    await page.getByRole('button', { name: scenario.diet, exact: true }).click();
    await question(page, 'Would a religious or faith community be important?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Will they need parking at the community?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Would you prefer a place that can provide more care later, so another move may be avoided?').getByRole('button', { name: scenario.futureCare, exact: true }).click();
    await question(page, 'Does staying near a particular area or person matter?').getByRole('button', { name: 'Yes', exact: true }).click();
    await page.getByLabel('Reference address').fill('Las Vegas, NV');
    await page.getByRole('button', { name: scenario.distance, exact: true }).click();
    await question(page, 'Would a pet need to move with them?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Can they go out independently?').getByRole('button', { name: 'Yes', exact: true }).click();
    await page.getByLabel('What worries them most about moving?').fill('Losing familiar routines');
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
    const canonical = payload.canonical_decision_state;
    expect(canonical?.authoritative).toBe(true);
    if (canonical.can_show_recommendations) {
      expect(results.length).toBeGreaterThan(0);
    } else {
      expect(results).toEqual([]);
      expect(canonical.phase).toBe('EVIDENCE_COLLECTION');
      await expect(page.getByText(/do not yet have enough verified information/)).toBeVisible();
      await expect(page.getByText(/Meets verified must-haves/)).toHaveCount(0);
    }
    expect(results.every((item) => item.synthetic_pilot === true)).toBe(true);
    expect(results.every((item) => String(item.canonical_facility_id || '').startsWith('PILOT-NV-'))).toBe(true);
    if (results.length) await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
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
