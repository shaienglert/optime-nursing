import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import type { FundingExplanation } from "../src/lib/api";
import { fundingLines, fundingLinks } from "../src/lib/funding-display";

const base: FundingExplanation = {
  pathway: "PRIVATE_PAY",
  monthly: { amount: 6000, basis: "PRIVATE_PAY_PRICE", budget: 7000, included_in_budget: true },
  one_time: { amount: 90000, available_capital: null, status: "CAPITAL_NOT_PROVIDED", provider_confirmation_required: true },
  medicaid: { state: "APPLICATION_PENDING", acceptance_evidence: "UNKNOWN", coverage_promised: false },
  links: ["https://example.org/a", "javascript:alert(1)"],
  explanation: "",
};

describe("funding display", () => {
  it("shows monthly and one-time as separate lines and never sums them", () => {
    const lines = fundingLines(base, true);
    expect(lines.map((l) => l.label)).toEqual(["Monthly cost", "One-time fee (separate from monthly)", "Medicaid"]);
    expect(lines[0].text).toContain("$6,000");
    expect(lines[0].text).not.toContain("96,000");
    expect(lines[1].text).toContain("not assessed");
  });

  it("states Medicaid state and never promises coverage without evidence", () => {
    const text = fundingLines(base, true)[2].text;
    expect(text).toContain("Application pending");
    expect(text).toContain("coverage is not promised");
  });

  it("states unknown cost as unknown, not as a fit", () => {
    const lines = fundingLines({ ...base, monthly: { ...base.monthly, amount: null, included_in_budget: null }, one_time: null }, false);
    expect(lines).toHaveLength(1);
    expect(lines[0].text).toContain("Not verified");
  });

  it("only exposes http(s) links", () => {
    expect(fundingLinks(base)).toEqual(["https://example.org/a"]);
    expect(fundingLinks(null)).toEqual([]);
  });

  it("is rendered by the results page", () => {
    const page = readFileSync("src/app/results/simple-results-page-client.tsx", "utf8");
    expect(page).toContain('data-testid="funding-explanation"');
    expect(page).toContain("fundingLines(item.funding_explanation");
  });
});
