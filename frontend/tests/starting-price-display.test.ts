import { describe, expect, it } from "vitest";
import { startingPriceDisplay } from "../src/lib/starting-price-display";
import type { DecisionEngineRecommendation } from "../src/lib/api";
const row = (fields: Partial<DecisionEngineRecommendation>) => fields as DecisionEngineRecommendation;
describe("starting-price display", () => {
  it("uses the base room price without confusing it with the all-in total", () => {
    const text = startingPriceDisplay(row({starting_monthly_price: 7000, room_pricing_options: [{room_type: "Studio", base_price: 4395, price_source: "OFFICIAL_WEBSITE"}]}), 5500);
    expect(text).toContain("$4,395"); expect(text).toContain("base price within");
    expect(text).toContain("care program not specified"); expect(text).toContain("final total");
    expect(text).toContain("published on the facility"); expect(text).not.toContain("$7,000");
  });
  it("does not label manual or unknown prices as supplied by the facility", () => {
    expect(startingPriceDisplay(row({starting_monthly_price: 6000, price_source: "MANUAL"}), 3000)).toContain("manually recorded");
    expect(startingPriceDisplay(row({starting_monthly_price: 6000}), 3000)).toContain("source not confirmed");
  });
  it("does not call a synthetic price a provider price", () => {
    expect(startingPriceDisplay(row({starting_monthly_price: 5000, synthetic_pilot: true}), 5500)).toContain("synthetic pilot test price");
  });
  it("keeps missing and nonfinite amounts unknown", () => {
    for (const amount of [null, 0, NaN, Infinity]) expect(startingPriceDisplay(row({starting_monthly_price: amount}), 5500)).toContain("cannot be compared");
  });
  it("does not claim affordability without a budget", () => {
    expect(startingPriceDisplay(row({starting_monthly_price: 5000}), 0)).toContain("affordability not assessed");
  });
});
