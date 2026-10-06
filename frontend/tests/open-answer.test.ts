import { describe, expect, it } from "vitest";

import { BUDGET_MISSING_EXPLANATION, budgetIsKnown, checkOpenAnswer, unknownChoiceLabel } from "../src/lib/open-answer";

describe("open answers are corrected or explicitly unknown, never silently dropped", () => {
  it.each(["7000", "7,000", "$7,000", "about $7,000"])("accepts a budget amount: %s", (value) => {
    expect(checkOpenAnswer("monthly_budget", value)).toEqual({ ok: true, answer: value });
  });

  it.each(["seven thousand", "lots", "no idea what to say"])("asks for a correction: %s", (value) => {
    const result = checkOpenAnswer("monthly_budget", value);
    expect(result.ok).toBe(false);
    expect(result.ok === false && result.message).toContain("7,000");
  });

  it.each(["not sure", "Not sure", "I'm not sure", "I don't know"])("treats %s as an explicit unknown", (value) => {
    expect(checkOpenAnswer("monthly_budget", value)).toEqual({ ok: true, answer: "Not sure" });
  });

  it("offers an explicit not-sure choice only for the open questions that need one", () => {
    expect(unknownChoiceLabel("monthly_budget")).toBe("I’m not sure");
    expect(unknownChoiceLabel("required_language")).toBe("I’m not sure");
    expect(unknownChoiceLabel("community_size_preference")).toBeNull();
  });

  it("rejects an empty answer", () => {
    expect(checkOpenAnswer("required_language", "  ").ok).toBe(false);
  });

  it("explains what is missing when the budget is unknown", () => {
    expect(BUDGET_MISSING_EXPLANATION).toContain("budget");
    expect([0, null, undefined, "seven thousand", NaN].map(budgetIsKnown)).toEqual([false, false, false, false, false]);
    expect(budgetIsKnown(7000)).toBe(true);
  });
});
