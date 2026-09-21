import { expect, it } from "vitest";
import { isFinalRecommendation, isPendingRecommendation } from "../src/lib/recommendation-eligibility";

it("never promotes an eligible legacy row past an unresolved MUST gate", () => {
  const row = { eligibility_status: "ELIGIBLE", must_eligibility: "MUST_PENDING_VERIFICATION" };
  expect(isFinalRecommendation(row)).toBe(false);
  expect(isPendingRecommendation(row)).toBe(true);
  expect(isFinalRecommendation({ ...row, must_eligibility: "MUST_REJECTED" })).toBe(false);
});
it("preserves canonical eligibility and legacy compatibility", () => {
  expect(isFinalRecommendation({ eligibility_status: "ELIGIBLE", must_eligibility: "MUST_ELIGIBLE" })).toBe(true);
  expect(isFinalRecommendation({ eligibility_status: "ELIGIBLE" })).toBe(true);
  expect(isPendingRecommendation({ eligibility_status: "INELIGIBLE" })).toBe(false);
});
