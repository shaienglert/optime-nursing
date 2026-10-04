/** Preserve the exact evidence-based floor, followed by round $500 amounts. */
export function budgetChoices(minimum: number, maximum: number): number[] {
  const choices = [minimum];
  for (let amount = (Math.floor(minimum / 500) + 1) * 500; amount <= maximum; amount += 500) {
    choices.push(amount);
  }
  return choices;
}
