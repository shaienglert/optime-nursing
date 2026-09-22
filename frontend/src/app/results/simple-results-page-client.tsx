"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { DecisionEngineResponse, fetchPatientDecisionRecommendations } from "@/lib/api";
import { loadDecisionResponseCache, saveDecisionResponseCache } from "@/lib/search-session";
import { isFinalRecommendation, isPendingRecommendation } from "@/lib/recommendation-eligibility";

const TOP_COUNT = 5;

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
  const [searchStage, setSearchStage] = useState(0);
  const [oomnikerOpen, setOOmnikerOpen] = useState(false);
  const [oomnikerText, setOOmnikerText] = useState("");
  const [oomnikerNotice, setOOmnikerNotice] = useState("");
  const oomnikerHistory = useRef<typeof state[]>([]);
  const beforeOOmnikerIds = useRef<string[]>([]);
  const [oomnikerDiff, setOOmnikerDiff] = useState<string>("");

  function applyOOmnikerChange() {
    const text = oomnikerText.trim();
    if (!text) return;
    const lower = text.toLowerCase();
    beforeOOmnikerIds.current = (response?.results || []).filter(isFinalRecommendation).map((item) => item.canonical_facility_id);
    setOOmnikerDiff("");
    setState((current) => {
      oomnikerHistory.current.push(JSON.parse(JSON.stringify(current)));
      const next = JSON.parse(JSON.stringify(current));
      const budget = lower.match(/(?:budget|up to|maximum|max)[^$0-9]{0,20}\$?([0-9][0-9,]*)/);
      if (budget) next.budget = Number(budget[1].replaceAll(",", ""));
      const miles = lower.match(/([0-9]+)\s*miles?/);
      if (miles) { next.maximumDistanceMiles = miles[1]; next.customDistanceMiles = miles[1]; next.locationImportant = "Yes"; }
      if (/dog.*(?:not|no longer).*(?:require|important)|(?:remove|drop).*(?:dog|pet)/.test(lower)) next.humanIntelligenceV2.independenceProfile.petOwnershipImportance = "Not important";
      if (/large community.*(?:not|no longer).*(?:important|required)|(?:remove|drop).*large community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "No preference";
      if (/independent.*(?:outing|leave|go out).*(?:required|must|only)/.test(lower)) next.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently = "Very important";
      if (/community.*small|small community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Small";
      if (/community.*medium|medium community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Medium";
      if (/community.*large|large community/.test(lower)) next.humanIntelligenceV2.personalityProfile.communitySizePreference = "Large";
      if (/parking.*(?:not|no longer).*(?:need|required)|(?:remove|drop).*parking/.test(lower)) next.parkingRequirement = "No";
      if (/parking.*(?:need|required|important)/.test(lower) && !/(?:not|no longer)/.test(lower)) next.parkingRequirement = "Yes";
      if (/future care.*(?:important|required)|avoid another move/.test(lower)) next.futureCarePreference = "Yes";
      if (/future care.*(?:not|no longer).*(?:important|required)|(?:remove|drop).*future care/.test(lower)) next.futureCarePreference = "No preference";
      next.questionnaireCompletion.clientSummaryConfirmed = true;
      next.questionnaireCompletion.confirmedAt = new Date().toISOString();
      return next;
    });
    setOOmnikerNotice(`Got it. I’ll make this change — “${text}” — and leave everything else as we agreed. I’m checking whether it changes the decision in a meaningful way.`);
    setOOmnikerText("");
    setOOmnikerOpen(false);
  }

  const activeCriteria = [
    state.assistanceLevel && ["Care", state.assistanceLevel],
    state.medicalCareProfile.mobilityMethod && ["Mobility", state.medicalCareProfile.mobilityMethod],
    state.memoryStatus && ["Memory", state.memoryStatus],
    state.futureCarePreference && ["Future care", state.futureCarePreference],
    state.humanIntelligenceV2.personalityProfile.communitySizePreference && ["Community", state.humanIntelligenceV2.personalityProfile.communitySizePreference],
    state.humanIntelligenceV2.independenceProfile.petOwnershipImportance && ["Pet", state.humanIntelligenceV2.independenceProfile.petOwnershipImportance],
    state.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently && ["Independent outings", state.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently],
    state.budget > 0 && ["Budget", `Up to ${state.budget.toLocaleString("en-US")}/month`],
    state.maximumDistanceMiles && ["Radius", `${state.maximumDistanceMiles} miles`],
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
  }, [decisionRequestKey, naturalLanguageQuery, router, searchParams, state]);

  useEffect(() => {
    if (loading || beforeOOmnikerIds.current.length === 0 || !response) return;
    const before = beforeOOmnikerIds.current;
    const afterItems = (response.results || []).filter(isFinalRecommendation);
    const after = afterItems.map((item) => item.canonical_facility_id);
    const added = after.filter((id) => !before.includes(id));
    const removed = before.filter((id) => !after.includes(id));
    const oldLeader = before[0];
    const newLeader = after[0];
    const parts: string[] = [];
    if (added.length) parts.push(`${added.length} new communit${added.length === 1 ? "y now qualifies" : "ies now qualify"}`);
    if (removed.length) parts.push(`${removed.length} previous option${removed.length === 1 ? " no longer qualifies" : "s no longer qualify"}`);
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
  const syntheticPilot = (response?.results || []).some((item) => item.synthetic_pilot);
  const relationship = personLabel(state.relationship, naturalLanguageQuery);
  const detailsHref = `/results/details${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const personalReportHref = `/results/personal-report${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  if (loading) {
    return <main className="min-h-screen bg-[#f7fbfd] px-5 py-16 text-[#22332d]"><div className="mx-auto max-w-3xl"><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#168fe0]">OOmnik is working for you</p><h1 className="mt-3 text-4xl font-semibold">I’m looking for the places that fit the decision — not just the search.</h1><div className="mt-10 space-y-4 text-xl leading-8"><p className={searchStage>=0?"text-[#22332d]":"text-[#89938f]"}>✓ Starting with the things that can’t be compromised: care, mobility and safety.</p><p className={searchStage>=1?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=1?"✓":"○"} Checking budget, location and timing.</p><p className={searchStage>=2?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=2?"✓":"○"} Looking beyond eligibility: independence, lifestyle, activities and future care.</p><p className={searchStage>=3?"text-[#22332d]":"text-[#89938f]"}>{searchStage>=3?"✓":"○"} Separating what is verified from what still needs confirmation.</p></div><p className="mt-10 text-lg italic text-[#527083]">I’ll keep uncertainty visible rather than hide it.</p></div></main>;
  }

  if (error || !response) {
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]"><div className="mx-auto max-w-5xl rounded-3xl border border-rose-200 bg-white p-8 text-lg">{error || "No results are available yet."}<Link href="/intake-confirmation?next=%2Fresults" className="mt-5 block underline">Review and confirm your profile</Link></div></main>;
  }

  return (
    <main className="min-h-screen bg-[#fffaf2] px-5 py-8 text-[#22332d] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <section className="rounded-[2rem] border border-[#e1d8c9] bg-white p-7 shadow-sm sm:p-10">
          {syntheticPilot ? <div className="mb-6 rounded-2xl border-2 border-amber-500 bg-amber-50 p-4 text-lg font-semibold text-amber-950">Pilot mode: every community, price, availability value and image on this page is synthetic test data—not a real facility.</div> : null}
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">OOmnik results</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">Here’s where I’d start for {relationship}</h1>
          <p className="mt-5 max-w-4xl text-xl leading-8 text-[#53635d]">
            I removed places that do not meet the requirements that matter in this case. The options below are the strongest combinations of fit, evidence and what we still need to verify.
          </p>
          {top.length > 0 ? (
            <div className="mt-7 rounded-2xl bg-[#eef7f2] p-5 text-xl leading-8 text-[#214d40]">
              I found <strong>{top.length}</strong> option{top.length === 1 ? "" : "s"} I think deserve your attention. I’ll show you what I like about each one, what gives me pause, and anything I still want to verify before you rely on it.
            </div>
          ) : (
            <div className="mt-7 rounded-2xl bg-[#fff5df] p-5 text-xl leading-8 text-[#6d5426]">
              I found some promising possibilities, but I’m not comfortable calling any of them a recommendation yet. There are still important details I want verified first.
            </div>
          )}
        </section>

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
              return (
                <article key={item.canonical_facility_id} className="rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9">
                  {item.visual_media?.hero?.url ? <div className="mb-6 overflow-hidden rounded-2xl border border-[#ded6c9] bg-[#f4f0e8]"><Image src={item.visual_media.hero.url} alt={`Synthetic illustration for ${item.facility_name}`} width={1200} height={700} className="h-64 w-full object-cover" /><p className="px-4 py-2 text-sm text-[#6b6257]">{item.visual_media.hero.source_note || "Synthetic pilot illustration—not a real facility"}</p></div> : null}
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-[#3e7868]">{index === 0 ? "Where I would start" : `Option ${index + 1}`}</p>
                      <h2 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{item.facility_name}</h2>
                      <p className="mt-2 text-lg text-[#627069]">{[item.city, item.state].filter(Boolean).join(", ")}</p>
                      <p className="mt-2 text-lg font-semibold text-[#334b42]">{item.starting_monthly_price ? `Starting at ${item.starting_monthly_price.toLocaleString()} / month` : "Price not provided"} · Availability: {item.availability_status === "YES" ? "available" : item.availability_status === "LIMITED" ? "limited / waitlist" : item.availability_status === "NO" ? "not currently available" : "needs confirmation"}</p>
                      {state.careSearchApproach !== "Care provided by the community" && item.starting_monthly_price ? (
                        <div className="mt-3 rounded-xl border border-[#cfe3da] bg-[#f7fbf9] px-4 py-3 text-sm leading-6 text-[#40564e]">
                          <strong>Independent living + outside support:</strong> housing starts at ${"$"}{item.starting_monthly_price.toLocaleString()} / month. Outside-care cost is shown separately only when a verified provider price and required service package are available. Until then, the combined monthly cost remains <strong>to be verified</strong>.
                        </div>
                      ) : null}
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <span className="w-fit rounded-full bg-[#eaf6ef] px-4 py-2 text-lg font-semibold text-[#25613f]">Meets verified must-haves</span>
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
            <div><p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#168fe0]">OOMNIKER</p><h2 className="mt-2 text-3xl font-semibold">Refine the search without starting over</h2><p className="mt-3 max-w-3xl text-lg leading-8 text-[#53635d]">These are the things currently shaping my search for you. Tell OOMNIKER what you want to change, remove or add, and I’ll reassess the options without making you start over.</p></div>
            <button type="button" onClick={() => setOOmnikerOpen((v) => !v)} className="rounded-full bg-[#079ff2] px-5 py-3 font-semibold text-white">{oomnikerOpen ? "Close" : "Open OOMNIKER"}</button>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">{activeCriteria.map(([label,value]) => <span key={label} className="rounded-full border border-[#bcd9e7] bg-white px-4 py-2 text-sm"><strong>{label}:</strong> {value}</span>)}</div>
          {oomnikerNotice ? <div className="mt-4 rounded-2xl bg-white p-4 text-base text-[#315f53]">{oomnikerNotice}{oomnikerDiff ? <p className="mt-2 font-medium">{oomnikerDiff}</p> : null} {oomnikerHistory.current.length > 0 ? <button type="button" onClick={() => { const previous = oomnikerHistory.current.pop(); if (previous) { setState(previous); setOOmnikerNotice("Done. I’ve put the previous preference back and I’m reassessing the earlier search."); } }} className="ml-2 font-semibold underline underline-offset-4">Undo last change</button> : null}</div> : null}
          {oomnikerOpen ? <div className="mt-6"><textarea value={oomnikerText} onChange={(e) => setOOmnikerText(e.target.value)} rows={3} placeholder="Try: Increase the radius to 75 miles, or budget can go to $8,000…" className="w-full rounded-2xl border border-[#bcd9e7] bg-white px-5 py-4 text-lg outline-none focus:border-[#079ff2]" /><button type="button" onClick={applyOOmnikerChange} disabled={!oomnikerText.trim()} className="mt-3 rounded-full bg-[#234f63] px-6 py-3 font-semibold text-white disabled:opacity-40">Update results</button></div> : null}
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
