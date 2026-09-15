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
};

const chosen = process.env.OOMNIK_SCENARIO || 'independent_mom';
const baseUrl = process.env.OOMNIK_PRODUCTION_URL;

test.describe('production synthetic journey', () => {
  test.skip(!baseUrl, 'Set OOMNIK_PRODUCTION_URL to run against the live site.');

  test(`${chosen} reaches real results`, async ({ page }) => {
    const scenario = scenarios[chosen];
    if (!scenario) throw new Error(`Unknown scenario: ${chosen}`);

    await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60_000 });
    await page.getByLabel('Describe your family situation').fill(scenario.story);
    await page.getByRole('button', { name: /See options that may fit/ }).click();
    await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 30_000 });

    for (let step = 0; step < 9; step += 1) {
      if (/\/results/.test(page.url())) break;
      const prompt = await page.locator('main').innerText({ timeout: 45_000 });
      const choices = page.locator('main button');
      const continueButton = page.getByRole('button', { name: /^Continue$/ });
      const answerBox = page.getByLabel('Your answer');

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
    await expect(page.getByText(/strongest options|options for/i).first()).toBeVisible({ timeout: 90_000 });
    await expect(page.locator('main').getByRole('link').filter({ hasText: /comparison|details|listing/i }).first()).toBeVisible({ timeout: 30_000 });
  });
});
