import { describe, expect, it } from "vitest";
import type { DecisionEngineRecommendation } from "../src/lib/api";
import { facilityRankingExplanation } from "../src/lib/ranking-explanation";

describe("facility ranking explanation ownership", () => {
  it("keeps duplicate-name facilities and reordered results attached to their own reasons", () => {
    const first = {
      canonical_facility_id: "A", facility_name: "Silver Court",
      ai_ranking: { reason: "A has verified daily activities." },
      tie_break_explanation_vs_next: { why_ranked_above: "A is above B." },
      explanation: { why_matches: [] },
    } as unknown as DecisionEngineRecommendation;
    const second = {
      canonical_facility_id: "B", facility_name: "Silver Court",
      ai_ranking: { reason: "B has a lower price." },
      explanation: { why_matches: [] },
    } as unknown as DecisionEngineRecommendation;
    expect([second, first].map(facilityRankingExplanation)).toEqual([
      "B has a lower price.", "A has verified daily activities.",
    ]);
  });

  it("does not invent an explanation when the facility has none", () => {
    expect(facilityRankingExplanation({ explanation: { why_matches: [] } } as unknown as DecisionEngineRecommendation)).toBeUndefined();
  });
});
