export const QUESTIONNAIRE_SESSION_KEY = "optime.questionnaire.session";
export const SEARCH_DRAFT_SESSION_KEY = "optime.search.draft";
export const COMPARE_SELECTION_SESSION_KEY = "optime.compare.selection";
export const FAVORITE_FACILITIES_SESSION_KEY = "optime.favorite.facilities";

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

export function loadCompareSelection(): string[] {
  const selection = loadSessionJson<unknown>(COMPARE_SELECTION_SESSION_KEY);
  return Array.isArray(selection) ? selection.map((value) => String(value)).filter(Boolean) : [];
}

export function saveCompareSelection(selectedIds: string[]): void {
  saveSessionJson(COMPARE_SELECTION_SESSION_KEY, selectedIds);
}

export function clearCompareSelection(): void {
  removeSessionKey(COMPARE_SELECTION_SESSION_KEY);
}

export function loadFavoriteFacilities(): string[] {
  const selection = loadSessionJson<unknown>(FAVORITE_FACILITIES_SESSION_KEY);
  return Array.isArray(selection) ? selection.map((value) => String(value)).filter(Boolean) : [];
}

export function saveFavoriteFacilities(selectedIds: string[]): void {
  saveSessionJson(FAVORITE_FACILITIES_SESSION_KEY, selectedIds);
}

export function clearFavoriteFacilities(): void {
  removeSessionKey(FAVORITE_FACILITIES_SESSION_KEY);
}