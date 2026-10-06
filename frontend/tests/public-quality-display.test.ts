import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { PublicQuality } from "../src/lib/api";
import { publicQualityLines, publicQualityLink } from "../src/lib/public-quality-display";

const alis: PublicQuality = { kind: "NV_STATE_INSPECTION", source_label: "Nevada DPBH inspection records", latest_grade: "A", latest_grade_date: "03/19/2026", graded_inspections: 9, inspections_on_record: 10, grades_below_a: { B: 2 }, disciplinary_action_on_record: false, source_url: "https://example.org/r", caveat: "An A grade means compliance; not resident satisfaction." };

describe("public quality display", () => {
  it("states the latest state grade with its date and history, without scoring", () => {
    const lines = publicQualityLines(alis);
    expect(lines[0].text).toContain("Latest grade A (03/19/2026)");
    expect(lines[0].text).toContain("2 × B");
    expect(lines.some((l) => l.text.includes("not resident satisfaction"))).toBe(true);
  });
  it("never turns a missing grade into a low grade", () => {
    const lines = publicQualityLines({ ...alis, latest_grade: null, latest_grade_date: null, graded_inspections: 0 });
    expect(lines[0].text).toContain("not a negative finding");
    expect(lines[0].text).not.toMatch(/Latest grade/);
  });
  it("keeps the Medicare scale separate and says when a part has no rating", () => {
    const text = publicQualityLines({ kind: "CMS_FIVE_STAR", source_label: "Medicare Care Compare", overall: 2, health_inspection: 1, staffing: 3, quality_measures: null, as_of: "2026-08-01", caveat: "c" })[0].text;
    expect(text).toContain("Overall 2 of 5");
    expect(text).toContain("quality measures no rating");
  });
  it("says no record, not a bad record", () => {
    expect(publicQualityLines({ kind: "NONE", statement: "No public record. This is not a negative finding." })[0].text).toContain("not a negative finding");
    expect(publicQualityLines(null)).toEqual([]);
  });
  it("only links http(s) and the results page renders the block", () => {
    expect(publicQualityLink(alis)).toBe("https://example.org/r");
    expect(publicQualityLink({ ...alis, source_url: "javascript:x" })).toBeNull();
    expect(readFileSync("src/app/results/simple-results-page-client.tsx", "utf8")).toContain('data-testid="public-quality"');
  });
});
