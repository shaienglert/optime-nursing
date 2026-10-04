import { describe, expect, it } from "vitest";
import type { CarePartnerOption, DecisionEngineRecommendation } from "../src/lib/api";
import { licensedResearchOptions, serviceBudgetPlan } from "../src/lib/service-budget";

const community = { starting_monthly_price: 5500, explanation: { concerns: ["Outside care requires a separate arrangement."] } } as DecisionEngineRecommendation;
describe("whole household service budget", () => {
  it("does not mistake remaining budget for an affordable care quote", () => {
    expect(serviceBudgetPlan(community, 6000, false)).toMatchObject({ allowance: 500, total: null, status: "TOTAL_UNCONFIRMED", external: true });
  });
  it("identifies an over-budget housing price without guessing service cost", () => {
    expect(serviceBudgetPlan(community, 5000, false)).toMatchObject({ allowance: 0, housingOverBudget: true, total: null });
  });
  it("does not invent a price or approve a couple's single-resident pilot rate", () => {
    expect(serviceBudgetPlan({ ...community, starting_monthly_price: undefined }, 6000, false).allowance).toBeNull();
    expect(serviceBudgetPlan({ ...community, synthetic_pilot: true, monthly_rate_includes_verified_care: true }, 6000, true).total).toBeNull();
  });
  it("does not let an inclusive pilot flag swallow an external care cost", () => {
    expect(serviceBudgetPlan({ ...community, synthetic_pilot: true, monthly_rate_includes_verified_care: true }, 6000, false).total).toBeNull();
  });
  it("shows only sourced active licensed research candidates", () => {
    const option = { agency_id: "a", license_number: "123", license_status: "ACTIVE", primary_source_url: "https://provider.example", care_agency_fit: { hard_gate: "UNKNOWN" } } as CarePartnerOption;
    expect(licensedResearchOptions([option, { ...option, license_status: "EXPIRED" }, { ...option, primary_source_url: "javascript:alert(1)" }, { ...option, care_agency_fit: { hard_gate: "FAIL" } }])).toEqual([option]);
  });
});
