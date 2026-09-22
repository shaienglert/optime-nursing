import { DECISION_RESPONSE_CACHE_SESSION_KEY, loadSessionJson, removeSessionKey, saveSessionJson } from "./search-session";

const KEY = "oomnik.confirmed-intake";
function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") return Object.fromEntries(
    Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, stable(item)]),
  );
  return value;
}
export function intakeInputKey(state: Record<string, unknown>, query: string) {
  const facts = { ...state };
  delete facts.questionnaireCompletion;
  return JSON.stringify(stable({ facts, query: query.trim() }));
}
export function saveConfirmedIntake(id: string, inputKey: string) {
  saveSessionJson(KEY, { id, inputKey });
  if (loadSessionJson<{ id: string }>(KEY)?.id !== id) throw new Error("Please enable session storage before confirming your profile.");
  removeSessionKey(DECISION_RESPONSE_CACHE_SESSION_KEY);
}
export function confirmedIntakeId(state: Record<string, unknown>, query: string): string | undefined {
  const saved = loadSessionJson<{ id: string; inputKey: string }>(KEY);
  if (!saved) return undefined; // Legacy/API-only journeys have no reviewed artifact.
  if (saved.inputKey !== intakeInputKey(state, query)) {
    throw new Error("Your answers changed. Please review and confirm your profile again.");
  }
  return saved.id;
}
