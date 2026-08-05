import { expect, test, type Locator } from "@playwright/test";


const DRAFT_KEY = "optime.family-assessment.v2.draft";

test.use({ video: "on" });

const recommendation = (id: string, name: string) => ({
  canonical_facility_id: id,
  facility_name: name,
  city: "Las Vegas",
  state: "NV",
  facility_profile_id: null,
  eligibility_status: "ELIGIBLE",
  match_score: 88,
  patient_match_score: 88,
  match_band: "STRONG_MATCH",
  matched_needs: [],
  unmet_verified_needs: [],
  unknown_critical_needs: [{ parameter_id: "current_availability" }],
  preference_matches: [],
  evidence_certainty: 82,
  evidence_confidence: 80,
  quality_safety_score: 75,
  staffing_score: 72,
  capability_depth_score: 84,
  patient_relevant_outcomes_score: 78,
  practical_fit_score: 86,
  match_evidence_profile: { proven_critical_matches: 4, taxonomy_supported_critical_matches: 0, unknown_critical_needs: 1, verified_gap_critical_needs: 0 },
  domain_breakdown: {},
  explanation: {
    why_matches: ["Verified information supports the daily assistance and rehabilitation needs your family shared."],
    needs_verification: ["Confirm current availability directly with the community."],
    concerns: [],
    eligibility_reasons: [],
    availability_note: "Current availability still needs confirmation.",
    location_note: "The community is within the selected search area.",
  },
  parameter_badges: [],
  comparison_parameter_ids: [],
});

async function finishWriting(turn: Locator) {
  const writing = turn.locator("[data-advisor-writing]");
  await writing.dispatchEvent("pointerdown", { pointerType: "mouse" });
  await expect(writing).toHaveAttribute("data-writing-state", "complete");
  await expect(turn.locator("[data-answer-choices]")).toBeVisible();
}

async function answerTurn(turn: Locator, labels?: string[]) {
  await finishWriting(turn);
  const requiresConfirmation = await turn.getByRole("button", { name: "Next", exact: true }).count() > 0;
  if (!labels) {
    await turn.locator("[data-answer-choices] button").first().click();
  } else {
    for (const label of labels) {
      await turn.getByRole("button", { name: label, exact: true }).click();
    }
  }
  if (requiresConfirmation) await turn.getByRole("button", { name: "Next", exact: true }).click();
}

test("owner recording: advisor writes one growing document through recommendations", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "The owner recording uses the desktop immersive document composition.");
  test.setTimeout(120_000);

  await page.route("**/api/backend/patient-case/questionnaire", (route) => route.fulfill({ json: { id: 91 } }));
  await page.route("**/api/backend/decision-engine/recommendations", (route) => route.fulfill({ json: {
    patient_case_id: 91,
    patient_needs_profile: { generated_from: { questionnaire: true, natural_language: false }, needs: [], need_tags: [], priority_parameter_ids: [], natural_language_mapping: {} },
    results: [recommendation("one", "Desert Springs Care Center"), recommendation("two", "Silver Hills Community"), recommendation("three", "Red Rock Care Center")],
    result_count: 3,
    total_candidates_scored: 3,
    availability_policy: "Verify directly",
  } }));

  await page.goto("/");
  await page.evaluate((key) => localStorage.removeItem(key), DRAFT_KEY);
  await page.reload();
  const initialUrl = page.url();
  const firstTen: Record<string, string[]> = {
    who_needs_care: ["My mom"],
    preferred_search_area: ["Summerlin"],
    avoid_search_areas: ["No areas to avoid"],
    urgency: ["Within 30 days"],
    urgent_availability: ["Yes"],
    current_living_situation: ["Lives with family"],
    mobility: ["Uses a cane, walker, or wheelchair", "Needs some help from another person"],
    daily_activities: ["Bathing", "Dressing"],
    transfer_assistance: ["One-person assistance"],
    medication_support: ["Needs staff to administer medications"],
  };
  const retainedIds: string[] = [];
  let previousHeight = await page.evaluate(() => document.documentElement.scrollHeight);

  for (let index = 0; index < 10; index += 1) {
    const turn = page.locator("[data-next-question-id]");
    await expect(turn).toHaveCount(1);
    const questionId = await turn.getAttribute("data-next-question-id");
    expect(questionId).toBeTruthy();
    await turn.scrollIntoViewIfNeeded();
    const writing = turn.locator("[data-advisor-writing]");
    await expect(writing).not.toHaveAttribute("data-writing-state", "complete");
    await page.waitForTimeout(320);
    await expect(writing).toHaveAttribute("data-writing-state", /response|prompt/);
    const advisorText = await turn.locator("p").first().innerText();
    const fullAdvisorText = await turn.locator("p").first().getAttribute("aria-label");
    const promptText = await turn.locator("legend").innerText();
    const fullPromptText = await turn.locator("legend").getAttribute("aria-label");
    expect(advisorText.length + promptText.length).toBeGreaterThan(0);
    expect(advisorText.length + promptText.length).toBeLessThan(fullAdvisorText!.length + fullPromptText!.length);

    const answeredBefore = retainedIds.length;
    await answerTurn(turn, firstTen[questionId!]);
    retainedIds.push(questionId!);
    await expect(page.locator("[data-answered-question-id]")).toHaveCount(answeredBefore + 1);
    for (const retainedId of retainedIds) await expect(page.locator(`[data-answered-question-id='${retainedId}']`)).toBeVisible();
    await expect(page.locator("[data-next-question-id]")).toHaveCount(1);
    const nextHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(nextHeight).toBeGreaterThan(previousHeight);
    previousHeight = nextHeight;
    await expect(page).toHaveURL(initialUrl);
  }

  for (let guard = 0; guard < 50 && await page.locator("[data-next-question-id]").count(); guard += 1) {
    const turn = page.locator("[data-next-question-id]");
    const answeredBefore = await page.locator("[data-answered-question-id]").count();
    await turn.scrollIntoViewIfNeeded();
    await answerTurn(turn);
    await expect(page.locator("[data-answered-question-id]")).toHaveCount(answeredBefore + 1);
  }

  await expect(page.locator("[data-next-question-id]")).toHaveCount(0);
  await expect(page.locator("[data-home-progress]").first()).toHaveAttribute("data-home-ready", "true");
  const readiness = page.locator("[data-advisor-writing-block='readiness']");
  await readiness.dispatchEvent("pointerdown", { pointerType: "mouse" });
  await expect(readiness).toHaveAttribute("data-writing-state", "complete");
  await page.locator("section[aria-labelledby='document-summary-heading']").getByRole("button", { name: "Find My Best Matches", exact: true }).click();

  const comparison = page.locator("[data-comparison-narrative]");
  await expect(comparison).toBeVisible();
  await page.waitForTimeout(420);
  await comparison.locator("[data-advisor-writing-block='comparison']").dispatchEvent("pointerdown", { pointerType: "mouse" });
  await expect(page.getByRole("heading", { name: "Desert Springs Care Center" })).toBeVisible();
  expect(await page.locator("[data-answered-question-id]").count()).toBeGreaterThan(10);
  await expect(page).toHaveURL(initialUrl);
  await page.screenshot({ path: testInfo.outputPath("owner-living-document-final.png"), fullPage: true });
});