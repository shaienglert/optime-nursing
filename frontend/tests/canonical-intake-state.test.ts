import { describe, expect, it } from "vitest";

import { applyCanonicalIdentity, canonicalIdentityFacts } from "../src/lib/canonical-intake-state";

describe("canonical intake identity", () => {
  it("keeps husband and wife as one resident while preserving gender", () => {
    expect(canonicalIdentityFacts("my husband")).toEqual({ relationship: "Spouse", gender: "Male" });
    expect(canonicalIdentityFacts("Wife")).toEqual({ relationship: "Spouse", gender: "Female" });
  });

  it("does not turn a spouse into a couple", () => {
    expect(canonicalIdentityFacts("husband").relationship).toBe("Spouse");
    expect(canonicalIdentityFacts("couple").relationship).toBe("Couple");
  });

  it("does not overwrite an explicit gender", () => {
    const state = { relationship: "", gender: "Other" };
    expect(applyCanonicalIdentity(state, "Dad").gender).toBe("Other");
    expect(applyCanonicalIdentity(state, "Spouse", "Male").gender).toBe("Other");
  });
});
