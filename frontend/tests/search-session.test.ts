import { afterEach, describe, expect, it } from "vitest";

import {
  COMPARE_SELECTION_SESSION_KEY,
  DECISION_RESPONSE_CACHE_SESSION_KEY,
  FAVORITE_FACILITIES_SESSION_KEY,
  PATIENT_CASE_ID_SESSION_KEY,
  QUESTIONNAIRE_SESSION_KEY,
  SEARCH_DRAFT_SESSION_KEY,
  clearAssessmentData,
} from "../src/lib/search-session";

class MemoryStorage {
  private values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

afterEach(() => {
  Reflect.deleteProperty(globalThis, "window");
});

describe("scoped assessment data clearing", () => {
  it("clears assessment and recommendation session data while preserving favorites", () => {
    const sessionStorage = new MemoryStorage();
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: { sessionStorage },
    });
    for (const key of [QUESTIONNAIRE_SESSION_KEY, SEARCH_DRAFT_SESSION_KEY, PATIENT_CASE_ID_SESSION_KEY, DECISION_RESPONSE_CACHE_SESSION_KEY, COMPARE_SELECTION_SESSION_KEY, FAVORITE_FACILITIES_SESSION_KEY]) {
      sessionStorage.setItem(key, "saved");
    }

    clearAssessmentData();

    expect(sessionStorage.getItem(QUESTIONNAIRE_SESSION_KEY)).toBeNull();
    expect(sessionStorage.getItem(SEARCH_DRAFT_SESSION_KEY)).toBeNull();
    expect(sessionStorage.getItem(PATIENT_CASE_ID_SESSION_KEY)).toBeNull();
    expect(sessionStorage.getItem(DECISION_RESPONSE_CACHE_SESSION_KEY)).toBeNull();
    expect(sessionStorage.getItem(COMPARE_SELECTION_SESSION_KEY)).toBeNull();
    expect(sessionStorage.getItem(FAVORITE_FACILITIES_SESSION_KEY)).toBe("saved");
  });
});