const { test, expect } = require('@playwright/test');

test.describe('real synthetic-pilot customer journey', () => {
  test.setTimeout(900_000);

  test('completes the questionnaire, confirms the summary, and receives only pilot facilities', async ({ page }) => {
    const errors = [];
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });

    const recommendationResponse = page.waitForResponse(
      (response) => response.url().includes('/decision-engine/recommendations')
        && response.request().method() === 'POST',
      { timeout: 720_000 },
    );

    await page.goto('http://127.0.0.1:3000/intake', { waitUntil: 'networkidle' });
    await expect(page.getByRole('heading', { name: /We ask first\. We conclude only after you confirm\./i })).toBeVisible();

    await page.getByRole('button', { name: 'Mom', exact: true }).click();
    await page.getByRole('button', { name: '80-84', exact: true }).click();
    await page.getByRole('button', { name: 'Help with bathing', exact: true }).click();
    await page.getByRole('button', { name: 'Help with dressing', exact: true }).click();
    await page.getByRole('button', { name: 'Help with medications', exact: true }).click();
    await page.getByRole('button', { name: 'Independent', exact: true }).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(0).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(1).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(2).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(3).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(4).click();
    await page.getByRole('button', { name: 'Not eligible', exact: true }).click();

    await page.locator('input[type="range"]').evaluate((element) => {
      element.value = '6500';
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.getByRole('button', { name: 'Within 30 days', exact: true }).click();
    await page.getByRole('button', { name: 'Cautious but open', exact: true }).click();
    await page.getByRole('button', { name: 'Daily', exact: true }).click();
    await page.getByRole('button', { name: 'Medium', exact: true }).click();
    await page.getByRole('button', { name: 'Music', exact: true }).click();
    await page.getByRole('button', { name: 'Games', exact: true }).click();
    await page.getByRole('button', { name: 'Outdoor activities', exact: true }).click();
    await page.getByRole('button', { name: 'Good food', exact: true }).click();
    await page.getByRole('button', { name: 'Social life', exact: true }).click();
    await page.getByLabel('Anything specific we should preserve?').fill('Gluten-free meals, classical music, card games, and time outdoors.');
    await page.getByRole('button', { name: 'English', exact: true }).click();
    await page.getByRole('button', { name: 'Gluten free', exact: true }).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(5).click();
    await page.getByRole('button', { name: 'No', exact: true }).nth(6).click();
    await page.getByRole('button', { name: 'Preferred', exact: true }).click();
    await page.getByRole('button', { name: 'Yes', exact: true }).last().click();
    await page.getByLabel('Reference address').fill('Las Vegas, NV');
    await page.getByRole('button', { name: '20', exact: true }).click();
    await page.getByText('I confirm that this summary reflects my answers.').click();
    await page.getByRole('button', { name: 'Continue to AI clarification' }).click();

    for (let turn = 0; turn < 10 && !/intake-confirmation/.test(page.url()); turn += 1) {
      await page.waitForLoadState('domcontentloaded');
      if (/intake-confirmation/.test(page.url())) break;
      const answerBox = page.getByLabel('Your answer');
      const continueButton = page.getByRole('button', { name: /^Continue$/ });
      if (await answerBox.count()) {
        await answerBox.fill('No additional requirement; use the confirmed questionnaire answers.');
        await continueButton.click();
      } else {
        const safeOption = page.getByRole('button', { name: /No preference|Not sure|More active|Las Vegas/i }).first();
        await expect(safeOption).toBeVisible({ timeout: 120_000 });
        await safeOption.click();
      }
      await page.waitForTimeout(500);
    }

    await expect(page).toHaveURL(/intake-confirmation/, { timeout: 180_000 });
    await expect(page.getByRole('heading', { name: /Please confirm what Oomnik understood/i })).toBeVisible();
    await page.getByRole('button', { name: /I confirm—show recommendations/i }).click();
    await expect(page).toHaveURL(/\/results/, { timeout: 180_000 });

    const response = await recommendationResponse;
    expect(response.status()).toBe(200);
    const payload = await response.json();
    const results = payload.results || [];
    expect([50, 100, 150, 200]).toContain(payload.total_candidates_scored);
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((item) => item.synthetic_pilot === true)).toBe(true);
    expect(results.every((item) => String(item.canonical_facility_id || '').startsWith('PILOT-NV-'))).toBe(true);
    await expect(page.getByText(/Pilot mode: every community/i)).toBeVisible();
    expect(errors.filter((message) => !/favicon/i.test(message))).toEqual([]);

    console.log('OOMNIK_REAL_PILOT_RESULT_BEGIN');
    console.log(JSON.stringify({
      total_candidates_scored: payload.total_candidates_scored,
      result_count: payload.result_count,
      market_coverage_notice: payload.market_coverage_notice,
      top_results: results.slice(0, 10).map((item) => ({
        canonical_facility_id: item.canonical_facility_id,
        facility_name: item.facility_name,
        eligibility_status: item.eligibility_status,
        total_score: item.total_score,
      })),
    }));
    console.log('OOMNIK_REAL_PILOT_RESULT_END');
  });
});
