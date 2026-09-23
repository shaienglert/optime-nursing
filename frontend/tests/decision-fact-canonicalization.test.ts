import { describe, expect, it } from "vitest";

import { canonicalizeAdaptiveFact, parseMonthlyBudgetAnswer } from "../src/lib/decision-fact-canonicalization";

/**
 * The five strings below are the exact options the backend offers for the
 * `monthly_budget` question (backend/app/services/living_strategy_runtime.py).
 * If that list changes, this test must change with it.
 */
const OPTIONS = ["Under $5,000", "$5,000-$8,000", "$8,000-$12,000", "Above $12,000", "Not sure"] as const;

describe("parseMonthlyBudgetAnswer", () => {
  it("reads a single ceiling", () => {
    expect(parseMonthlyBudgetAnswer("Under $5,000")).toEqual({
      budget: 5000,
      noUpperLimit: false,
      acknowledgedUnknown: false,
    });
  });

  it("takes the TOP of a range as the upper bound", () => {
    expect(parseMonthlyBudgetAnswer("$5,000-$8,000")).toEqual({
      budget: 8000,
      noUpperLimit: false,
      acknowledgedUnknown: false,
    });
    expect(parseMonthlyBudgetAnswer("$8,000-$12,000")).toEqual({
      budget: 12000,
      noUpperLimit: false,
      acknowledgedUnknown: false,
    });
  });

  it("never concatenates the digits of a range", () => {
    // Regression: "$5,000-$8,000" previously became 50008000 and disabled budget gating.
    for (const option of OPTIONS) {
      const parsed = parseMonthlyBudgetAnswer(option);
      expect(parsed.budget ?? 0).toBeLessThanOrEqual(12000);
    }
  });

  it("treats a floor-style answer as no upper bound, not a ceiling", () => {
    expect(parseMonthlyBudgetAnswer("Above $12,000")).toEqual({
      budget: undefined,
      noUpperLimit: true,
      acknowledgedUnknown: false,
    });
    expect(parseMonthlyBudgetAnswer("over $9,000")).toMatchObject({ noUpperLimit: true });
    expect(parseMonthlyBudgetAnswer("$9,000+")).toMatchObject({ noUpperLimit: true });
  });

  it("treats an amount-free answer as an acknowledged unknown", () => {
    expect(parseMonthlyBudgetAnswer("Not sure")).toEqual({
      budget: undefined,
      noUpperLimit: false,
      acknowledgedUnknown: true,
    });
    expect(parseMonthlyBudgetAnswer("")).toMatchObject({ acknowledgedUnknown: true });
  });
});

describe("canonicalizeAdaptiveFact monthly_budget", () => {
  const state = () => ({ budget: 0 }) as never;

  it("stores the upper bound of a range", () => {
    expect((canonicalizeAdaptiveFact(state(), "monthly_budget", "$5,000-$8,000") as { budget: number }).budget).toBe(8000);
  });

  it("leaves the budget unset when no ceiling was stated", () => {
    for (const option of ["Above $12,000", "Not sure"]) {
      expect((canonicalizeAdaptiveFact(state(), "monthly_budget", option) as { budget: number }).budget).toBe(0);
    }
  });
});
