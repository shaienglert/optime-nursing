"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { VerificationOffer } from "@/app/results/verification-offer";
import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  DecisionEngineRecommendation,
  DecisionEngineResponse,
  fetchPatientDecisionRecommendations,
} from "@/lib/api";
import { clearSearchSession, clearCompareSelection, loadCompareSelection, saveCompareSelection } from "@/lib/search-session";

const TOP_RECOMMENDATION_COUNT = 5;

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function highlightLabel(index: number): string {
  if (index === 0) return "Best Match";
  if (index === 1) return "Strong Alternative";
  if (index === 2) return "Good Alternative";
  return "Worth Considering";
}

function recommendationTitle(index: number): string {
  if (index === 0) return "#1 Recommendation";
  if (index === 1) return "#2 Recommendation";
  if (index === 2) return "#3 Recommendation";
  return `#${index + 1} Recommendation`;
}

function eligibilityTone(status: string): string {
  if (status === "ELIGIBLE") return "text-[#2f6d3e] bg-[#f3fbf5] border-[#cde2d2]";
  if (status === "POTENTIALLY_ELIGIBLE") return "text-[#7a5a2f] bg-[#fff8ea] border-[#f0d9b0]";
  if (status === "INSUFFICIENT_EVIDENCE") return "text-[#24425e] bg-[#f6fbff] border-[#d9e3ec]";
  return "text-[#8b4f3f] bg-[#fff3ef] border-[#f0c9bf]";
}

function displayNeedLabel(parameterId: string): string {
  const labels: Record<string, string> = {
    nursing_24_7: "24/7 nursing support",
    skilled_nursing_capabilities: "Skilled nursing",
    adl_support: "Daily living assistance",
    medication_support: "Medication management",
    ot: "Occupational therapy",
    pt: "Physical therapy",
    speech_therapy: "Speech therapy",
    transfer_assistance: "Transfer assistance",
    post_stroke_neuro_evidence: "Stroke / neuro rehabilitation",
    languages: "Language support",
    medicare_attributes: "Medicare acceptance",
    memory_care: "Memory care",
    published_rates: "Transparent pricing",
    transportation: "Transportation support",
  };
  return labels[parameterId] || parameterId.replace(/_/g, " ");
}

function displayScope(scope?: string | null): string {
  const normalized = (scope || "").toUpperCase();
  if (normalized === "FACILITY") return "Facility-wide";
  if (normalized === "PROGRAM") return "Program-level";
  if (normalized === "UNIT") return "Unit-level";
  if (normalized === "SERVICE") return "Service-level";
  return "Facility-wide";
}

function qualitativeScoreLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Not enough verified evidence";
  if (value >= 80) return "Strong";
  if (value >= 65) return "Good";
  if (value >= 45) return "Mixed";
  return "Needs caution";
}

function confidenceBand(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Insufficient evidence";
  if (value >= 80) return "High confidence";
  if (value >= 60) return "Medium confidence";
  return "Low confidence";
}

function eligibilitySummary(status: DecisionEngineRecommendation["eligibility_status"]): string {
  if (status === "ELIGIBLE") return "Verified fit for current critical needs";
  if (status === "POTENTIALLY_ELIGIBLE") return "Potential fit pending direct verification";
  if (status === "INSUFFICIENT_EVIDENCE") return "Insufficient evidence for critical needs";
  return "Verified critical gaps present";
}

function comparisonStatusLabel(status: "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"): string {
  if (status === "MATCH") return "Supported";
  if (status === "VERIFIED_GAP") return "Not supported";
  return "Needs verification";
}

function buildNeedStatusMap(recommendation: DecisionEngineRecommendation): Map<string, "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"> {
  const statusMap = new Map<string, "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED">();
  for (const item of recommendation.matched_needs || []) {
    if (typeof item?.parameter_id === "string") {
      statusMap.set(item.parameter_id, "MATCH");
    }
  }
  for (const item of recommendation.unmet_verified_needs || []) {
    if (typeof item?.parameter_id === "string") {
      statusMap.set(item.parameter_id, "VERIFIED_GAP");
    }
  }
  for (const item of recommendation.unknown_critical_needs || []) {
    if (typeof item?.parameter_id === "string" && !statusMap.has(item.parameter_id)) {
      statusMap.set(item.parameter_id, "NOT_VERIFIED");
    }
  }
  return statusMap;
}

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();

  const [decisionResponse, setDecisionResponse] = useState<DecisionEngineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiLoadError, setApiLoadError] = useState<string | null>(null);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [savedCanonicalIds, setSavedCanonicalIds] = useState<string[]>([]);
  const [hiddenNeedIds, setHiddenNeedIds] = useState<string[]>([]);
  const [compareSelectedIds, setCompareSelectedIds] = useState<string[]>(() => loadCompareSelection());

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";
  const notesQuery = searchParams.get("notes") || "";
  const naturalLanguageQuery = (textQuery || notesQuery || state.notes || "").trim();
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );

  useEffect(() => {
    let isMounted = true;
    async function loadFacilities() {
      setIsLoading(true);
      setApiLoadError(null);
      try {
        const recommendations = await fetchPatientDecisionRecommendations(JSON.parse(decisionRequestKey) as {
          questionnaire_state: Record<string, unknown>;
          natural_language_query: string;
          limit: number;
        });
        if (!isMounted) return;
        setDecisionResponse(recommendations);
      } catch (error) {
        if (!isMounted) return;
        setDecisionResponse(null);
        setApiLoadError(error instanceof Error ? error.message : "Unable to load decision recommendations from backend API.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [decisionRequestKey]);

  useEffect(() => {
    if (compareSelectedIds.length > 0) {
      saveCompareSelection(compareSelectedIds.slice(0, 5));
      return;
    }
    clearCompareSelection();
  }, [compareSelectedIds]);

  const recommendations = decisionResponse?.results || [];
  const topRecommendations = useMemo(() => recommendations.slice(0, TOP_RECOMMENDATION_COUNT), [recommendations]);
  const remainingRecommendations = useMemo(() => recommendations.slice(TOP_RECOMMENDATION_COUNT), [recommendations]);

  const visibleNeeds = useMemo(() => {
    const allNeeds = decisionResponse?.patient_needs_profile.needs || [];
    return allNeeds.filter((need) => !hiddenNeedIds.includes(need.parameter_id));
  }, [decisionResponse, hiddenNeedIds]);

  const visibleNeedLabels = useMemo(
    () => visibleNeeds.map((need) => ({ ...need, label: displayNeedLabel(need.parameter_id) })),
    [visibleNeeds],
  );

  const recommendationByCanonicalId = useMemo(() => {
    const map = new Map<string, DecisionEngineRecommendation>();
    for (const recommendation of recommendations) {
      map.set(recommendation.canonical_facility_id, recommendation);
    }
    return map;
  }, [recommendations]);

  const compareTrayItems = useMemo(
    () => compareSelectedIds.map((facilityId) => {
      const recommendation = recommendationByCanonicalId.get(facilityId);
      return {
        facilityId,
        facilityName: recommendation?.facility_name || facilityId,
      };
    }),
    [compareSelectedIds, recommendationByCanonicalId],
  );
  const currentResultsPath = `/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  const comparisonNeeds = useMemo(() => {
    const allNeeds = decisionResponse?.patient_needs_profile.needs || [];
    return allNeeds.filter((need) => need.requirement_level === "REQUIRED" || need.requirement_level === "HIGH" || need.requirement_level === "PREFERENCE");
  }, [decisionResponse]);

  const comparisonRows = useMemo(() => {
    const topFacilities = topRecommendations.slice(0, TOP_RECOMMENDATION_COUNT).map((recommendation) => ({
      recommendation,
      statusMap: buildNeedStatusMap(recommendation),
    }));
    return comparisonNeeds.map((need) => ({
      need,
      facilities: topFacilities.map(({ recommendation, statusMap }) => ({
        recommendation,
        status: statusMap.get(need.parameter_id) || "NOT_VERIFIED",
      })),
    }));
  }, [comparisonNeeds, topRecommendations]);

  const startNewSearch = () => {
    clearSearchSession();
    clearCompareSelection();
    resetState();
    router.replace("/");
  };

  const backToSearch = () => {
    router.push("/");
  };

  const toggleCompareSelection = (recommendation: DecisionEngineRecommendation) => {
    setCompareSelectedIds((current) => {
      if (current.includes(recommendation.canonical_facility_id)) {
        return current.filter((item) => item !== recommendation.canonical_facility_id);
      }
      if (current.length >= 5) return current;
      return [...current, recommendation.canonical_facility_id];
    });
  };

  const buildCompareHref = () => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("facilities", compareSelectedIds.join(","));
    params.set("returnTo", currentResultsPath);
    return `/compare?${params.toString()}`;
  };

  const renderRecommendationCard = (recommendation: DecisionEngineRecommendation, index: number) => {
    const isSaved = savedCanonicalIds.includes(recommendation.canonical_facility_id);
    const isSelectedForCompare = compareSelectedIds.includes(recommendation.canonical_facility_id);
    const compareDisabled = !isSelectedForCompare && compareSelectedIds.length >= 5;

    return (
      <article
        key={recommendation.canonical_facility_id}
        className={`rounded-2xl border bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)] ${isSelectedForCompare ? "border-[#6f9a86] ring-1 ring-[#6f9a86]/30" : "border-[#e8ddcc]"}`}
      >
        <div className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
              <h3 className="mt-2 text-xl font-semibold text-[#2f2a24]">{recommendation.facility_name}</h3>
              <p className="mt-1 text-sm text-[#6d655b]">{recommendation.city || "City unknown"}, {recommendation.state || "FL"}</p>
              <p className="mt-1 text-xs font-medium text-[#5f7f6b]">{recommendation.canonical_facility_id}</p>
              <p className="mt-1 text-xs font-semibold text-[#2f6d3e]">
                {recommendation.rank_display || `#${index + 1}`}
                {recommendation.rank_tie_status === "JOINT_RANK" ? " (Tied)" : ""}
              </p>
            </div>
            <div className="rounded-2xl border border-[#d8e7dc] bg-[#f4fbf6] px-3 py-2 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#3e7a4d]">Fit verdict</p>
              <p className="mt-1 text-sm font-semibold text-[#2f6d3e]">{eligibilitySummary(recommendation.eligibility_status)}</p>
              <p className="text-[10px] text-[#5e7264]">{recommendation.match_band.replace("_", " ")}</p>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Quality & Safety</p>
              <p className="text-sm font-semibold text-[#24425e]">{qualitativeScoreLabel(recommendation.quality_safety_score)}</p>
            </div>
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Staffing</p>
              <p className="text-sm font-semibold text-[#24425e]">{qualitativeScoreLabel(recommendation.staffing_score)}</p>
            </div>
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Evidence confidence</p>
              <p className="text-sm font-semibold text-[#24425e]">{confidenceBand(recommendation.evidence_confidence ?? recommendation.evidence_certainty)}</p>
            </div>
          </div>

          <div className={`rounded-2xl border px-3 py-2 text-xs font-semibold ${eligibilityTone(recommendation.eligibility_status)}`}>
            Eligibility: {recommendation.eligibility_status}
          </div>

          <p className="text-sm text-[#4f473d]">
            {recommendation.explanation.why_matches.length > 0
              ? `Strong match because: ${recommendation.explanation.why_matches.slice(0, 3).join("; ")}.`
              : "Evidence-based match assessment available."}
          </p>

          <p className="text-xs text-[#6b6257]">
            Needs verification: {recommendation.explanation.needs_verification.slice(0, 3).join("; ") || "None currently flagged"}
          </p>

          <p className="text-xs text-[#8b4f3f]">
            Concerns: {recommendation.explanation.concerns.slice(0, 2).join("; ") || "No verified gap in current top needs"}
          </p>

          <p className="text-xs text-[#24425e]">Evidence confidence: {confidenceBand(recommendation.evidence_confidence ?? recommendation.evidence_certainty)}</p>
          {recommendation.match_evidence_profile ? (
            <p className="text-xs text-[#24425e]">
              Critical evidence mix: {recommendation.match_evidence_profile.proven_critical_matches} proven, {recommendation.match_evidence_profile.taxonomy_supported_critical_matches} taxonomy-supported, {recommendation.match_evidence_profile.unknown_critical_needs} unknown.
            </p>
          ) : null}
          <p className="text-xs text-[#5b5245]">{recommendation.explanation.availability_note}</p>

          {recommendation.tie_break_explanation_vs_next ? (
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f8fcff] px-3 py-2 text-xs text-[#355270]">
              <p className="font-semibold">Tie-break explanation</p>
              <p className="mt-1">{recommendation.tie_break_explanation_vs_next.why_ranked_above}</p>
              {recommendation.tie_break_explanation_vs_next.remained_equal.length > 0 ? (
                <p className="mt-1">Remained equal: {recommendation.tie_break_explanation_vs_next.remained_equal.join(", ")}</p>
              ) : null}
              {recommendation.tie_break_explanation_vs_next.remaining_unknown.length > 0 ? (
                <p className="mt-1">Unknown: {recommendation.tie_break_explanation_vs_next.remaining_unknown.join(", ")}</p>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {recommendation.parameter_badges.slice(0, 6).map((badge) => (
              <span key={`${recommendation.canonical_facility_id}-${badge}`} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5b5245]">
                {badge}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => toggleCompareSelection(recommendation)}
              disabled={compareDisabled}
              className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isSelectedForCompare ? "border-[#6f9a86] bg-[#f1faf3] text-[#2f6d3e]" : compareDisabled ? "border-[#e1d8c9] bg-[#f7f3eb] text-[#a0907d]" : "border-[#cddce5] bg-white text-[#24425e] hover:bg-[#f6fbff]"}`}
            >
              {isSelectedForCompare ? "Selected for compare" : compareDisabled ? "Compare limit reached" : "Compare"}
            </button>

            {recommendation.facility_profile_id ? (
              <Link href={`/facility/${recommendation.facility_profile_id}?canonical=${encodeURIComponent(recommendation.canonical_facility_id)}&back=${encodeURIComponent(currentResultsPath)}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                VIEW DETAILS
              </Link>
            ) : (
              <span className="inline-flex rounded-full border border-[#d9cfbf] bg-[#f9f6ef] px-4 py-2 text-sm font-semibold text-[#8a7d6e]">
                VIEW DETAILS (not linked)
              </span>
            )}

            <button
              type="button"
              onClick={() => {
                setSavedCanonicalIds((current) =>
                  current.includes(recommendation.canonical_facility_id)
                    ? current.filter((id) => id !== recommendation.canonical_facility_id)
                    : [...current, recommendation.canonical_facility_id]
                );
              }}
              className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isSaved ? "border-[#6f9a86] bg-[#f1faf3] text-[#2f6d3e]" : "border-[#dccfb9] bg-white text-[#5b5245]"}`}
            >
              {isSaved ? "Saved" : "SAVE"}
            </button>

            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${recommendation.facility_name} ${recommendation.city || "Florida"}`)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]"
            >
              MAP
            </a>
          </div>

          {recommendation.facility_profile_id ? <p className="text-xs text-[#6d655b]">Profile-connected facility record: {recommendation.facility_profile_id}</p> : null}
        </div>
      </article>
    );
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">Results are personalized to your current needs profile and governed parameter evidence.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={backToSearch} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]">Back to search</button>
            <button type="button" onClick={startNewSearch} className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]">New search</button>
          </div>

          {visibleNeeds.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Active patient needs</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {visibleNeedLabels.map((need) => (
                  <button
                    key={need.parameter_id}
                    type="button"
                    onClick={() => setHiddenNeedIds((current) => [...current, need.parameter_id])}
                    className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-3 py-1 text-sm text-[#534a3d] hover:bg-[#efe8db]"
                  >
                    {need.requirement_level}: {need.label} x
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {compareTrayItems.length > 0 ? (
            <div className="mt-5 rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#24425e]">Compare tray</p>
                  <p className="mt-1 text-sm text-[#4a6076]">Compare selected ({compareTrayItems.length})</p>
                </div>
                <button
                  type="button"
                  disabled={compareTrayItems.length < 2}
                  onClick={() => router.push(buildCompareHref())}
                  className="rounded-full bg-[#24425e] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb0c1]"
                >
                  Compare now
                </button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {compareTrayItems.map((facility) => (
                  <button
                    key={`tray-${facility.facilityId}`}
                    type="button"
                    onClick={() => setCompareSelectedIds((current) => current.filter((id) => id !== facility.facilityId))}
                    className="inline-flex items-center gap-2 rounded-full border border-[#cddce5] bg-white px-3 py-1.5 text-sm text-[#24425e] hover:bg-[#edf6fb]"
                  >
                    <span>{facility.facilityName}</span>
                    <span aria-hidden="true">x</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-[#4a6076]">Select 2 to 5 facilities. Compare stays separate from Save.</p>
            </div>
          ) : null}
        </header>

        {!isLoading && apiLoadError ? (
          <section className="mt-6 rounded-3xl border border-[#e5b7b7] bg-[#fff4f4] p-6 text-sm text-[#7a2f2f]">
            <p className="font-semibold">Decision API unavailable</p>
            <p className="mt-2">{apiLoadError}</p>
          </section>
        ) : null}

        {!isLoading && recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Personalized Recommendations</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                {decisionResponse?.result_count || 0} communities shown from {decisionResponse?.total_candidates_scored || 0} scored facilities.
              </p>
              <p className="mt-2 text-sm text-[#5c5347]">{decisionResponse?.availability_policy}</p>
              {decisionResponse?.tie_break_policy ? (
                <p className="mt-2 text-xs text-[#5c5347]">
                  True-tie support is active: {decisionResponse.tie_break_policy.true_tie_label}. Recommendations preserve unknowns as neutral and keep confidence separate from ranking.
                </p>
              ) : null}
            </article>

            <VerificationOffer />

            <section className="space-y-6">
              {topRecommendations.map((recommendation, index) => (
                <section key={`top-${recommendation.canonical_facility_id}`} className="space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdf9] p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
                  <div className="rounded-2xl border border-[#d9cfbf] bg-[linear-gradient(120deg,#f7efe0_0%,#fbf6ec_55%,#ffffff_100%)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Advisor Recommendation</p>
                    <h3 className="mt-1 text-2xl font-semibold text-[#2f2a24]">{recommendationTitle(index)}</h3>
                    <p className="mt-2 text-sm text-[#5f5548]">{highlightLabel(index)} for {relationship}, with governed explainability.</p>
                  </div>
                  {renderRecommendationCard(recommendation, index)}
                </section>
              ))}
            </section>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <div className="h-px w-full bg-[linear-gradient(90deg,transparent,#d9cfbf,transparent)]" />
                <button type="button" onClick={() => setShowMoreCommunities((current) => !current)} className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]">
                  {showMoreCommunities ? "Hide additional communities" : "Show more communities"}
                </button>
                {showMoreCommunities ? (
                  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {remainingRecommendations.map((recommendation, index) => renderRecommendationCard(recommendation, index + TOP_RECOMMENDATION_COUNT))}
                  </section>
                ) : null}
              </div>
            ) : null}

            {comparisonRows.length > 0 ? (
              <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Patient-specific comparison</p>
                <p className="mt-2 text-sm text-[#4a6076]">Top recommendations are compared on identical patient-need parameters. Needs verification is neutral and never treated as an automatic failure.</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {topRecommendations.map((recommendation) => {
                    return (
                      <div key={`summary-${recommendation.canonical_facility_id}`} className="rounded-xl border border-[#cddce5] bg-white px-3 py-2 text-xs text-[#24425e]">
                        <p className="font-semibold">{recommendation.facility_name}</p>
                        <p>{recommendation.rank_display || "Unranked"}{recommendation.rank_tie_status === "JOINT_RANK" ? " (Tied)" : ""}</p>
                        <p>Fit: {eligibilitySummary(recommendation.eligibility_status)}</p>
                        <p>Quality & Safety: {qualitativeScoreLabel(recommendation.quality_safety_score)}</p>
                        <p>Confidence: {confidenceBand(recommendation.evidence_confidence ?? recommendation.evidence_certainty)}</p>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full border-collapse text-xs">
                    <thead>
                      <tr>
                        <th className="border border-[#d9e3ec] bg-white px-2 py-1 text-left">Need</th>
                        {topRecommendations.map((recommendation) => (
                          <th key={recommendation.canonical_facility_id} className="border border-[#d9e3ec] bg-white px-2 py-1 text-left">{recommendation.facility_name}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonRows.map(({ need, facilities }) => (
                        <tr key={`cmp-${need.parameter_id}`}>
                          <td className="border border-[#d9e3ec] bg-white px-2 py-1">{need.requirement_level} · {displayNeedLabel(need.parameter_id)}</td>
                          {facilities.map(({ recommendation, status }) => {
                            return (
                              <td key={`${recommendation.canonical_facility_id}-${need.parameter_id}`} className="border border-[#d9e3ec] bg-white px-2 py-1">
                                  {`${comparisonStatusLabel(status)} (${displayScope(need.applicable_scope)})`}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">
          {isLoading ? "Loading communities..." : apiLoadError ? "Decision API unavailable" : recommendations.length > 0 ? "End of recommendations" : "No communities available"}
        </div>
      </section>
    </main>
  );
}
