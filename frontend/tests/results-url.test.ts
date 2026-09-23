import { describe, expect, it } from "vitest";

import { buildResultsUrl } from "../src/lib/results-url";

describe("buildResultsUrl", () => {
  it("keeps current and stale family facts out of the destination", () => {
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

    expect(url).toBe("/results/details");
    expect(buildResultsUrl(state, "/results#medical-story")).toBe("/results");
    expect(buildResultsUrl(state, "/results-elsewhere?notes=private")).toBe("/results");
    expect(buildResultsUrl(state, "//external.example/results")).toBe("/results");
  });
});
