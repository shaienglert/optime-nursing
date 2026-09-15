const { test, expect } = require('@playwright/test');

const scenarios = {
  independent_mom: {
    story: 'My mother is 82 and fully independent. She lives in Las Vegas, enjoys music, gardening and regular social activities, speaks Hebrew and English, and wants a community with a clear future-care path. Her budget is up to $8,000 a month.',
    answer: (question) => {
      const text = question.toLowerCase();
      if (/city|area|location|market/.test(text)) return 'Las Vegas Valley';
      if (/budget|cost|monthly|afford/.test(text)) return '$8,000 per month';
      if (/care|support|adl|bathing|dressing|medication/.test(text)) return 'She is fully independent today and wants support available later if needed.';
      if (/memory/.test(text)) return 'No diagnosed memory condition; occasional normal forgetfulness only.';
      if (/social|activity|music|garden/.test(text)) return 'Music, gardening and regular social activities matter a great deal.';
      return 'No additional preference beyond what I described.';
    },
  },
  memory_mom: {
    story: "My mother is 84 and has advancing Alzheimer's disease. She needs constant supervision, help with bathing, dressing, toileting and medication management, and she sometimes wanders at night. She lives in the Las Vegas Valley. She needs a secure memory-care setting with 24/7 staff. Her budget is about $5,000 per month and Medicaid eligibility is pending.",
    answer: (question) => {
      const text = question.toLowerCase();
      if (/city|area|location|market/.test(text)) return 'Las Vegas Valley';
      if (/budget|cost|monthly|afford|medicaid/.test(text)) return '$5,000 per month; Medicaid eligibility is pending.';
      if (/memory|cognitive|dementia|alzheimer|wander/.test(text)) return "Advancing Alzheimer's with nighttime wandering; she needs a secured memory-care setting.";
      if (/care|support|adl|bathing|dressing|toilet|medication|supervision/.test(text)) return 'Hands-on ADL help, medication management and awake 24/7 supervision are required.';
      if (/safety|secure|night/.test(text)) return 'A secured environment and staff able to respond at all hours are required.';
      return 'No additional preference beyond the safety, memory-care and budget requirements described.';
    },
    forbiddenVerifiedFacilities: ['Revel Vegas', 'STEWART PINES II SENIOR APTS'],
  },
};

const chosen = process.env.OOMNIK_SCENARIO || 'memory_mom';
const baseUrl = process.env.OOMNIK_PRODUCTION_URL;

test.describe('production synthetic journey', () => {
  test.skip(!baseUrl, 'Set OOMNIK_PRODUCTION_URL to run against the live site.');
  test.setTimeout(300_000);

  test(`${chosen} reaches real results`, async ({ page }) => {
    const scenario = scenarios[chosen];
    if (!scenario) throw new Error(`Unknown scenario: ${chosen}`);

    const recommendationResponse = page.waitForResponse(
      (response) => response.url().includes('/decision-engine/recommendations')
        && response.request().method() === 'POST',
      { timeout: 240_000 },
    );
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    const storyBox = page.getByLabel('Describe your family situation');
    await expect(storyBox).toBeVisible({ timeout: 60_000 });
    await storyBox.fill(scenario.story);
    await page.waitForTimeout(2_000);
    await page.getByRole('button', { name: /See options that may fit/ }).click();
    try {
      await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 15_000 });
    } catch {
      await expect(storyBox).toBeVisible({ timeout: 30_000 });
      await storyBox.fill(scenario.story);
      await page.waitForTimeout(2_000);
      await page.getByRole('button', { name: /See options that may fit/ }).click();
      await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 60_000 });
    }

    let transientRetries = 0;
    for (let step = 0; step < 9; step += 1) {
      await page.waitForFunction(
        () => /\/results/.test(window.location.pathname)
          || Boolean(document.querySelector('#decision-answer'))
          || Boolean(document.querySelector('main button')),
        undefined,
        { timeout: 90_000 },
      );
      if (/\/results/.test(page.url())) break;

      const prompt = await page.locator('main').innerText({ timeout: 45_000 });
      const choices = page.locator('main button');
      const continueButton = page.getByRole('button', { name: /^Continue$/ });
      const answerBox = page.getByLabel('Your answer');

      if (/API request failed \(50[234]\)/i.test(prompt)) {
        if (transientRetries >= 1) throw new Error(`Adaptive interview remained unavailable after retry: ${prompt}`);
        transientRetries += 1;
        await page.getByRole('button', { name: /^Try again$/ }).click();
        step -= 1;
        await page.waitForTimeout(2_000);
        continue;
      }

      if (await answerBox.count()) {
        await answerBox.fill(scenario.answer(prompt));
        await continueButton.click();
      } else if (await choices.count()) {
        const option = choices.filter({ hasText: /No preference|Not sure|More active|Las Vegas/i }).first();
        if (!(await option.count())) throw new Error(`No safe answer option for: ${prompt}`);
        await option.click();
      } else {
        throw new Error(`No answer control visible for: ${prompt}`);
      }
      await page.waitForTimeout(500);
    }

    await expect(page).toHaveURL(/\/results/, { timeout: 90_000 });
    await expect(page.getByText('OPTIME results')).toBeVisible({ timeout: 120_000 });
    const resultsText = await page.locator('main').innerText();
    console.log('OOMNIK_RESULTS_BEGIN');
    console.log(resultsText);
    console.log('OOMNIK_RESULTS_END');
    const recommendationPayload = await (await recommendationResponse).json();
    const verifiedResults = (recommendationPayload.results || []).filter((item) =>
      item.must_eligibility
        ? item.must_eligibility === 'MUST_ELIGIBLE'
        : item.eligibility_status === 'ELIGIBLE',
    );
    for (const facilityName of scenario.forbiddenVerifiedFacilities || []) {
      expect(
        verifiedResults.some((item) => item.facility_name === facilityName),
        `${facilityName} must not be verified for ${chosen}`,
      ).toBe(false);
    }
    console.log('OOMNIK_DECISION_JSON_BEGIN');
    console.log(JSON.stringify({
      result_count: recommendationPayload.result_count,
      patient_needs_profile: recommendationPayload.patient_needs_profile,
      facility_selection_pipeline: recommendationPayload.decision_intelligence?.facility_selection_pipeline,
      results: (recommendationPayload.results || []).slice(0, 10).map((item) => ({
        canonical_facility_id: item.canonical_facility_id,
        facility_name: item.facility_name,
        eligibility_status: item.eligibility_status,
        must_eligibility: item.must_eligibility,
        ai_ranking: item.ai_ranking,
        client_intent_fit: item.client_intent_fit,
      })),
    }));
    console.log('OOMNIK_DECISION_JSON_END');
    expect(resultsText.length).toBeGreaterThan(200);
  });
});
