/** Only a successfully resolved, positive area price can anchor the budget slider. */
export function verifiedBudgetFloor(
  response: { minimum_budget_is_binding?: boolean; minimum_monthly_price?: number | null } | null,
): number | null {
  const candidate = response?.minimum_monthly_price;
  if (response?.minimum_budget_is_binding !== true || typeof candidate !== "number"
      || !Number.isFinite(candidate) || candidate <= 0) return null;
  return candidate;
}
