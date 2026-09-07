"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  DecisionEngineResponse,
  PersonalDecisionReportResponse,
  PersonalReportClaim,
  PersonalReportSections,
  fetchPersonalDecisionReport,
} from "@/lib/api";
import { loadDecisionResponseCache } from "@/lib/search-session";

function personLabel(relationship: string): string {
  if (relationship === "Myself") return "you";
  if (relationship === "Couple") return "both of you";
  if (relationship === "Mom") return "Mom";
  if (relationship === "Dad") return "Dad";
  return relationship || "your loved one";
}

function claimMarker(claim: PersonalReportClaim): string {
  if (claim.claim_type === "UNKNOWN") return "?";
  if (claim.claim_id.includes(".concern.")) return "△";
  return "✓";
}

function bySection(sections: PersonalReportSections | undefined, key: string): PersonalReportClaim[] {
  return sections?.[key] || [];
}

export function PersonalReportPageClient() {
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();
  const [report, setReport] = useState<PersonalDecisionReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const naturalLanguageQuery = (
    searchParams.get("q") || searchParams.get("search") || searchParams.get("notes") || state.notes || ""
  ).trim();
  // Same shape/limit as the results page's cache key -- reuses an already-computed
  // decision result when the visitor just came from /results for this exact case,
  // instead of paying for a second, redundant multi-minute AI-ranking pass.
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const cachedDecisionResult = loadDecisionResponseCache<DecisionEngineResponse>(decisionRequestKey);
    void fetchPersonalDecisionReport({
      questionnaire_state: state as unknown as Record<string, unknown>,
      natural_language_query: naturalLanguageQuery,
      limit: 50,
      decision_result: cachedDecisionResult ? (cachedDecisionResult as unknown as Record<string, unknown>) : undefined,
    })
      .then((value) => {
        if (active) setReport(value);
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "We could not prepare your report.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [decisionRequestKey, naturalLanguageQuery, state]);

  const relationship = personLabel(state.relationship);
  const backHref = `/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  const situation = useMemo(() => bySection(report?.sections, "YOUR_SITUATION"), [report]);
  const role = useMemo(() => bySection(report?.sections, "YOUR_ROLE")[0], [report]);
  const whatMatters = useMemo(() => bySection(report?.sections, "WHAT_MATTERS"), [report]);
  const whyRecommendation = useMemo(() => bySection(report?.sections, "WHY_RECOMMENDATION"), [report]);
  const pending = useMemo(() => bySection(report?.sections, "BEFORE_YOU_DECIDE"), [report]);

  if (loading) {
    return (
      <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]">
        <div className="mx-auto max-w-5xl text-xl">Preparing your personal report…</div>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]">
        <div className="mx-auto max-w-5xl rounded-3xl border border-rose-200 bg-white p-8 text-lg">
          {error || "No report is available yet."}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#fffaf2] px-5 py-8 text-[#22332d] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <section className="rounded-[2rem] border border-[#e1d8c9] bg-white p-7 shadow-sm sm:p-10">
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">Personal decision report</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">The full picture for {relationship}</h1>
          {role ? <p className="mt-5 max-w-4xl text-xl leading-8 text-[#53635d]">{role.text}</p> : null}
        </section>

        {situation.length > 0 ? (
          <section className="mt-8 rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9">
            <h2 className="text-3xl font-semibold">Your situation</h2>
            <ul className="mt-5 space-y-3 text-xl leading-8">
              {situation.map((claim) => (
                <li key={claim.claim_id}>{claim.text}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {whatMatters.length > 0 ? (
          <section className="mt-8 rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9">
            <h2 className="text-3xl font-semibold">What matters most in your case</h2>
            <ul className="mt-5 space-y-3 text-xl leading-8">
              {whatMatters.map((claim) => (
                <li key={claim.claim_id}>• {claim.text}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {whyRecommendation.length > 0 ? (
          <section className="mt-8 rounded-2xl bg-[#eef7f2] p-6 text-xl leading-8 text-[#214d40]">
            <h2 className="text-2xl font-semibold text-[#22332d]">Why this recommendation</h2>
            <ul className="mt-4 space-y-2">
              {whyRecommendation.map((claim) => (
                <li key={claim.claim_id}>{claim.text}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {report.report_ready && report.candidates.length > 0 ? (
          <section className="mt-8 grid gap-6">
            {report.candidates.map((candidate, index) => {
              const whyThisPlace = bySection(candidate.sections, "WHY_THIS_PLACE");
              const stillUnknown = bySection(candidate.sections, "BEFORE_YOU_DECIDE");
              return (
                <article
                  key={candidate.canonical_facility_id}
                  className="rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-[#3e7868]">#{index + 1} current match</p>
                      <h2 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{candidate.facility_name}</h2>
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      {candidate.match_score !== null ? (
                        <span className="w-fit rounded-full bg-[#eaf6ef] px-4 py-2 text-lg font-semibold text-[#25613f]">
                          {candidate.match_band ? candidate.match_band.replace(/_/g, " ") : "Match"} · {Math.round(candidate.match_score)}%
                        </span>
                      ) : null}
                      <Link
                        href={`/facility/canonical?canonical=${encodeURIComponent(candidate.canonical_facility_id)}&back=${encodeURIComponent(`/results/personal-report${searchParams.toString() ? `?${searchParams.toString()}` : ""}`)}`}
                        className="rounded-full border border-[#315f53] px-4 py-2 text-base font-semibold text-[#315f53] hover:bg-[#f4fbf7]"
                      >
                        View full listing →
                      </Link>
                    </div>
                  </div>

                  <div className="mt-7 grid gap-5 lg:grid-cols-2">
                    <div className="rounded-2xl bg-[#f4f8f6] p-6">
                      <h3 className="text-2xl font-semibold">Why it fits your case</h3>
                      {whyThisPlace.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">
                          {whyThisPlace.map((claim) => (
                            <li key={claim.claim_id}>
                              {claimMarker(claim)} {claim.text}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8 text-[#596761]">
                          We are still building the plain-language explanation for this option.
                        </p>
                      )}
                    </div>

                    <div className="rounded-2xl bg-[#fff7e7] p-6">
                      <h3 className="text-2xl font-semibold">We don&apos;t know yet</h3>
                      {stillUnknown.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">
                          {stillUnknown.map((claim) => (
                            <li key={claim.claim_id}>? {claim.text}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8">No open verification items are currently flagged for this option.</p>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </section>
        ) : null}

        {!report.report_ready && pending.length > 0 ? (
          <section className="mt-8 rounded-[2rem] border border-[#ead9b4] bg-[#fffaf0] p-7 sm:p-9">
            <h2 className="text-3xl font-semibold">We need a bit more information first</h2>
            <ul className="mt-5 space-y-3 text-xl leading-8 text-[#655a45]">
              {pending.map((claim) => (
                <li key={claim.claim_id}>{claim.text}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="mt-8 flex flex-wrap gap-4 pb-10">
          <Link href={backHref} className="rounded-2xl border-2 border-[#315f53] px-6 py-4 text-xl font-semibold text-[#315f53]">
            Back to results
          </Link>
          <Link
            href="/adaptive-interview?review=1&next=/results/personal-report"
            className="rounded-2xl border border-[#cfc6b7] bg-white px-6 py-4 text-xl font-semibold"
          >
            Change answers
          </Link>
        </section>
      </div>
    </main>
  );
}
