import type { FundingExplanation } from "./api";

export type FundingLine = { label: string; text: string };

const money = (value: number) => `$${Math.round(value).toLocaleString("en-US")}`;

function sourceLabel(source: string | null | undefined): string {
  switch (source) {
    case "OUTREACH":
    case "PROVIDER":
    case "MANUAL":
      return "price received from the facility";
    case "OFFICIAL_WEBSITE":
      return "price published on the facility’s website";
    case "RESEARCH":
      return "price found in public research, not yet confirmed by the facility";
    default:
      return "price source not confirmed";
  }
}

/**
 * One line shown to the family: the facility's "starting at" (lowest room) monthly price and where it
 * came from. One-time fees, insurance and Medicaid are intentionally not shown here (owner decision).
 * Unknown price is stated as unknown, never as a pass or fail.
 */
export function fundingLines(funding: FundingExplanation | null | undefined, _medicaidAnswered?: boolean): FundingLine[] {
  if (!funding) return [];
  const { monthly } = funding;
  if (monthly.amount == null) {
    return [{ label: "Starting price", text: "Not received from the facility yet, so it cannot be compared with your budget." }];
  }
  const fit = monthly.included_in_budget == null ? "not compared with a budget" : monthly.included_in_budget ? "within your monthly budget" : "above your monthly budget";
  return [{ label: "Starting at", text: `${money(monthly.amount)} / month (lowest-priced room) — ${sourceLabel(monthly.price_source)}; ${fit}` }];
}

export function fundingLinks(funding: FundingExplanation | null | undefined): string[] {
  return (funding?.links || []).filter((link) => /^https?:\/\//i.test(link));
}
