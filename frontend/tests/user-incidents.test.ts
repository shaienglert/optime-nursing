import { afterEach, expect, it, vi } from "vitest";
import { reportClientIncident } from "../src/lib/user-incidents";

afterEach(() => vi.unstubAllGlobals());

it("sends only a page category and event identity, never a private URL", async () => {
  vi.stubGlobal("window", { location: { pathname: "/facilities/private-token", search: "?email=secret" } });
  const fetch = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fetch);
  reportClientIncident("CLIENT_RUNTIME_ERROR");
  const body = JSON.parse(fetch.mock.calls[0][1].body);
  expect(body.page).toBe("/facilities");
  expect(Object.keys(body).sort()).toEqual(["event_id", "kind", "page"]);
  expect(JSON.stringify(body)).not.toContain("private-token");
});

it("a telemetry outage does not throw into the user flow", async () => {
  vi.stubGlobal("window", { location: { pathname: "/results" } });
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  expect(() => reportClientIncident("UNHANDLED_REJECTION")).not.toThrow();
  await Promise.resolve();
});
