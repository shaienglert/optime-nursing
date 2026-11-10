import { describe, expect, it } from "vitest";
import { verifiedBudgetFloor } from "../src/lib/verified-budget-floor";

describe("budget floor evidence gating", () => {
  it("does not invent a floor when the API fails", () => {
    expect(verifiedBudgetFloor(null)).toBeNull();
  });
  it("does not use pending price evidence as a known floor", () => {
    expect(verifiedBudgetFloor({ minimum_budget_is_binding: false, minimum_monthly_price: 5500 })).toBeNull();
  });
  it("rejects zero, negative, missing and malformed prices", () => {
    for (const amount of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, null]) {
      expect(verifiedBudgetFloor({ minimum_budget_is_binding: true, minimum_monthly_price: amount })).toBeNull();
    }
  });
  it("preserves the exact verified starting price", () => {
    expect(verifiedBudgetFloor({ minimum_budget_is_binding: true, minimum_monthly_price: 4328 })).toBe(4328);
  });
});
