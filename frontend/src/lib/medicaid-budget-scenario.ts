type FundingBudget = {
  budget: number;
  medicaidStatus: string;
  medicaidMonthlyAmount?: number;
  medicaidBudgetIncludesSupport?: string;
  medicaidBudgetScenarioChoice?: string;
  medicaidOriginalBudget?: number;
};

/** A family-selected search assumption, never a finding of coverage. */
export function applyMedicaidBudgetScenario<T extends FundingBudget>(state: T, choice: string): T {
  const original = state.medicaidOriginalBudget ?? state.budget;
  const amount = Number(state.medicaidMonthlyAmount);
  const canAdd = ["Approved", "Application pending"].includes(state.medicaidStatus)
    && state.medicaidBudgetIncludesSupport === "Additional to my budget"
    && Number.isFinite(amount) && amount > 0;
  return { ...state, medicaidOriginalBudget: original, medicaidBudgetScenarioChoice: choice,
    budget: choice === "Include support in my search" && canAdd ? original + amount : original };
}

export function medicaidBudgetIsConditional(state: FundingBudget): boolean {
  return ["Approved", "Application pending"].includes(state.medicaidStatus)
    && Number(state.medicaidMonthlyAmount) > 0
    && (state.medicaidBudgetIncludesSupport === "Already included"
      || state.medicaidBudgetScenarioChoice === "Include support in my search");
}
