import type { DecisionEngineRecommendation } from "./api";

export function facilityRankingExplanation(recommendation: DecisionEngineRecommendation): string | undefined {
  const ranking = recommendation.ai_ranking;
  const pairwiseReason = recommendation.tie_break_explanation_vs_next?.why_ranked_above;
  // The deterministic fallback's generic summary cannot explain why this
  // particular facility precedes the next one. Use the actual governed comparator.
  if (ranking?.status === "DETERMINISTIC_THIN_EVIDENCE_WATERFALL" && pairwiseReason) {
    return pairwiseReason;
  }
  return ranking?.reason || pairwiseReason || recommendation.explanation.why_matches?.[0];
}
