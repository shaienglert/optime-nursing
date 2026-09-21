import { describe, expect, it } from "vitest";
import { boundPersonalReportRequest } from "../src/lib/personal-report-request";

describe("personal report upload", () => {
  it("reuses a small cached decision", () => {
    const request = { questionnaire_state: { budget: 5000 }, decision_result: { results: [] } };
    expect(boundPersonalReportRequest(request)).toBe(request);
  });
  it("preserves the original inputs when a Unicode evidence graph exceeds the byte limit", () => {
    const inputs = { questionnaire_state: { budget: 5000 }, natural_language_query: "אמא זקוקה לעזרה", limit: 50 };
    const request = { ...inputs, decision_result: { evidence: "א".repeat(300000) } };
    expect(boundPersonalReportRequest(request)).toEqual(inputs);
    expect(request.decision_result).toBeDefined();
  });
});
