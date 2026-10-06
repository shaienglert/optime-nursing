/** Start at the exact local floor and increase by $500 at every step. */
export function budgetChoices(minimum: number, maximum: number): number[] {
  const choices = [minimum];
  for (let amount = minimum + 500; amount <= maximum; amount += 500) {
    choices.push(amount);
  }
  return choices;
}
