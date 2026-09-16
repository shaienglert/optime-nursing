const { test, expect } = require('@playwright/test');
const { scenarios, answerFor } = require('./launch-scenarios.cjs');
const { validateLaunchContract } = require('./launch-contract.cjs');

const chosen = process.env.OOMNIK_SCENARIO || 'memory_mom';
const baseUrl = process.env.OOMNIK_PRODUCTION_URL;

test.describe('production synthetic journey', () => {
  test.skip(!baseUrl, 'Set OOMNIK_PRODUCTION_URL to run against the live site.');
  test.setTimeout(900_000);

  test(`${chosen} reaches real results`, async ({ page }) => {
    const scenario = scenarios[chosen];
    if (!scenario) throw new Error(`Unknown scenario: ${chosen}`);

    const recommendationResponse = page.waitForResponse(
      (response) => response.url().includes('/decision-engine/recommendations')
        && response.request().method() === 'POST',
      { timeout: 720_000 },
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
    let clarificationRetries = 0;
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

      if (/no useful next question was returned/i.test(prompt)) {
        if (clarificationRetries >= 2) throw new Error(`Adaptive interview returned no usable clarification after retries: ${prompt}`);
        clarificationRetries += 1;
        await page.getByRole('button', { name: /^Try again$/ }).click();
        step -= 1;
        await page.waitForTimeout(2_000);
        continue;
      }

      if (await answerBox.count()) {
        await answerBox.fill(answerFor(prompt, scenario));
        await continueButton.click();
      } else if (await choices.count()) {
        const option = choices.filter({ hasText: /No preference|Not sure|More active|Las Vegas/i }).first();
        if (!(await option.count())) throw new Error(`No safe answer option for: ${prompt}`);
        await option.click();
      } else {
        throw new Error(`No answer control visible for: ${prompt}`);
      }
      await page.waitForFunction(
        (previousPrompt) => {
          if (/\/results/.test(window.location.pathname)) return true;
          const main = document.querySelector('main');
          if (!main || main.innerText === previousPrompt) return false;
          const controls = Array.from(main.querySelectorAll('button, textarea, input'));
          return controls.some((node) => !(node instanceof HTMLButtonElement || node instanceof HTMLInputElement || node instanceof HTMLTextAreaElement) || !node.disabled);
        },
        prompt,
        { timeout: 320_000 },
      );
    }

    await expect(page).toHaveURL(/\/results/, { timeout: 90_000 });
    await expect(page.getByText('OPTIME results')).toBeVisible({ timeout: 120_000 });
    const resultsText = await page.locator('main').innerText();
    console.log('OOMNIK_RESULTS_BEGIN');
    console.log(resultsText);
    console.log('OOMNIK_RESULTS_END');
    const recommendationPayload = await (await recommendationResponse).json();
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
    validateLaunchContract({ scenarioName: chosen, scenario, payload: recommendationPayload, resultsText });
    expect(resultsText.length).toBeGreaterThan(200);
  });
});
