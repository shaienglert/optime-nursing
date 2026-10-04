"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { createClientCase, DecisionEngineResponse, fetchPatientDecisionRecommendations, type OOmnikerPreferenceSuggestion } from "@/lib/api";
import { loadDecisionResponseCache, saveDecisionResponseCache, saveSessionJson, QUESTIONNAIRE_SESSION_KEY } from "@/lib/search-session";
import { isFinalRecommendation, isPendingRecommendation } from "@/lib/recommendation-eligibility";
import { applyAdaptiveAnswer } from "@/lib/adaptive-answer";
import { resultsClientState } from "@/lib/results-client-state";
import { DistanceScope } from "./distance-scope";
import { applyMeasuredPreferenceAdvice, askMeasuredAdvisor, type AdvisorReply, type AdvisorTurn } from "@/lib/oomniker-advice";

const TOP_COUNT = 5;

const adviceLabels: Record<string, string> = {
  COMMUNITY_ENVIRONMENT_MATCH: "Community size", PREFERRED_LANGUAGE_SUPPORT: "Preferred language", CONTINUUM_OF_CARE: "Future care continuity",
  RICH_CULTURE_AND_ACTIVITIES: "Culture and activities", CLASSICAL_MUSIC_ACCESS: "Classical music",
  TRANSPORTATION_AND_OUTINGS: "Transportation and outings", DINING_EXPERIENCE: "Dining experience",
  KOSHER_MEALS: "Kosher meals", SOCIAL_INTERACTION_FREQUENCY: "Social interaction frequency", NEARBY_PLACES: "Nearby amenities",
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

  const [advisorConversation, setAdvisorConversation] = useState<AdvisorTurn[]>([]);
  const [advisorReply, setAdvisorReply] = useState<AdvisorReply | null>(null);
  const [advisorBusy, setAdvisorBusy] = useState(false);
  const advisorGeneration = useRef(0);

  async function askOOmniker(message: string) {
    if (!response?.decision_id || advisorBusy) return;
    const generation = advisorGeneration.current;
    const text = message.trim() || "Which two or three preference changes would you recommend, and why?";
    const history = advisorConversation;
    setAdvisorConversation(current => [...current, { role: "user", content: text }]);
    setAdvisorBusy(true);
    setOOmnikerText("");
    try {
      const reply = await askMeasuredAdvisor({ decision_id: response.decision_id, questionnaire_state: state,
        natural_language_query: naturalLanguageQuery, limit: 50, client_message: text, conversation: history });
      if (generation !== advisorGeneration.current) return;
      if (reply.status !== "AI_ADVISORY_READY") {
        setAdvisorConversation(current => [...current, { role: "assistant", content: "The advisor is temporarily unavailable. You can still review the measured options below." }]);
        return;
      }
      setAdvisorReply(reply);
      setAdvisorConversation(current => [...current, { role: "assistant",
        content: [reply.message, reply.follow_up].filter(Boolean).join(" ") }]);
    } catch (cause) {
      if (generation === advisorGeneration.current) setAdvisorConversation(current => [...current, { role: "assistant",
        content: cause instanceof Error ? cause.message : "The advisor is temporarily unavailable." }]);
    } finally {
      if (generation === advisorGeneration.current) setAdvisorBusy(false);
    }
  }

  function acceptPreferenceAdvice(suggestion: OOmnikerPreferenceSuggestion) {
    const next = applyMeasuredPreferenceAdvice(state, suggestion);
    if (next === state) return;
    beforeOOmnikerIds.current = (response?.results || []).filter(isFinalRecommendation).slice(0, TOP_COUNT).map(item => item.canonical_facility_id);
    setOOmnikerDiff("");
    oomnikerHistory.current.push(structuredClone(state));
    setState(next);
    setOOmnikerNotice(`You chose ${suggestion.alternative_value.toLowerCase()}. I’m running the search again. Your required conditions remain in force.`);
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
    // A reply belongs to exactly one saved decision. Cancel stale conversational
    // responses when a preference is accepted, undone or any answer changes.
    advisorGeneration.current += 1;
    setAdvisorConversation([]);
    setAdvisorReply(null);
    setAdvisorBusy(false);
  }, [decisionRequestKey]);

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
  const preferenceAdvice = (advisorReply?.proposals || response?.oomniker?.suggestions || []).filter((item): item is OOmnikerPreferenceSuggestion =>
    item.action === "OFFER_PREFERENCE_ALTERNATIVE" && item.authority === "PREFERENCE" && item.new_recommendation_count >= 2).slice(0, 3);
  const pendingEvidence = response?.pending_evidence_summary;
  const missingEvidence = [...new Set(pendingEvidence?.unresolved_requirements || [])]
    .map((key) => missingEvidenceLabels[key] || "another required facility detail");
  const syntheticPilot = (response?.results || []).some((item) => item.synthetic_pilot)
    || pendingEvidence?.synthetic_pilot === true;
  const relationship = personLabel(state.relationship, naturalLanguageQuery);
  const detailsHref = `/results/details${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const personalReportHref = `/results/personal-report${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  if (loading) {
    return <main className="min-h-screen bg-[#f7fbfd] px-5 py-16 text-[#22332d]"><div className="mx-auto max-w-3xl"><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#168fe0]">OOmnik is working for you</p><h1 className="mt-3 text-4xl font-semibold">I’m looking for the places that fit the decision — not just the search.</h1><div className="mt-10 space-y-4 text-xl leading-8"><p className={searchStage>=0?"text-[#22332d]":"text-[#89938f]"}>✓ Starting with the things that can’t be compromised: care, mobility and safety.</p><p className={searchStage>=1?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=1?"✓":"○"} Checking budget, location and timing.</p><p className={searchStage>=2?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=2?"✓":"○"} Looking beyond eligibility: independence, lifestyle, activities and future care.</p><p className={searchStage>=3?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=3?"✓":"○"} Separating what is verified from what still needs confirmation.</p></div><p className="mt-10 text-lg italic text-[#527083]">I’ll keep uncertainty visible rather than hide it.</p></div></main>;
  }

  if (error || !response) {
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]"><div className="mx-auto max-w-5xl rounded-3xl border border-rose-200 bg-white p-8 text-lg">{error || "No results are available yet."}<Link href="/intake-confirmation?next=%2Fresults" className="mt-5 block underline">Review and confirm your profile</Link></div></main>;
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
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]">
      <section className="mx-auto max-w-3xl rounded-3xl bg-white p-8">
        <p className="text-base font-semibold text-[#437667]">OOmnik</p>
        <h1 className="mt-3 text-3xl font-semibold">{clientState.blocked ? "Your search needs another check" : "One more detail before we recommend places"}</h1>
        {question ? <>
          <p className="mt-6 text-2xl leading-9">{question.question}</p>
          <div className="mt-5 flex flex-wrap gap-3">{(question.answer_options || []).map(option =>
            <button key={option} type="button" disabled={continuingInterview} onClick={() => submitFollowUp(option)} className="rounded-full border px-5 py-3 text-lg disabled:opacity-50">{option}</button>
          )}</div>
          <form className="mt-5" onSubmit={event => { event.preventDefault(); submitFollowUp(followUpAnswer); }}>
            <label htmlFor="results-follow-up" className="block text-lg">Your answer</label>
            <textarea id="results-follow-up" value={followUpAnswer} onChange={event => setFollowUpAnswer(event.target.value)} disabled={continuingInterview} rows={3} className="mt-2 w-full rounded-2xl border p-4 text-lg" />
            <button type="submit" disabled={continuingInterview || !followUpAnswer.trim()} className="mt-4 rounded-2xl bg-[#315f53] px-7 py-4 text-xl text-white disabled:opacity-50">{continuingInterview ? "Using your answer…" : "Continue"}</button>
          </form>
        </> : <>
          <p className="mt-5 text-xl">Your answers are saved. We need to check our understanding before showing recommendations.</p>
          <Link href="/adaptive-interview?next=%2Fresults" className="mt-6 inline-block rounded-2xl bg-[#315f53] px-6 py-4 text-lg text-white">Continue our conversation</Link>
        </>}
      </section>
    </main>;
  }

  return (
    <main className="min-h-screen bg-[#fffaf2] px-5 py-8 text-[#22332d] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <section className="rounded-[2rem] border border-[#e1d8c9] bg-white p-7 shadow-sm sm:p-10">
          {syntheticPilot ? <div className="mb-6 rounded-2xl border-2 border-amber-500 bg-amber-50 p-4 text-lg font-semibold text-amber-950">Pilot mode: every community, price, availability value and image on this page is synthetic test data—not a real facility.</div> : null}
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">OOmnik results</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">Care-compatible options to review for {relationship}</h1>
          <p className="mt-5 max-w-4xl text-xl leading-8 text-[#53635d]">
            {top.length > 0
              ? "The options below have verified care capabilities for this case. Availability and admission details still need direct confirmation."
              : "I don’t have a verified recommendation to show yet. Missing information is still being distinguished from a confirmed mismatch."}
          </p>
          {top.length > 0 ? (
            <div className="mt-7 rounded-2xl bg-[#eef7f2] p-5 text-xl leading-8 text-[#214d40]">
              I found <strong>{top.length}</strong> option{top.length === 1 ? "" : "s"} I think deserve your attention. I’ll show you what I like about each one, what gives me pause, and anything I still want to verify before you rely on it.
            </div>
          ) : (
            <div className="mt-7 rounded-2xl bg-[#fff5df] p-5 text-xl leading-8 text-[#6d5426]">
              {pending.length > 0
                ? "Some communities still need important details verified before I can recommend them."
                : "No community is ready to recommend from this search. You can review your answers or return to the conversation."}
              {pendingEvidence && pendingEvidence.candidate_count > 0 ? <p className="mt-3 text-base leading-7">
                {pendingEvidence.candidate_count} communit{pendingEvidence.candidate_count === 1 ? "y needs" : "ies need"} more evidence before I can recommend {pendingEvidence.candidate_count === 1 ? "it" : "them"}.
                {missingEvidence.length > 0 ? ` I still need to verify ${missingEvidence.join(", ")}.` : " I still need to verify the required conditions."}
                {" These are open questions, not confirmed mismatches."}
              </p> : null}
              {response.market_coverage_notice ? <p className="mt-3 text-base leading-7">{response.market_coverage_notice}</p> : null}
              {(response.results || []).some((item) => item.budget_exception === true) ? <p className="mt-3 text-base leading-7">We did not find enough otherwise suitable communities within the budget you requested, so OOmnik is also showing suitable options up to 10% above it. The budget difference lowers their ranking and is marked on the relevant option. Use OOmniker below to change the budget or any other parameter and add more communities.</p> : null}
            </div>
          )}
          <div className="mt-6 rounded-2xl border border-[#d9e3df] bg-[#f7faf8] p-5">
            {savedCaseToken ? <p className="text-lg"><strong>Your OOmnik case is saved.</strong> Your questionnaire and future activity can now stay together under one case.</p> : <>
              <p className="text-lg font-semibold">Want to save this case or have OOmnik help with the next steps?</p>
              <p className="mt-1 text-base text-[#53635d]">Add contact details to save the case, keep your report, and track communities, referrals, tours and follow-ups.</p>
              <button type="button" onClick={() => setSaveCaseOpen(true)} className="mt-3 rounded-full bg-[#315f53] px-6 py-3 font-semibold text-white">Save my case</button>
            </>}
          </div>
          {saveCaseOpen ? <div className="mt-4 rounded-2xl border border-[#d9e3df] bg-white p-5"><h2 className="text-2xl font-semibold">Save your OOmnik case</h2><div className="mt-4 grid gap-3 sm:grid-cols-3"><input aria-label="Name" placeholder="Name" value={caseContact.name} onChange={e=>setCaseContact(v=>({...v,name:e.target.value}))} className="rounded-xl border p-3"/><input aria-label="Email" placeholder="Email" value={caseContact.email} onChange={e=>setCaseContact(v=>({...v,email:e.target.value}))} className="rounded-xl border p-3"/><input aria-label="Phone" placeholder="Phone" value={caseContact.phone} onChange={e=>setCaseContact(v=>({...v,phone:e.target.value}))} className="rounded-xl border p-3"/></div><label className="mt-4 flex gap-3"><input type="checkbox" checked={caseContact.terms} onChange={e=>setCaseContact(v=>({...v,terms:e.target.checked}))}/><span>I agree to the Terms of Use and allow OOmnik to save this case and contact me about it.</span></label><div className="mt-4 flex gap-3"><button type="button" disabled={savingCase || !caseContact.terms || (!caseContact.email.trim() && !caseContact.phone.trim())} onClick={saveClientCase} className="rounded-full bg-[#315f53] px-6 py-3 font-semibold text-white disabled:opacity-40">{savingCase?"Saving…":"Save case"}</button><button type="button" onClick={()=>setSaveCaseOpen(false)} className="rounded-full border px-6 py-3">Cancel</button></div></div> : null}
          <p className="mt-5 text-lg leading-8 text-[#53635d]">Confirm current pricing and availability before any move.</p>
          <DistanceScope scope={response.location_scope} onWiden={acceptRadiusExpansion} />
          {/medicaid/i.test(naturalLanguageQuery) ? <p className="mt-2 text-lg leading-8 text-[#53635d]">Medicaid eligibility and each community’s participation must be confirmed separately.</p> : null}
        </section>

        {(response.price_research_candidates || []).length > 0 ? (
          <section className="mt-8 rounded-[2rem] border border-amber-300 bg-amber-50 p-7" aria-label="Price research">
            <h2 className="text-2xl font-semibold">Price not verified — not a recommendation</h2>
            <p className="mt-3 text-lg leading-8">These communities passed the other mandatory checks for this search, but their price is missing. We cannot confirm affordability. This alphabetical list is for further research and has no ranking.</p>
            <ul className="mt-5 space-y-4">
              {response.price_research_candidates?.map((item) => (
                <li key={item.canonical_facility_id} className="rounded-2xl bg-white p-5">
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
              // The free-form ranking narrative sees a bounded claim sample and
              // can therefore describe evidence as missing even when the full
              // deterministic MUST gate verified it elsewhere.  Show only the
              // canonical, structured explanation on the customer results page;
              // keep AI ranking prose internal for audit and diagnostics.
              const why = (item.explanation?.why_matches || []).map(cleanText).filter(Boolean).slice(0, 3);
              const verify = (item.explanation?.needs_verification || []).map(cleanText).filter(Boolean).slice(0, 3);
              const nearbyFit = item.explanation?.nearby_place_fit;
              const personalDistances = nearbyFit?.personal_destinations || [];
              const nearbyDistances = Object.entries(nearbyFit?.nearest || {}).filter(([, place]) => Number.isFinite(place?.driving_distance_miles ?? place?.distance_miles)).sort((a, b) => Number(a[1]?.driving_distance_miles ?? a[1]?.distance_miles ?? 999) - Number(b[1]?.driving_distance_miles ?? b[1]?.distance_miles ?? 999));
              return (
                <article key={item.canonical_facility_id} className="rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9">
                  {item.visual_media?.hero?.url ? <div className="mb-6 overflow-hidden rounded-2xl border border-[#ded6c9] bg-[#f4f0e8]"><Image src={item.visual_media.hero.url} alt={`Synthetic illustration for ${item.facility_name}`} width={1200} height={700} className="h-64 w-full object-cover" /><p className="px-4 py-2 text-sm text-[#6b6257]">{item.visual_media.hero.source_note || "Synthetic pilot illustration—not a real facility"}</p></div> : null}
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-[#3e7868]">{`Option ${index + 1}`}</p>
                      <h2 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{item.facility_name}</h2>
                      <p className="mt-2 text-lg text-[#627069]">{[item.city, item.state].filter(Boolean).join(", ")}</p>
                      <p className="mt-2 text-lg font-semibold text-[#334b42]">{item.starting_monthly_price ? `Starting at $${item.starting_monthly_price.toLocaleString("en-US")} / month` : "Price not provided"}{item.budget_exception ? ` · ${Math.abs(Number(item.budget_variance_pct || 0)).toFixed(1)}% above your requested budget` : ""} · Availability: {item.availability_status === "YES" ? "available" : item.availability_status === "LIMITED" ? "limited / waitlist" : item.availability_status === "NO" ? "not currently available" : "needs confirmation"}</p>
                      <p className="mt-2 text-base text-[#684d19]">{item.availability_status === "NO" ? "No space is currently recorded. Ask whether a suitable opening is expected by your move date." : "Confirm a suitable room and admission date directly with the community."} Care compatibility does not confirm readiness to move.</p>
                      {personalDistances.length > 0 || nearbyDistances.length > 0 ? <div className="mt-4 rounded-2xl bg-[#f5f8f6] p-4">{personalDistances.length > 0 ? <><p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#437667]">Close to the people and places that matter</p><ul className="mt-2 grid gap-x-6 gap-y-1 text-base sm:grid-cols-2">{personalDistances.map((place, destinationIndex) => <li key={`${place.label}-${destinationIndex}`}><strong>{place.label}</strong>: {place.driving_distance_miles != null || place.distance_miles != null ? `${Number(place.driving_distance_miles ?? place.distance_miles).toFixed(1)} mi` : "distance unavailable"}{place.driving_time_minutes ? ` · ${place.driving_time_minutes} min drive` : place.status === "UNKNOWN" ? "" : " · estimated"}</li>)}</ul></> : null}{nearbyDistances.length > 0 ? <><p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#437667]">Distances that matter to you</p><ul className="mt-2 grid gap-x-6 gap-y-1 text-base sm:grid-cols-2">{nearbyDistances.map(([category, place]) => <li key={category}><strong>{category}</strong>: {Number(place.driving_distance_miles ?? place.distance_miles).toFixed(1)} mi{place.driving_time_minutes ? ` · ${place.driving_time_minutes} min drive` : ""}{place.name && place.name !== category ? ` · ${place.name}` : ""}</li>)}</ul><p className="mt-2 text-xs text-[#68766f]">Based on the preferences you selected. Driving distance and time are shown when routing is available; otherwise OOmnik shows straight-line proximity and labels it as an estimate.</p></> : null}</div> : null}
                      {item.synthetic_pilot && item.monthly_rate_includes_verified_care ? <p className="mt-2 text-base text-[#334b42]">{item.monthly_price_basis === "TWO_RESIDENT_TOTAL" ? `Pilot monthly total for two residents, including verified care and the $${Number(item.second_resident_monthly_fee || 0).toLocaleString()} second-resident fee.` : "Pilot monthly rate includes the care services verified for this community."}</p> : null}
                      {typeof item.entrance_fee === "number" && item.entrance_fee > 0 ? <div className="mt-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-base text-[#684d19]"><p>One-time entrance fee: ${item.entrance_fee.toLocaleString()}, separate from the monthly rate.</p><p className="mt-2">One-time affordability is not confirmed. Can the household fund this amount separately? The community must also confirm whether this fee applies to the specific care program and admission contract.</p></div> : null}
                      {(item.nice_to_have_coverage?.unresolved || []).length > 0 || (item.structured_nice_to_have_coverage?.unresolved || []).length > 0 ? <p className="mt-3 text-sm text-[#684d19]">Some of your personal preferences still need facility-specific evidence. Verified care does not prove every lifestyle preference.</p> : null}
                      {state.budget > 0 && !(item.synthetic_pilot && item.monthly_rate_includes_verified_care && (state.relationship !== "Couple" || item.monthly_price_basis === "TWO_RESIDENT_TOTAL")) && (state.relationship === "Couple" || (response?.patient_needs_profile?.needs || []).some((need) => ["adl_support", "medication_support", "transfer_assistance", "memory_care", "nursing_24_7"].includes(need.parameter_id) && ["REQUIRED", "HIGH"].includes(need.requirement_level))) ? (
                        <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm leading-6 text-[#684d19]">
                          <strong>Full monthly cost needs confirmation.</strong> The starting price alone does not show whether care, outside agency support, or a second resident is included. Request a written quote for everyone and every required service before treating this as within your ${state.budget.toLocaleString()} budget.
                        </p>
                      ) : null}
                      {item.starting_monthly_price && (item.combined_care_solution?.care_component?.delivery_model === "FACILITY_PLUS_EXTERNAL_AGENCY" || item.combined_care_solution?.medication_component?.delivery_model === "FACILITY_PLUS_EXTERNAL_AGENCY") ? (
                        <div className="mt-3 rounded-xl border border-[#cfe3da] bg-[#f7fbf9] px-4 py-3 text-sm leading-6 text-[#40564e]">
                          <strong>Verified care depends on an outside agency:</strong> housing starts at ${"$"}{item.starting_monthly_price.toLocaleString()} / month. Outside-care cost is shown separately only when a verified provider price and required service package are available. Until then, the combined monthly cost remains <strong>to be verified</strong>.
                        </div>
                      ) : null}
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <span className="w-fit rounded-full bg-[#eaf6ef] px-4 py-2 text-lg font-semibold text-[#25613f]">Verified care capabilities</span>
                      <Link
                        href={`/facility/canonical?canonical=${encodeURIComponent(item.canonical_facility_id)}&back=${encodeURIComponent(`/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`)}`}
                        className="rounded-full border border-[#315f53] px-4 py-2 text-base font-semibold text-[#315f53] hover:bg-[#f4fbf7]"
                      >
                        View full listing →
                      </Link>
                    </div>
                  </div>

                  <div className="mt-7 grid gap-5 lg:grid-cols-2">
                    <div className="rounded-2xl bg-[#f4f8f6] p-6">
                      <h3 className="text-2xl font-semibold">Why I think this is worth looking at</h3>
                      {why.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">{why.map((text) => <li key={text}>✓ {text}</li>)}</ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8 text-[#596761]">It meets the important requirements we agreed on. I’m still building the clearest explanation of why it stands out from the other options.</p>
                      )}
                    </div>

                    <div className="rounded-2xl bg-[#fff7e7] p-6">
                      <h3 className="text-2xl font-semibold">What gives me pause</h3>
                      {verify.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">{verify.map((text) => <li key={text}>• {text}</li>)}</ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8">I don’t see a critical unresolved issue here right now.</p>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </section>
        ) : null}

        {pending.length > 0 ? (
          <section className="mt-8 rounded-[2rem] border border-[#ead9b4] bg-[#fffaf0] p-7 sm:p-9">
            <h2 className="text-3xl font-semibold">Other promising places we are still checking</h2>
            <p className="mt-3 text-xl leading-8 text-[#655a45]">
              I’m keeping these places in view, but I’m not asking you to rely on them yet. One or more details that matter to this decision still need verification.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {pending.slice(0, 8).map((item) => (
                <span key={item.canonical_facility_id} className="rounded-full border border-[#ddcda9] bg-white px-4 py-2 text-lg">{item.facility_name}</span>
              ))}
            </div>
          </section>
        ) : null}

        <section className="mt-8 rounded-[2rem] border border-[#bcd9e7] bg-[#f5fbfe] p-7 sm:p-9">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#168fe0]">OOMNIKER</p><h2 className="mt-2 text-3xl font-semibold">Discuss which preference changes could help</h2><p className="mt-3 max-w-3xl text-lg leading-8 text-[#53635d]">I’ll compare changes using the information available and explain how many additional communities each could bring into your first five recommendations. Your required conditions stay in force. You decide whether to try a change.</p></div>
            <button type="button" onClick={() => { if (!oomnikerOpen && !advisorConversation.length) void askOOmniker(""); setOOmnikerOpen((v) => !v); }} className="rounded-full bg-[#079ff2] px-5 py-3 font-semibold text-white">{oomnikerOpen ? "Close" : "Discuss my options with OOMNIKER"}</button>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">{activeCriteria.map(([label,value]) => <span key={label} className="rounded-full border border-[#bcd9e7] bg-white px-4 py-2 text-sm"><strong>{label}:</strong> {value}</span>)}</div>
          {preferenceAdvice.map(suggestion => <article key={`${suggestion.parameter}-${suggestion.alternative_value}`} className="mt-5 rounded-2xl border border-[#bcd9e7] bg-white p-5">
            <h3 className="text-xl font-semibold">An alternative for your {(suggestion.label || adviceLabels[suggestion.parameter])?.toLowerCase() || "preference"}</h3>
            <p className="mt-3 leading-7">{suggestion.message}</p>
            <ul className="mt-3 space-y-3">{suggestion.candidates.map(candidate => <li key={candidate.canonical_facility_id}>
              <strong>{candidate.facility_name || "Community"}</strong>: {adviceLabels[candidate.quality_advantage.parameter] || "Verified quality measure"}: {String(candidate.quality_advantage.value)}, compared with {String(candidate.quality_advantage.compared_value)} for a current option ({candidate.quality_advantage.source_family}).
              {candidate.unresolved_preferences.length ? <p>Still to verify: {candidate.unresolved_preferences.map(key => adviceLabels[key] || missingEvidenceLabels[key] || "another preference").join(", ")}.</p> : null}
              {typeof candidate.entrance_fee === "number" && candidate.entrance_fee > 0 ? <p>Entrance fee: ${candidate.entrance_fee.toLocaleString("en-US")}. One-time affordability and contract details still need confirmation.</p> : null}
            </li>)}</ul>
            {suggestion.change_kind === "WAIVE_NTH" || suggestion.parameter === "COMMUNITY_ENVIRONMENT_MATCH" ? <button type="button" onClick={() => acceptPreferenceAdvice(suggestion)} className="mt-4 rounded-full bg-[#234f63] px-5 py-3 font-semibold text-white">Explore this change</button> : <Link href="/adaptive-interview?review=1&next=/results" className="mt-4 inline-block font-semibold underline">Review this preference</Link>}
          </article>)}
          {(response.oomniker?.preference_analysis?.parameters || []).map(item => <p key={item.parameter} className="mt-4 text-base leading-7">
            <strong>{item.label || adviceLabels[item.parameter] || "Another preference"}:</strong> {item.eligible_below_display_count} eligible communities outside the first five have a verified mismatch; {item.unknown_count} need more evidence. This preference does not exclude them.
            {item.status === "NO_VERIFIED_RANKING_EFFECT" ? " Changing it has no verified effect on the current recommendation order." : null}
          </p>)}
          {(response.oomniker?.constraint_impacts || []).slice(0, 3).map(item => <p key={item.parameter} className="mt-3 text-base leading-7">
            <strong>{missingEvidenceLabels[item.parameter] || "A required condition"}:</strong> {item.blocked_count} communities have a confirmed blocker; for {item.sole_verified_blocker_count}, it is the only confirmed blocker with no pending evidence. Your requirements stay in force. Counts may overlap across conditions.
          </p>)}
          {oomnikerNotice ? <div className="mt-4 rounded-2xl bg-white p-4 text-base text-[#315f53]">{oomnikerNotice}{oomnikerDiff ? <p className="mt-2 font-medium">{oomnikerDiff}</p> : null} {oomnikerHistory.current.length > 0 ? <button type="button" onClick={() => { const previous = oomnikerHistory.current.pop(); if (previous) { setState(previous); setOOmnikerNotice("Done. I’ve put the previous preference back and I’m reassessing the earlier search."); } }} className="ml-2 font-semibold underline underline-offset-4">Undo last change</button> : null}</div> : null}
          {oomnikerOpen ? <div className="mt-6">
            <div aria-live="polite" className="space-y-3">{advisorConversation.map((turn, index) => <p key={index} className="rounded-xl bg-white p-4"><strong>{turn.role === "user" ? "You" : "OOmniker"}:</strong> {turn.content}</p>)}{advisorBusy ? <p>Reviewing your question and the evidence…</p> : null}</div>
            <label className="mt-4 block font-semibold" htmlFor="oomniker-question">Discuss your options</label>
            <textarea id="oomniker-question" value={oomnikerText} onChange={(e) => setOOmnikerText(e.target.value)} rows={3} placeholder="Which change would help most? What would I give up?" className="mt-2 w-full rounded-2xl border border-[#bcd9e7] bg-white px-5 py-4 text-lg outline-none focus:border-[#079ff2]" />
            <button type="button" onClick={() => void askOOmniker(oomnikerText)} disabled={advisorBusy || !oomnikerText.trim() || !response.decision_id} className="mt-3 rounded-full bg-[#234f63] px-6 py-3 font-semibold text-white disabled:opacity-40">Ask OOMNIKER</button>
            <p className="mt-3 text-sm">Discussing a change does not apply it. Choose an option above to run a new search, or <Link href="/adaptive-interview?review=1&next=/results" className="underline">review your answers</Link>.</p>
          </div> : null}
        </section>

        <section className="mt-8 flex flex-wrap gap-4 pb-10">
          <Link href={detailsHref} className="rounded-2xl border-2 border-[#315f53] px-6 py-4 text-xl font-semibold text-[#315f53]">See detailed comparison</Link>
          <Link href={personalReportHref} className="rounded-2xl border-2 border-[#315f53] px-6 py-4 text-xl font-semibold text-[#315f53]">See your personal report</Link>
          <Link href="/adaptive-interview?review=1&next=/results" className="rounded-2xl border border-[#cfc6b7] bg-white px-6 py-4 text-xl font-semibold">Change answers</Link>
        </section>
      </div>
    </main>
  );
}
