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
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
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
