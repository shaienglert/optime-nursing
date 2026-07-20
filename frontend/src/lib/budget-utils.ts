export function resolveBudgetValue(budget: number | null | undefined): number | null {
  const numericBudget = Number(budget);
  if (!Number.isFinite(numericBudget) || numericBudget <= 0) {
    return null;
  }

  return numericBudget;
}

export function formatBudgetRangeLabel(budget: number | null | undefined): string {
  const resolvedBudget = resolveBudgetValue(budget);
  return resolvedBudget === null ? "Budget not supplied" : `Up to $${resolvedBudget.toLocaleString()}/month`;
}