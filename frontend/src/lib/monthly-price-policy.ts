/** Insurance is settled directly with providers (owner, 2026-10-05). */
export function withoutInsurance<T extends { budget: number; medicareStatus: string; medicaidStatus: string; medicaidOriginalBudget?: number; medicaidBudgetScenarioChoice?: string }>(state: T): T {
  return { ...state,
    budget: state.medicaidBudgetScenarioChoice === "Include support in my search" && Number.isFinite(state.medicaidOriginalBudget)
      ? state.medicaidOriginalBudget as number : state.budget,
    medicareStatus: "", medicaidStatus: "", medicaidAmountKnown: "", medicaidMonthlyAmount: 0,
    medicaidBudgetIncludesSupport: "", medicaidBudgetScenarioChoice: "", medicaidOriginalBudget: undefined,
  };
}
