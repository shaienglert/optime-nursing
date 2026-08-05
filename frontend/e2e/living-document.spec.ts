import { expect, test, type Page } from "@playwright/test";

import { isAdvisorQuestionRelevant } from "../src/lib/assessment-advisor";
import { ASSESSMENT_QUESTIONS, UNKNOWN_FROM_FAMILY, type AssessmentAnswers } from "../src/lib/assessment-schema";

const DRAFT_KEY = "optime.family-assessment.v2.draft";

async function startFresh(page: Page, path = "/") {
  await page.goto(path);
  await page.evaluate((key) => localStorage.removeItem(key), DRAFT_KEY);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Finding the Right Care for Your Family" })).toBeVisible();
}

async function answerFirstFive(page: Page) {
  await page.getByRole("button", { name: "My mom", exact: true }).click();
  await page.getByRole("button", { name: "Summerlin", exact: true }).click();
  await page.getByRole("button", { name: "No areas to avoid", exact: true }).click();
  await page.getByRole("button", { name: "Within 30 days", exact: true }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.locator("[data-answered-question-id]" )).toHaveCount(5);
}

async function prepareScreenshot(page: Page) {
  await page.addStyleTag({ content: "header, [role='banner'] { position: static !important; } nextjs-portal { display: none !important; }" });
}

function completeAnswers(): AssessmentAnswers {
  return Object.fromEntries(
    ASSESSMENT_QUESTIONS
      .filter(isAdvisorQuestionRelevant)
      .map((question) => [question.id, question.id === "who_needs_care" ? "Mom" : question.answerType === "multi" || question.answerType === "priority" ? [UNKNOWN_FROM_FAMILY] : UNKNOWN_FROM_FAMILY]),
  );
}

const recommendation = (id: string, name: string) => ({
  canonical_facility_id: id,
  facility_name: name,
  city: "Las Vegas",
  state: "NV",
  facility_profile_id: null,
  eligibility_status: "ELIGIBLE",
  match_score: 0,
  patient_match_score: 0,
  match_band: "GOOD_MATCH",
  matched_needs: [],
  unmet_verified_needs: [],
  unknown_critical_needs: [{ parameter_id: "therapy_schedule" }],
  preference_matches: [],
  evidence_certainty: 0,
  evidence_confidence: 0,
  quality_safety_score: null,
  staffing_score: null,
  capability_depth_score: null,
  patient_relevant_outcomes_score: null,
  practical_fit_score: null,
  match_evidence_profile: { proven_critical_matches: 2, taxonomy_supported_critical_matches: 0, unknown_critical_needs: 1, verified_gap_critical_needs: 0 },
  domain_breakdown: {},
  explanation: {
    why_matches: ["The current evidence supports the rehabilitation and mobility needs you shared.", "The community is in the area your family selected."],
    needs_verification: ["Confirm the current therapy schedule and bed availability."],
    concerns: [],
    eligibility_reasons: [],
    availability_note: "Current availability still needs confirmation.",
    location_note: "The community is near the preferred area.",
  },
  parameter_badges: [],
  comparison_parameter_ids: [],
});

test("the homepage and compatibility route begin the same advisor immediately", async ({ page }) => {
  await startFresh(page, "/");
  await expect(page.getByRole("group", { name: "Who are you helping find care?" })).toBeVisible();
  await startFresh(page, "/assessment");
  await expect(page.getByRole("group", { name: "Who are you helping find care?" })).toBeVisible();
});

test("answers append, retain prior questions, stay contextual, and remain editable", async ({ page }, testInfo) => {
  await startFresh(page);
  const initialUrl = page.url();
  const firstQuestionText = await page.locator("[data-next-question-id] legend").innerText();
  const completedTurns: Array<{ questionId: string; questionText: string; answerText: string }> = [];
  const steps = [
    { option: "My mom", answerText: "right care for your mom" },
    { option: "Summerlin", answerText: "Summerlin" },
    { option: "No areas to avoid", answerText: "no Las Vegas Valley areas to exclude" },
    { option: "Within 30 days", answerText: "within 30 days" },
    { option: "Yes", answerText: "timely opening is a deal-breaker" },
  ];
  let previousHeight = await page.evaluate(() => document.documentElement.scrollHeight);

  for (const step of steps) {
    const activeTurn = page.locator("[data-next-question-id]");
    await expect(activeTurn).toHaveCount(1);
    const questionId = await activeTurn.getAttribute("data-next-question-id");
    const questionText = await activeTurn.locator("legend").innerText();
    expect(questionId).toBeTruthy();

    await activeTurn.getByRole("button", { name: step.option, exact: true }).click();
    const nextButton = activeTurn.getByRole("button", { name: "Next", exact: true });
    if (await nextButton.count()) await nextButton.click();

    const completedTurn = page.locator(`[data-answered-question-id='${questionId}']`);
    await expect(completedTurn).toBeVisible();
    await expect(completedTurn).toContainText(questionText);
    await expect(completedTurn).toContainText(step.answerText);
    await expect(completedTurn.locator("[data-selected-answer]")).toContainText(step.option);
    completedTurns.push({ questionId: questionId!, questionText, answerText: step.answerText });

    for (const completed of completedTurns) {
      const retainedTurn = page.locator(`[data-answered-question-id='${completed.questionId}']`);
      await expect(retainedTurn).toBeVisible();
      await expect(retainedTurn).toContainText(completed.questionText);
      await expect(retainedTurn).toContainText(completed.answerText);
    }

    const sequence = await page.locator("[data-conversation-question-id]").evaluateAll((items) => items.map((item) => ({
      questionId: item.getAttribute("data-conversation-question-id"),
      top: item.getBoundingClientRect().top + window.scrollY,
    })));
    expect(sequence.slice(0, completedTurns.length).map((item) => item.questionId)).toEqual(completedTurns.map((item) => item.questionId));
    expect(sequence).toHaveLength(completedTurns.length + 1);
    for (let index = 1; index < sequence.length; index += 1) expect(sequence[index].top).toBeGreaterThan(sequence[index - 1].top);

    const nextHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(nextHeight).toBeGreaterThan(previousHeight);
    previousHeight = nextHeight;

    await expect(page.locator("[data-assessment-environment]")).toBeVisible();
    await expect(page.locator("[data-home-progress]")).toHaveCount(1);
    if (completedTurns.length === 1) {
      if (testInfo.project.name === "desktop") {
        await prepareScreenshot(page);
        await page.screenshot({ path: testInfo.outputPath("desktop-one-answer.png"), fullPage: true });
      }
    }
    await expect(page).toHaveURL(initialUrl);
  }

  expect(completedTurns[0].questionText).toBe(firstQuestionText);
  await expect(page.locator("[data-answered-question-id]")).toHaveCount(5);
  await expect(page.locator("[data-next-question-id]")).toHaveCount(1);
  await expect(page.getByText("What I understand so far")).toHaveCount(0);

  await expect(page.locator("[data-next-question-id] [data-advisor-writing]")).toHaveAttribute("data-writing-state", "complete");
  await prepareScreenshot(page);
  await page.screenshot({ path: testInfo.outputPath("desktop-five-answers.png"), fullPage: true });

  const nextQuestionId = await page.locator("[data-next-question-id]").getAttribute("data-next-question-id");
  await page.locator("[data-answered-question-id='who_needs_care']").getByRole("button", { name: "Edit this detail" }).click();
  await expect(page.locator("[data-answered-question-id='who_needs_care']")).toBeVisible();
  await expect(page.getByRole("button", { name: "My dad", exact: true })).toBeVisible();
  await expect(page.locator(`[data-next-question-id='${nextQuestionId}']`)).toBeVisible();
  await expect(page.locator("[data-answered-question-id]")).toHaveCount(5);
  await expect(page).toHaveURL(initialUrl);

  await page.getByRole("button", { name: "My dad", exact: true }).click();
  await expect(page.locator("[data-answered-question-id='who_needs_care']")).toContainText("right care for your dad");
  await expect(page.locator(`[data-next-question-id='${nextQuestionId}']`)).toBeVisible();
  await expect(page.locator("[data-answered-question-id]")).toHaveCount(5);

  await page.locator("[data-answered-question-id='urgency']").getByRole("button", { name: "Edit this detail" }).click();
  await page.locator("[data-answered-question-id='urgency']").getByRole("button", { name: "Just exploring", exact: true }).click();
  await expect(page.locator("[data-answered-question-id='urgency']")).toContainText("just exploring");
  await expect(page.locator("[data-answered-question-id='urgent_availability']")).toHaveCount(0);
  for (const retainedQuestionId of completedTurns.map((turn) => turn.questionId).filter((questionId) => questionId !== "urgent_availability")) {
    await expect(page.locator(`[data-answered-question-id='${retainedQuestionId}']`)).toBeVisible();
  }
  await expect(page.locator("[data-answered-question-id]")).toHaveCount(4);
  await expect(page.locator("[data-next-question-id]")).toHaveCount(1);
  await expect(page).toHaveURL(initialUrl);
});

test("recommendations continue below the conversation without technical tables", async ({ page }, testInfo) => {
  const answers = completeAnswers();
  await page.addInitScript(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)), {
    key: DRAFT_KEY,
    value: { answers, currentQuestionId: "family_priorities", updatedAt: new Date().toISOString() },
  });
  await page.route("**/api/backend/patient-case/questionnaire", (route) => route.fulfill({ json: { id: 42 } }));
  await page.route("**/api/backend/decision-engine/recommendations", (route) => route.fulfill({ json: {
    patient_case_id: 42,
    patient_needs_profile: { generated_from: { questionnaire: true, natural_language: false }, needs: [], need_tags: [], priority_parameter_ids: [], natural_language_mapping: {} },
    results: [recommendation("one", "Desert Springs Care Center"), recommendation("two", "Silver Hills Community"), recommendation("three", "Red Rock Care Center")],
    result_count: 3,
    total_candidates_scored: 3,
    availability_policy: "Verify directly",
  } }));

  await page.goto("/");
  const url = page.url();
  await expect(page.locator("[data-home-progress]")).toHaveAttribute("data-home-ready", "true");
  await expect(page.locator("[data-assessment-environment]")).toHaveAttribute("data-reveal-ready", "true");
  const readinessHeading = page.getByRole("heading", { name: "I now understand enough about your family's needs to begin finding the communities most likely to fit." });
  await expect(readinessHeading).toBeVisible();
  await expect(page.locator("[data-advisor-writing-block='readiness']")).toHaveAttribute("data-writing-state", "complete");
  await prepareScreenshot(page);
  await page.screenshot({ path: testInfo.outputPath("completed-house-ready.png"), fullPage: true });
  await page.locator("section[aria-labelledby='document-summary-heading']").getByRole("button", { name: "Find My Best Matches", exact: true }).click();
  await expect(page.locator("[data-comparison-narrative]")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Desert Springs Care Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why this appears to fit your mom", exact: true }).first()).toBeVisible();
  await expect(page.getByText("Community photo is being verified.").first()).toBeVisible();
  await expect(page.getByText("No material concerns were identified in the sources currently available.").first()).toBeVisible();
  await expect(page).toHaveURL(url);
  await expect(page.locator("table")).toHaveCount(0);
  await expect(page.getByText(/runtime version/i)).toHaveCount(0);
  await expect(page.getByText(/confidence percentage/i)).toHaveCount(0);

  await expect(page.locator("[data-advisor-writing-block='comparison']")).toHaveAttribute("data-writing-state", "complete");
  await prepareScreenshot(page);
  await page.screenshot({ path: testInfo.outputPath("recommendations-continuation.png"), fullPage: true });
});

test("mobile remains selection-first, readable, and free of horizontal overflow", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Mobile-only accessibility check");
  await startFresh(page);
  await answerFirstFive(page);
  await expect(page.locator("[data-assessment-environment]")).toBeVisible();
  await expect(page.locator("[data-home-progress]")).toHaveCount(1);
  const metrics = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    smallestOptionHeight: Math.min(...Array.from(document.querySelectorAll<HTMLButtonElement>("button[aria-pressed]")).map((button) => button.getBoundingClientRect().height)),
    bodyFontSize: Number.parseFloat(getComputedStyle(document.querySelector("main")!).fontSize),
    textInputs: document.querySelectorAll("input[type='text'], textarea").length,
  }));
  expect(metrics.overflow).toBeLessThanOrEqual(1);
  expect(metrics.smallestOptionHeight).toBeGreaterThanOrEqual(44);
  expect(metrics.bodyFontSize).toBeGreaterThanOrEqual(16);
  expect(metrics.textInputs).toBe(0);
  await expect(page.locator("[data-next-question-id] [data-advisor-writing]")).toHaveAttribute("data-writing-state", "complete");
  await prepareScreenshot(page);
  await page.screenshot({ path: testInfo.outputPath("mobile-five-answers.png"), fullPage: true });
});

test("Las Vegas choices are visible, multi-selectable, remembered, and touch friendly", async ({ page }, testInfo) => {
  await startFresh(page);
  const relationshipTurn = page.locator("[data-next-question-id='who_needs_care']");
  await expect(relationshipTurn.getByRole("group").locator("button[aria-pressed]")).toHaveCount(8);
  await expect(relationshipTurn.getByText(/See .*more choices/)).toHaveCount(0);
  await relationshipTurn.getByRole("button", { name: "My mom", exact: true }).click();

  const locationTurn = page.locator("[data-next-question-id='preferred_search_area']");
  await expect(locationTurn).toContainText("current demonstration market is Las Vegas, Nevada");
  await expect(locationTurn.getByRole("group").locator("button[aria-pressed]")).toHaveCount(10);
  await expect(locationTurn.getByRole("button", { name: "Las Vegas", exact: true })).toBeVisible();
  await expect(locationTurn.getByText(/See .*more choices/)).toHaveCount(0);
  await locationTurn.getByRole("button", { name: "Summerlin", exact: true }).click();
  await expect(page.locator("[data-next-question-id='preferred_search_area']")).toBeVisible();
  await expect.poll(() => page.evaluate((key) => JSON.parse(localStorage.getItem(key) || "{}").answers?.preferred_search_area, DRAFT_KEY)).toEqual(["SUMMERLIN"]);
  await locationTurn.getByRole("button", { name: "Henderson", exact: true }).click();
  await expect(locationTurn.getByRole("button", { name: "Summerlin", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(locationTurn.getByRole("button", { name: "Henderson", exact: true })).toHaveAttribute("aria-pressed", "true");
  const optionHeights = await locationTurn.getByRole("group").locator("button[aria-pressed]").evaluateAll((buttons) => buttons.map((button) => button.getBoundingClientRect().height));
  expect(Math.min(...optionHeights)).toBeGreaterThanOrEqual(48);
  await expect(page.locator("[data-next-question-id='preferred_search_area']")).toBeVisible();
  await expect(page.locator("[data-answered-question-id='preferred_search_area']")).toHaveCount(0);
  await locationTurn.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator("[data-answered-question-id='preferred_search_area']")).toContainText("Summerlin, Henderson");

  const avoidTurn = page.locator("[data-next-question-id='avoid_search_areas']");
  await expect(avoidTurn).toBeVisible();
  await expect(avoidTurn.getByRole("group").locator("button[aria-pressed]")).toHaveCount(10);
  await avoidTurn.getByRole("button", { name: "Paradise", exact: true }).click();
  await avoidTurn.getByRole("button", { name: "Spring Valley", exact: true }).click();
  await expect(page.locator("[data-next-question-id='avoid_search_areas']")).toBeVisible();
  await avoidTurn.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator("[data-answered-question-id='avoid_search_areas']")).toContainText("Paradise, Spring Valley");
  await expect(page.getByText(/What city/i)).toHaveCount(0);

  await prepareScreenshot(page);
  await page.screenshot({ path: testInfo.outputPath("las-vegas-multi-select.png"), fullPage: true });
});

test("the twelve-choice priority list expands only after ten", async ({ page }) => {
  const answers = completeAnswers();
  delete answers.family_priorities;
  await page.addInitScript(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)), {
    key: DRAFT_KEY,
    value: { answers, currentQuestionId: "family_priorities", updatedAt: new Date().toISOString() },
  });
  await page.goto("/");
  const priorityTurn = page.locator("[data-next-question-id='family_priorities']");
  await expect(priorityTurn.getByRole("button", { name: "Private room", exact: true })).toBeVisible();
  await expect(priorityTurn.getByRole("button", { name: "Price", exact: true })).toHaveCount(0);
  await expect(priorityTurn.getByRole("button", { name: "Immediate availability", exact: true })).toHaveCount(0);
  await priorityTurn.getByRole("button", { name: "See 2 more choices" }).click();
  await expect(priorityTurn.getByRole("button", { name: "Price", exact: true })).toBeVisible();
  await expect(priorityTurn.getByRole("button", { name: "Immediate availability", exact: true })).toBeVisible();
});

test("rehabilitation therapies share one multi-select question", async ({ page }) => {
  const answers = completeAnswers();
  answers.rehabilitation_needed = "YES";
  answers.rehabilitation_focus = ["STROKE"];
  delete answers.rehabilitation_services;
  await page.addInitScript(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)), {
    key: DRAFT_KEY,
    value: { answers, currentQuestionId: "rehabilitation_services", updatedAt: new Date().toISOString() },
  });
  await page.goto("/");
  const rehabilitationTurn = page.locator("[data-next-question-id='rehabilitation_services']");
  await expect(rehabilitationTurn).toBeVisible();
  await expect(rehabilitationTurn.getByRole("group").locator("button[aria-pressed]")).toHaveCount(5);
  await rehabilitationTurn.getByRole("button", { name: "Physical therapy", exact: true }).click();
  await rehabilitationTurn.getByRole("button", { name: "Speech or swallowing therapy", exact: true }).click();
  await expect(page.locator("[data-next-question-id='rehabilitation_services']")).toBeVisible();
  await rehabilitationTurn.getByRole("button", { name: "Next", exact: true }).click();
  const completed = page.locator("[data-answered-question-id='rehabilitation_services']");
  await expect(completed).toContainText("Physical therapy, Speech or swallowing therapy");
  await expect(page.locator("[data-next-question-id='physical_therapy'], [data-next-question-id='occupational_therapy'], [data-next-question-id='speech_therapy']")).toHaveCount(0);
});

test("reduced motion presents finished advisor prose and choices immediately", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await startFresh(page);
  const turn = page.locator("[data-next-question-id='who_needs_care']");
  await expect(turn.locator("[data-advisor-writing]")).toHaveAttribute("data-writing-state", "complete");
  await expect(turn.getByRole("group", { name: "Who are you helping find care?" })).toBeVisible();
  await expect(turn.locator("[data-writing-cursor]")).toHaveCount(0);
  await expect.poll(() => page.locator("[data-assessment-environment] img").first().evaluate((image) => getComputedStyle(image).transitionDuration)).toBe("0s");
});