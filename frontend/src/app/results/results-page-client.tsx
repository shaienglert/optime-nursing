"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";
import { RankedRecommendation, runOptimeV2Engine } from "@/lib/optime-v2-engine";

const TOP_RECOMMENDATION_COUNT = 3;

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

function familyNarrative(recommendation: RankedRecommendation): string[] {
  const facility = recommendation.facility;
  const clinical = recommendation.report.audit.clinicalReasoning;
  const unknownCount = recommendation.report.audit.verificationRequest.unknownCount;

  const first = `We recommend ${facility.name} because it appears to match the requested level of daily support while staying within the selected budget range.`;
  const second = `Based on the current information, this community looks suitable for someone who needs ongoing care and values a socially engaging environment.`;
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
  const bullets: string[] = [];

  bullets.push("Meets the requested care level.");
  bullets.push("Fits the selected budget range.");
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

function normalizeTagLabel(value: string): string {
  return value.trim().toLowerCase();
}

function visualFitForFacility(facility: SearchFacility, state: ReturnType<typeof useQuestionnaire>["state"]): number {
  const tags = new Set(facility.visualIntelligence.lifestyleTags.map((tag) => normalizeTagLabel(tag.label)));
  let score = 52;

  const activityPrefs = new Set((state.happinessPreferences || []).map((item) => item.toLowerCase()));
  const environmentPrefs = new Set((state.humanIntelligenceV2.communityPreferenceProfile.preferredEnvironment || []).map((item) => item.toLowerCase()));
  const socialProfile = state.humanIntelligenceV2.socialProfile;
  const culturalProfile = state.humanIntelligenceV2.culturalProfile;

  if (activityPrefs.has("social activities") && tags.has("active social life")) score += 12;
  if (activityPrefs.has("outdoor activities") && tags.has("large gardens")) score += 12;
  if (activityPrefs.has("good food") && tags.has("cafe environment")) score += 10;
  if (activityPrefs.has("exercise and wellness") && tags.has("fitness center")) score += 10;
  if (environmentPrefs.has("quiet community") && tags.has("active social life")) score -= 8;
  if (environmentPrefs.has("quiet community") && tags.has("clinical setting")) score -= 16;
  if ((socialProfile.socialInteractionFrequency || "").toLowerCase() === "daily" && tags.has("active social life")) score += 8;
  if ((culturalProfile.faithTraditions || []).includes("Jewish") && tags.has("jewish services")) score += 10;
  if (["Important", "Very important", "High", "Very high"].includes(state.humanIntelligenceV2.independenceProfile.petOwnershipImportance) && tags.has("pet friendly")) score += 8;

  return Math.max(0, Math.min(100, Math.round(score)));
}

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();

  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [verificationSentByFacility, setVerificationSentByFacility] = useState<Record<number, boolean>>({});
  const [verificationAuditLog, setVerificationAuditLog] = useState<Array<{
    facilityId: number;
    timestamp: string;
    sharedFields: string[];
    consent: boolean;
  }>>([]);

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const futureCarePreference = searchParams.get("futureCarePreference") || state.futureCarePreference || "";
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
  const visibleRecommendations = useMemo(() => engineOutput.displayedRecommendations, [engineOutput]);
  const topRecommendations = useMemo(() => visibleRecommendations.slice(0, TOP_RECOMMENDATION_COUNT), [visibleRecommendations]);
  const remainingRecommendations = useMemo(() => visibleRecommendations.slice(TOP_RECOMMENDATION_COUNT), [visibleRecommendations]);
  const hasExactMatches = engineOutput.accepted.length > 0;
  const hasVisibleRecommendations = visibleRecommendations.length > 0;

  const startNewSearch = () => {
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
    const verificationSent = Boolean(verificationSentByFacility[facility.id]);
    const latestAuditLog = [...verificationAuditLog].reverse().find((item) => item.facilityId === facility.id);
    const narrativeParagraphs = familyNarrative(recommendation);
    const verifiedItems = report.audit.verificationChecklist.filter((item) => item.state === "YES");
    const unknownItems = report.audit.verificationChecklist.filter((item) => item.state === "UNKNOWN");
    const noItems = report.audit.verificationChecklist.filter((item) => item.state === "NO");
    const standout = stoodOutBullets(recommendation);

    return (
      <article key={facility.id} className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
        <div className="mb-4 overflow-hidden rounded-2xl border border-[#e3d8c8] bg-[#f7f2e8]">
          <img
            src={facility.visualIntelligence.heroImage.url}
            alt={`${facility.name} hero`}
            className="h-52 w-full object-cover"
            onError={(event) => {
              event.currentTarget.src = "/cms-placeholder.svg";
            }}
          />
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#e3d8c8] bg-white px-3 py-2 text-xs text-[#6b6257]">
            <span>Hero source: {facility.visualIntelligence.heroImage.source}</span>
            <span>Coverage {facility.visualIntelligence.visualCoverageScore}%</span>
          </div>
        </div>

        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="mb-2 inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
            <h3 className="text-2xl font-semibold text-[#2f2a24]">{facility.name}</h3>
            <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
          </div>
          <div className="rounded-2xl border border-[#d8e7dc] bg-[#f4fbf6] px-3 py-2 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#3e7a4d]">Recommendation Ready</p>
            <p className="mt-1 text-base font-semibold text-[#2f6d3e]">Yes</p>
          </div>
        </div>

        <div className="mt-4 space-y-3 text-sm text-[#4f473d]">
          <section className="rounded-xl border border-[#d6e4ef] bg-[#f5fbff] p-4">
            <p className="font-semibold text-[#24425e]">Why OPTIME recommends this community</p>
            <div className="mt-2 space-y-3 text-sm leading-6 text-[#3f5f79]">
              {narrativeParagraphs.map((paragraph) => (
                <p key={`${facility.id}-narrative-${paragraph}`}>{paragraph}</p>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-[#cde2d2] bg-[#f3fbf5] p-4">
            <p className="font-semibold text-[#2f6d3e]">Good matches</p>
            {verifiedItems.length > 0 ? (
              <ul className="mt-2 space-y-2 text-sm text-[#2f6d3e]">
                {verifiedItems.slice(0, 8).map((item) => (
                  <li key={`${facility.id}-verified-good-${item.label}`} className="rounded-lg border border-[#bcd9c0] bg-[#eef8f1] px-3 py-2">
                    ✔ {item.label}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-[#4f473d]">No items are verified yet.</p>
            )}
          </section>

          <section className="rounded-xl border border-[#f0d9b0] bg-[#fff8ea] p-4">
            <p className="font-semibold text-[#8a6a2f]">Still needs confirmation</p>
            {unknownItems.length > 0 ? (
              <ul className="mt-2 space-y-2 text-sm text-[#7a6847]">
                {unknownItems.slice(0, 8).map((item) => (
                  <li key={`${facility.id}-unknown-confirm-${item.label}`} className="rounded-lg border border-[#e3d2a6] bg-[#fff8e9] px-3 py-2">
                    ❓ {item.label}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-[#4f473d]">No open confirmation items.</p>
            )}
            <p className="mt-3 text-xs text-[#6f6148]">We have not found reliable confirmation yet. OPTIME can verify these directly with the community.</p>
          </section>

          {noItems.length > 0 ? (
            <section className="rounded-xl border border-[#f0c9bf] bg-[#fff3ef] p-4">
              <p className="font-semibold text-[#8b4f3f]">Not currently available</p>
              <ul className="mt-2 space-y-2 text-sm text-[#8b4f3f]">
                {noItems.slice(0, 6).map((item) => (
                  <li key={`${facility.id}-not-available-${item.label}`} className="rounded-lg border border-[#e9c5bc] bg-[#fff3ef] px-3 py-2">
                    ✖ {item.label}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-xl border border-[#d9e3ec] bg-white p-4">
            <p className="font-semibold text-[#2f2a24]">Why this community stood out</p>
            <ul className="mt-2 space-y-2 text-sm text-[#4f473d]">
              {standout.map((item) => (
                <li key={`${facility.id}-stoodout-${item}`} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#6f9a86]" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-[#d9e3ec] bg-white p-4">
            <p className="font-semibold text-[#24425e]">What should happen next</p>
            <button
              type="button"
              onClick={() => {
                setVerificationSentByFacility((current) => ({
                  ...current,
                  [facility.id]: true,
                }));
                setVerificationAuditLog((current) => [
                  ...current,
                  {
                    facilityId: facility.id,
                    timestamp: new Date().toISOString(),
                    sharedFields: [
                      "Care level",
                      "Functional needs",
                      "Dietary needs",
                      "Lifestyle interests",
                      "Move-in timeframe",
                      "Geographic area",
                    ],
                    consent: false,
                  },
                ]);
              }}
              className="w-full rounded-2xl bg-[#2f6d3e] px-5 py-4 text-base font-semibold text-white hover:bg-[#265a33]"
            >
              Verify remaining questions with this community
            </button>
            <p className="mt-2 text-xs text-[#5f5548]">No personal information will be shared. We will only ask about the unanswered items.</p>
            {verificationSent ? (
              <div className="mt-3 rounded-lg border border-[#c9dfcf] bg-[#f1faf3] p-2 text-xs text-[#2f6d3e]">
                <p className="font-semibold">Verification request sent anonymously.</p>
                {latestAuditLog ? (
                  <p className="mt-1 text-[#3f6a48]">Audit log: {latestAuditLog.timestamp}</p>
                ) : null}
              </div>
            ) : null}
          </section>
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
    const facility = recommendation.facility;
    return (
      <article key={`compact-${facility.id}`} className="rounded-2xl border border-[#e8ddcc] bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)]">
        <div className="mb-3 overflow-hidden rounded-xl border border-[#e3d8c8] bg-[#f7f2e8]">
          <img
            src={facility.visualIntelligence.heroImage.url}
            alt={`${facility.name} hero`}
            className="h-36 w-full object-cover"
            onError={(event) => {
              event.currentTarget.src = "/cms-placeholder.svg";
            }}
          />
        </div>

        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#6a6257]">{recommendationTitle(index)}</p>
            <h3 className="mt-1 text-lg font-semibold text-[#2f2a24]">{facility.name}</h3>
            <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
          </div>
        </div>

        <div className="mt-3 rounded-xl border border-[#e7ddcd] bg-[#fcfaf5] p-3 text-sm text-[#4f473d]">
          <p className="font-semibold text-[#2f2a24]">Family summary</p>
          <p className="mt-2 text-sm text-[#5f5548]">{recommendation.whyThisFits}</p>
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

        {!isLoading && !engineOutput.qualityCheck.passed ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">No exact match passed every hard requirement.</p>
            <p className="mt-3 text-sm">Showing the closest verified matches ranked by satisfied requirements. You can relax one or more requirements to refine the list.</p>
            {hasVisibleRecommendations ? (
              <p className="mt-4 rounded-2xl border border-[#e3cfa6] bg-[#fff6e7] px-4 py-3 text-sm font-semibold text-[#8a6330]">
                Closest verified matches are shown now with the highest satisfied-requirement score.
              </p>
            ) : null}
          </section>
        ) : null}

        {!isLoading && engineOutput.qualityCheck.passed && engineOutput.accepted.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn&apos;t find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        {!isLoading && hasVisibleRecommendations ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">{hasExactMatches ? "Top person-first matches for this search" : "Closest verified matches for this search"}</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                {hasExactMatches
                  ? "Each recommendation answers four simple questions: why it is a good fit, what we already know, what still needs confirmation, and what should happen next."
                  : "These recommendations are ranked by satisfied requirements and verified fit, with unsatisfied hard requirements called out clearly."}
              </p>
            </article>

            {!hasExactMatches ? (
              <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf0] p-6 text-sm text-[#5f554a]">
                <p className="font-semibold text-[#7a5a2f]">Hard requirements that remain unsatisfied</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div>Budget: {engineOutput.rejectionSummary.rejectedByBudget}</div>
                  <div>Care: {engineOutput.rejectionSummary.rejectedByCare}</div>
                  <div>Activities: {engineOutput.rejectionSummary.rejectedByActivities}</div>
                  <div>Future care: {engineOutput.rejectionSummary.rejectedByFutureCare}</div>
                  <div>Distance: {engineOutput.rejectionSummary.rejectedByDistance}</div>
                  <div>Verification: {engineOutput.rejectionSummary.rejectedByVerification}</div>
                  <div>Unknown: {engineOutput.rejectionSummary.rejectedByUnknown}</div>
                  <div className="sm:col-span-2 lg:col-span-3">Top rejection reason: {engineOutput.rejectionSummary.topRejectionReason}</div>
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
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">{isLoading ? "Loading communities..." : hasVisibleRecommendations ? "End of recommendations" : "No communities available"}</div>
      </section>
    </main>
  );
}
