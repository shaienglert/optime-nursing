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
  test.describe.configure({ mode: 'parallel' });
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
    await question(page, 'How does the person move around?').getByRole('button', { name: 'Independent', exact: true }).click();
    await question(page, 'Help with standing or transfers?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Any falls in the last six months?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Are there memory or confusion concerns?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Are there ongoing medical conditions or treatments the new community must manage or coordinate?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Has there been a recent hospitalization?').getByRole('button', { name: 'No', exact: true }).click();
    await page.getByRole('button', { name: 'Not eligible', exact: true }).click();

    await page.locator('input[type="range"]').evaluate((element, budget) => {
      element.value = String(budget);
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    }, scenario.budget);
    await page.getByRole('button', { name: scenario.moveTiming, exact: true }).click();
    await page.getByRole('button', { name: scenario.attitude, exact: true }).click();
    await page.getByRole('button', { name: scenario.social, exact: true }).click();
    await page.getByRole('button', { name: scenario.community, exact: true }).click();
    for (const activity of scenario.activities) await page.getByRole('button', { name: activity, exact: true }).click();
    for (const concern of scenario.concerns) await page.getByRole('button', { name: concern, exact: true }).click();
    await page.getByLabel('Anything specific we should preserve?').fill(`${scenario.id}: preserve familiar routines and preferred activities.`);
    await page.getByRole('button', { name: 'English', exact: true }).click();
    await page.getByRole('button', { name: scenario.diet, exact: true }).click();
    await question(page, 'Is a religious community important?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Is parking required at the residence?').getByRole('button', { name: 'No', exact: true }).click();
    await question(page, 'Is it important to have higher levels of care available later to avoid another move?').getByRole('button', { name: scenario.futureCare, exact: true }).click();
    await question(page, 'Is location important?').getByRole('button', { name: 'Yes', exact: true }).click();
    await page.getByLabel('Reference address').fill('Las Vegas, NV');
    await page.getByRole('button', { name: scenario.distance, exact: true }).click();
    await page.getByText('I confirm that this summary reflects my answers.').click();
    await page.getByRole('button', { name: 'Continue to AI clarification' }).click();

    for (let turn = 0; turn < 25; turn += 1) {
      await page.waitForLoadState('domcontentloaded');
      const finalConfirmation = page.getByRole('button', { name: /I confirm—show recommendations/i });
      await Promise.race([
        finalConfirmation.waitFor({ state: 'visible', timeout: 120_000 }),
        page.getByLabel('Your answer').waitFor({ state: 'visible', timeout: 120_000 }),
        page.locator('main section button').first().waitFor({ state: 'visible', timeout: 120_000 }),
      ]).catch(() => {});
      if (await finalConfirmation.isVisible()) break;
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

    await expect(page.getByRole('heading', { name: /Please confirm what Oomnik understood/i })).toBeVisible({ timeout: 180_000 });
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
    if (expectedCohort) expect(payload.total_candidates_scored).toBe(expectedCohort);
    else expect([50, 100, 150, 200]).toContain(payload.total_candidates_scored);
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((item) => item.synthetic_pilot === true)).toBe(true);
    expect(results.every((item) => String(item.canonical_facility_id || '').startsWith('PILOT-NV-'))).toBe(true);
    await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
    expect(errors.filter((message) => !/favicon/i.test(message))).toEqual([]);

    console.log('OOMNIK_REAL_PILOT_RESULT_BEGIN');
    const runResult = {
      scenario_id: scenario.id,
      scenario,
      total_candidates_scored: payload.total_candidates_scored,
      result_count: payload.result_count,
      market_coverage_notice: payload.market_coverage_notice,
      top_results: results.slice(0, 10).map((item) => ({
        canonical_facility_id: item.canonical_facility_id,
        facility_name: item.facility_name,
        eligibility_status: item.eligibility_status,
        total_score: item.total_score,
      })),
    };
    fs.mkdirSync(path.join(process.cwd(), 'pilot-results'), { recursive: true });
    fs.writeFileSync(path.join(process.cwd(), 'pilot-results', `${scenario.id}.json`), `${JSON.stringify(runResult, null, 2)}\n`);
    console.log(JSON.stringify(runResult));
    console.log('OOMNIK_REAL_PILOT_RESULT_END');
    });
  }
});
