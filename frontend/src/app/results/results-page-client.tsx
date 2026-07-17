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

function verificationStateStyle(state: string): string {
  if (state === "YES") return "border-[#bcd9c0] bg-[#eef8f1] text-[#2f6d3e]";
  if (state === "NO") return "border-[#e9c5bc] bg-[#fff3ef] text-[#8b4f3f]";
  if (state === "LIMITED") return "border-[#e3d2a6] bg-[#fff8e9] text-[#8b6a2f]";
  return "border-[#d7ddeb] bg-[#f2f6fb] text-[#4a647d]";
}

function verificationStateLabel(state: string): string {
  if (state === "YES") return "Confirmed";
  if (state === "NO") return "Not available";
  if (state === "LIMITED") return "Limited";
  return "Needs verification";
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

function tierSummary(report: RankedRecommendation["report"], tier: "MANDATORY" | "CRITICAL" | "IMPORTANT" | "OPTIONAL") {
  return report.audit.tierSummaries.find((item) => item.tier === tier);
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

function visualConfidenceLabel(score: number): string {
  if (score >= 80) return "High";
  if (score >= 55) return "Medium";
  return "Low";
}

function confidenceCopy(confidenceScore: number, unknownCount: number): { title: string; reason: string } {
  if (confidenceScore >= 80 && unknownCount <= 2) {
    return {
      title: "High confidence",
      reason: "Most important care requirements have been verified.",
    };
  }
  if (confidenceScore >= 55 && unknownCount <= 7) {
    return {
      title: "Medium confidence",
      reason: "Core needs appear aligned, but a few important items still need direct confirmation.",
    };
  }
  return {
    title: "Limited information available",
    reason: "Several important items still require confirmation from the community.",
  };
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
  const topRecommendations = useMemo(() => engineOutput.accepted.slice(0, TOP_RECOMMENDATION_COUNT), [engineOutput]);
  const topAuditRecommendations = useMemo(() => engineOutput.accepted.slice(0, TOP_AUDIT_COUNT), [engineOutput]);
  const remainingRecommendations = useMemo(() => engineOutput.accepted.slice(TOP_RECOMMENDATION_COUNT), [engineOutput]);
  const hasBestAvailableMatches = engineOutput.accepted.length > 0;
  const belowConfidenceThresholdMode = !engineOutput.qualityCheck.passed && hasBestAvailableMatches;

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
    const unknownCount = report.audit.verificationRequest.unknownCount;
    const verificationSent = Boolean(verificationSentByFacility[facility.id]);
    const anonymousPayload = report.audit.anonymousVerificationPayload;
    const latestAuditLog = [...verificationAuditLog].reverse().find((item) => item.facilityId === facility.id);
    const confidence = confidenceCopy(report.confidenceScore, unknownCount);
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
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#3e7a4d]">Match Confidence</p>
            <p className="mt-1 text-base font-semibold text-[#2f6d3e]">{confidence.title}</p>
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

          <section className="rounded-xl border border-[#d9e3ec] bg-[#f5fbff] p-4">
            <p className="font-semibold text-[#24425e]">Match confidence</p>
            <p className="mt-1 text-base font-semibold text-[#24425e]">{confidence.title}</p>
            <p className="mt-1 text-sm text-[#4b6176]">{confidence.reason}</p>
          </section>

          <section className="rounded-xl border border-[#d9e3ec] bg-white p-4">
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

          <details className="rounded-xl border border-[#e7ddcd] bg-[#fcfaf5] p-4">
            <summary className="cursor-pointer text-sm font-semibold text-[#2f2a24]">Technical Details</summary>
            <div className="mt-3 space-y-3 text-xs text-[#5f5548]">
              <p><strong>Formula:</strong> {report.audit.executedFormula}</p>
              <p><strong>Runtime score:</strong> {report.finalMatchScore}</p>
              <p><strong>Confidence math:</strong> {report.audit.confidence.missingDataImpact}</p>
              <p><strong>Sources:</strong> {report.intelligenceSourcesUsed.join(", ")}</p>
              <div>
                <p className="font-semibold">Checklist</p>
                <ul className="mt-1 space-y-1">
                  {report.audit.verificationChecklist.slice(0, 10).map((item) => (
                    <li key={`${facility.id}-tech-check-${item.label}`}>{item.label}: {verificationStateLabel(item.state)}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-semibold">Breakdown</p>
                <ul className="mt-1 space-y-1">
                  {report.scoreBreakdown.map((item) => (
                    <li key={`${facility.id}-tech-break-${item.name}`}>{item.name}: {item.score}/{item.maxScore}</li>
                  ))}
                </ul>
              </div>
              <p><strong>Runtime trace:</strong> {report.scoreTraceability.join(" | ")}</p>
            </div>
          </details>
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
          {belowConfidenceThresholdMode ? (
            <span className="rounded-full border border-[#e3cfa6] bg-[#fff6e7] px-3 py-1 text-xs font-semibold text-[#8a6330]">
              Below confidence threshold
            </span>
          ) : null}
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
    const report = recommendation.report;
    const unknownCount = report.audit.verificationRequest.unknownCount;
    const confidence = confidenceCopy(report.confidenceScore, unknownCount);
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
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${scoreBadgeStyle(recommendation.totalScore)}`}>
            {Math.round(recommendation.totalScore)}
          </span>
        </div>

        <div className="mt-3 rounded-xl border border-[#e7ddcd] bg-[#fcfaf5] p-3 text-sm text-[#4f473d]">
          <p className="font-semibold text-[#2f2a24]">Family summary</p>
          <p className="mt-2 text-sm text-[#5f5548]">{recommendation.whyThisFits}</p>
          <p className="mt-2 text-sm font-semibold text-[#24425e]">{confidence.title}</p>
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
            <p className="text-xl font-semibold">Additional refinement required before recommendations can be fully trusted.</p>
            <p className="mt-3 text-sm">Quality checks failed on:</p>
            <ul className="mx-auto mt-2 max-w-3xl space-y-1 text-left text-sm">
              {engineOutput.qualityCheck.failures.map((failure) => (
                <li key={failure} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#c18b7a]" aria-hidden="true" />
                  <span>{failure}</span>
                </li>
              ))}
            </ul>
            {hasBestAvailableMatches ? (
              <p className="mt-4 rounded-2xl border border-[#e3cfa6] bg-[#fff6e7] px-4 py-3 text-sm font-semibold text-[#8a6330]">
                Showing best available matches below confidence threshold.
              </p>
            ) : null}
          </section>
        ) : null}

        {!isLoading && engineOutput.qualityCheck.passed && engineOutput.accepted.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn&apos;t find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        {!isLoading && engineOutput.accepted.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Top person-first matches for this search</h2>
              <p className="mt-2 text-sm text-[#5c5347]">Ranking priority follows care, lifestyle, social, cultural, family, financial, clinical quality, then luxury amenities.</p>
              <p className="mt-1 text-sm text-[#5c5347]">Distance affects score only and never removes a community from visibility.</p>
            </article>

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
