"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";
import { RankedRecommendation, runOptimeV2Engine } from "@/lib/optime-v2-engine";

const TOP_RECOMMENDATION_COUNT = 3;
const TOP_AUDIT_COUNT = 10;

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function scoreBadgeStyle(score: number): string {
  if (score >= 90) return "bg-[#5f8768] text-white";
  if (score >= 80) return "bg-[#dbe8d8] text-[#35523d]";
  if (score >= 70) return "bg-[#f0dfad] text-[#6c5322]";
  return "bg-[#f1caa4] text-[#7c4f23]";
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

function prettyCategoryLabel(name: string): string {
  switch (name) {
    case "Medical Fit":
      return "Care Fit";
    case "Family Proximity":
      return "Family Proximity";
    case "Cultural Fit":
      return "Culture";
    case "Clinical Quality":
      return "Clinical";
    case "Activities Fit":
      return "Activities";
    default:
      return name;
  }
}

function maxPointsForCategory(name: string): number {
  switch (name) {
    case "Medical Fit":
      return 28;
    case "Lifestyle Fit":
      return 18;
    case "Social Fit":
      return 15;
    case "Family Proximity":
      return 10;
    case "Cultural Fit":
      return 12;
    case "Clinical Quality":
      return 6;
    default:
      return 0;
  }
}

function pointsAwardedForCategory(name: string, points: number): number {
  if (name === "Medical Fit" || name === "Lifestyle Fit" || name === "Social Fit" || name === "Family Proximity" || name === "Cultural Fit" || name === "Clinical Quality") {
    return Math.round(points * 100) / 100;
  }
  return Math.round(points * 100) / 100;
}

function formatPoints(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatWeightPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function normalizedContribution(points: number, totalPoints: number): string {
  if (totalPoints <= 0) return "0.00%";
  return `${((points / totalPoints) * 100).toFixed(2)}%`;
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

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();

  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const activities = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const budget = Number(searchParams.get("budget") || state.budget || 7000);
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";
  const distanceProfile = state.humanIntelligenceV2.distanceProfile;
  const hasAddresses = hasRealAddressData(distanceProfile);
  const distance = hasAddresses ? (searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes") : "Not used";

  const filters = useMemo(
    () => [
      { label: `Age: ${age}`, disabled: false },
      { label: `Care: ${care}`, disabled: false },
      { label: `Activities: ${activities}`, disabled: false },
      { label: `Budget: $${budget.toLocaleString()}`, disabled: false },
      { label: `Distance: ${distance}`, disabled: !hasAddresses },
    ],
    [age, care, activities, budget, distance, hasAddresses],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      const data = await fetchSearchFacilities(textQuery);
      if (isMounted) {
        setFacilities(data);
        setIsLoading(false);
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [textQuery]);

  const engineOutput = useMemo(() => runOptimeV2Engine(facilities, state), [facilities, state]);
  const topRecommendations = useMemo(() => engineOutput.accepted.slice(0, TOP_RECOMMENDATION_COUNT), [engineOutput]);
  const topAuditRecommendations = useMemo(() => engineOutput.accepted.slice(0, TOP_AUDIT_COUNT), [engineOutput]);
  const remainingRecommendations = useMemo(() => engineOutput.accepted.slice(TOP_RECOMMENDATION_COUNT), [engineOutput]);

  const startNewSearch = () => {
    resetState();
    router.replace("/");
  };

  const renderFullCard = (recommendation: RankedRecommendation, index: number) => {
    const facility = recommendation.facility;
    const report = recommendation.report;

    return (
      <article key={facility.id} className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="mb-2 inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
            <h3 className="text-2xl font-semibold text-[#2f2a24]">{facility.name}</h3>
            <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
          </div>
          <div className={`rounded-2xl px-3 py-2 text-center ${scoreBadgeStyle(recommendation.totalScore)}`}>
            <p className="text-2xl font-bold leading-none">{report.finalMatchScore}</p>
            <p className="mt-1 text-xs font-semibold">Final match score</p>
            <p className="mt-1 text-[11px] font-medium opacity-90">Confidence {report.confidenceScore}/100</p>
            <p className="mt-1 text-[11px] font-medium opacity-90">Rank #{report.rankingPosition ?? index + 1} of {Math.max(engineOutput.accepted.length, 1)}</p>
          </div>
        </div>

        <div className="mt-4 space-y-3 text-sm text-[#4f473d]">
          <section>
            <p className="font-semibold text-[#2f2a24]">A. Final Score</p>
            <p className="mt-1">Final Match Score: {report.finalMatchScore}/100</p>
            <p>Confidence: {report.confidenceScore}/100</p>
            <p>Ranking: #{report.rankingPosition ?? index + 1} of {engineOutput.accepted.length} communities evaluated</p>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">B. Score Breakdown</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {report.scoreBreakdown.map((item) => (
                <div key={`${facility.id}-breakdown-${item.name}`} className="rounded-xl border border-[#e7ddcd] bg-[#fcfaf5] p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="font-semibold text-[#2f2a24]">{item.name}</p>
                    <p className="text-sm text-[#5f5548]">{item.score}/{item.maxScore}</p>
                  </div>
                  <p className="mt-1 text-xs text-[#6c655b]">{item.rationale}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.08em] text-[#7b735f]">Source: {item.source}</p>
                  <p className="mt-1 text-[11px] text-[#7b735f]">Traceable contribution: {item.weightedContribution.toFixed(2)}</p>
                </div>
              ))}
            </div>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">C. Positive Contributors</p>
            <ul className="mt-1 space-y-1">
              {report.positiveContributors.map((item) => (
                <li key={`${facility.id}-positive-${item.signal}`} className="rounded-lg border border-[#e6efe4] bg-[#f7fbf7] p-3 text-sm text-[#46574d]">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-[#2f2a24]">{item.signal}</span>
                    <span>{item.scoreContribution >= 0 ? "+" : ""}{item.scoreContribution}</span>
                  </div>
                  <p className="mt-1 text-xs text-[#6c655b]">source: {item.source} | weight: {item.weight}</p>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">D. Negative Contributors</p>
            <ul className="mt-1 space-y-1">
              {report.negativeContributors.map((item) => (
                <li key={`${facility.id}-negative-${item.signal}`} className="rounded-lg border border-[#eeddd5] bg-[#fff9f7] p-3 text-sm text-[#5c4d49]">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-[#2f2a24]">{item.signal}</span>
                    <span>{item.scoreContribution}</span>
                  </div>
                  <p className="mt-1 text-xs text-[#6c655b]">source: {item.source} | weight: {item.weight}</p>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">E. Intelligence Sources Used</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {report.intelligenceSourcesUsed.map((source) => (
                <span key={`${facility.id}-source-${source}`} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5f5548]">
                  {source}
                </span>
              ))}
            </div>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">F. Missing Intelligence</p>
            <ul className="mt-1 space-y-1">
              {report.missingIntelligence.map((item) => (
                <li key={`${facility.id}-missing-${item}`} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#8f8b7a]" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">G. Human Narrative Explanation</p>
            <p className="mt-1">{report.humanNarrativeExplanation}</p>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">H. Explain Ranking Position</p>
            <p className="mt-1">{report.rankingExplanation}</p>
          </section>

          <section>
            <p className="font-semibold text-[#2f2a24]">I. Score Traceability</p>
            <ul className="mt-1 space-y-1">
              {report.scoreTraceability.map((item) => (
                <li key={`${facility.id}-trace-${item}`} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#6f9a86]" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="mt-4 rounded-2xl border border-[#e7ddcd] bg-[#fdfbf6] p-4 text-sm text-[#5f5548]">
          <p className="font-semibold text-[#2f2a24]">Why this community fits</p>
          <p className="mt-1">{recommendation.whyThisFits}</p>
          <p className="mt-2">{recommendation.rankReason}</p>
          <p className="mt-2">{recommendation.tradeoff}</p>
        </div>

        <p className="mt-4 text-sm font-semibold text-[#4f6f8f]">{facility.priceRange}</p>

        <div className="mt-4 flex flex-wrap gap-2">
          {facility.careTypes.map((careType) => (
            <span key={careType} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5f5548]">
              {careType}
            </span>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {facility.matchBadges.map((badge) => (
            <span key={badge} className="rounded-full bg-[#edf3ea] px-3 py-1 text-xs font-medium text-[#4c6f5b]">
              {badge}
            </span>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Link href={`/facilities/${facility.id}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
            View details
          </Link>
          <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer" className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
            Map
          </a>
        </div>
      </article>
    );
  };

  const renderTopRecommendation = (recommendation: RankedRecommendation, index: number) => {
    const facility = recommendation.facility;

    return (
      <section key={`top-${facility.id}`} className="space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdf9] p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
        <div className="rounded-2xl border border-[#d9cfbf] bg-[linear-gradient(120deg,#f7efe0_0%,#fbf6ec_55%,#ffffff_100%)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Advisor Recommendation</p>
          <h3 className="mt-1 text-2xl font-semibold text-[#2f2a24]">{recommendationTitle(index)}</h3>
          <p className="mt-2 text-sm text-[#5f5548]">{highlightLabel(index)} for {relationship}, with a person-first ranking emphasis on care fit before facility prestige.</p>
        </div>

        <div className="rounded-2xl border border-[#e7ddcd] bg-white p-4">
          <p className="text-sm font-semibold text-[#2f2a24]">Personalized explanation</p>
          <p className="mt-1 text-sm text-[#5f5548]">{recommendation.whyThisFits}</p>
        </div>

        {renderFullCard(recommendation, index)}
      </section>
    );
  };

  const renderCompactCard = (recommendation: RankedRecommendation, index: number) => {
    const facility = recommendation.facility;
    const report = recommendation.report;
    const categoryRows = report.audit.categoryRows.filter((row) => ["Medical Fit", "Lifestyle Fit", "Social Fit", "Family Proximity", "Cultural Fit", "Activities Fit", "Clinical Quality"].includes(row.name));
    const totalPointsAwarded = categoryRows.reduce((sum, row) => sum + row.finalContribution, 0) + report.audit.bonuses.reduce((sum, bonus) => sum + (bonus.applied ? bonus.value : 0), 0) - report.audit.penalties.reduce((sum, penalty) => sum + (penalty.applied ? penalty.value : 0), 0);
    const maximumPossiblePoints = categoryRows.reduce((sum, row) => sum + maxPointsForCategory(row.name), 0);
    const normalizedScore = maximumPossiblePoints > 0 ? Math.round((totalPointsAwarded / maximumPossiblePoints) * 100) : report.finalMatchScore;
    const normalizedCategoryTotal = categoryRows.reduce((sum, row) => sum + row.finalContribution, 0);
    return (
      <article key={`compact-${facility.id}`} className="rounded-2xl border border-[#e8ddcc] bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#6a6257]">{recommendationTitle(index)}</p>
            <h3 className="mt-1 text-lg font-semibold text-[#2f2a24]">{facility.name}</h3>
            <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${scoreBadgeStyle(recommendation.totalScore)}`}>
            {Math.round(recommendation.totalScore)}
          </span>
        </div>

        <div className="mt-3 rounded-xl border border-[#e7ddcd] bg-[#fcfaf5] p-3 text-sm text-[#4f473d]">
          <p className="font-semibold text-[#2f2a24]">Score composition</p>
          <div className="mt-2 space-y-1 text-xs sm:text-sm">
            {categoryRows.map((row) => (
              <div key={`compact-audit-${facility.id}-${row.name}`} className="flex items-center justify-between gap-3 font-medium text-[#2f2a24]">
                <span>{prettyCategoryLabel(row.name)}</span>
                <span>{normalizedCategoryTotal > 0 ? normalizedContribution(row.finalContribution, normalizedCategoryTotal) : "0.00%"}</span>
              </div>
            ))}
            <div className="mt-2 border-t border-[#e7ddcd] pt-2">
              <div className="flex items-center justify-between gap-3 font-semibold text-[#2f2a24]">
                <span>Total Points Awarded</span>
                <span>{formatPoints(totalPointsAwarded)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Maximum Possible Points</span>
                <span>{formatPoints(maximumPossiblePoints)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Normalized Score</span>
                <span>{normalizedScore}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Penalties</span>
                <span>-{report.audit.penalties.reduce((sum, penalty) => sum + (penalty.applied ? penalty.value : 0), 0)}</span>
              </div>
            </div>
          </div>
        </div>

        <p className="mt-3 text-sm text-[#5f554a]">{recommendation.tradeoff}</p>
        <p className="mt-2 text-sm font-semibold text-[#4f6f8f]">{facility.priceRange}</p>

        <div className="mt-3 flex flex-wrap gap-2">
          {facility.matchBadges.slice(0, 3).map((badge) => (
            <span key={`compact-${facility.id}-${badge}`} className="rounded-full bg-[#edf3ea] px-3 py-1 text-xs font-medium text-[#4c6f5b]">
              {badge}
            </span>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <Link href={`/facilities/${facility.id}`} className="text-sm font-semibold text-[#5f7f6b] hover:text-[#4f6f8f]">
            View
          </Link>
          <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer" className="text-sm font-semibold text-[#5b5245] hover:text-[#2f2a24]">
            Map
          </a>
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
          <p className="mt-2 text-[#6b645a]">These communities best match what matters most to {relationship}.</p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={startNewSearch}
              className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]"
            >
              New search
            </button>
            <Link href="/" className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]">
              Back to home
            </Link>
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

        {!isLoading && !engineOutput.qualityCheck.passed ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">Additional refinement required before recommendations can be trusted.</p>
            <p className="mt-3 text-sm">Quality checks failed on:</p>
            <ul className="mx-auto mt-2 max-w-3xl space-y-1 text-left text-sm">
              {engineOutput.qualityCheck.failures.map((failure) => (
                <li key={failure} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#c18b7a]" aria-hidden="true" />
                  <span>{failure}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {!isLoading && engineOutput.qualityCheck.passed && engineOutput.accepted.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn't find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        {!isLoading && engineOutput.qualityCheck.passed && engineOutput.accepted.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Top person-first matches for this search</h2>
              <p className="mt-2 text-sm text-[#5c5347]">Ranking priority follows care, lifestyle, social, cultural, family, financial, clinical quality, then luxury amenities.</p>
              <p className="mt-1 text-sm text-[#5c5347]">Distance affects score only and never removes a community from visibility.</p>
            </article>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_14px_40px_-32px_rgba(69,58,43,0.3)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Generated Persona</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">{engineOutput.persona.personaType}</h2>
              <p className="mt-1 text-sm text-[#5c5347]">{engineOutput.persona.rankingStrategy}</p>

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-2xl border border-[#e7ddcd] bg-[#fcfaf5] p-4">
                  <p className="text-sm font-semibold text-[#2f2a24]">Active Weights</p>
                  <div className="mt-3 space-y-2 text-sm text-[#4f473d]">
                    {engineOutput.persona.activeWeights.map((item) => (
                      <div key={item.label} className="flex items-center justify-between gap-3">
                        <span>{item.label}</span>
                        <span className="font-semibold">{formatWeightPercent(item.weight)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-[#e7ddcd] bg-[#fcfaf5] p-4">
                    <p className="text-sm font-semibold text-[#2f2a24]">Why these weights were selected</p>
                    <ul className="mt-2 space-y-1 text-sm text-[#4f473d]">
                      {engineOutput.persona.whySelected.map((item) => (
                        <li key={item} className="flex items-start gap-2">
                          <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#6f9a86]" aria-hidden="true" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-[#e7ddcd] bg-[#fcfaf5] p-4">
                    <p className="text-sm font-semibold text-[#2f2a24]">What would change this ranking?</p>
                    <ul className="mt-2 space-y-1 text-sm text-[#4f473d]">
                      {engineOutput.persona.whatWouldChangeThisRanking.map((item) => (
                        <li key={item} className="flex items-start gap-2">
                          <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#c18b7a]" aria-hidden="true" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_14px_40px_-32px_rgba(69,58,43,0.3)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Live Recommendation Score Audit Report</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Top 10 communities with exact runtime score math</h2>
              <p className="mt-2 text-sm text-[#5c5347]">Each audit row below uses the current runtime scores from the ranking engine. Missing intelligence lowers confidence only and never changes the score.</p>

              <div className="mt-5 space-y-3">
                {topAuditRecommendations.map((recommendation, index) => {
                  const report = recommendation.report;

                  return (
                    <details key={`audit-${recommendation.facility.id}`} className="group rounded-2xl border border-[#e7ddcd] bg-[#fcfaf5] p-4">
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#6a6257]">Rank #{report.rankingPosition ?? index + 1}</p>
                          <h3 className="text-lg font-semibold text-[#2f2a24]">{recommendation.facility.name}</h3>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold text-[#2f2a24]">{report.finalMatchScore}/100</p>
                          <p className="text-xs text-[#6c655b]">Confidence {report.confidenceScore}/100</p>
                        </div>
                      </summary>

                      <div className="mt-4 space-y-5 text-sm text-[#4f473d]">
                        <section className="overflow-hidden rounded-xl border border-[#e7ddcd] bg-white">
                          <table className="w-full border-collapse text-left text-sm">
                            <thead className="bg-[#f7f3ea] text-xs uppercase tracking-[0.08em] text-[#6a6257]">
                              <tr>
                                <th className="px-3 py-2">Category</th>
                                <th className="px-3 py-2">Raw Score</th>
                                <th className="px-3 py-2">Weight</th>
                                <th className="px-3 py-2">Weighted Score</th>
                                <th className="px-3 py-2">Normalized Weight Contribution</th>
                                <th className="px-3 py-2">Final Contribution</th>
                              </tr>
                            </thead>
                            <tbody>
                              {report.audit.categoryRows.map((row) => (
                                <tr key={`${recommendation.facility.id}-${row.name}`} className="border-t border-[#efe7d9]">
                                  <td className="px-3 py-2 font-medium text-[#2f2a24]">{row.name}</td>
                                  <td className="px-3 py-2">{row.rawScore}</td>
                                  <td className="px-3 py-2">{row.weight.toFixed(2)}</td>
                                  <td className="px-3 py-2">{row.weightedScore.toFixed(2)}</td>
                                  <td className="px-3 py-2">{normalizedContribution(row.finalContribution, report.audit.categoryRows.reduce((sum, current) => sum + current.finalContribution, 0))}</td>
                                  <td className="px-3 py-2">{row.finalContribution.toFixed(2)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </section>

                        <section>
                          <p className="font-semibold text-[#2f2a24]">Bonuses</p>
                          <ul className="mt-2 space-y-1">
                            {report.audit.bonuses.map((item) => (
                              <li key={`${recommendation.facility.id}-bonus-${item.name}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#e6efe4] bg-[#f7fbf7] p-3">
                                <span>{item.name}</span>
                                <span>{item.applied ? `+${item.value}` : `+0`}</span>
                              </li>
                            ))}
                          </ul>
                        </section>

                        <section>
                          <p className="font-semibold text-[#2f2a24]">Penalties</p>
                          <ul className="mt-2 space-y-1">
                            {report.audit.penalties.map((item) => (
                              <li key={`${recommendation.facility.id}-penalty-${item.name}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#eeddd5] bg-[#fff9f7] p-3">
                                <span>{item.name}</span>
                                <span>{item.applied ? `-${item.value}` : `0`}</span>
                              </li>
                            ))}
                          </ul>
                        </section>

                        <section>
                          <p className="font-semibold text-[#2f2a24]">Data sources used</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {report.intelligenceSourcesUsed.map((source) => (
                              <span key={`${recommendation.facility.id}-audit-source-${source}`} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5f5548]">
                                {source}
                              </span>
                            ))}
                          </div>
                        </section>

                        <section>
                          <p className="font-semibold text-[#2f2a24]">Confidence calculation</p>
                          <p className="mt-1">Confidence score: {report.audit.confidence.confidenceScore}/100</p>
                          <p>Missing data impact: {report.audit.confidence.missingDataImpact}</p>
                          <p>Source coverage: {report.audit.confidence.sourceCoverage}</p>
                          <p>Last intelligence refresh: {report.audit.confidence.lastIntelligenceRefresh}</p>
                        </section>

                        <section>
                          <p className="font-semibold text-[#2f2a24]">Executed formula</p>
                          <p className="mt-1">{report.audit.executedFormula}</p>
                          <p className="mt-1">Final score = {report.audit.finalScore}/100</p>
                        </section>
                      </div>
                    </details>
                  );
                })}
              </div>
            </section>

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
          </section>
        ) : null}

        {engineOutput.rejected.length > 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-5 text-sm text-[#5f554a]">
            <p className="font-semibold">Rejected by hard requirements only</p>
            <ul className="mt-2 space-y-1">
              {engineOutput.rejected.slice(0, 5).map((item) => (
                <li key={`rejected-${item.facility.id}`}>{item.facility.name}: {item.hardRejectionReasons.join(" ")}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">{isLoading ? "Loading communities..." : "End of recommendations"}</div>
      </section>
    </main>
  );
}
