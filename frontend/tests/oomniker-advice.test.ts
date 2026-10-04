import { expect, it } from "vitest";
import { applyMeasuredPreferenceAdvice } from "../src/lib/oomniker-advice";
import type { QuestionnaireState } from "../src/context/questionnaire-context";
import type { OOmnikerPreferenceSuggestion } from "../src/lib/api";

const state = { budget: 7000, maximumDistanceMiles: "20", memoryStatus: "Significant memory issues",
  questionnaireCompletion: { clientSummaryConfirmed: true }, humanIntelligenceV2: {
    personalityProfile: { communitySizePreference: "Small and familiar" },
    transitionRiskProfile: { wanderingConcerns: "Yes" } } } as unknown as QuestionnaireState;
const advice = { parameter: "DINING_EXPERIENCE", authority: "PREFERENCE", action: "OFFER_PREFERENCE_ALTERNATIVE",
  change_kind: "WAIVE_NTH", new_recommendation_count: 2, requires_client_approval: true, may_auto_change: false,
  acceptance: { parameter: "DINING_EXPERIENCE", input_fingerprint: "a".repeat(64) },
  candidates: [{ canonical_facility_id: "A" }, { canonical_facility_id: "B" }] } as OOmnikerPreferenceSuggestion;

it("records explicit consent without changing any underlying answer or MUST", () => {
  const before = structuredClone(state);
  const next = applyMeasuredPreferenceAdvice(state, advice);
  expect(state).toEqual(before);
  expect(next.questionnaireCompletion.oomnikerRelaxedPreferences).toEqual([advice.acceptance]);
  expect(next.budget).toBe(7000);
  expect(next.maximumDistanceMiles).toBe("20");
  expect(next.humanIntelligenceV2.transitionRiskProfile.wanderingConcerns).toBe("Yes");
  expect(next.memoryStatus).toBe(state.memoryStatus);
});

it("does not accept a single candidate, duplicate identities, mismatched consent or unsafe action", () => {
  for (const changed of [ { new_recommendation_count: 1 }, { candidates: [advice.candidates[0], advice.candidates[0]] },
    { may_auto_change: true }, { authority: "CLIENT_MUST" },
    { acceptance: { parameter: "SECURED_UNIT_AVAILABLE", input_fingerprint: "a".repeat(64) } } ]) {
    expect(applyMeasuredPreferenceAdvice(state, { ...advice, ...changed } as OOmnikerPreferenceSuggestion)).toBe(state);
  }
});

it("supports existing community-size choices and does not apply arbitrary profile patches", () => {
  const size = { ...advice, parameter: "COMMUNITY_ENVIRONMENT_MATCH", change_kind: "PROFILE_PATCH", alternative_value: "Medium" } as OOmnikerPreferenceSuggestion;
  expect(applyMeasuredPreferenceAdvice(state, size).humanIntelligenceV2.personalityProfile.communitySizePreference).toBe("Medium");
  expect(applyMeasuredPreferenceAdvice(state, size).questionnaireCompletion.clientSummaryConfirmed).toBe(false);
  expect(applyMeasuredPreferenceAdvice(state, { ...size, alternative_value: "Drop care" })).toBe(state);
});
