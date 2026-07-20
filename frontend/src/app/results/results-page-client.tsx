"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
import { resolveBudgetValue } from "@/lib/budget-utils";
import { GovernanceRuntimeContext, SearchFacility, fetchGovernanceRuntimeContext, fetchSearchFacilities } from "@/lib/api";
import { resolveFacilityImage, resolvePriceTruth } from "@/lib/facility-experience";
import { RankedRecommendation, runOptimeV2Engine } from "@/lib/optime-v2-engine";
import { clearSearchSession } from "@/lib/search-session";

const TOP_RECOMMENDATION_COUNT = 5;

type RelaxationOverrides = {
  adjustBudget: boolean;
  expandDistance: boolean;
  allowAssistedLiving: boolean;
  includeCommunitiesWithoutMemoryCare: boolean;
  removeActivityPreference: boolean;
};

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


function hasRealAddressData(distanceProfile: ReturnType<typeof useQuestionnaire>["state"]["humanIntelligenceV2"]["distanceProfile"]): boolean {
  return Boolean(
    distanceProfile.referenceLocations.parentCurrentHome ||
      distanceProfile.referenceLocations.primaryCaregiverHome ||
      distanceProfile.referenceLocations.secondaryFamilyHomes ||
      distanceProfile.referenceLocations.preferredHospital ||
      distanceProfile.referenceLocations.placeOfWorship ||
      distanceProfile.driveTimes.normal ||
      distanceProfile.driveTimes.rushHour ||
      distanceProfile.driveTimes.emergency,
  );
}

function visualConfidenceLabel(score: number): string {
  if (score >= 80) return "High";
  if (score >= 55) return "Medium";
  return "Low";
}

function ensureSentence(text: string): string {
  const value = (text || "").trim();
  if (!value) return "";
  if (/[.!?]$/.test(value)) return value;
  return `${value}.`;
}

function formatReviewDate(value: string | undefined): string {
  if (!value) return "Recently reviewed";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Recently reviewed";
  return parsed.toLocaleDateString();
}

function buildBestAvailableSummary(summary: ReturnType<typeof runOptimeV2Engine>["rejectionSummary"]): string {
  const messages: string[] = [];
  if (summary.rejectedByCare > 0) {
    messages.push(`${summary.rejectedByCare} communities came close but offer a different level of daily support than requested.`);
  }
  if (summary.rejectedByBudget > 0) {
    messages.push(`${summary.rejectedByBudget} communities exceeded the budget that was marked as mandatory.`);
  }
  if (summary.rejectedByDistance > 0) {
    messages.push(`${summary.rejectedByDistance} communities were outside the distance range that was marked as mandatory.`);
  }
  if (summary.rejectedByVerification > 0) {
    messages.push(`${summary.rejectedByVerification} communities still need extra confirmation on a required detail.`);
  }

  if (messages.length === 0) {
    return "No community matched every requirement. These communities provide the closest overall fit based on what has been verified so far.";
  }

  return `${messages.slice(0, 2).join(" ")} These communities provide the closest overall fit based on what has been verified so far.`;
}

function deriveEngineState(baseState: QuestionnaireState, overrides: RelaxationOverrides): QuestionnaireState {
  const next = JSON.parse(JSON.stringify(baseState)) as QuestionnaireState;

  if (overrides.adjustBudget) {
    const currentBudget = Number(next.budget || 0);
    next.budget = Math.round(Math.max(currentBudget * 1.25, currentBudget + 1500));
    next.notes = next.notes.replace(/strict budget|hard budget|must stay under|budget is mandatory/gi, "").trim();
  }

  if (overrides.expandDistance) {
    next.distanceFromFamily = "";
    next.referenceLocationValue = "";
    next.humanIntelligenceV2.distanceProfile.referenceLocations.parentCurrentHome = "";
    next.humanIntelligenceV2.distanceProfile.referenceLocations.primaryCaregiverHome = "";
    next.humanIntelligenceV2.distanceProfile.referenceLocations.secondaryFamilyHomes = "";
    next.humanIntelligenceV2.distanceProfile.referenceLocations.preferredHospital = "";
    next.humanIntelligenceV2.distanceProfile.referenceLocations.placeOfWorship = "";
    next.humanIntelligenceV2.distanceProfile.driveTimes.normal = "";
    next.humanIntelligenceV2.distanceProfile.driveTimes.rushHour = "";
    next.humanIntelligenceV2.distanceProfile.driveTimes.emergency = "";
    next.notes = next.notes.replace(/distance is mandatory|must be within|only in miami-dade|stay in miami-dade|only in palm beach|must stay close/gi, "").trim();
  }

  if (overrides.allowAssistedLiving) {
    if (next.assistanceLevel === "Skilled nursing care") {
      next.assistanceLevel = "Light assistance";
    }
    if (next.futureCarePreference === "Independent communities only") {
      next.futureCarePreference = "Independent today, support available later";
    }
  }

  if (overrides.includeCommunitiesWithoutMemoryCare && next.memoryStatus === "Significant memory issues") {
    next.memoryStatus = "Mild memory issues";
  }

  if (overrides.removeActivityPreference) {
    next.happinessPreferences = [];
  }

  return next;
}

function familyNarrative(recommendation: RankedRecommendation): string[] {
  const facility = recommendation.facility;
  const clinical = recommendation.report.audit.clinicalReasoning;
  const unknownCount = recommendation.report.audit.verificationRequest.unknownCount;
  const budgetRange = recommendation.report.audit.anonymousVerificationPayload.budgetRange;

  const first = `We recommend ${facility.name} because it appears to match the requested level of daily support.`;
  const second = budgetRange === "Budget not supplied"
    ? "A budget was not supplied, so OPTIME is using verified care and fit signals instead of claiming a price-based match."
    : `The current budget signal is ${budgetRange.toLowerCase()}.`;
  const third = clinical.whyThisCommunity
    ? ensureSentence(clinical.whyThisCommunity)
    : "Clinical and lifestyle indicators suggest a strong overall fit for this search.";
  const fourth = unknownCount > 0
    ? `Several requested features are still awaiting confirmation, and OPTIME can verify those directly with the community before next steps.`
    : "Most requested features are already confirmed, which reduces uncertainty before next steps.";

  return [first, second, third, fourth];
}

function stoodOutBullets(recommendation: RankedRecommendation): string[] {
  const facility = recommendation.facility;
  const budgetRange = recommendation.report.audit.anonymousVerificationPayload.budgetRange;
  const bullets: string[] = [];

  bullets.push("Meets the requested care level.");
  bullets.push(budgetRange === "Budget not supplied" ? "Budget was not supplied, so price remains an estimate." : "Fits the selected budget range.");
  if ((facility.lifestyleCapabilities || []).length > 0) {
    bullets.push("Supports a socially active daily routine.");
  }
  if ((facility.quality_rating ?? 0) >= 4) {
    bullets.push("Shows strong clinical quality indicators.");
  }
  if (facility.continuum_of_care === "YES") {
    bullets.push("Offers a future-care pathway if needs increase.");
  }

  return bullets.slice(0, 5);
}

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();

  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [governanceContext, setGovernanceContext] = useState<GovernanceRuntimeContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiLoadError, setApiLoadError] = useState<string | null>(null);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [relaxationOverrides, setRelaxationOverrides] = useState<RelaxationOverrides>({
    adjustBudget: false,
    expandDistance: false,
    allowAssistedLiving: false,
    includeCommunitiesWithoutMemoryCare: false,
    removeActivityPreference: false,
  });
  const [savedFacilityIds, setSavedFacilityIds] = useState<number[]>([]);
  const [skippedFacilityIds, setSkippedFacilityIds] = useState<number[]>([]);
  const [compareFacilityIds, setCompareFacilityIds] = useState<number[]>([]);

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const futureCarePreference = searchParams.get("futureCarePreference") || state.futureCarePreference || "";
  const activities = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const budgetParam = searchParams.get("budget");
  const budget = budgetParam !== null && budgetParam !== "" ? Number(budgetParam) : resolveBudgetValue(state.budget) ?? 7000;
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";
  const distanceProfile = state.humanIntelligenceV2.distanceProfile;
  const hasAddresses = hasRealAddressData(distanceProfile);
  const distance = hasAddresses ? (searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes") : "Not used";

  const filters = useMemo(
    () => [
      { label: `Age: ${age}`, disabled: false },
      { label: `Care: ${care}`, disabled: false },
      ...(futureCarePreference ? [{ label: `Future care: ${futureCarePreference}`, disabled: false }] : []),
      { label: `Activities: ${activities}`, disabled: false },
      { label: `Budget: $${budget.toLocaleString()}`, disabled: false },
      { label: `Distance: ${distance}`, disabled: !hasAddresses },
    ],
    [age, care, futureCarePreference, activities, budget, distance, hasAddresses],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      setApiLoadError(null);
      try {
        const [data, governedContext] = await Promise.all([
          fetchSearchFacilities(textQuery),
          fetchGovernanceRuntimeContext(),
        ]);
        if (isMounted) {
          setFacilities(data);
          setGovernanceContext(governedContext);
        }
      } catch (error) {
        if (isMounted) {
          setFacilities([]);
          setGovernanceContext(null);
          setApiLoadError(error instanceof Error ? error.message : "Unable to load authoritative production API data.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [textQuery]);

  const engineState = useMemo(() => deriveEngineState(state, relaxationOverrides), [state, relaxationOverrides]);
  const engineOutput = useMemo(
    () => runOptimeV2Engine(facilities, engineState, { governanceContext }),
    [facilities, engineState, governanceContext],
  );
  const visibleRecommendations = useMemo(() => engineOutput.displayedRecommendations, [engineOutput]);
  const topRecommendations = useMemo(() => visibleRecommendations.slice(0, TOP_RECOMMENDATION_COUNT), [visibleRecommendations]);
  const remainingRecommendations = useMemo(() => visibleRecommendations.slice(TOP_RECOMMENDATION_COUNT), [visibleRecommendations]);
  const hasExactMatches = engineOutput.accepted.length > 0;
  const hasVisibleRecommendations = visibleRecommendations.length > 0;

  const startNewSearch = () => {
    clearSearchSession();
    resetState();
    router.replace("/");
  };

  const backToSearch = () => {
    router.push("/");
  };

  const renderFullCard = (recommendation: RankedRecommendation, index: number) => {
    const facility = recommendation.facility;
    const report = recommendation.report;
    const clinical = report.audit.clinicalReasoning;
    const narrativeParagraphs = familyNarrative(recommendation);
    const verifiedItems = report.audit.verificationChecklist.filter((item) => item.state === "YES");
    const unknownItems = report.audit.verificationChecklist.filter((item) => item.state === "UNKNOWN");
    const noItems = report.audit.verificationChecklist.filter((item) => item.state === "NO");
    const standout = stoodOutBullets(recommendation);
    const visitQuestions = report.audit.clinicalReasoning.questionsForFacility.slice(0, 4);
    const reviewDate = formatReviewDate(report.audit.confidence.lastIntelligenceRefresh);
    const governed = report.audit.governedFacilityDecision;
    const imageTruth = resolveFacilityImage(facility);
    const priceTruth = resolvePriceTruth(facility);
    const isSaved = savedFacilityIds.includes(facility.id);
    const isSkipped = skippedFacilityIds.includes(facility.id);
    const isCompared = compareFacilityIds.includes(facility.id);

    return (
      <article key={facility.id} className={`rounded-2xl border ${isSkipped ? "border-[#f0c9bf] bg-[#fff8f4] opacity-85" : "border-[#e8ddcc] bg-white"} p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)]`}>
        <div className="grid gap-4 lg:grid-cols-[96px,1fr]">
          <div className="overflow-hidden rounded-xl border border-[#e3d8c8] bg-[#f7f2e8]">
            <img
              src={imageTruth.url}
              alt={`${facility.name} thumbnail`}
              className="h-24 w-full object-cover"
              onError={(event) => {
                event.currentTarget.src = "/cms-placeholder.svg";
              }}
            />
            <div className="border-t border-[#e3d8c8] bg-white px-2 py-1 text-[10px] text-[#6b6257]">
              {imageTruth.isPlaceholder ? "Compact placeholder" : imageTruth.sourceLabel}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
                <h3 className="mt-2 text-xl font-semibold text-[#2f2a24]">{facility.name}</h3>
                <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                <p className="mt-1 text-xs font-medium text-[#5f7f6b]">{facility.careTypes.slice(0, 2).join(" • ")}</p>
              </div>
              <div className="rounded-2xl border border-[#d8e7dc] bg-[#f4fbf6] px-3 py-2 text-center">
                <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#3e7a4d]">OPTIME fit</p>
                <p className="mt-1 text-lg font-semibold text-[#2f6d3e]">{Math.max(1, Math.round(recommendation.totalScore))}%</p>
                <p className="text-[10px] text-[#5e7264]">{visualConfidenceLabel(report.confidenceScore)} confidence</p>
              </div>
            </div>

            <p className="text-sm text-[#4f473d]">{narrativeParagraphs[0]}</p>
            <p className="text-sm text-[#5f5548]">{standout.slice(0, 3).join(" · ")}</p>
            <p className="text-sm text-[#5f5548]">{clinical.whyThisCommunity || recommendation.rankReason}</p>
            <p className="text-xs text-[#6b6257]">{verifiedItems.length > 0 ? `Verified: ${verifiedItems.slice(0, 2).map((item) => item.label).join("; ")}` : "No verified matches yet."}</p>
            <p className="text-xs text-[#8b4f3f]">{noItems.length > 0 ? `Biggest concern: ${noItems[0].label}` : "No confirmed negative item yet."}</p>
            <p className="text-xs text-[#24425e]">{visitQuestions[0] ? `Ask: ${visitQuestions[0]}` : "No unanswered question surfaced yet."}</p>

            <div className="flex flex-wrap gap-2 text-xs text-[#5b5245]">
              <span className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 font-medium">{governed ? `Governed: ${governed.eligibility_status}` : "Governed data pending"}</span>
              <span className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 font-medium">{reviewDate}</span>
              <span className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 font-medium">{priceTruth.label}: {priceTruth.value}</span>
              <span className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 font-medium">{unknownItems.length} unresolved</span>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link href={`/facility/${facility.id}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                VIEW FACILITY
              </Link>
              <button
                type="button"
                onClick={() => {
                  setSavedFacilityIds((current) => current.includes(facility.id) ? current.filter((id) => id !== facility.id) : [...current, facility.id]);
                  setSkippedFacilityIds((current) => current.filter((id) => id !== facility.id));
                }}
                className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isSaved ? "border-[#6f9a86] bg-[#f1faf3] text-[#2f6d3e]" : "border-[#dccfb9] bg-white text-[#5b5245]"}`}
              >
                {isSaved ? "Saved" : "SAVE"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setSkippedFacilityIds((current) => current.includes(facility.id) ? current.filter((id) => id !== facility.id) : [...current, facility.id]);
                  setSavedFacilityIds((current) => current.filter((id) => id !== facility.id));
                }}
                className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isSkipped ? "border-[#f0c9bf] bg-[#fff3ef] text-[#8b4f3f]" : "border-[#dccfb9] bg-white text-[#5b5245]"}`}
              >
                {isSkipped ? "Skipped" : "NOT FOR ME"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setCompareFacilityIds((current) => current.includes(facility.id) ? current.filter((id) => id !== facility.id) : [...current.slice(0, 2), facility.id]);
                }}
                className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isCompared ? "border-[#5f7f6b] bg-[#eef7f1] text-[#3f6a48]" : "border-[#dccfb9] bg-white text-[#5b5245]"}`}
              >
                {isCompared ? "Comparing" : "COMPARE"}
              </button>
              <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer" className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                MAP
              </a>
            </div>
          </div>
        </div>
      </article>
    );
  };

  const renderTopRecommendation = (recommendation: RankedRecommendation, index: number) => {
    const facility = recommendation.facility;
    const verification = recommendation.report.audit.verificationRequest;

    return (
      <section key={`top-${facility.id}`} className="space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdf9] p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
        <div className="rounded-2xl border border-[#d9cfbf] bg-[linear-gradient(120deg,#f7efe0_0%,#fbf6ec_55%,#ffffff_100%)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Advisor Recommendation</p>
          <h3 className="mt-1 text-2xl font-semibold text-[#2f2a24]">{recommendationTitle(index)}</h3>
          <p className="mt-2 text-sm text-[#5f5548]">{highlightLabel(index)} for {relationship}, explained in family-first language.</p>
        </div>

        <div className="rounded-2xl border border-[#d9e3ec] bg-[#f6fbff] p-4 text-sm text-[#4a6076]">
          <p className="font-semibold text-[#24425e]">Next step</p>
          <p className="mt-1">{verification.nextStepMessage}</p>
        </div>

        {renderFullCard(recommendation, index)}
      </section>
    );
  };

  const renderCompactCard = (recommendation: RankedRecommendation, index: number) => {
    return renderFullCard(recommendation, index);
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">These communities best match what matters most to {relationship}.</p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={backToSearch}
              className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]"
            >
              Back to search
            </button>
            <button
              type="button"
              onClick={startNewSearch}
              className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]"
            >
              New search
            </button>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter.label}
                type="button"
                disabled={filter.disabled}
                className={`rounded-full border px-3 py-1 text-sm ${
                  filter.disabled
                    ? "cursor-default border-[#d9d3c7] bg-[#f0ede6] text-[#8b8578]"
                    : "border-[#d9cfbf] bg-[#f6f2ea] text-[#534a3d] hover:bg-[#efe8db]"
                }`}
              >
                {filter.label}{filter.disabled ? "" : " x"}
              </button>
            ))}
          </div>
        </header>

        {!isLoading && apiLoadError ? (
          <section className="mt-6 rounded-3xl border border-[#e5b7b7] bg-[#fff4f4] p-6 text-sm text-[#7a2f2f]">
            <p className="font-semibold">Authoritative API unavailable</p>
            <p className="mt-2">{apiLoadError}</p>
            <p className="mt-2">Production fallback recommendations are disabled until backend API connectivity is restored.</p>
          </section>
        ) : null}

        {!isLoading && facilities.length > 0 && !hasExactMatches ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">Best Available Communities</p>
            <p className="mt-3 text-sm">No community matched every requirement. These communities provide the closest overall fit.</p>
            {hasVisibleRecommendations ? (
              <p className="mt-4 rounded-2xl border border-[#e3cfa6] bg-[#fff6e7] px-4 py-3 text-sm font-semibold text-[#8a6330]">
                {buildBestAvailableSummary(engineOutput.rejectionSummary)}
              </p>
            ) : null}
          </section>
        ) : null}

        {!isLoading && hasVisibleRecommendations ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">{hasExactMatches ? "Recommended Communities" : "Best Available Communities"}</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                {hasExactMatches
                  ? "Each recommendation answers four simple questions: why it is a good fit, what we already know, what still needs confirmation, and what should happen next."
                  : "These communities are the strongest available options based on verified fit, trade-offs, and what still needs confirmation."}
              </p>
            </article>

            {!hasExactMatches ? (
              <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf0] p-6 text-sm text-[#5f554a]">
                <p className="font-semibold text-[#7a5a2f]">Things to consider</p>
                <p className="mt-2 leading-6">{buildBestAvailableSummary(engineOutput.rejectionSummary)}</p>
                <p className="mt-4 font-semibold text-[#7a5a2f]">Adjust your search</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => setRelaxationOverrides((current) => ({ ...current, adjustBudget: !current.adjustBudget }))} className={`rounded-full border px-4 py-2 text-sm font-semibold ${relaxationOverrides.adjustBudget ? "border-[#5f7f6b] bg-[#e9f1e7] text-[#30563e]" : "border-[#d9cfbf] bg-white text-[#534a3d] hover:bg-[#efe8db]"}`}>
                    Adjust Budget
                  </button>
                  <button type="button" onClick={() => setRelaxationOverrides((current) => ({ ...current, expandDistance: !current.expandDistance }))} className={`rounded-full border px-4 py-2 text-sm font-semibold ${relaxationOverrides.expandDistance ? "border-[#5f7f6b] bg-[#e9f1e7] text-[#30563e]" : "border-[#d9cfbf] bg-white text-[#534a3d] hover:bg-[#efe8db]"}`}>
                    Expand Distance
                  </button>
                  <button type="button" onClick={() => setRelaxationOverrides((current) => ({ ...current, allowAssistedLiving: !current.allowAssistedLiving }))} className={`rounded-full border px-4 py-2 text-sm font-semibold ${relaxationOverrides.allowAssistedLiving ? "border-[#5f7f6b] bg-[#e9f1e7] text-[#30563e]" : "border-[#d9cfbf] bg-white text-[#534a3d] hover:bg-[#efe8db]"}`}>
                    Allow Assisted Living
                  </button>
                  <button type="button" onClick={() => setRelaxationOverrides((current) => ({ ...current, includeCommunitiesWithoutMemoryCare: !current.includeCommunitiesWithoutMemoryCare }))} className={`rounded-full border px-4 py-2 text-sm font-semibold ${relaxationOverrides.includeCommunitiesWithoutMemoryCare ? "border-[#5f7f6b] bg-[#e9f1e7] text-[#30563e]" : "border-[#d9cfbf] bg-white text-[#534a3d] hover:bg-[#efe8db]"}`}>
                    Include Communities Without Memory Care
                  </button>
                  <button type="button" onClick={() => setRelaxationOverrides((current) => ({ ...current, removeActivityPreference: !current.removeActivityPreference }))} className={`rounded-full border px-4 py-2 text-sm font-semibold ${relaxationOverrides.removeActivityPreference ? "border-[#5f7f6b] bg-[#e9f1e7] text-[#30563e]" : "border-[#d9cfbf] bg-white text-[#534a3d] hover:bg-[#efe8db]"}`}>
                    Remove Activity Preference
                  </button>
                </div>
              </article>
            ) : null}

            <section className="space-y-6">
              {topRecommendations.map((recommendation, index) => renderTopRecommendation(recommendation, index))}
            </section>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <div className="h-px w-full bg-[linear-gradient(90deg,transparent,#d9cfbf,transparent)]" />
                <button
                  type="button"
                  onClick={() => setShowMoreCommunities((current) => !current)}
                  className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]"
                >
                  {showMoreCommunities ? "Hide additional communities" : "Show more communities"}
                </button>

                {showMoreCommunities ? (
                  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {remainingRecommendations.map((recommendation, index) => renderCompactCard(recommendation, index + TOP_RECOMMENDATION_COUNT))}
                  </section>
                ) : null}
              </div>
            ) : null}

            {compareFacilityIds.length > 0 ? (
              <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Compare tray</p>
                <p className="mt-2 text-sm text-[#4a6076]">Selected facilities are staged locally for future comparison. This does not change ranking.</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {compareFacilityIds.map((id) => {
                    const item = visibleRecommendations.find((recommendation) => recommendation.facility.id === id);
                    return (
                      <span key={`compare-${id}`} className="rounded-full border border-[#cddce5] bg-white px-3 py-1 text-xs font-semibold text-[#24425e]">
                        {item?.facility.name || `Facility ${id}`}
                      </span>
                    );
                  })}
                </div>
              </section>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">{isLoading ? "Loading communities..." : apiLoadError ? "Authoritative API unavailable" : hasVisibleRecommendations ? "End of recommendations" : "No communities available"}</div>
      </section>
    </main>
  );
}
