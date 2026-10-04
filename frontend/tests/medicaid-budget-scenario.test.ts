import { describe, expect, it } from "vitest";
import { applyMedicaidBudgetScenario, medicaidBudgetIsConditional } from "../src/lib/medicaid-budget-scenario";

const state = { budget: 5000, medicaidStatus: "Application pending", medicaidMonthlyAmount: 3000, medicaidBudgetIncludesSupport: "Additional to my budget" };
describe("family-selected funding budget scenario", () => {
  it("adds once, remains conditional, and restores the household budget on withdrawal", () => {
    const expanded = applyMedicaidBudgetScenario(state, "Include support in my search");
    expect(expanded.budget).toBe(8000);
    expect(applyMedicaidBudgetScenario(expanded, "Include support in my search").budget).toBe(8000);
    expect(medicaidBudgetIsConditional(expanded)).toBe(true);
    expect(applyMedicaidBudgetScenario(expanded, "Use my own budget only").budget).toBe(5000);
  });
  it("does not add coverage already included in the stated budget", () => {
    const included = { ...state, medicaidBudgetIncludesSupport: "Already included" };
    expect(applyMedicaidBudgetScenario(included, "Include support in my search").budget).toBe(5000);
    expect(medicaidBudgetIsConditional(included)).toBe(true);
  });
  it.each([NaN, Infinity, 0, -3000])("does not add an invalid amount %s", amount => {
    expect(applyMedicaidBudgetScenario({ ...state, medicaidMonthlyAmount: amount }, "Include support in my search").budget).toBe(5000);
  });
});
