export const QUESTIONNAIRE_SESSION_KEY = "optime.questionnaire.session";
export const SEARCH_DRAFT_SESSION_KEY = "optime.search.draft";
export const COMPARE_SELECTION_SESSION_KEY = "optime.compare.selection";
export const FAVORITE_FACILITIES_SESSION_KEY = "optime.favorite.facilities";
export const DECISION_RESPONSE_CACHE_SESSION_KEY = "optime.decision.response.cache";
export const RECENT_SEARCHES_STORAGE_KEY = "optime.recent.searches";
export const SAVED_SEARCHES_STORAGE_KEY = "optime.saved.searches";
export const PATIENT_PROFILES_STORAGE_KEY = "optime.patient.profiles";
export const RECOMMENDATION_SESSIONS_STORAGE_KEY = "optime.recommendation.sessions";
export const PATIENT_CASE_ID_SESSION_KEY = "optime.patient.case.id";

export type SavedSearch = {
  id: string;
  title: string;
  naturalLanguageQuery: string;
  questionnaireState: Record<string, unknown>;
  createdAt: string;
};

export type PatientProfileRecord = {
  id: string;
  label: string;
  version: number;
  updatedAt: string;
  state: Record<string, unknown>;
};

export type RecommendationSessionRecord = {
  id: string;
  label: string;
  createdAt: string;
  recommendationIds: string[];
  requestKey: string;
};

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

export function clearAssessmentData(): void {
  clearSearchSession();
  removeSessionKey(DECISION_RESPONSE_CACHE_SESSION_KEY);
  clearCompareSelection();
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

function dedupeById<T extends { id: string }>(rows: T[]): T[] {
  const seen = new Set<string>();
  const output: T[] = [];
  for (const row of rows) {
    const id = String(row.id || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    output.push(row);
  }
  return output;
}

export function loadRecentSearches(): SavedSearch[] {
  const rows = loadLocalJson<SavedSearch[]>(RECENT_SEARCHES_STORAGE_KEY);
  return Array.isArray(rows) ? dedupeById(rows) : [];
}

export function saveRecentSearch(search: SavedSearch): void {
  const next = [search, ...loadRecentSearches().filter((row) => row.id !== search.id)].slice(0, 20);
  saveLocalJson(RECENT_SEARCHES_STORAGE_KEY, next);
}

export function loadSavedSearches(): SavedSearch[] {
  const rows = loadLocalJson<SavedSearch[]>(SAVED_SEARCHES_STORAGE_KEY);
  return Array.isArray(rows) ? dedupeById(rows) : [];
}

export function saveSavedSearch(search: SavedSearch): void {
  const next = [search, ...loadSavedSearches().filter((row) => row.id !== search.id)].slice(0, 50);
  saveLocalJson(SAVED_SEARCHES_STORAGE_KEY, next);
}

export function removeSavedSearch(id: string): void {
  saveLocalJson(
    SAVED_SEARCHES_STORAGE_KEY,
    loadSavedSearches().filter((row) => row.id !== id),
  );
}

export function loadPatientProfiles(): PatientProfileRecord[] {
  const rows = loadLocalJson<PatientProfileRecord[]>(PATIENT_PROFILES_STORAGE_KEY);
  return Array.isArray(rows) ? dedupeById(rows) : [];
}

export function upsertPatientProfile(profile: PatientProfileRecord): void {
  const next = [profile, ...loadPatientProfiles().filter((row) => row.id !== profile.id)].slice(0, 50);
  saveLocalJson(PATIENT_PROFILES_STORAGE_KEY, next);
}

export function removePatientProfile(id: string): void {
  saveLocalJson(
    PATIENT_PROFILES_STORAGE_KEY,
    loadPatientProfiles().filter((row) => row.id !== id),
  );
}

export function loadRecommendationSessions(): RecommendationSessionRecord[] {
  const rows = loadLocalJson<RecommendationSessionRecord[]>(RECOMMENDATION_SESSIONS_STORAGE_KEY);
  return Array.isArray(rows) ? dedupeById(rows) : [];
}

export function saveRecommendationSession(session: RecommendationSessionRecord): void {
  const next = [session, ...loadRecommendationSessions().filter((row) => row.id !== session.id)].slice(0, 100);
  saveLocalJson(RECOMMENDATION_SESSIONS_STORAGE_KEY, next);
}

export function removeRecommendationSession(id: string): void {
  saveLocalJson(
    RECOMMENDATION_SESSIONS_STORAGE_KEY,
    loadRecommendationSessions().filter((row) => row.id !== id),
  );
}