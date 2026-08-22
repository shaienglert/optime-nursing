const { test, expect } = require('@playwright/test');

function profileFor(signals) {
  if (signals.length === 0) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        adaptive_questions: [{
          question_key: 'browser-q1',
          question: 'Does the resident need help with daily activities?',
          reason: 'This can materially change the care setting.',
          information_gain: 'HIGH',
          answer_options: ['Yes', 'No'],
        }],
      },
    };
  }
  if (signals.length === 1) {
    return {
      decision_intelligence: {
        decision_readiness: 'NEEDS_CLARIFICATION',
        adaptive_questions: [{
          question_key: 'browser-q2',
          question: 'What walking distance is comfortable?',
          reason: 'Layout can be a MUST constraint.',
          information_gain: 'HIGH',
        }],
      },
    };
  }
  return { decision_intelligence: { decision_readiness: 'READY', adaptive_questions: [] } };
}

const emptyDecisionResponse = {
  patient_needs_profile: {
    needs: [],
    need_tags: [],
    priority_parameter_ids: [],
  },
  results: [],
  tie_break_decisions: [],
};

test('adaptive interview supports Continue, Back, Edit, results review and Start over', async ({ page }) => {
  await page.route('**/api/backend/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/decision-engine/patient-needs-profile')) {
      const body = route.request().postDataJSON();
      const signals = body?.questionnaire_state?.humanIntelligenceV2?.scoringEngine?.adaptiveSignals || [];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profileFor(signals)) });
    }
    if (url.includes('/human-intelligence/adaptive-response')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyDecisionResponse) });
  });

  await page.goto('http://127.0.0.1:3000/adaptive-interview');
  await expect(page.getByText('Does the resident need help with daily activities?')).toBeVisible();
  await page.getByRole('button', { name: 'Yes' }).click();
  await expect(page.getByText('What walking distance is comfortable?')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible();
  await page.getByPlaceholder('Answer in your own words').fill('About 100 meters.');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page).toHaveURL(/\/results/);
  await expect(page.getByRole('link', { name: 'Change decision answers' })).toBeVisible();
  await page.getByRole('link', { name: 'Change decision answers' }).click();
  await expect(page.getByRole('heading', { name: 'Your answers' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(2);
  await page.getByRole('button', { name: 'Edit' }).first().click();
  await expect(page.getByText('Does the resident need help with daily activities?')).toBeVisible();
  await page.getByRole('button', { name: 'No' }).click();
  await expect(page.getByText('What walking distance is comfortable?')).toBeVisible();
  await page.getByRole('button', { name: 'Back' }).click();
  await expect(page.getByText('Does the resident need help with daily activities?')).toBeVisible();
  await page.getByRole('button', { name: 'Start over' }).click();
  await expect(page.getByText('Does the resident need help with daily activities?')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(0);
});

test('intake family-member selection must not navigate or jump backward', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000/intake');
  const familyQuestion = page.getByText('How many family members are actively involved?');
  await expect(familyQuestion).toHaveCount(1);

  const initial = await familyQuestion.evaluate((el) => ({
    display: getComputedStyle(el).display,
    visibility: getComputedStyle(el).visibility,
    rectTop: el.getBoundingClientRect().top,
    rectHeight: el.getBoundingClientRect().height,
  }));
  console.log('FAMILY_INITIAL_DOM', JSON.stringify(initial));

  await familyQuestion.evaluate((el) => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await page.waitForTimeout(100);
  const familyBlock = familyQuestion.locator('xpath=..');
  const option = familyBlock.getByRole('button', { name: '2', exact: true });
  const before = await page.evaluate(() => ({ url: location.pathname + location.search, y: window.scrollY }));
  const beforeRect = await familyQuestion.evaluate((el) => el.getBoundingClientRect().top);

  await option.evaluate((el) => el.click());
  await page.waitForTimeout(300);

  const after = await page.evaluate(() => ({ url: location.pathname + location.search, y: window.scrollY }));
  const afterRect = await familyQuestion.evaluate((el) => el.getBoundingClientRect().top);
  const selectedClass = await option.getAttribute('class');
  console.log('FAMILY_MEMBER_SELECTION_TRACE', JSON.stringify({ before, after, beforeRect, afterRect, selectedClass }));

  expect(after.url).toBe('/intake');
  expect(Math.abs(afterRect - beforeRect)).toBeLessThan(120);
  expect(Math.abs(after.y - before.y)).toBeLessThan(120);
  expect(selectedClass || '').toContain('bg-[#7f9f88]');
});
