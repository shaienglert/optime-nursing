"use client";

import { useSyncExternalStore } from "react";
import { useQuestionnaire } from "@/context/questionnaire-context";
import type { DecisionEngineResponse } from "@/lib/api";
import { DECISION_RESPONSE_CACHE_SESSION_KEY } from "@/lib/search-session";
import { facilityExplanation, recommendationFromDecision } from "@/lib/personal-guidance";
import { PersonalNarrative } from "./personal-narrative";
import { CommunityNextStep } from "./community-next-step";

import { ServiceBudgetPlan } from "./service-budget-plan";
import { isOutsideCareConcern } from "@/lib/service-budget";

const subscribeCache = (callback: () => void) => {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
};
const cacheSnapshot = () => {
  try { return window.sessionStorage.getItem(DECISION_RESPONSE_CACHE_SESSION_KEY) || ""; }
  catch { return ""; }
};

export function FacilityPersonalFit({ facilityId, facilityName, backHref }: { facilityId: string; facilityName: string; backHref: string }) {
  const { state } = useQuestionnaire();
  const params = new URLSearchParams(backHref.split("?")[1] || "");
  const query = (params.get("q") || params.get("search") || params.get("notes") || state.notes || "").trim();
  const requestKey = JSON.stringify({ questionnaire_state: state, natural_language_query: query, limit: 50 });
  const rawCache = useSyncExternalStore(subscribeCache, cacheSnapshot, () => "");
  let decision: DecisionEngineResponse | null = null;
  try {
    const cached = JSON.parse(rawCache) as { requestKey: string; response: DecisionEngineResponse };
    if (cached.requestKey === requestKey) decision = cached.response;
  } catch { /* No current search is saved in this session. */ }
  const item = state.questionnaireCompletion.clientSummaryConfirmed ? recommendationFromDecision(decision, facilityId) : null;
  return <section className="rounded-3xl border border-[#d4e2da] bg-white p-5 sm:p-8">
    <h2 className="text-3xl font-semibold text-[#294f41]">{item ? "Why this place fits your search" : "Explore this community"}</h2>
    {item ? <div className="mt-4"><PersonalNarrative state={state} decisionId={decision?.decision_id || undefined} facilityId={facilityId} query={query} fallback={facilityExplanation(item)} />
      {(item.explanation?.concerns || []).filter(text => !isOutsideCareConcern(text)).length ? <div className="mt-5 rounded-2xl bg-amber-50 p-5 text-lg leading-8"><h3 className="font-semibold">Important considerations</h3>{item.explanation.concerns.filter(text => !isOutsideCareConcern(text)).map(text => <p key={text}>{text}</p>)}</div> : null}
      {(item.explanation?.needs_verification || []).length ? <div className="mt-5 text-lg leading-8"><h3 className="font-semibold">What we’ll check with the community</h3>{item.explanation.needs_verification.map(text => <p key={text}>{text}</p>)}</div> : null}
    </div> : <p className="mt-4 text-lg leading-8">A personal recommendation is available after you complete and confirm your questionnaire. The details below describe the evidence we have for this community.</p>}
    {item ? <ServiceBudgetPlan item={item} budget={state.budget} couple={state.relationship === "Couple"} needs={decision?.patient_needs_profile?.needs} options={decision?.care_partner_options} /> : null}
    {item?.explanation?.concerns.some(isOutsideCareConcern) ? <details className="mt-4 text-base"><summary className="cursor-pointer underline">Original care evidence notes</summary>{item.explanation.concerns.filter(isOutsideCareConcern).map(text => <p key={text}>{text}</p>)}</details> : null}
    {item?.synthetic_pilot ? <p className="mt-5 rounded-xl bg-amber-50 p-4 text-lg">This is a synthetic pilot community. Visits and room enquiries for it are test requests.</p> : null}
    <CommunityNextStep facilityId={facilityId} facilityName={facilityName} serviceNeeds={decision?.patient_needs_profile?.needs.map(need => need.need_text || need.parameter_id)} />
  </section>;
}
