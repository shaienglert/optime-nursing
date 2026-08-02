import { describe, expect, it } from "vitest";

import { ASSESSMENT_QUESTIONS, ASSESSMENT_SCHEMA_VERSION, DECISION_AREAS, UNKNOWN_FROM_FAMILY, getVisibleQuestions } from "../src/lib/assessment-schema";

describe("family assessment schema", () => {
  it("covers every required decision area with stable mappings", () => {
    const ids = ASSESSMENT_QUESTIONS.map((question) => question.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ASSESSMENT_QUESTIONS).toHaveLength(34);
    expect(ASSESSMENT_QUESTIONS.filter((question) => question.showIf)).toHaveLength(12);
    expect(ASSESSMENT_QUESTIONS.every((question) => question.version === ASSESSMENT_SCHEMA_VERSION)).toBe(true);
    expect(ASSESSMENT_QUESTIONS.every((question) => question.canonicalMappings.length > 0)).toBe(true);
    for (const area of DECISION_AREAS) {
      expect(ASSESSMENT_QUESTIONS.some((question) => question.decisionArea === area)).toBe(true);
    }
  });

  it("uses explicit uncertainty and valid conditional references", () => {
    const ids = new Set(ASSESSMENT_QUESTIONS.map((question) => question.id));
    for (const question of ASSESSMENT_QUESTIONS) {
      if (question.showIf) expect(ids.has(question.showIf.questionId)).toBe(true);
      if (question.options?.some((answer) => answer.label === "Not sure")) {
        expect(question.options.some((answer) => answer.value === UNKNOWN_FROM_FAMILY)).toBe(true);
      }
    }
  });

  it("only opens relevant rehabilitation, stroke, language, diet, and urgency follow-ups", () => {
    expect(getVisibleQuestions({}).map((question) => question.id)).not.toContain("physical_therapy");
    const visible = getVisibleQuestions({ rehabilitation_needed: "YES", rehabilitation_focus: ["STROKE"], dietary_requirements: ["GLUTEN_FREE"], language_needs: ["HEBREW"], urgency: "IMMEDIATE", payment_method: ["PRIVATE_PAY"] }).map((question) => question.id);
    expect(visible).toContain("physical_therapy");
    expect(visible).toContain("stroke_recovery");
    expect(visible).toContain("gluten_free_details");
    expect(visible).toContain("hebrew_support");
    expect(visible).toContain("urgent_availability");
    expect(visible).toContain("monthly_budget");
    expect(visible).not.toContain("neurological_rehabilitation");
  });
});