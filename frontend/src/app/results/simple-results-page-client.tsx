"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { DecisionEngineResponse, fetchPatientDecisionRecommendations } from "@/lib/api";
import { loadDecisionResponseCache, saveDecisionResponseCache } from "@/lib/search-session";

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
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );

  useEffect(() => {
    let active = true;
    // A home-page answer is saved immediately before navigation.  Give React a
    // short settling window so the results request uses that final state rather
    // than sending both the previous and the just-updated questionnaire.
    const timer = window.setTimeout(() => {
      setLoading(true);
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
        });
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [decisionRequestKey, naturalLanguageQuery, state]);

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
  const personalReportHref = `/results/personal-report${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

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
