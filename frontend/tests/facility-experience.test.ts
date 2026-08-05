import { describe, expect, it } from "vitest";

import { resolveFacilityImage, resolvePriceTruth, personLabel } from "../src/lib/facility-experience";

describe("facility experience helpers", () => {
  it("uses a compact placeholder when the image is not governed", () => {
    const result = resolveFacilityImage({
      visualIntelligence: {
        heroImage: {
          category: "exterior",
          url: "",
          source: "CMS Placeholder",
          collected_at: "",
        },
        galleryImages: [],
        lifestyleTags: [],
        visualConfidenceScore: 0,
        visualCoverageScore: 0,
      },
    } as never);

    expect(result.url).toBe("/cms-placeholder.svg");
    expect(result.isPlaceholder).toBe(true);
    expect(result.sourceLabel).toBe("Neutral placeholder");
  });

  it("preserves a verified facility image without inventing a fallback", () => {
    const result = resolveFacilityImage({
      visualIntelligence: {
        heroImage: {
          category: "exterior",
          url: "https://riversidecarecenter.com/wp-content/uploads/2022/08/Riverside-edited-1.jpeg",
          source: "Official Site",
          collected_at: "2026-07-22T00:00:00Z",
        },
        galleryImages: [],
        lifestyleTags: [],
        visualConfidenceScore: 100,
        visualCoverageScore: 100,
      },
    } as never);

    expect(result.url).toContain("riversidecarecenter.com");
    expect(result.isPlaceholder).toBe(false);
  });

  it("labels derived price as an estimate and missing price as unknown", () => {
    expect(resolvePriceTruth({ priceRange: "$5,000 - $6,000/month" } as never).truthState).toBe("DERIVED");
    expect(resolvePriceTruth({ priceRange: "" } as never).truthState).toBe("UNKNOWN");
  });

  it("resolves the family label without inventing identity", () => {
    expect(personLabel("Dad")).toBe("Dad");
    expect(personLabel("Myself")).toBe("yourself");
    expect(personLabel("")).toBe("your family member");
  });
});
