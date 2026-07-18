export const QUESTIONNAIRE_SESSION_KEY = "optime.questionnaire.session";
export const SEARCH_DRAFT_SESSION_KEY = "optime.search.draft";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

export function loadSessionJson<T>(key: string): T | null {
  if (!hasWindow()) return null;

  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function saveSessionJson(key: string, value: unknown): void {
  if (!hasWindow()) return;

  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Best-effort persistence only.
  }
}

export function removeSessionKey(key: string): void {
  if (!hasWindow()) return;

  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Ignore storage cleanup failures.
  }
}

export function clearSearchSession(): void {
  removeSessionKey(QUESTIONNAIRE_SESSION_KEY);
  removeSessionKey(SEARCH_DRAFT_SESSION_KEY);
}