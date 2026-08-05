import { describe, expect, it } from "vitest";

import {
  assessmentAnswerLabel,
  advisorResponseFor,
  buildAssessmentSummary,
  buildConversationCheckpoint,
  completedAnswerSentence,
  getProgressiveQuestions,
  pruneHiddenAssessmentAnswers,
} from "../src/lib/assessment-conversation";
import { ADVISOR_PARAMETER_COUNT, buildAdvisorCompletionSummary, buildAdvisorPrompt, getAdvisorInteractionMetrics, isAdvisorQuestionRelevant, selectAdvisorTurn } from "../src/lib/assessment-advisor";
import { ASSESSMENT_QUESTIONS, UNKNOWN_FROM_FAMILY, type AssessmentAnswers } from "../src/lib/assessment-schema";

const question = (id: string) => ASSESSMENT_QUESTIONS.find((item) => item.id === id)!;

describe("assessment conversation", () => {
  it("reveals only the first unanswered relevant question", () => {
    expect(getProgressiveQuestions({}).map((item) => item.id)).toEqual(["who_needs_care"]);
    expect(getProgressiveQuestions({ who_needs_care: "Mom" }).map((item) => item.id)).toEqual(["who_needs_care", "current_living_situation"]);
  });

  it("restores a draft to the first unanswered conversation block", () => {
    const restored = { who_needs_care: "Mom", current_living_situation: "WITH_FAMILY" };
    expect(getProgressiveQuestions(restored).at(-1)?.id).toBe("mobility");
  });

  it("personalizes relationship wording", () => {
    expect(buildAdvisorPrompt(question("mobility"), { who_needs_care: "Dad" })).toContain("your dad");
  });

  it("connects follow-up wording to earlier answers", () => {
    expect(buildAdvisorPrompt(question("daily_activities"), { who_needs_care: "Mom", mobility: ["DEVICE", "SOME_HELP"] }))
      .toContain("your mom uses a cane, walker, or wheelchair");
    expect(buildAdvisorPrompt(question("stroke_recovery"), { who_needs_care: "Dad", rehabilitation_focus: ["STROKE"] }))
      .toContain("your dad's care plan includes stroke recovery");
    expect(buildAdvisorPrompt(question("monthly_budget"), { who_needs_care: "Mom", payment_method: ["PRIVATE_PAY"] }))
      .toContain("private pay may be part of the plan");
  });

  it("uses the approved stroke response template", () => {
    expect(advisorResponseFor(question("rehabilitation_services"), { rehabilitation_needed: "YES", rehabilitation_focus: ["STROKE"] })).toContain("Stroke recovery");
  });

  it("reassures without converting unknown to no", () => {
    expect(advisorResponseFor(question("current_living_situation"), { who_needs_care: UNKNOWN_FROM_FAMILY })).toContain("unknown rather than assuming no");
  });

  it("clears dependent answers when a parent answer changes", () => {
    const answers: AssessmentAnswers = { rehabilitation_needed: "NO", rehabilitation_focus: ["STROKE"], stroke_recovery: "YES" };
    const result = pruneHiddenAssessmentAnswers(answers);
    expect(result.answers.rehabilitation_focus).toBeUndefined();
    expect(result.answers.stroke_recovery).toBeUndefined();
    expect(result.clearedQuestionIds).toEqual(expect.arrayContaining(["rehabilitation_focus", "stroke_recovery"]));
  });

  it("generates a family-facing live summary", () => {
    const summary = buildAssessmentSummary({
      who_needs_care: "Mom",
      preferred_search_area: ["SUMMERLIN", "HENDERSON"],
      rehabilitation_focus: ["STROKE"],
      mobility: ["DEVICE"],
      daily_activities: ["BATHING"],
      medication_support: "ADMINISTRATION",
      language_needs: ["HEBREW"],
      dietary_requirements: ["GLUTEN_FREE"],
    });
    expect(summary).toContain("your mom near Summerlin, Henderson");
    expect(summary).toContain("recovering from a stroke");
    expect(summary).toContain("Hebrew support");
    expect(summary).toContain("gluten-free meals");
  });

  it("turns structured answers into conversational checkpoint language", () => {
    const answers: AssessmentAnswers = {
      who_needs_care: "Dad",
      preferred_search_area: ["SUMMERLIN"],
      urgency: "WITHIN_30_DAYS",
    };
    const questions = [question("who_needs_care"), question("preferred_search_area"), question("urgency")];
    const checkpoint = buildConversationCheckpoint(questions, answers);
    expect(checkpoint).toContain("your dad near Summerlin");
    expect(checkpoint).toContain("Care may be needed within 30 days");
    expect(assessmentAnswerLabel(question("who_needs_care"), answers)).toBe("My dad");
  });

  it("turns every completed answer into a visible document sentence", () => {
    const answers: AssessmentAnswers = {
      who_needs_care: "Mom",
      preferred_search_area: ["SUMMERLIN"],
      mobility: ["DEVICE"],
      daily_activities: ["BATHING"],
      rehabilitation_focus: ["STROKE"],
      dietary_requirements: ["GLUTEN_FREE"],
      language_needs: ["HEBREW"],
      family_priorities: ["CLINICAL_FIT", "REHABILITATION"],
    };
    for (const questionId of Object.keys(answers)) {
      expect(completedAnswerSentence(question(questionId), answers).trim()).not.toBe("");
    }
  });

  it("chooses the uncertainty with the greatest immediate decision impact", () => {
    expect(selectAdvisorTurn({})?.question.id).toBe("who_needs_care");
    expect(selectAdvisorTurn({ who_needs_care: "Dad", preferred_search_area: ["SUMMERLIN"] })?.question.id).toBe("avoid_search_areas");
    expect(selectAdvisorTurn({ who_needs_care: "Dad", preferred_search_area: ["SUMMERLIN"], avoid_search_areas: ["NONE"] })?.question.id).toBe("urgency");
    expect(selectAdvisorTurn({ who_needs_care: "Dad", urgency: "WITHIN_30_DAYS" })?.question.id).toBe("urgent_availability");
    expect(selectAdvisorTurn({ rehabilitation_needed: "YES", rehabilitation_focus: ["STROKE"] })?.question.id).toBe("stroke_recovery");
    expect(selectAdvisorTurn({ payment_method: ["PRIVATE_PAY"] })?.question.id).toBe("monthly_budget");
    expect(selectAdvisorTurn({ language_needs: ["HEBREW"] })?.question.id).toBe("hebrew_support");
  });

  it("explains each advisor decision from known facts and uncertainty", () => {
    const turn = selectAdvisorTurn({
      who_needs_care: "Dad",
      rehabilitation_needed: "YES",
      rehabilitation_focus: ["STROKE"],
    });

    expect(turn?.question.id).toBe("stroke_recovery");
    expect(turn?.knownFacts.join(" ")).toContain("your dad");
    expect(turn?.knownFacts.join(" ").toLowerCase()).toContain("stroke recovery");
    expect(turn?.uncertainties.join(" ")).toContain("dedicated stroke program");
    expect(turn?.rationale).toContain("why I’m asking");
    expect(turn?.knowledgeSources).toEqual(expect.arrayContaining(["care-path knowledge", "rehabilitation knowledge", "facility evidence rules"]));
    expect(turn?.canonicalParameters.map((parameter) => parameter.parameterId)).toContain("post_stroke_neuro_evidence");
    expect(turn?.canonicalParameters[0]?.currentCoveragePercent).toBeGreaterThanOrEqual(0);
    expect(turn?.canonicalParameters[0]?.recommendedActionWhenMissing).toContain("UNKNOWN");
    expect(turn?.informationGainScore).toBeGreaterThan(0);
    expect(turn?.informationGainScore).toBeLessThanOrEqual(100);
  });

  it("uses every canonical facility parameter definition through the generated advisor index", () => {
    expect(ADVISOR_PARAMETER_COUNT).toBe(59);
  });

  it("keeps unknown answers unresolved without asking them again or treating them as no", () => {
    const turn = selectAdvisorTurn({ who_needs_care: "Dad", urgency: UNKNOWN_FROM_FAMILY });
    expect(turn?.question.id).not.toBe("urgency");
    expect(turn?.question.id).not.toBe("urgent_availability");
    expect(turn?.uncertainties.join(" ")).toContain("remains unknown");
  });

  it("skips questions that cannot affect recommendation quality", () => {
    const answers = Object.fromEntries(
      ASSESSMENT_QUESTIONS
        .filter(isAdvisorQuestionRelevant)
        .map((item) => [item.id, item.answerType === "multi" || item.answerType === "priority" ? [UNKNOWN_FROM_FAMILY] : UNKNOWN_FROM_FAMILY]),
    );
    expect(selectAdvisorTurn(answers)).toBeNull();
  });

  it("keeps at least 95 percent of advisor interactions selection based", () => {
    expect(getAdvisorInteractionMetrics().selectionPercentage).toBeGreaterThanOrEqual(95);
  });

  it("summarizes confidence and automatic verification without a technical score", () => {
    const summary = buildAdvisorCompletionSummary({
      who_needs_care: "Dad",
      preferred_search_area: ["LAS_VEGAS_VALLEY"],
      urgency: "WITHIN_30_DAYS",
      urgent_availability: UNKNOWN_FROM_FAMILY,
    });
    expect(["Strong", "Developing", "Limited"]).toContain(summary.confidence);
    expect(summary.stillNeedsConfirmation).toContain("Is immediate bed availability a deal-breaker");
    expect(summary.automaticVerification.length).toBeGreaterThan(0);
  });
});