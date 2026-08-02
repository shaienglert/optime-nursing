import { describe, expect, it } from "vitest";

import {
  advisorResponseFor,
  buildAssessmentSummary,
  getProgressiveQuestions,
  pruneHiddenAssessmentAnswers,
} from "../src/lib/assessment-conversation";
import { ASSESSMENT_QUESTIONS, UNKNOWN_FROM_FAMILY, type AssessmentAnswers } from "../src/lib/assessment-schema";

const question = (id: string) => ASSESSMENT_QUESTIONS.find((item) => item.id === id)!;

describe("assessment conversation", () => {
  it("reveals only the first unanswered relevant question", () => {
    expect(getProgressiveQuestions({}).map((item) => item.id)).toEqual(["who_needs_care"]);
    expect(getProgressiveQuestions({ who_needs_care: "Mom" }).map((item) => item.id)).toEqual(["who_needs_care", "current_location"]);
  });

  it("restores a draft to the first unanswered conversation block", () => {
    const restored = { who_needs_care: "Mom", current_location: "Miami", current_living_situation: "WITH_FAMILY" };
    expect(getProgressiveQuestions(restored).at(-1)?.id).toBe("mobility");
  });

  it("personalizes relationship wording", () => {
    expect(advisorResponseFor(question("current_location"), { who_needs_care: "Dad" })).toContain("your dad");
  });

  it("uses the approved stroke response template", () => {
    expect(advisorResponseFor(question("physical_therapy"), { rehabilitation_needed: "YES", rehabilitation_focus: ["STROKE"] })).toContain("Stroke recovery");
  });

  it("reassures without converting unknown to no", () => {
    expect(advisorResponseFor(question("current_location"), { who_needs_care: UNKNOWN_FROM_FAMILY })).toContain("unknown rather than assuming no");
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
      preferred_search_area: "Miami-Dade",
      rehabilitation_focus: ["STROKE"],
      mobility: "DEVICE",
      daily_activities: ["BATHING"],
      medication_support: "ADMINISTRATION",
      language_needs: ["HEBREW"],
      dietary_requirements: ["GLUTEN_FREE"],
    });
    expect(summary).toContain("your mom near Miami-Dade");
    expect(summary).toContain("recovering from a stroke");
    expect(summary).toContain("Hebrew support");
    expect(summary).toContain("gluten-free meals");
  });
});