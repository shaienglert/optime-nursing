import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ExternalRatingsPanel } from "../src/components/facility/external-ratings";

const missing = { status: "UNAVAILABLE" as const, rating: null, review_count: null, recognition: null,
  assessment_year: null, observed_at: null, source_url: null };

describe("external source display", () => {
  it("shows exact source attribution, count, year and the no-ranking disclosure", () => {
    const html = renderToStaticMarkup(createElement(ExternalRatingsPanel, { data: {
      google: { ...missing, status: "AVAILABLE", rating: 4.7, review_count: 82,
        observed_at: "2026-11-06T10:00:00Z", source_url: "https://maps.google.com/?cid=123" },
      us_news: { ...missing, status: "AVAILABLE", recognition: "Best Assisted Living", assessment_year: 2026,
        source_url: "https://health.usnews.com/best-senior-living/example-123" },
    } }));
    expect(html).toContain("4.7 / 5");
    expect(html).toContain("82 reviews");
    expect(html).toContain("Best Assisted Living");
    expect(html).toContain("2026 assessment");
    expect(html).toContain("do not affect Oomnik&#x27;s match ranking or break ties");
    expect(html).toContain('rel="noopener noreferrer"');
  });
  it("does not turn missing ratings into zero or an invented US News score", () => {
    const html = renderToStaticMarkup(createElement(ExternalRatingsPanel, { data: { google: missing, us_news: missing } }));
    expect(html).toContain("No rating available");
    expect(html).toContain("No assessment available");
    expect(html).not.toContain("0 / 5");
    expect(html).toContain("does not mean poor quality");
  });
  it("keeps failed loading separate from absent assessments", () => {
    const html = renderToStaticMarkup(createElement(ExternalRatingsPanel, { data: null, failed: true }));
    expect(html).toContain("Source temporarily unavailable");
    expect(html).not.toContain("0 / 5");
  });
});
