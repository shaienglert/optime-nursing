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
  it("shows the real deciding dimension instead of a generic fallback when the displayed score is lower", () => {
    const recommendation = {
      patient_match_score: 95,
      ai_ranking: {
        status: "DETERMINISTIC_THIN_EVIDENCE_WATERFALL",
        reason: "Ranked by the governed deterministic order.",
      },
      tie_break_explanation_vs_next: {
        why_ranked_above: "This option is closer to the nearby places you requested.",
      },
      explanation: { why_matches: [] },
    } as unknown as DecisionEngineRecommendation;
    expect(facilityRankingExplanation(recommendation)).toBe(
      "This option is closer to the nearby places you requested.",
    );
  });

  it("retains AI-specific rank reasoning when AI ranked the candidates", () => {
    const recommendation = {
      ai_ranking: { status: "AI_RANKED", reason: "Verified music access supports the preference." },
      tie_break_explanation_vs_next: { why_ranked_above: "Closer to a park." },
      explanation: { why_matches: [] },
    } as unknown as DecisionEngineRecommendation;
    expect(facilityRankingExplanation(recommendation)).toBe("Verified music access supports the preference.");
  });

});
