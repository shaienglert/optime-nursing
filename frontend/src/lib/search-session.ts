export const QUESTIONNAIRE_SESSION_KEY = "optime.questionnaire.session";
export const SEARCH_DRAFT_SESSION_KEY = "optime.search.draft";
export const COMPARE_SELECTION_SESSION_KEY = "optime.compare.selection";
export const FAVORITE_FACILITIES_SESSION_KEY = "optime.favorite.facilities";
export const DECISION_RESPONSE_CACHE_SESSION_KEY = "optime.decision.response.cache";
export const PATIENT_CASE_ID_SESSION_KEY = "optime.patient.case.id";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

function canUseLocalStorage(): boolean {
  return hasWindow() && typeof window.localStorage !== "undefined";
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
  removeSessionKey(PATIENT_CASE_ID_SESSION_KEY);
}

export function loadPatientCaseId(): number | null {
  const value = loadSessionJson<number | string>(PATIENT_CASE_ID_SESSION_KEY);
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function savePatientCaseId(patientCaseId: number): void {
  if (!Number.isFinite(patientCaseId) || patientCaseId <= 0) return;
  saveSessionJson(PATIENT_CASE_ID_SESSION_KEY, patientCaseId);
}

export function clearPatientCaseId(): void {
  removeSessionKey(PATIENT_CASE_ID_SESSION_KEY);
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

type DecisionResponseCachePayload<T> = {
  requestKey: string;
  response: T;
};

export function loadDecisionResponseCache<T>(requestKey: string): T | null {
  const cached = loadSessionJson<DecisionResponseCachePayload<T>>(DECISION_RESPONSE_CACHE_SESSION_KEY);
  if (!cached) return null;
  if (cached.requestKey !== requestKey) return null;
  return cached.response;
}

export function saveDecisionResponseCache<T>(requestKey: string, response: T): void {
  saveSessionJson(DECISION_RESPONSE_CACHE_SESSION_KEY, { requestKey, response } satisfies DecisionResponseCachePayload<T>);
}

export function loadLocalJson<T>(key: string): T | null {
  if (!canUseLocalStorage()) return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function saveLocalJson(key: string, value: unknown): void {
  if (!canUseLocalStorage()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore local persistence failures in constrained environments.
  }
}

export function removeLocalKey(key: string): void {
  if (!canUseLocalStorage()) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore cleanup failures.
  }
}