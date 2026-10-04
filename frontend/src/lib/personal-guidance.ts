import type { QuestionnaireState } from "@/context/questionnaire-context";
import type { DecisionEngineResponse } from "./api";
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

export function facilityExplanation(item: DecisionEngineResponse["results"][number]): string[] {
  const reasons = item.explanation?.why_matches || [];
  // Preserve the authoritative facts, but place substantive care/lifestyle before basics.
  const substantive = reasons.filter(text => !/\benglish\b|budget|price|language/i.test(text));
  const basics = reasons.filter(text => !substantive.includes(text));
  const explanation = [...substantive, ...basics].filter(Boolean).join(" ");
  return [explanation || "This option passed the essential checks for your confirmed needs. A detailed explanation of its personal fit is not available yet.",
    item.tie_break_explanation_vs_next?.why_ranked_above || ""].filter(Boolean);
}

export function resultsIntroduction(state: QuestionnaireState, count: number): string[] {
  return [count ? `We have ${count} option${count === 1 ? "" : "s"} for you to explore. We compared your confirmed care needs and personal priorities with the evidence available for each community. The order below reflects that comparison; each option explains its fit and any open questions.` : "We do not yet have a recommendation that passes the essential checks. Let’s review the open questions and decide how to move forward.",
    state.notes?.trim() ? `Your additional comments remain part of the search: “${state.notes.trim()}”. Each community still needs evidence before we can say it meets those requests.` : ""] .filter(Boolean);
}

export function recommendationFromDecision(decision: DecisionEngineResponse | null, id: string) {
  return decision?.results.find(item => item.canonical_facility_id === id && isFinalRecommendation(item)) || null;
}
