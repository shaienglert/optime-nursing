import type { QuestionnaireState } from "@/context/questionnaire-context";
import type { OOmnikerPreferenceSuggestion } from "./api";

export type AdvisorTurn = { role: "user" | "assistant"; content: string };
export type AdvisorReply = { status: string; message?: string | null; follow_up?: string;
  proposals: OOmnikerPreferenceSuggestion[]; profile_mutated: false };

export function applyMeasuredPreferenceAdvice(state: QuestionnaireState, suggestion: OOmnikerPreferenceSuggestion): QuestionnaireState {
  if (suggestion.authority !== "PREFERENCE" || suggestion.action !== "OFFER_PREFERENCE_ALTERNATIVE"
    || suggestion.new_recommendation_count < 2 || suggestion.may_auto_change || !suggestion.requires_client_approval
    || suggestion.candidates.length !== suggestion.new_recommendation_count
    || suggestion.candidates.some(candidate => !candidate.canonical_facility_id)
    || new Set(suggestion.candidates.map(candidate => candidate.canonical_facility_id)).size !== suggestion.new_recommendation_count) return state;
  if (suggestion.change_kind === "WAIVE_NTH") {
    const consent = suggestion.acceptance;
    if (!consent || consent.parameter !== suggestion.parameter || !/^[a-f0-9]{64}$/.test(consent.input_fingerprint)) return state;
    return { ...state, questionnaireCompletion: { ...state.questionnaireCompletion,
      oomnikerRelaxedPreferences: [...(state.questionnaireCompletion.oomnikerRelaxedPreferences || [])
        .filter(item => item.parameter !== consent.parameter), { ...consent }] } };
  }
  if (suggestion.parameter === "COMMUNITY_ENVIRONMENT_MATCH" && ["Medium", "Large and active"].includes(suggestion.alternative_value)) {
    return { ...state, questionnaireCompletion: { ...state.questionnaireCompletion,
      clientSummaryConfirmed: false, confirmedAt: "" }, humanIntelligenceV2: { ...state.humanIntelligenceV2,
      personalityProfile: { ...state.humanIntelligenceV2.personalityProfile, communitySizePreference: suggestion.alternative_value } } };
  }
  return state;
}

export async function askMeasuredAdvisor(payload: {
  decision_id: string; questionnaire_state: QuestionnaireState; natural_language_query: string;
  limit: number; client_message: string; conversation: AdvisorTurn[];
}): Promise<AdvisorReply> {
  const response = await fetch("/api/backend/api/oomniker/advice", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(response.status === 409
    ? "Your answers changed or this search expired. Run the search again for current advice."
    : "The advisor is temporarily unavailable. You can still review the measured options below.");
  return response.json() as Promise<AdvisorReply>;
}
