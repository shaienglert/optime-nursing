import type { FundingExplanation } from "./api";

export type FundingLine = { label: string; text: string };

const MEDICAID_LABEL: Record<FundingExplanation["medicaid"]["state"], string> = {
  APPROVED: "Approved",
  APPLICATION_PENDING: "Application pending",
  MAY_QUALIFY: "May qualify",
  NOT_ELIGIBLE: "Not eligible",
  UNKNOWN: "Not known",
};

const money = (value: number) => `$${Math.round(value).toLocaleString("en-US")}`;

/**
 * Lines shown to the family. Monthly cost and one-time capital are separate lines and are
 * never added together; unknown information is stated as unknown, never as a pass or fail.
 */
export function fundingLines(funding: FundingExplanation | null | undefined, medicaidAnswered: boolean): FundingLine[] {
  if (!funding) return [];
  const lines: FundingLine[] = [];
  const { monthly } = funding;
  lines.push({
    label: "Monthly cost",
    text: monthly.amount == null
      ? "Not verified yet, so it cannot be compared with your budget."
      : `${money(monthly.amount)} (${monthly.basis === "MEDICAID_HOUSEHOLD_OUT_OF_POCKET" ? "household cost under Medicaid" : "private-pay price"}) — ${monthly.included_in_budget == null ? "not compared with a budget" : monthly.included_in_budget ? "within your monthly budget" : "above your monthly budget"}`,
  });
  if (funding.one_time) {
    const capital = funding.one_time;
    lines.push({
      label: "One-time fee (separate from monthly)",
      text: `${money(capital.amount)} — ${capital.status === "CAPITAL_NOT_PROVIDED" ? "available funds not provided, so not assessed" : capital.status === "FEE_WITHIN_STATED_CAPITAL" ? "within the funds you stated; the community must confirm the fee applies" : "above the funds you stated"}`,
    });
  }
  if (medicaidAnswered || funding.pathway === "MEDICAID") {
    lines.push({
      label: "Medicaid",
      text: `${MEDICAID_LABEL[funding.medicaid.state]} — ${funding.medicaid.acceptance_evidence === "YES" ? "acceptance is verified for this community" : "acceptance not confirmed; coverage is not promised"}`,
    });
  }
  return lines;
}

export function fundingLinks(funding: FundingExplanation | null | undefined): string[] {
  return (funding?.links || []).filter((link) => /^https?:\/\//i.test(link));
}
