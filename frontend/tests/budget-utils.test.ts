import { describe, expect, it } from "vitest";

import { formatBudgetRangeLabel, resolveBudgetValue } from "../src/lib/budget-utils";

describe("budget utils", () => {
  it("treats zero as an unspecified budget", () => {
    expect(resolveBudgetValue(0)).toBeNull();
    expect(formatBudgetRangeLabel(0)).toBe("Budget not supplied");
  });

  it("formats real budgets as monthly ranges", () => {
    expect(resolveBudgetValue(7250)).toBe(7250);
    expect(formatBudgetRangeLabel(7250)).toBe("Up to $7,250/month");
  });
});