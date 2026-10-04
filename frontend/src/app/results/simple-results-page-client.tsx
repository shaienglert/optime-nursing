"use client";

import Link from "next/link";
import { OomnikMark } from "@/components/brand/oomnik-mark";
import Image from "next/image";
import { PilotPhoto } from "@/components/facility/pilot-photo";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { createClientCase, DecisionEngineResponse, fetchPatientDecisionRecommendations, type OOmnikerPreferenceSuggestion } from "@/lib/api";
import { loadDecisionResponseCache, saveDecisionResponseCache, saveSessionJson, QUESTIONNAIRE_SESSION_KEY } from "@/lib/search-session";
import { isFinalRecommendation, isPendingRecommendation } from "@/lib/recommendation-eligibility";
import { applyAdaptiveAnswer } from "@/lib/adaptive-answer";
import { resultsClientState } from "@/lib/results-client-state";
import { parseOomnikerQuantities } from "@/lib/oomniker-quantity";
import { medicaidBudgetIsConditional } from "@/lib/medicaid-budget-scenario";
import { DistanceScope } from "./distance-scope";

import { PersonalNarrative } from "@/components/guidance/personal-narrative";
import { LiveText } from "@/components/guidance/live-text";
import { CommunityNextStep } from "@/components/guidance/community-next-step";
import { facilityExplanation, resultsIntroduction } from "@/lib/personal-guidance";

import { ServiceBudgetPlan } from "@/components/guidance/service-budget-plan";
import { isOutsideCareConcern } from "@/lib/service-budget";

import { preferenceAdvice } from "@/lib/search-advice";

const TOP_COUNT = 5;

const adviceLabels: Record<string, string> = {
  COMMUNITY_ENVIRONMENT_MATCH: "Community size", PREFERRED_LANGUAGE_SUPPORT: "Preferred language", CONTINUUM_OF_CARE: "Future care continuity",
  inspection_rating: "Inspection rating", deficiency_count: "Inspection deficiencies", total_nurse_hours_per_resident_day: "Nursing hours per resident per day",
  rn_hours_per_resident_day: "Registered nurse hours per resident per day", staffing_turnover: "Staff turnover (%)",
  public_rating: "Public review rating", public_review_count: "Public review count", alis_latest_grade: "Regulatory grade", alis_disciplinary_action: "Regulatory disciplinary record",
};

const missingEvidenceLabels: Record<string, string> = {
  SEMANTIC_BUDGET_VERIFICATION: "a current price within your budget",
  SEMANTIC_SOCIAL_DELIVERY: "the social activities you asked for",
  SEMANTIC_FUTURE_CARE_PATH: "a verified future care pathway",
  SEMANTIC_MOBILITY_LAYOUT: "an accessible layout",
  SEMANTIC_DIETARY_SAFETY: "dietary safety",
  SEMANTIC_ALL_DAILY_MEALS: "daily meal service",
  SEMANTIC_CLINICAL_ACUITY: "the clinical support needed",
  SEMANTIC_KOSHER_DIET: "kosher meals",
  SEMANTIC_LANGUAGE_SUPPORT: "language support",
  SEMANTIC_MEDICAID_PATHWAY: "Medicaid participation",
  MEDICATION_SUPPORT_AVAILABLE: "medication support",
  ADL_SUPPORT_AVAILABLE: "help with daily activities",
  SECURE_MEMORY_CARE_CONFIRMED: "secure memory care",
  SECURED_UNIT_AVAILABLE: "a secured unit with wandering protection",
  REHAB_PATH_AVAILABLE: "a rehabilitation pathway",
  COUPLE_CORESIDENCE: "a shared living arrangement",
  RECOVERY_TRANSITION_COMPATIBLE: "a suitable recovery transition",
};

function personLabel(relationship: string, query: string): string {
  if (relationship === "Myself") return "you";
  if (relationship === "Couple") return "both of you";
  if (relationship === "Mom") return "Mom";
  if (relationship === "Dad") return "Dad";
  if (relationship) return relationship;
  const text = query.toLowerCase();
  if (/\b(my\s+)?mother\b|\bmom\b/.test(text)) return "Mom";
  if (/\b(my\s+)?father\b|\bdad\b/.test(text)) return "Dad";
  if (/\b(my\s+)?wife\b/.test(text)) return "your wife";
  if (/\b(my\s+)?husband\b/.test(text)) return "your husband";
  return "your loved one";
}

function cleanText(value: string): string {
  return value
    .replace(/UNKNOWN/gi, "information still being checked")
    .replace(/not verified/gi, "still being checked")
    .replace(/potentially eligible/gi, "needs verification")
    .replace(/cms placeholder/gi, "")
    .trim();
}

export function SimpleResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, setState } = useQuestionnaire();
  const [response, setResponse] = useState<DecisionEngineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [followUpAnswer, setFollowUpAnswer] = useState("");
  const [continuingInterview, setContinuingInterview] = useState(false);
  const followUpTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (followUpTimer.current) clearTimeout(followUpTimer.current); }, []);
  const [searchStage, setSearchStage] = useState(0);
  const [oomnikerOpen, setOOmnikerOpen] = useState(false);
  const [oomnikerText, setOOmnikerText] = useState("");
  const [oomnikerNotice, setOOmnikerNotice] = useState("");
  const oomnikerHistory = useRef<typeof state[]>([]);
  const beforeOOmnikerIds = useRef<string[]>([]);
  const [oomnikerDiff, setOOmnikerDiff] = useState<string>("");
  const [saveCaseOpen, setSaveCaseOpen] = useState(false);
  const [caseContact, setCaseContact] = useState({ name: "", email: "", phone: "", terms: false });
  const [savingCase, setSavingCase] = useState(false);
  const [savedCaseToken, setSavedCaseToken] = useState<string | null>(null);

  async function saveClientCase() {
    if (!caseContact.terms || (!caseContact.email.trim() && !caseContact.phone.trim())) return;
    setSavingCase(true);
    try {
      const created = await createClientCase({ questionnaire_state: state as unknown as Record<string, unknown>, contact_name: caseContact.name.trim() || undefined, email: caseContact.email.trim() || undefined, phone: caseContact.phone.trim() || undefined, terms_accepted: true });
      setSavedCaseToken(created.case_token);
      window.localStorage.setItem("oomnik.client.case.token", created.case_token);
      setSaveCaseOpen(false);
    } finally { setSavingCase(false); }
  }

  function applyOOmnikerChange() {
    const text = oomnikerText.trim();
    if (!text) return;
    const lower = text.toLowerCase();
    beforeOOmnikerIds.current = (response?.results || []).filter(isFinalRecommendation).slice(0, TOP_COUNT).map((item) => item.canonical_facility_id);
    setOOmnikerDiff("");
    setState((current) => {
      oomnikerHistory.current.push(JSON.parse(JSON.stringify(current)));
      const next = JSON.parse(JSON.stringify(current));
      const quantities = parseOomnikerQuantities(text);
      if (quantities.budget !== undefined) { next.budget = quantities.budget; next.medicaidOriginalBudget = undefined; next.medicaidBudgetScenarioChoice = ""; next.medicaidBudgetIncludesSupport = "Not sure"; }
      if (quantities.miles) { next.maximumDistanceMiles = quantities.miles; next.customDistanceMiles = quantities.miles; next.approvedSearchRadiusMiles = ""; next.locationImportant = "Yes"; }
      if (quantities.clearRadius) { next.maximumDistanceMiles = ""; next.customDistanceMiles = ""; next.approvedSearchRadiusMiles = ""; next.locationImportant = "No"; }
      if (/dog.*(?:not|no longer).*(?:require|important)|(?:remove|drop).*(?:dog|pet)/.test(lower)) next.humanIntelligenceV2.independenceProfile.petOwnershipImportance = "Not important";
      if (/large community.*(?:not|no longer).*(?:important|required)|(?:remove|drop).*large community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "No preference";
      if (/independent.*(?:outing|leave|go out).*(?:required|must|only)/.test(lower)) next.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently = "Very important";
      if (/community.*small|small community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Small";
      if (/community.*medium|medium community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Medium";
      if (/community.*large|large community/.test(lower) && !/large community.*(?:not|no longer).*(?:important|required)|(?:remove|drop).*large community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Large";
      if (/parking.*(?:not|no longer).*(?:need|required)|(?:remove|drop).*parking/.test(lower)) next.parkingRequirement = "No";
      if (/parking.*(?:need|required|important)/.test(lower) && !/(?:not|no longer)/.test(lower)) next.parkingRequirement = "Yes";
      if (/future care.*(?:important|required)|avoid another move/.test(lower)) next.futureCarePreference = /future care.*required/.test(lower) ? "Required" : "Preferred";
      if (/future care.*(?:not|no longer).*(?:important|required)|(?:remove|drop).*future care/.test(lower)) next.futureCarePreference = "No preference";
      next.questionnaireCompletion.clientSummaryConfirmed = true;
      next.questionnaireCompletion.confirmedAt = new Date().toISOString();
      return next;
    });
    setOOmnikerNotice(`Got it. I’ll make this change — “${text}” — and leave everything else as we agreed. I’m checking whether it changes the decision in a meaningful way.`);
    setOOmnikerText("");
    setOOmnikerOpen(false);
  }

  function acceptCommunitySizeAdvice(suggestion: OOmnikerPreferenceSuggestion) {
    if (suggestion.parameter !== "COMMUNITY_ENVIRONMENT_MATCH" || suggestion.new_recommendation_count < 2
      || suggestion.may_auto_change || !suggestion.requires_client_approval
      || !["Medium", "Large and active"].includes(suggestion.alternative_value)) return;
    beforeOOmnikerIds.current = (response?.results || []).filter(isFinalRecommendation).slice(0, TOP_COUNT).map(item => item.canonical_facility_id);
    setOOmnikerDiff("");
    setState(current => {
      oomnikerHistory.current.push(JSON.parse(JSON.stringify(current)));
      return { ...current, humanIntelligenceV2: { ...current.humanIntelligenceV2,
        personalityProfile: { ...current.humanIntelligenceV2.personalityProfile, communitySizePreference: suggestion.alternative_value } } };
    });
    setOOmnikerNotice(`You chose ${suggestion.alternative_value.toLowerCase()}. I’m running the search again with that community size preference.`);
  }

  // Widening waits for the family: the engine only counts who fits a little further out,
  // and this is the one place that radius is accepted. It is undoable like any OOMNIKER change.
  function acceptRadiusExpansion(miles: number) {
    beforeOOmnikerIds.current = (response?.results || []).filter(isFinalRecommendation).slice(0, TOP_COUNT).map((item) => item.canonical_facility_id);
    setOOmnikerDiff("");
    setState((current) => {
      oomnikerHistory.current.push(JSON.parse(JSON.stringify(current)));
      return { ...JSON.parse(JSON.stringify(current)), approvedSearchRadiusMiles: String(miles) };
    });
    setOOmnikerNotice(`Got it. I’m widening the search to ${miles} miles and leaving everything else as we agreed.`);
  }

  const activeCriteria = [
    state.assistanceLevel && ["Care", state.assistanceLevel],
    state.medicalCareProfile.mobilityMethod && ["Mobility", state.medicalCareProfile.mobilityMethod],
    state.memoryStatus && ["Memory", state.memoryStatus],
    state.futureCarePreference && ["Future care", state.futureCarePreference],
    state.humanIntelligenceV2.personalityProfile.communitySizePreference && ["Community", state.humanIntelligenceV2.personalityProfile.communitySizePreference],
    state.humanIntelligenceV2.independenceProfile.petOwnershipImportance && ["Pet", state.humanIntelligenceV2.independenceProfile.petOwnershipImportance],
    state.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently && ["Independent outings", state.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently],
    state.budget > 0 && ["Budget", `Up to $${state.budget.toLocaleString("en-US")}/month`],
    state.maximumDistanceMiles && ["Distance limit", `${state.approvedSearchRadiusMiles && Number(state.approvedSearchRadiusMiles) > Number(state.maximumDistanceMiles) ? state.approvedSearchRadiusMiles : state.maximumDistanceMiles} miles`],
    state.moveTiming && ["Timing", state.moveTiming],
  ].filter(Boolean) as string[][];

  const naturalLanguageQuery = (
    searchParams.get("q") || searchParams.get("search") || searchParams.get("notes") || state.notes || ""
  ).trim();
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );

  useEffect(() => {
    if (continuingInterview) return;
    if (!state.questionnaireCompletion?.mandatoryComplete || !state.questionnaireCompletion?.conditionalFollowUpsComplete) {
      router.replace("/intake");
      return;
    }
    if (!state.questionnaireCompletion.clientSummaryConfirmed) {
      router.replace(`/intake-confirmation?next=${encodeURIComponent(`/results?${searchParams.toString()}`)}`);
      return;
    }
    let active = true;
    // A home-page answer is saved immediately before navigation.  Give React a
    // short settling window so the results request uses that final state rather
    // than sending both the previous and the just-updated questionnaire.
    const timer = window.setTimeout(() => {
      setLoading(true);
      setSearchStage(0);
      const stageTimers = [window.setTimeout(() => setSearchStage(1), 1200), window.setTimeout(() => setSearchStage(2), 3200), window.setTimeout(() => setSearchStage(3), 6000)];
      setError(null);
      const cached = loadDecisionResponseCache<DecisionEngineResponse>(decisionRequestKey);
      const load = cached
        ? Promise.resolve(cached)
        : fetchPatientDecisionRecommendations({
            questionnaire_state: state as unknown as Record<string, unknown>,
            natural_language_query: naturalLanguageQuery,
            limit: 50,
          }).then((value) => {
            saveDecisionResponseCache(decisionRequestKey, value);
            return value;
          });
      void load
        .then((value) => {
          if (active) setResponse(value);
        })
        .catch((cause) => {
          if (active) setError(cause instanceof Error ? cause.message : "We could not load the recommendations.");
        })
        .finally(() => {
          if (active) setLoading(false);
          stageTimers.forEach((id) => window.clearTimeout(id));
        });
    }, 1000);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [continuingInterview, decisionRequestKey, naturalLanguageQuery, router, searchParams, state]);

  useEffect(() => {
    if (loading || beforeOOmnikerIds.current.length === 0 || !response) return;
    const before = beforeOOmnikerIds.current;
    const afterItems = (response.results || []).filter(isFinalRecommendation).slice(0, TOP_COUNT);
    const after = afterItems.map((item) => item.canonical_facility_id);
    const added = after.filter((id) => !before.includes(id));
    const removed = before.filter((id) => !after.includes(id));
    const oldLeader = before[0];
    const newLeader = after[0];
    const parts: string[] = [];
    if (added.length) parts.push(`${added.length} additional communit${added.length === 1 ? "y enters" : "ies enter"} the first five recommendations`);
    if (removed.length) parts.push(`${removed.length} previous option${removed.length === 1 ? " moves" : "s move"} outside the first five recommendations`);
    if (oldLeader && newLeader && oldLeader !== newLeader) {
      const leader = afterItems.find((item) => item.canonical_facility_id === newLeader);
      parts.push(`${leader?.facility_name || "A different community"} now comes first based on the updated priorities`);
    }
    if (!parts.length) parts.push("the leading recommendations did not materially change");
    setOOmnikerDiff(`Here’s what changed: ${parts.join("; ")}.`);
    beforeOOmnikerIds.current = [];
  }, [loading, response]);

  const eligible = useMemo(
    () => (response?.results || []).filter(isFinalRecommendation),
    [response],
  );
  const pending = useMemo(
    () => (response?.results || []).filter(isPendingRecommendation),
    [response],
  );
  const top = eligible.slice(0, TOP_COUNT);
  const measuredPreferenceAdvice = (response?.oomniker?.suggestions || []).filter((item): item is OOmnikerPreferenceSuggestion =>
    item.action === "OFFER_PREFERENCE_ALTERNATIVE" && item.authority === "PREFERENCE" && "new_recommendation_count" in item && item.new_recommendation_count >= 2);
  const pendingEvidence = response?.pending_evidence_summary;
  const missingEvidence = [...new Set(pendingEvidence?.unresolved_requirements || [])]
    .map((key) => missingEvidenceLabels[key] || "another required facility detail");
  const syntheticPilot = (response?.results || []).some((item) => item.synthetic_pilot)
    || pendingEvidence?.synthetic_pilot === true;
  const relationship = personLabel(state.relationship, naturalLanguageQuery);
  const detailsHref = `/results/details${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const personalReportHref = `/results/personal-report${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  if (loading) {
    return <main className="min-h-screen bg-canvas px-5 py-16 text-ink"><div className="mx-auto max-w-3xl"><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#934b38]">OOmnik is working for you</p><h1 className="mt-3 text-4xl font-semibold">I’m looking for the places that fit the decision — not just the search.</h1><div className="mt-10 space-y-4 text-xl leading-8"><p className={searchStage>=0?"text-ink":"text-forest"}>✓ Starting with the things that can’t be compromised: care, mobility and safety.</p><p className={searchStage>=1?"text-ink":"text-forest"}>{searchStage>=1?"✓":"○"} Checking budget, location and timing.</p><p className={searchStage>=2?"text-ink":"text-forest"}>{searchStage>=2?"✓":"○"} Looking beyond eligibility: independence, lifestyle, activities and future care.</p><p className={searchStage>=3?"text-ink":"text-forest"}>{searchStage>=3?"✓":"○"} Separating what is verified from what still needs confirmation.</p></div><p className="mt-10 text-lg italic text-muted">I’ll keep uncertainty visible rather than hide it.</p></div></main>;
  }

  if (error || !response) {
    return <main className="min-h-screen bg-canvas px-5 py-12 text-ink"><div className="mx-auto max-w-5xl rounded-xl border border-rose-200 bg-white p-8 text-lg">{error || "No results are available yet."}<Link href="/intake-confirmation?next=%2Fresults" className="mt-5 block underline">Review and confirm your profile</Link></div></main>;
  }

  const clientState = resultsClientState(response);
  if (clientState.blocked || clientState.needsAnswer) {
    const question = clientState.question;
    const submitFollowUp = (raw: string) => {
      const answer = raw.trim();
      if (!question || !answer || continuingInterview) return;
      setContinuingInterview(true);
      const next = applyAdaptiveAnswer({ ...state, notes: naturalLanguageQuery }, question, answer);
      // Persist before navigation so the interview restores this explicit answer.
      saveSessionJson(QUESTIONNAIRE_SESSION_KEY, next);
      setState(next);
      router.push("/adaptive-interview?next=%2Fresults");
    };
    return <main className="min-h-screen bg-canvas px-5 py-12 text-ink">
      <section className="mx-auto max-w-3xl rounded-xl bg-white p-8">
        <p className="text-base font-semibold text-forest">OOmnik</p>
        <h1 className="mt-3 text-3xl font-semibold">{clientState.blocked ? "Your search needs another check" : "One more detail before we recommend places"}</h1>
        {question ? <>
          <p className="mt-6 text-2xl leading-9">{question.question}</p>
          <div className="mt-5 flex flex-wrap gap-3">{(question.answer_options || []).map(option =>
            <button key={option} type="button" aria-pressed={followUpAnswer === option} aria-label={option} disabled={continuingInterview} onClick={() => { setFollowUpAnswer(option); setContinuingInterview(true); followUpTimer.current = setTimeout(() => submitFollowUp(option), 450); }} className={`rounded-xl border px-5 py-3 text-lg ${followUpAnswer === option ? "border-forest bg-forest text-white" : "border-line bg-white text-ink disabled:opacity-50"}`}>{followUpAnswer === option ? "✓ " : ""}{option}</button>
          )}</div>
          <form className="mt-5" onSubmit={event => { event.preventDefault(); submitFollowUp(followUpAnswer); }}>
            <label htmlFor="results-follow-up" className="block text-lg">Your answer</label>
            <textarea id="results-follow-up" value={followUpAnswer} onChange={event => setFollowUpAnswer(event.target.value)} disabled={continuingInterview} rows={3} className="mt-2 w-full rounded-xl border p-4 text-lg" />
            <button type="submit" disabled={continuingInterview || !followUpAnswer.trim()} className="mt-4 inline-flex items-center gap-3 rounded-xl bg-forest px-7 py-4 text-xl text-white disabled:opacity-50"><OomnikMark />{continuingInterview ? "Using your answer…" : "Continue"}</button>
          </form>
        </> : <>
          <p className="mt-5 text-xl">Your answers are saved. We need to check our understanding before showing recommendations.</p>
          <Link href="/adaptive-interview?next=%2Fresults" className="mt-6 inline-flex items-center gap-3 rounded-xl bg-forest px-6 py-4 text-lg text-white"><OomnikMark />Continue our conversation</Link>
        </>}
      </section>
    </main>;
  }

  return (
    <main className="min-h-screen bg-canvas px-5 py-8 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto max-w-4xl">
        <section className="py-7 sm:py-10">
          {syntheticPilot ? <div className="mb-6 rounded-xl border-2 border-amber-500 bg-amber-50 p-4 text-lg font-semibold text-amber-950">Pilot mode: every community, price and availability value on this page is synthetic test data—not a real facility. Photos are illustrations, not community photographs.</div> : null}
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#934b38]">A little closer to your next chapter</p>
          <h1 data-testid="personal-results-heading" className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">Let’s find a place that feels right for {relationship}</h1>
          <div className="mt-5 max-w-4xl"><PersonalNarrative state={state} query={naturalLanguageQuery} decisionId={response.decision_id || undefined} fallback={resultsIntroduction(state, top.length)} /></div>
          {top.length === 0 ? (
            <div className="mt-7 rounded-xl bg-sand p-5 text-xl leading-8 text-[#6d5426]">
              {pending.length > 0
                ? "Some communities still need important details verified before I can recommend them."
                : "No community is ready to recommend from this search. You can review your answers or return to the conversation."}
              {pendingEvidence && pendingEvidence.candidate_count > 0 ? <p className="mt-3 text-base leading-7">
                {pendingEvidence.candidate_count} communit{pendingEvidence.candidate_count === 1 ? "y needs" : "ies need"} more evidence before I can recommend {pendingEvidence.candidate_count === 1 ? "it" : "them"}.
                {missingEvidence.length > 0 ? ` I still need to verify ${missingEvidence.join(", ")}.` : " I still need to verify the required conditions."}
                {" These are open questions, not confirmed mismatches."}
              </p> : null}
              {response.market_coverage_notice ? <p className="mt-3 text-base leading-7">{response.market_coverage_notice}</p> : null}
              {(response.results || []).some((item: any) => item.budget_exception === true) ? <p className="mt-3 text-base leading-7">We did not find enough otherwise suitable communities within the budget you requested, so OOmnik is also showing suitable options up to 10% above it. The budget difference lowers their ranking and is marked on the relevant option. Use OOmniker below to change the budget or any other parameter and add more communities.</p> : null}
              {medicaidBudgetIsConditional(state) ? <p className="mt-3 text-base leading-7">Your search budget is ${state.budget.toLocaleString()} per month and includes ${Number(state.medicaidMonthlyAmount).toLocaleString()} in Medicaid support you reported. {state.medicaidStatus === "Application pending" ? "That support is pending approval. " : ""}These options depend on that support being usable for the quoted services. OOmnik has not verified coverage or the amount you will personally pay; confirm both with the funding agency and community before committing.</p> : null}
            </div>
          ) : null}
          <details className="mt-6 text-lg"><summary className="cursor-pointer underline underline-offset-4">Keep our conversation for later</summary><div className="mt-4">
            {savedCaseToken ? <p className="text-lg"><strong>Your OOmnik case is saved.</strong> Your questionnaire and future activity can now stay together under one case.</p> : <>
              <p className="text-lg font-semibold">Want to save this case or have OOmnik help with the next steps?</p>
              <p className="mt-1 text-base text-forest">Add contact details to save the case, keep your report, and track communities, referrals, tours and follow-ups.</p>
              <button type="button" onClick={() => setSaveCaseOpen(true)} className="mt-3 rounded-xl bg-forest px-6 py-3 font-semibold text-white">Save my case</button>
            </>}
          </div></details>
          {saveCaseOpen ? <div className="mt-4 rounded-xl border border-line bg-white p-5"><h2 className="text-2xl font-semibold">Save your OOmnik case</h2><div className="mt-4 grid gap-3 sm:grid-cols-3"><input aria-label="Name" placeholder="Name" value={caseContact.name} onChange={e=>setCaseContact(v=>({...v,name:e.target.value}))} className="rounded-xl border p-3"/><input aria-label="Email" placeholder="Email" value={caseContact.email} onChange={e=>setCaseContact(v=>({...v,email:e.target.value}))} className="rounded-xl border p-3"/><input aria-label="Phone" placeholder="Phone" value={caseContact.phone} onChange={e=>setCaseContact(v=>({...v,phone:e.target.value}))} className="rounded-xl border p-3"/></div><label className="mt-4 flex gap-3"><input type="checkbox" checked={caseContact.terms} onChange={e=>setCaseContact(v=>({...v,terms:e.target.checked}))}/><span>I agree to the Terms of Use and allow OOmnik to save this case and contact me about it.</span></label><div className="mt-4 flex gap-3"><button type="button" disabled={savingCase || !caseContact.terms || (!caseContact.email.trim() && !caseContact.phone.trim())} onClick={saveClientCase} className="rounded-xl bg-forest px-6 py-3 font-semibold text-white disabled:opacity-40">{savingCase?"Saving…":"Save case"}</button><button type="button" onClick={()=>setSaveCaseOpen(false)} className="rounded-xl border px-6 py-3">Cancel</button></div></div> : null}
          <p className="mt-5 text-lg leading-8 text-forest">Confirm current pricing and availability before any move.</p>
          <DistanceScope scope={response.location_scope} onWiden={acceptRadiusExpansion} />
          {/medicaid/i.test(naturalLanguageQuery) ? <p className="mt-2 text-lg leading-8 text-forest">Medicaid eligibility and each community’s participation must be confirmed separately.</p> : null}
        </section>

        {(response.price_research_candidates || []).length > 0 ? (
          <section className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-7" aria-label="Price research">
            <h2 className="text-2xl font-semibold">Price not verified — not a recommendation</h2>
            <p className="mt-3 text-lg leading-8">These communities passed the other mandatory checks for this search, but their price is missing. We cannot confirm affordability. This alphabetical list is for further research and has no ranking.</p>
            <ul className="mt-5 space-y-4">
              {response.price_research_candidates?.map((item) => (
                <li key={item.canonical_facility_id} className="rounded-xl bg-white p-5">
                  <h3 className="text-xl font-semibold">{item.facility_name}</h3>
                  {item.synthetic_pilot ? <p>Synthetic test community</p> : null}
                  <p className="mt-2">{item.passed_requirement_count} other mandatory checks passed. Monthly price: not verified.</p>
                  <p className="mt-2">Next step: obtain a current written quote including the care services needed, then compare the total with your budget.</p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {top.length > 0 ? (
          <section className="mt-8 grid gap-6">
            {top.map((item, index) => {
              // Personal guidance reads the stored final decision and full match
              // explanation. AI ranking prose remains internal: it must never
              // override the authoritative eligibility checks or comparison.
              const why = facilityExplanation(item, response.patient_needs_profile?.needs);
              const verify = (item.explanation?.needs_verification || []).map(cleanText).filter(Boolean);
              const concerns = (item.explanation?.concerns || []).map(cleanText).filter(Boolean);
              const nearbyFit = item.explanation?.nearby_place_fit;
              const personalDistances = nearbyFit?.personal_destinations || [];
              const nearbyDistances = Object.entries(nearbyFit?.nearest || {}).filter(([, place]) => Number.isFinite(place?.driving_distance_miles ?? place?.distance_miles)).sort((a, b) => Number(a[1]?.driving_distance_miles ?? a[1]?.distance_miles ?? 999) - Number(b[1]?.driving_distance_miles ?? b[1]?.distance_miles ?? 999));
              return (
                <article key={item.canonical_facility_id} className="border-t border-line py-10 sm:py-12">
                  {item.synthetic_pilot ? <PilotPhoto facilityId={item.canonical_facility_id} /> : item.visual_media?.hero?.url ? <div className="mb-6 overflow-hidden rounded-xl border border-line bg-sand"><Image src={item.visual_media.hero.url} alt={`Synthetic illustration for ${item.facility_name}`} width={1200} height={700} className="h-64 w-full object-cover" /><p className="px-4 py-2 text-sm text-muted">{item.visual_media.hero.source_note || "Synthetic pilot illustration—not a real facility"}</p></div> : null}
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-forest">{index === 0 ? "Let’s start here" : "Another place to consider"}</p>
                      <h2 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{item.facility_name}</h2>
                      <p className="mt-2 text-lg text-forest">{[item.city, item.state].filter(Boolean).join(", ")}</p>
                      <details className="mt-4 text-base"><summary className="cursor-pointer underline underline-offset-4">Practical details and the places that matter to you</summary>
                      <p className="mt-2 text-lg font-semibold text-ink">{item.starting_monthly_price ? `Starting at $${item.starting_monthly_price.toLocaleString("en-US")} / month` : "Price not provided"}{(item as any).budget_exception ? ` · ${Math.abs(Number((item as any).budget_variance_pct || 0)).toFixed(1)}% above your requested budget` : ""} · Availability: {item.availability_status === "YES" ? "available" : item.availability_status === "LIMITED" ? "limited / waitlist" : item.availability_status === "NO" ? "not currently available" : "needs confirmation"}</p>
                      <p className="mt-2 text-base text-[#684d19]">{item.availability_status === "NO" ? "No space is currently recorded. Ask whether a suitable opening is expected by your move date." : "Confirm a suitable room and admission date directly with the community."} Care compatibility does not confirm readiness to move.</p>
                      {personalDistances.length > 0 || nearbyDistances.length > 0 ? <div className="mt-4 rounded-xl bg-sand p-4">{personalDistances.length > 0 ? <><p className="text-sm font-semibold uppercase tracking-[0.12em] text-forest">Close to the people and places that matter</p><ul className="mt-2 grid gap-x-6 gap-y-1 text-base sm:grid-cols-2">{personalDistances.map((place, destinationIndex) => <li key={`${place.label}-${destinationIndex}`}><strong>{place.label}</strong>: {place.driving_distance_miles != null || place.distance_miles != null ? `${Number(place.driving_distance_miles ?? place.distance_miles).toFixed(1)} mi` : "distance unavailable"}{place.driving_time_minutes ? ` · ${place.driving_time_minutes} min drive` : place.status === "UNKNOWN" ? "" : " · estimated"}</li>)}</ul></> : null}{nearbyDistances.length > 0 ? <><p className="text-sm font-semibold uppercase tracking-[0.12em] text-forest">Distances that matter to you</p><ul className="mt-2 grid gap-x-6 gap-y-1 text-base sm:grid-cols-2">{nearbyDistances.map(([category, place]) => <li key={category}><strong>{category}</strong>: {Number(place.driving_distance_miles ?? place.distance_miles).toFixed(1)} mi{place.driving_time_minutes ? ` · ${place.driving_time_minutes} min drive` : ""}{place.name && place.name !== category ? ` · ${place.name}` : ""}</li>)}</ul><p className="mt-2 text-xs text-forest">Based on the preferences you selected. Driving distance and time are shown when routing is available; otherwise OOmnik shows straight-line proximity and labels it as an estimate.</p></> : null}</div> : null}
                      {item.synthetic_pilot && item.monthly_rate_includes_verified_care ? <p className="mt-2 text-base text-ink">{item.monthly_price_basis === "TWO_RESIDENT_TOTAL" ? `Pilot monthly total for two residents, including verified care and the $${Number(item.second_resident_monthly_fee || 0).toLocaleString()} second-resident fee.` : "Pilot monthly rate includes the care services verified for this community."}</p> : null}
                      {typeof item.entrance_fee === "number" && item.entrance_fee > 0 ? <div className="mt-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-base text-[#684d19]"><p>One-time entrance fee: ${item.entrance_fee.toLocaleString()}, separate from the monthly rate.</p><p className="mt-2">One-time affordability is not confirmed. Can the household fund this amount separately? The community must also confirm whether this fee applies to the specific care program and admission contract.</p></div> : null}
                      {(item.nice_to_have_coverage?.unresolved || []).length > 0 || (item.structured_nice_to_have_coverage?.unresolved || []).length > 0 ? <p className="mt-3 text-sm text-[#684d19]">Some of your personal preferences still need facility-specific evidence. Verified care does not prove every lifestyle preference.</p> : null}
                      </details>
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <Link
                        href={`/facility/canonical?canonical=${encodeURIComponent(item.canonical_facility_id)}&back=${encodeURIComponent(`/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`)}`}
                        className="rounded-xl border border-forest px-4 py-2 text-base font-semibold text-forest hover:bg-sand"
                      >
                        Get to know this place →
                      </Link>
                    </div>
                  </div>

                  <div className="mt-7 space-y-5">
                    <div className="max-w-3xl">
                      <h3 className="text-2xl font-semibold">Why this place fits your search</h3>
                      <div className="mt-3"><PersonalNarrative state={state} query={naturalLanguageQuery} decisionId={response.decision_id || undefined} facilityId={item.canonical_facility_id} fallback={why} /></div>
                      <details className="mt-4 text-base"><summary className="cursor-pointer underline underline-offset-4">The matching facts behind this explanation</summary>{item.explanation?.why_matches.map(text => <p key={text} className="mt-2 leading-7">{text}</p>)}</details>
                    </div>

                    <div className="max-w-3xl">
                      <h3 className="text-2xl font-semibold">Before you decide</h3>
                      {verify.length ? (
                        <p className="mt-3 text-xl leading-9">There are a few things to settle together. {verify.join(" ")} These details will help you decide whether the next step feels right.</p>
                      ) : (
                        <p className="mt-3 text-xl leading-8">Next, confirm the room, total monthly cost and a suitable move-in date with the community.</p>
                      )}
                    </div>
                  </div>
                  <ServiceBudgetPlan item={item} budget={state.budget} couple={state.relationship === "Couple"} needs={response.patient_needs_profile?.needs} options={response.care_partner_options} />
                  {concerns.filter(text => !isOutsideCareConcern(text)).length > 0 ? <div className="mt-6 text-xl leading-9"><h3 className="text-xl font-semibold">Something I want you to know</h3>{concerns.filter(text => !isOutsideCareConcern(text)).map(text => <p key={text}>{text}</p>)}</div> : null}
                  {concerns.some(isOutsideCareConcern) ? <details className="mt-4 text-base"><summary className="cursor-pointer underline">Original care evidence notes</summary>{concerns.filter(isOutsideCareConcern).map(text => <p key={text}>{text}</p>)}</details> : null}
                  <CommunityNextStep facilityId={item.canonical_facility_id} facilityName={item.facility_name} serviceNeeds={response.patient_needs_profile?.needs.map(need => need.need_text || need.parameter_id)} />
                </article>
              );
            })}
          </section>
        ) : null}

        {pending.length > 0 ? (
          <section className="mt-8 rounded-xl border border-line bg-sand p-7 sm:p-9">
            <h2 className="text-3xl font-semibold">Other promising places we are still checking</h2>
            <p className="mt-3 text-xl leading-8 text-muted">
              I’m keeping these places in view, but I’m not asking you to rely on them yet. One or more details that matter to this decision still need verification.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {pending.slice(0, 8).map((item) => (
                <span key={item.canonical_facility_id} className="rounded-xl border border-line bg-white px-4 py-2 text-lg">{item.facility_name}</span>
              ))}
            </div>
          </section>
        ) : null}

        <section className="mt-8 rounded-xl bg-sand p-7 sm:p-9">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#934b38]">OOMNIKER</p><h2 className="mt-2 text-3xl font-semibold">We can think this through together</h2><LiveText paragraphs={["How do these places feel to you? If something isn’t quite right, tell me what you would like to be different. We can explore your preferences together and keep the essential support you need in place."]} className="mt-3 max-w-3xl text-lg leading-8 text-forest" /></div>
            <button type="button" onClick={() => setOOmnikerOpen((v) => !v)} className="rounded-xl bg-forest px-5 py-3 font-semibold text-white">{oomnikerOpen ? "Close conversation" : "Talk it through"}</button>
          </div>
          <LiveText paragraphs={preferenceAdvice(response)} className="mt-5 text-xl leading-9" /><details className="mt-5"><summary className="cursor-pointer underline underline-offset-4">The preferences guiding our conversation</summary><p className="mt-3 text-lg leading-8">{activeCriteria.map(([label, value]) => `${label}: ${value}`).join(". ")}.</p></details>
          {measuredPreferenceAdvice.map(suggestion => <article key={`${suggestion.parameter}-${suggestion.alternative_value}`} className="mt-5 rounded-2xl border border-line bg-white p-5">
            <h3 className="text-xl font-semibold">An alternative for your {adviceLabels[suggestion.parameter]?.toLowerCase() || "preference"}</h3>
            <LiveText paragraphs={[suggestion.message]} className="mt-3 leading-7" />
            <ul className="mt-3 space-y-3">{suggestion.candidates.map(candidate => <li key={candidate.canonical_facility_id}>
              <strong>{candidate.facility_name || "Community"}</strong>: {adviceLabels[candidate.quality_advantage.parameter] || "Verified quality measure"}: {String(candidate.quality_advantage.value)}, compared with {String(candidate.quality_advantage.compared_value)} for a current option ({candidate.quality_advantage.source_family}).
              {candidate.unresolved_preferences.length ? <p>Still to verify: {candidate.unresolved_preferences.map(key => adviceLabels[key] || missingEvidenceLabels[key] || "another preference").join(", ")}.</p> : null}
              {typeof candidate.entrance_fee === "number" && candidate.entrance_fee > 0 ? <p>Entrance fee: ${candidate.entrance_fee.toLocaleString("en-US")}. One-time affordability and contract details still need confirmation.</p> : null}
            </li>)}</ul>
            {suggestion.parameter === "COMMUNITY_ENVIRONMENT_MATCH" ? <button type="button" onClick={() => acceptCommunitySizeAdvice(suggestion)} className="mt-4 inline-flex items-center gap-3 rounded-xl bg-forest px-5 py-3 font-semibold text-white"><OomnikMark />Try {suggestion.alternative_value.toLowerCase()}</button> : <Link href="/adaptive-interview?review=1&next=/results" className="mt-4 inline-block font-semibold underline">Review this preference</Link>}
          </article>)}
          {(response.oomniker?.preference_analysis?.parameters || []).filter(item => item.eligible_below_display_count > 0 || item.unknown_count > 0).slice(0, 3).map(item => <p key={item.parameter} className="mt-4 text-base leading-7">
            <strong>{adviceLabels[item.parameter] || "Another preference"}:</strong> {item.eligible_below_display_count} eligible communities outside the first five have a verified mismatch; {item.unknown_count} need more evidence. This preference does not exclude them.
          </p>)}
          {(response.oomniker?.constraint_impacts || []).slice(0, 3).map(item => <p key={item.parameter} className="mt-3 text-base leading-7">
            <strong>{missingEvidenceLabels[item.parameter] || "A required condition"}:</strong> {item.blocked_count} communities have a confirmed blocker; for {item.sole_verified_blocker_count}, it is the only confirmed blocker with no pending evidence. Your requirements stay in force. Counts may overlap across conditions.
          </p>)}
          {oomnikerNotice ? <div className="mt-4 rounded-xl bg-white p-4 text-base text-forest"><LiveText paragraphs={[oomnikerNotice, ...(oomnikerDiff ? [oomnikerDiff] : [])]} /> {oomnikerHistory.current.length > 0 ? <button type="button" onClick={() => { const previous = oomnikerHistory.current.pop(); if (previous) { setState(previous); setOOmnikerNotice("Done. I’ve put the previous preference back and I’m reassessing the earlier search."); } }} className="ml-2 font-semibold underline underline-offset-4">Undo last change</button> : null}</div> : null}
          {oomnikerOpen ? <div className="mt-6"><label htmlFor="oomniker-message" className="mb-3 block text-lg">What would you like me to consider?</label><textarea id="oomniker-message" value={oomnikerText} onChange={(e) => setOOmnikerText(e.target.value)} rows={3} placeholder="For example: I’d like to consider a medium community, or search within 30 miles." className="w-full rounded-xl border border-line bg-white px-5 py-4 text-lg outline-none focus:border-forest" /><button type="button" onClick={applyOOmnikerChange} disabled={!oomnikerText.trim()} className="mt-3 rounded-xl bg-forest px-6 py-3 font-semibold text-white disabled:opacity-40">Update results</button></div> : null}

        </section>

        <section className="mt-8 flex flex-wrap gap-4 pb-10">
          <Link href={detailsHref} className="rounded-xl border-2 border-forest px-6 py-4 text-xl font-semibold text-forest">See detailed comparison</Link>
          <Link href={personalReportHref} className="rounded-xl border-2 border-forest px-6 py-4 text-xl font-semibold text-forest">See your personal report</Link>
          <Link href="/adaptive-interview?review=1&next=/results" className="rounded-xl border border-line bg-white px-6 py-4 text-xl font-semibold">Change answers</Link>
        </section>
      </div>
    </main>
  );
}
