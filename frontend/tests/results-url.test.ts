import { describe, expect, it } from "vitest";

import { buildResultsUrl } from "../src/lib/results-url";

describe("buildResultsUrl", () => {
  it("rebuilds the destination only from the confirmed current case", () => {
    const state = {
      relationship: "Dad",
      ageGroup: "70-74",
      assistanceLevel: "Fully independent",
      memoryStatus: "",
      budget: 7000,
      distanceFromFamily: "",
      notes: "My father is fully independent and needs no dialysis.",
    };

    const url = buildResultsUrl(state, "/results/details?notes=stale-mother&relationship=Mom&budget=10000");

    expect(url).toContain("/results/details?");
    expect(url).toContain("relationship=Dad");
    expect(url).toContain("budget=7000");
    expect(url).not.toContain("Mom");
    expect(url).not.toContain("10000");
    expect(url).not.toContain("stale-mother");
  });
});
