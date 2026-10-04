import type { QuestionnaireState } from "@/context/questionnaire-context";
import type { DecisionEngineResponse, PatientNeed } from "./api";
import { isFinalRecommendation } from "./recommendation-eligibility";

export function personalSummary(state: QuestionnaireState): string[] {
  const person = ({ Mom: "your mother", Dad: "your father", Myself: "yourself", Couple: "both of you", Spouse: "your spouse" } as Record<string, string>)[state.relationship] || "your loved one";
  const needs = [state.assistanceLevel, state.memoryStatus, ...state.medicalCareProfile.needs].filter(Boolean);
  const priorities = [...state.happinessPreferences, ...state.moveLossConcerns].filter(Boolean);
  return [
    `You are looking for a place for ${person}${state.ageGroup ? ` (${state.ageGroup})` : ""}. ${needs.length ? `Your answers describe the support and safety needs we should focus on: ${needs.join("; ")}.` : "We will use the needs you confirmed to guide the search."}`,
    priorities.length ? `The move also needs to respect what matters in everyday life: ${priorities.join(", ")}. These priorities will be considered alongside the essential care requirements.` : "We will distinguish the essential requirements from preferences, so you can see what each option actually offers.",
    [state.budget > 0 ? `Your monthly budget is up to $${state.budget.toLocaleString("en-US")}.` : "", state.referenceAddress || state.referenceLocationValue ? `You chose ${state.referenceAddress || state.referenceLocationValue}${state.maximumDistanceMiles ? `, within ${state.maximumDistanceMiles} miles` : ""}.` : "", state.moveTiming ? `Your move timing is ${state.moveTiming}.` : ""].filter(Boolean).join(" "),
    state.notes?.trim() ? `You also told us: “${state.notes.trim()}”` : "",
  ].filter(Boolean);
}

export function facilityExplanation(item: DecisionEngineResponse["results"][number], needs: PatientNeed[] = []): string[] {
  const reasons = item.explanation?.why_matches || [];
  // Preserve the authoritative facts, but place substantive care/lifestyle before basics.
  const substantive = reasons.filter(text => !/\benglish\b|budget|price|language/i.test(text));
  // Language/starting-price facts remain in expandable matching notes. They
  // should not substitute for a meaningful explanation of personal fit.
  const explanation = substantive.filter(Boolean).join(" ");
  const requested = needs.filter(need => ["REQUIRED", "HIGH"].includes(need.requirement_level) && need.need_text).map(need => need.need_text).slice(0, 3);
  const context = requested.length ? `You asked me to keep ${requested.join(", ")} in mind. ` : "";
  return [explanation ? `${context}Here is what brought ${item.facility_name || "this community"} into your search. ${explanation}` : `${context}This community meets the essential checks for the needs you confirmed. I still need more evidence to explain what everyday life here would mean for you.`,
    item.tie_break_explanation_vs_next?.why_ranked_above || ""].filter(Boolean);
}

export function resultsIntroduction(state: QuestionnaireState, count: number): string[] {
  const person = ({ Mom: "your mother", Dad: "your father", Myself: "you", Couple: "both of you", Spouse: "your spouse" } as Record<string, string>)[state.relationship] || "your loved one";
  return [count ? `Thank you for telling me what matters to ${person}. I’ve found ${count} ${count === 1 ? "place" : "places"} to explore together, using the needs you confirmed and the information we have about each community. Let’s start with why each one is here, then talk through what you would want to know before taking the next step. You can take your time.` : "We do not yet have a recommendation that meets the essential checks. Your answers are saved. Let’s talk through what is still missing and where we can go from here, keeping the support you need in view.",
    state.notes?.trim() ? `I’m also keeping your own words in view: “${state.notes.trim()}”. Each community still needs evidence before I can say it meets those requests.` : ""] .filter(Boolean);
}

export function recommendationFromDecision(decision: DecisionEngineResponse | null, id: string) {
  return decision?.results.find(item => item.canonical_facility_id === id && isFinalRecommendation(item)) || null;
}
