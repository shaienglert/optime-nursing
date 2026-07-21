import { afterEach, describe, expect, it } from "vitest";

import { getApiBaseUrl } from "../src/lib/api";

describe("getApiBaseUrl", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const originalWindow = (globalThis as { window?: unknown }).window;

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
  });

  it("falls back to local backend in development when no NEXT_PUBLIC_API_URL is set", () => {
    process.env.NODE_ENV = "development";
    delete process.env.NEXT_PUBLIC_API_URL;
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("guards against localhost self-reference to frontend origin", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://localhost:3000",
        hostname: "localhost",
      },
    };

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses configured backend base when provided", () => {
    process.env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000";
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });
});
