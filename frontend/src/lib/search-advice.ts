import type { DecisionEngineResponse } from "./api";

const preferenceNames: Record<string, string> = {
  COMMUNITY_SIZE: "community size", COMMUNITY_SIZE_PREFERENCE: "community size", community_size: "community size",
  PET_FRIENDLY: "pet arrangements", PET_OWNERSHIP: "pet arrangements", pet_ownership: "pet arrangements",
  SOCIAL_ACTIVITIES: "social activities", social_activities: "social activities",
  LIFESTYLE_FIT: "everyday lifestyle", lifestyle: "everyday lifestyle",
};

export function preferenceAdvice(decision: DecisionEngineResponse): string[] {
  if (decision.oomniker?.input_universe !== "FULL_CANDIDATE_LEDGER_OF_THIS_SEARCH") return [];
  return (decision.oomniker.suggestions || []).filter(suggestion =>
    suggestion.authority === "PREFERENCE" && suggestion.action === "RECOMMEND_TRANSPARENT_ALTERNATIVE" &&
    suggestion.basis === "COUNTERFACTUAL_OVER_FULL_CANDIDATE_UNIVERSE" && suggestion.may_auto_change === false &&
    Number.isInteger(suggestion.additional_options_if_relaxed) && (suggestion.additional_options_if_relaxed || 0) >= 2 &&
    !!preferenceNames[suggestion.parameter]
  ).slice(0, 2).map(suggestion =>
    `There is one preference worth talking about: ${preferenceNames[suggestion.parameter]}. The analysis of this search found ${suggestion.additional_options_if_relaxed} additional communities that could become options if that preference changed, while keeping the other requirements. Would you like to explore that possibility? I’ll keep your search as it is unless you choose a change.`
  );
}
