const { test, expect } = require('@playwright/test');

test('a fresh facility visit does not invent a personal recommendation', async ({ page }) => {
  const base = process.env.OOMNIK_BASE_URL || 'http://127.0.0.1:3000';
  const response = await page.request.get(`${base}/api/backend/facilities`);
  expect(response.ok()).toBeTruthy();
  const facilities = await response.json();
  expect(facilities.length).toBeGreaterThan(0);
  await page.goto(`${base}/facility/${encodeURIComponent(facilities[0].id)}`);
  await expect(page.getByRole('heading', { name: facilities[0].name, exact: true })).toBeVisible({ timeout: 60000 });
  await expect(page.getByText('No personalized assessment is available for this facility.', { exact: true })).toBeVisible();
  await expect(page.getByText(/Ranked #|Why .* selected this facility for|One of the strongest available options for this search/)).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Complete and confirm your questionnaire to explore your options' })).toHaveAttribute('href', '/intake');
});
