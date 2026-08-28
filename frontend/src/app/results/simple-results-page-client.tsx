"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { DecisionEngineResponse, fetchPatientDecisionRecommendations } from "@/lib/api";

const TOP_COUNT = 5;

function personLabel(relationship: string): string {
  if (relationship === "Myself") return "you";
  if (relationship === "Couple") return "both of you";
  if (relationship === "Mom") return "Mom";
  if (relationship === "Dad") return "Dad";
  return relationship || "your loved one";
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
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();
  const [response, setResponse] = useState<DecisionEngineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const naturalLanguageQuery = (
    searchParams.get("q") || searchParams.get("search") || searchParams.get("notes") || state.notes || ""
  ).trim();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    void fetchPatientDecisionRecommendations({
      questionnaire_state: state as unknown as Record<string, unknown>,
      natural_language_query: naturalLanguageQuery,
      limit: 50,
    })
      .then((value) => {
        if (active) setResponse(value);
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "We could not load the recommendations.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [naturalLanguageQuery, state]);

  const eligible = useMemo(
    () => (response?.results || []).filter((item) => item.eligibility_status === "ELIGIBLE"),
    [response],
  );
  const pending = useMemo(
    () => (response?.results || []).filter((item) => item.eligibility_status !== "ELIGIBLE" && item.eligibility_status !== "INELIGIBLE"),
    [response],
  );
  const top = eligible.slice(0, TOP_COUNT);
  const relationship = personLabel(state.relationship);
  const detailsHref = `/results/details${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  if (loading) {
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]"><div className="mx-auto max-w-5xl text-xl">Preparing the clearest options for you…</div></main>;
  }

  if (error || !response) {
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]"><div className="mx-auto max-w-5xl rounded-3xl border border-rose-200 bg-white p-8 text-lg">{error || "No results are available yet."}</div></main>;
  }

  return (
    <main className="min-h-screen bg-[#fffaf2] px-5 py-8 text-[#22332d] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <section className="rounded-[2rem] border border-[#e1d8c9] bg-white p-7 shadow-sm sm:p-10">
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">OPTIME results</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">The strongest options for {relationship}</h1>
          <p className="mt-5 max-w-4xl text-xl leading-8 text-[#53635d]">
            We first removed places that do not meet the required conditions. Then we ranked the remaining options using the information we currently have.
          </p>
          {top.length > 0 ? (
            <div className="mt-7 rounded-2xl bg-[#eef7f2] p-5 text-xl leading-8 text-[#214d40]">
              We currently have <strong>{top.length}</strong> leading option{top.length === 1 ? "" : "s"} with verified eligibility. We still recommend confirming the few facility-specific details shown below before making a final decision.
            </div>
          ) : (
            <div className="mt-7 rounded-2xl bg-[#fff5df] p-5 text-xl leading-8 text-[#6d5426]">
              We have promising candidates, but we do not yet have enough verified information to call any of them a final recommendation. We should verify the missing facility details first.
            </div>
          )}
        </section>

        {top.length > 0 ? (
          <section className="mt-8 grid gap-6">
            {top.map((item, index) => {
              const why = (item.explanation?.why_matches || []).map(cleanText).filter(Boolean).slice(0, 3);
              const verify = (item.explanation?.needs_verification || []).map(cleanText).filter(Boolean).slice(0, 3);
              return (
                <article key={item.canonical_facility_id} className="rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-9">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-lg font-semibold text-[#3e7868]">#{index + 1} current match</p>
                      <h2 className="mt-1 text-3xl font-semibold leading-tight sm:text-4xl">{item.facility_name}</h2>
                      <p className="mt-2 text-lg text-[#627069]">{[item.city, item.state].filter(Boolean).join(", ")}</p>
                    </div>
                    <span className="w-fit rounded-full bg-[#eaf6ef] px-4 py-2 text-lg font-semibold text-[#25613f]">Meets verified must-haves</span>
                  </div>

                  <div className="mt-7 grid gap-5 lg:grid-cols-2">
                    <div className="rounded-2xl bg-[#f4f8f6] p-6">
                      <h3 className="text-2xl font-semibold">Why it fits</h3>
                      {why.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">{why.map((text) => <li key={text}>✓ {text}</li>)}</ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8 text-[#596761]">It passed the required-care and location checks. We are still building the plain-language explanation.</p>
                      )}
                    </div>

                    <div className="rounded-2xl bg-[#fff7e7] p-6">
                      <h3 className="text-2xl font-semibold">What we still want to confirm</h3>
                      {verify.length ? (
                        <ul className="mt-3 space-y-3 text-xl leading-8">{verify.map((text) => <li key={text}>• {text}</li>)}</ul>
                      ) : (
                        <p className="mt-3 text-xl leading-8">No critical verification item is currently flagged.</p>
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
              These places are not being presented as recommendations yet because one or more important facts still need verification.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {pending.slice(0, 8).map((item) => (
                <span key={item.canonical_facility_id} className="rounded-full border border-[#ddcda9] bg-white px-4 py-2 text-lg">{item.facility_name}</span>
              ))}
            </div>
          </section>
        ) : null}

        <section className="mt-8 flex flex-wrap gap-4 pb-10">
          <Link href={detailsHref} className="rounded-2xl border-2 border-[#315f53] px-6 py-4 text-xl font-semibold text-[#315f53]">See detailed comparison</Link>
          <Link href="/adaptive-interview?review=1&next=/results" className="rounded-2xl border border-[#cfc6b7] bg-white px-6 py-4 text-xl font-semibold">Change answers</Link>
        </section>
      </div>
    </main>
  );
}
