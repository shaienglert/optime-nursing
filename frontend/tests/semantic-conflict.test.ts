import { describe, expect, it } from "vitest";
import { hasUnresolvedSemanticConflict } from "../src/lib/semantic-conflict";

describe("unresolved semantic conflicts", () => {
  it("requires an explicit answer for ambiguous required input", () => {
    expect(hasUnresolvedSemanticConflict([{ status: "ASKED", knowledge_state: "AMBIGUOUS", importance: "MUST" }])).toBe(true);
  });
  it("does not block resolved facts or optional ambiguity", () => {
    expect(hasUnresolvedSemanticConflict([{ status: "USED", knowledge_state: "KNOWN", importance: "MUST" }])).toBe(false);
    expect(hasUnresolvedSemanticConflict([{ status: "ASKED", knowledge_state: "AMBIGUOUS", importance: "NICE" }])).toBe(false);
    expect(hasUnresolvedSemanticConflict(undefined)).toBe(false);
  });
});
