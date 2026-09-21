import { describe, expect, it } from "vitest";
import { hasUnresolvedSemanticConflict, semanticConflictQuestion, semanticIntakeFailure } from "../src/lib/semantic-conflict";

describe("semantic intake availability", () => {
  it("blocks failed AI even when deterministic readiness reports complete", () => {
    expect(semanticIntakeFailure({ enabled: true, status: "FAILED" })).toBe(true);
    expect(semanticIntakeFailure({ required: true, status: "DISABLED" })).toBe(true);
    expect(semanticIntakeFailure({ enabled: true })).toBe(true);
  });
  it("allows validated AI and explicitly disabled local mode", () => {
    expect(semanticIntakeFailure({ enabled: true, status: "CONSULTED_AND_VALIDATED" })).toBe(false);
    expect(semanticIntakeFailure({ enabled: false, required: false, status: "DISABLED" })).toBe(false);
  });
});

describe("unresolved semantic conflicts", () => {
  it("preserves the model's clarification even without an adaptive question", () => {
    const question = semanticConflictQuestion([{
      status: "ASKED", knowledge_state: "AMBIGUOUS", importance: "MUST",
      clarification_question: "Is your budget $500 or $50,000?", gap_key: "monthly_affordability",
      mapped_parameters: ["monthly_affordability"],
    }]);
    expect(question?.question).toBe("Is your budget $500 or $50,000?");
    expect(question?.question_key).toBe("semantic-conflict-monthly_affordability");
    expect(semanticConflictQuestion([{ status: "USED", knowledge_state: "KNOWN", importance: "MUST" }])).toBeNull();
  });
  it("requires an explicit answer for ambiguous required input", () => {
    expect(hasUnresolvedSemanticConflict([{ status: "ASKED", knowledge_state: "AMBIGUOUS", importance: "MUST" }])).toBe(true);
  });
  it("does not block resolved facts or optional ambiguity", () => {
    expect(hasUnresolvedSemanticConflict([{ status: "USED", knowledge_state: "KNOWN", importance: "MUST" }])).toBe(false);
    expect(hasUnresolvedSemanticConflict([{ status: "ASKED", knowledge_state: "AMBIGUOUS", importance: "NICE" }])).toBe(false);
    expect(hasUnresolvedSemanticConflict(undefined)).toBe(false);
  });
});
