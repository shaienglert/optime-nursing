import { describe, expect, it } from "vitest";
import type { DecisionEngineResponse } from "../src/lib/api";
import { preferenceAdvice } from "../src/lib/search-advice";

const suggestion = { parameter: "COMMUNITY_SIZE", authority: "PREFERENCE", action: "RECOMMEND_TRANSPARENT_ALTERNATIVE", basis: "COUNTERFACTUAL_OVER_FULL_CANDIDATE_UNIVERSE", additional_options_if_relaxed: 3, may_auto_change: false };
const response = (suggestions = [suggestion]) => ({ oomniker: { input_universe: "FULL_CANDIDATE_LEDGER_OF_THIS_SEARCH", suggestions } }) as DecisionEngineResponse;
describe("grounded conversational advice", () => {
  it("uses the governed count and leaves the decision to the family", () => {
    expect(preferenceAdvice(response())[0]).toContain("3 additional communities");
    expect(preferenceAdvice(response())[0]).toContain("unless you choose a change");
  });
  it("never turns MUST, evidence gaps, radius counts or one option into preference advice", () => {
    expect(preferenceAdvice(response([
      { ...suggestion, authority: "CLIENT_MUST" }, { ...suggestion, authority: "CARE_MUST" },
      { ...suggestion, authority: "EVIDENCE" }, { ...suggestion, basis: "LOCATION_SCOPE_EXPANSION_OFFER" },
      { ...suggestion, additional_options_if_relaxed: 1 }, { ...suggestion, may_auto_change: true },
    ]))).toEqual([]);
  });
  it("does not invent advice when the full search analysis is absent", () => {
    expect(preferenceAdvice({} as DecisionEngineResponse)).toEqual([]);
    expect(preferenceAdvice({ oomniker: { input_universe: "POST_SYSTEM_MUST_FILTER_ONLY", suggestions: [suggestion] } } as DecisionEngineResponse)).toEqual([]);
  });
});
