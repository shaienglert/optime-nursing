import { expect, it } from "vitest";
import { extractExplicitMonthlyBudget } from "../src/lib/story-budget";

it("leaves conflicting English and Hebrew amounts unresolved", () => {
  expect(extractExplicitMonthlyBudget("My budget is $50,000 or $500")).toBeNull();
  expect(extractExplicitMonthlyBudget("התקציב הוא $50,000 או $500 לחודש")).toBeNull();
});
it("preserves a clear low budget and repeated identical amounts", () => {
  expect(extractExplicitMonthlyBudget("התקציב $2,500 לחודש")).toBe(2500);
  expect(extractExplicitMonthlyBudget("Budget $5,000 monthly, maximum $5,000")).toBe(5000);
});
it("does not confuse separate prices with a single confirmed budget", () => {
  expect(extractExplicitMonthlyBudget("Budget $5000 with an extra $500 for care")).toBeNull();
});
