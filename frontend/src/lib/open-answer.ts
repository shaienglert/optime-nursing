import { parseMonthlyBudgetAnswer } from "./decision-fact-canonicalization";

export type OpenAnswerCheck = { ok: true; answer: string } | { ok: false; message: string };

const UNKNOWN_PATTERN = /^(i'?m )?not sure$|^i don'?t know$|^unknown$/i;

/** Questions whose free-text answer must be usable, and that also accept an explicit "not sure". */
const QUESTIONS_WITH_EXPLICIT_UNKNOWN = new Set(["monthly_budget", "required_language"]);

export function unknownChoiceLabel(targetFactKey: string | undefined | null): string | null {
  return targetFactKey && QUESTIONS_WITH_EXPLICIT_UNKNOWN.has(targetFactKey) ? "I’m not sure" : null;
}

/** Explicit "I'm not sure" is stored as the acknowledged unknown the backend already understands. */
export function explicitUnknownAnswer(): string {
  return "Not sure";
}

/**
 * Validate a free-text answer before it is submitted. An answer that cannot be used is
 * never silently accepted: the family corrects it or chooses "I'm not sure" explicitly.
 */
export function checkOpenAnswer(targetFactKey: string | undefined | null, raw: string): OpenAnswerCheck {
  const answer = String(raw ?? "").trim();
  if (!answer) return { ok: false, message: "Please enter an answer." };
  if (targetFactKey === "monthly_budget") {
    if (UNKNOWN_PATTERN.test(answer)) return { ok: true, answer: explicitUnknownAnswer() };
    const parsed = parseMonthlyBudgetAnswer(answer);
    if (parsed.acknowledgedUnknown) {
      return { ok: false, message: "I couldn’t read that as an amount. Enter a number such as 7,000, or choose “I’m not sure”." };
    }
  }
  return { ok: true, answer };
}

/** What is missing when the budget is unknown, shown instead of a bare "no results". */
export const BUDGET_MISSING_EXPLANATION =
  "I don’t have a monthly budget to compare prices with, so I can’t confirm that any community is affordable yet. Add your budget to continue; this is missing information, not a mismatch.";

export function budgetIsKnown(budget: unknown): boolean {
  return typeof budget === "number" && Number.isFinite(budget) && budget > 0;
}
