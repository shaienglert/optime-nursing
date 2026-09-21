export function extractExplicitMonthlyBudget(text: string): number | null {
  // Multiple amounts require semantic clarification (or distinguishing separate
  // costs). Never prefill one of them as the client's confirmed monthly budget.
  const amounts = [...text.matchAll(/\$\s*([\d,]+(?:\.\d+)?)/g)]
    .map((match) => Number(match[1].replaceAll(",", "")))
    .filter((amount) => Number.isFinite(amount) && amount > 0);
  if (new Set(amounts).size > 1) return null;
  const patterns = [
    /(?:budget|afford|spend|pay|תקציב)[^.$\n]{0,60}\$\s*([\d,]+(?:\.\d+)?)/i,
    /\$\s*([\d,]+(?:\.\d+)?)[^.$\n]{0,60}(?:per month|monthly|budget|לחודש|תקציב)/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    const amount = Number(match[1].replaceAll(",", ""));
    if (Number.isFinite(amount) && amount > 0) return amount;
  }
  return null;
}
