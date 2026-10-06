import { describe, expect, it } from "vitest";
import { hasSeparateRecoveryEpisode } from "../src/lib/recovery-scope";
describe("recovery scope", () => {
  it("discloses only a recovery episode already identified by the decision", () => {
    expect(hasSeparateRecoveryEpisode({ living_strategy: { strategy_candidates: [{ strategy_id: "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING" }] } })).toBe(true);
    expect(hasSeparateRecoveryEpisode({ living_strategy: { strategy_candidates: [{ strategy_id: "ASSISTED_LIVING" }] } })).toBe(false);
    expect(hasSeparateRecoveryEpisode()).toBe(false);
  });
});
