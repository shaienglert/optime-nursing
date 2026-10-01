import type { DecisionEngineRecommendation } from "./api";

export function facilityRankingExplanation(recommendation: DecisionEngineRecommendation): string | undefined {
  return recommendation.ai_ranking?.reason
    || recommendation.tie_break_explanation_vs_next?.why_ranked_above
    || recommendation.explanation.why_matches?.[0];
}
