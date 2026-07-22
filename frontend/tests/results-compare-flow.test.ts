import { describe, expect, it } from "vitest";

import {
  canCompareFavorites,
  getResultsAfterTopFive,
  hasCanonicalParameterCount,
  isStrictRankOrder,
  mobileCardsPerRow,
  selectOptimeReference,
  toggleFavorite,
  uniqueCanonicalParameters,
  unknownIsNeutral,
} from "../src/lib/results-compare-flow";

describe("results->favorites->compare flow helpers", () => {
  it("show more results begins at rank #6", () => {
    const ranked = [
      { canonical_facility_id: "A", rank_position: 1 },
      { canonical_facility_id: "B", rank_position: 5 },
      { canonical_facility_id: "C", rank_position: 6 },
      { canonical_facility_id: "D", rank_position: 7 },
    ];
    const afterTopFive = getResultsAfterTopFive(ranked);
    expect(afterTopFive.map((item) => item.rank_position)).toEqual([6, 7]);
  });

  it("preserves ranking order", () => {
    expect(isStrictRankOrder([
      { canonical_facility_id: "A", rank_position: 6 },
      { canonical_facility_id: "B", rank_position: 7 },
      { canonical_facility_id: "C", rank_position: 8 },
    ])).toBe(true);

    expect(isStrictRankOrder([
      { canonical_facility_id: "A", rank_position: 7 },
      { canonical_facility_id: "B", rank_position: 6 },
    ])).toBe(false);
  });

  it("favorite toggle and compare readiness", () => {
    const first = toggleFavorite([], "CMS-1");
    expect(first).toEqual(["CMS-1"]);
    expect(canCompareFavorites(first)).toBe(false);

    const second = toggleFavorite(first, "CMS-2");
    expect(second).toEqual(["CMS-1", "CMS-2"]);
    expect(canCompareFavorites(second)).toBe(true);

    const third = toggleFavorite(second, "CMS-1");
    expect(third).toEqual(["CMS-2"]);
  });

  it("selects correct OPTIME reference when top rank is disqualified", () => {
    const ranked = [
      { canonical_facility_id: "CMS-1", rank_position: 1 },
      { canonical_facility_id: "CMS-2", rank_position: 2 },
      { canonical_facility_id: "CMS-3", rank_position: 3 },
    ];
    expect(selectOptimeReference(ranked)?.canonical_facility_id).toBe("CMS-1");
    expect(selectOptimeReference(ranked, ["CMS-1"])?.canonical_facility_id).toBe("CMS-2");
  });

  it("keeps exactly 59 unique canonical parameters in full view", () => {
    const parameters = Array.from({ length: 59 }, (_, index) => `p_${index + 1}`);
    expect(hasCanonicalParameterCount(parameters)).toBe(true);
    expect(uniqueCanonicalParameters([...parameters, "p_10"]).length).toBe(59);
  });

  it("treats unknown as neutral", () => {
    expect(unknownIsNeutral("NOT_VERIFIED")).toBe(true);
    expect(unknownIsNeutral("MATCH")).toBe(false);
    expect(unknownIsNeutral("VERIFIED_GAP")).toBe(false);
  });

  it("uses a readable mobile card layout at 390px", () => {
    expect(mobileCardsPerRow(390)).toBe(1);
    expect(mobileCardsPerRow(680)).toBe(2);
  });
});
