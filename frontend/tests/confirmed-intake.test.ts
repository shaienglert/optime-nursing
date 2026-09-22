import { beforeEach, expect, test, vi } from "vitest";

const memory = vi.hoisted(() => new Map<string, unknown>());
vi.mock("../src/lib/search-session", () => ({
  DECISION_RESPONSE_CACHE_SESSION_KEY: "decision-cache",
  loadSessionJson: (key: string) => memory.get(key) ?? null,
  saveSessionJson: (key: string, value: unknown) => memory.set(key, value),
  removeSessionKey: (key: string) => memory.delete(key),
}));
import { confirmedIntakeId, intakeInputKey, saveConfirmedIntake } from "../src/lib/confirmed-intake";

beforeEach(() => memory.clear());
test("confirmation metadata preserves the artifact; changed case facts require review", () => {
  const facts = { budget: 5000, notes: "mother", medical: { oxygen: false } };
  memory.set("decision-cache", { old: true });
  saveConfirmedIntake("server-id", intakeInputKey(facts, "mother"));
  expect(memory.has("decision-cache")).toBe(false);
  expect(confirmedIntakeId({ ...facts, aiProcessContinuity: { phase: "RECOMMEND", lastEvent: "RESULTS_VIEWED", updatedAt: "now" } }, "mother")).toBe("server-id");
  expect(confirmedIntakeId({ medical: facts.medical, notes: "mother", budget: 5000, questionnaireCompletion: { clientSummaryConfirmed: true } }, " mother ")).toBe("server-id");
  expect(() => confirmedIntakeId({ ...facts, budget: 6000 }, "mother")).toThrow(/review/);
  expect(() => confirmedIntakeId(facts, "father")).toThrow(/review/);
});
test("legacy journeys do not manufacture a reviewed artifact", () => {
  expect(confirmedIntakeId({}, "")).toBeUndefined();
});
