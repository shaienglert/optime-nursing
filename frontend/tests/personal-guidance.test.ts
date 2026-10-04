import { describe, expect, it } from "vitest";
import { DEFAULT_STATE } from "../src/context/questionnaire-context";
import type { DecisionEngineResponse } from "../src/lib/api";
import { facilityExplanation, personalSummary, recommendationFromDecision, resultsIntroduction } from "../src/lib/personal-guidance";

describe("personal guidance boundaries", () => {
  it("retains the person's additional story without claiming a facility satisfies it", () => {
    const state = { ...DEFAULT_STATE, notes: "My mother fears losing her bridge group.", budget: 6500 };
    expect(personalSummary(state).join(" ")).toContain(state.notes);
    expect(resultsIntroduction(state, 2).join(" ")).toContain("still needs evidence");
  });
  it("places substantive support before language and budget without deleting facts", () => {
    const item = { explanation: { why_matches: ["English is available.", "Help with medication is provided.", "The price is within budget."] }, tie_break_explanation_vs_next: { why_ranked_above: "These communities are tied." } } as DecisionEngineResponse["results"][number];
    const before = structuredClone(item);
    const text = facilityExplanation(item).join(" ");
    expect(text.indexOf("medication")).toBeLessThan(text.indexOf("English"));
    expect(text).toContain("within budget");
    expect(text).toContain("are tied");
    expect(item).toEqual(before);
  });
  it("does not present a pending facility as a personal recommendation", () => {
    const decision = { results: [{ canonical_facility_id: "a", eligibility_status: "ELIGIBLE", must_eligibility: "MUST_PENDING_VERIFICATION" }] } as DecisionEngineResponse;
    expect(recommendationFromDecision(decision, "a")).toBeNull();
    expect(recommendationFromDecision(decision, "missing")).toBeNull();
  });
  it("keeps the empty-search introduction accurate", () => {
    expect(resultsIntroduction(DEFAULT_STATE, 0).join(" ")).toContain("do not yet have a recommendation");
  });
});
