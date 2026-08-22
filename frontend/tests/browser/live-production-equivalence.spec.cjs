const { test, expect } = require('@playwright/test');

const BASE = 'https://optime-nursing.vercel.app';
const CLIENT_TEXT = 'My mother is 82 and is looking for senior living in Las Vegas. She is fully independent with bathing, dressing, toileting, transfers, medications, decision-making and memory. She has no memory concerns, does not need cognitive support, has no mobility limitation, and has no special medical or nursing needs. Her total monthly budget is up to $8,000.';

function answerFor(question) {
  const q = question.toLowerCase();
  if (/daily activities|bathing|dressing|toileting|transfer|medication/.test(q)) return 'She is fully independent with bathing, dressing, toileting, transfers, and medications. She needs no help with daily activities.';
  if (/memory|cognitive|decision-making|dementia/.test(q)) return 'She has no memory concerns, is fully independent with decision-making, and does not want or need cognitive support services.';
  if (/where|location|city|las vegas/.test(q) && /budget|monthly|afford|cost/.test(q)) return 'Las Vegas, Nevada. Her total monthly budget is up to $8,000.';
  if (/where|location|city|las vegas/.test(q)) return 'Las Vegas, Nevada.';
  if (/budget|monthly|cost|afford/.test(q)) return 'Her total monthly budget is up to $8,000.';
  if (/independent living|assisted living|care setting|personal-care/.test(q)) return 'Independent living. She does not need assisted living or personal-care support.';
  if (/mobility|walk|walker|wheelchair|distance/.test(q)) return 'She walks independently and has no mobility limitation, walker, or wheelchair requirement.';
  if (/medical|nursing|health|clinical/.test(q)) return 'She has no special medical, skilled-nursing, or clinical-support requirement.';
  if (/meal|food|diet/.test(q)) return 'No special dietary requirement. Normal community meal options are acceptable.';
  if (/social|activity|companionship/.test(q)) return 'Social activities are welcome but are not a hard requirement.';
  return 'No additional requirement. She is fully independent and has no special support need in this area.';
}

function attachDecisionDiagnostics(page, label) {
  page.on('response', async (response) => {
    if (!response.url().includes('/decision-engine/recommendations')) return;
    try {
      const requestBody = response.request().postDataJSON();
      const body = await response.json();
      console.log(`${label}_DECISION_REQUEST=${JSON.stringify({ budget: requestBody?.questionnaire_state?.budget, location: requestBody?.questionnaire_state?.referenceLocationValue, notes: requestBody?.questionnaire_state?.notes, adaptiveSignals: requestBody?.questionnaire_state?.humanIntelligenceV2?.scoringEngine?.adaptiveSignals })}`);
      console.log(`${label}_DECISION_RESPONSE=${JSON.stringify({ status: response.status(), result_count: body?.result_count, total_candidates_scored: body?.total_candidates_scored, location_city: body?.patient_needs_profile?.location_city, decision_intelligence: body?.decision_intelligence, recommendations: (body?.results || []).slice(0,5).map((x) => x.facility_name) })}`);
    } catch (error) {
      console.log(`${label}_DECISION_DIAGNOSTIC_ERROR=${String(error)}`);
    }
  });
}

async function openHydrated(page) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await expect(page.getByRole('button', { name: 'my mother', exact: true })).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(1200);
}

async function waitOutLoading(page) {
  const loading = page.getByText('Checking what still matters for this decision...');
  try { await loading.waitFor({ state: 'hidden', timeout: 105000 }); } catch {}
  const retry = page.getByRole('button', { name: 'Retry' });
  if (await retry.isVisible().catch(() => false)) {
    console.log('LIVE_RETRY_USED');
    await retry.click();
    await loading.waitFor({ state: 'hidden', timeout: 105000 });
  }
}

async function answerAdaptiveUntilResults(page, label) {
  const transcript = [];
  for (let turn = 1; turn <= 12; turn++) {
    if (page.url().includes('/results')) break;
    await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 15000 });
    await waitOutLoading(page);
    if (page.url().includes('/results')) break;

    const errorBox = page.locator('.border-rose-200');
    if (await errorBox.isVisible().catch(() => false)) {
      throw new Error(`${label} adaptive interview error: ${await errorBox.innerText()}`);
    }

    const question = page.locator('p.text-xl').last();
    await expect(question).toBeVisible({ timeout: 10000 });
    const qText = (await question.innerText()).trim();
    const answer = answerFor(qText);
    transcript.push({ question: qText, answer });
    console.log(`${label}_TURN_${turn}_QUESTION=${qText}`);
    console.log(`${label}_TURN_${turn}_ANSWER=${answer}`);

    const textarea = page.getByPlaceholder('Answer in your own words');
    if (await textarea.isVisible().catch(() => false)) {
      await textarea.fill(answer);
      await page.getByRole('button', { name: 'Continue' }).click();
    } else {
      const optionButtons = page.locator('button').filter({ hasNotText: /Back|Start over|Edit|Retry/ });
      const labels = await optionButtons.allInnerTexts();
      let target = labels.find(x => /fully independent|independent living/i.test(x));
      if (/memory|cognitive|help|support|medical|nursing/i.test(qText)) target = labels.find(x => /^(no|none|no support|fully independent)$/i.test(x.trim())) || target;
      target = target || labels[0];
      if (!target) throw new Error(`${label}: no answer control for question: ${qText}`);
      await page.getByRole('button', { name: target.trim(), exact: true }).click();
    }
    await page.waitForTimeout(700);
  }
  await expect(page).toHaveURL(/\/results/, { timeout: 120000 });
  return transcript;
}

async function extractTopFacilities(page, label) {
  await page.waitForLoadState('domcontentloaded');
  await page.getByText('Loading results...').waitFor({ state: 'hidden', timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const body = await page.locator('body').innerText();
  const names = [...new Set((await page.locator('h3').allInnerTexts()).map(x => x.trim()).filter(Boolean))].slice(0, 5);
  console.log(`${label}_RESULTS=${JSON.stringify(names)}`);
  if (names.length === 0) {
    console.log(`${label}_RESULTS_BODY=${JSON.stringify(body.slice(0,3000))}`);
    throw new Error(`${label}: results page rendered no facility recommendations`);
  }
  return names;
}

async function structuredJourney(page) {
  attachDecisionDiagnostics(page, 'STRUCTURED');
  await openHydrated(page);
  await page.getByRole('button', { name: 'my mother', exact: true }).click();
  await expect(page.getByRole('heading', { name: /How old is your mother\?/ })).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: '80–84', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'What kind of help is needed today?' })).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: 'fully independent', exact: true }).click();
  await page.getByRole('button', { name: 'Next →', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Are there any memory concerns?' })).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: 'no memory concerns', exact: true }).click();
  await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 15000 });
  const transcript = await answerAdaptiveUntilResults(page, 'STRUCTURED');
  return { transcript, results: await extractTopFacilities(page, 'STRUCTURED') };
}

async function freeTextJourney(page) {
  attachDecisionDiagnostics(page, 'FREETEXT');
  await openHydrated(page);
  await page.getByLabel('Describe your family situation').fill(CLIENT_TEXT);
  await page.getByRole('button', { name: /See options that may fit/ }).click();
  await expect(page).toHaveURL(/\/adaptive-interview/, { timeout: 15000 });
  const transcript = await answerAdaptiveUntilResults(page, 'FREETEXT');
  return { transcript, results: await extractTopFacilities(page, 'FREETEXT') };
}

test('live production: structured questions then same client free text produce the same top results', async ({ browser }) => {
  test.setTimeout(600000);

  const context1 = await browser.newContext();
  const page1 = await context1.newPage();
  const first = await structuredJourney(page1);
  await context1.close();

  const context2 = await browser.newContext();
  const page2 = await context2.newPage();
  const second = await freeTextJourney(page2);
  await context2.close();

  console.log(`STRUCTURED_TRANSCRIPT=${JSON.stringify(first.transcript)}`);
  console.log(`FREETEXT_TRANSCRIPT=${JSON.stringify(second.transcript)}`);
  console.log(`CLIENT_TEXT=${CLIENT_TEXT}`);
  expect(second.results).toEqual(first.results);
});
