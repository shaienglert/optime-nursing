import { describe, expect, it } from "vitest";
import { withoutInsurance } from "../src/lib/monthly-price-policy";
describe("insurance-free monthly price policy", () => {
  it("restores the original budget when old support was automatically added", () => {
    const saved = {budget: 8000, medicaidOriginalBudget: 5000, medicaidStatus: "Approved", medicareStatus: "Original Medicare", medicaidBudgetScenarioChoice: "Include support in my search", assistanceLevel: "Help with bathing"};
    const clean = withoutInsurance(saved);
    expect(clean.budget).toBe(5000); expect(clean.medicaidStatus).toBe(""); expect(clean.medicareStatus).toBe("");
    expect(clean.assistanceLevel).toBe(saved.assistanceLevel); expect(withoutInsurance(clean)).toEqual(clean);
    expect(saved.budget).toBe(8000);
  });
  it("preserves a family's explicitly entered budget", () => {
    expect(withoutInsurance({budget: 8000, medicaidStatus: "Approved", medicareStatus: "", medicaidBudgetScenarioChoice: "Already included"}).budget).toBe(8000);
  });
});
