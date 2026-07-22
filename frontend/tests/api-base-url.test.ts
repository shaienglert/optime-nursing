import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchPatientDecisionRecommendations, getApiBaseUrl } from "../src/lib/api";

describe("getApiBaseUrl", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const originalWindow = (globalThis as { window?: unknown }).window;
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    if (originalPublicApiUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = originalPublicApiUrl;
    }

    if (originalWindow === undefined) {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }

    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("falls back to local backend in development when no NEXT_PUBLIC_API_URL is set", () => {
    process.env.NODE_ENV = "development";
    delete process.env.NEXT_PUBLIC_API_URL;
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses same-origin proxy in browser even if NEXT_PUBLIC_API_URL points at localhost:3000", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://localhost:3000",
        hostname: "localhost",
      },
    };

    expect(getApiBaseUrl()).toBe("/api/backend");
  });

  it("uses same-origin proxy in browser with loopback alias mismatch", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://127.0.0.1:3000",
        hostname: "127.0.0.1",
      },
    };

    expect(getApiBaseUrl()).toBe("/api/backend");
  });

  it("guards against local frontend :3000 base even when window is unavailable", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:3000";
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses configured backend base when provided", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000";
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("routes Results recommendations request through same-origin backend proxy", async () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://localhost:3000",
        hostname: "localhost",
      },
    };

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        patient_needs_profile: {
          generated_from: { questionnaire: true, natural_language: true },
          needs: [],
          need_tags: [],
          priority_parameter_ids: [],
          profile_key: null,
        },
        evaluation_context: {
          available_facilities_count: 0,
          scored_facilities_count: 0,
          filter_exclusion_summary: {
            hard_filter_exclusions: 0,
            soft_penalty_flags: 0,
            unavailable_marked: 0,
            insufficient_evidence_flags: 0,
          },
          assumptions_applied: [],
        },
        result_count: 0,
        total_candidates_scored: 0,
        availability_policy: "",
        results: [],
        recommendation_matrix: [],
        recommendation_trace: [],
      }),
    })) as unknown as typeof fetch;

    globalThis.fetch = fetchMock;

    await fetchPatientDecisionRecommendations({
      questionnaire_state: {
        relationship: "Dad",
        ageGroup: "80-84",
      },
      natural_language_query: "stroke rehab",
      limit: 50,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestUrl, requestInit] = (fetchMock as unknown as { mock: { calls: unknown[][] } }).mock.calls[0] || [];
    expect(requestUrl).toBe("/api/backend/decision-engine/recommendations");
    expect((requestInit as { method?: string })?.method).toBe("POST");
  });
});
