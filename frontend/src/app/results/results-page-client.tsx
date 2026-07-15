"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";

const INITIAL_LOAD = 20;
const PAGE_SIZE = 10;

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

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function parsePriceRange(priceRange: string): { low: number; high: number } {
  const matches = priceRange.match(/\$([\d,]+)/g) || [];
  const amounts = matches
    .map((value) => Number(value.replace(/[$,]/g, "")))
    .filter((value) => Number.isFinite(value));

  if (amounts.length >= 2) {
    return { low: amounts[0], high: amounts[1] };
  }

  return { low: 0, high: 0 };
}

function careAlignmentScore(facility: SearchFacility, care: string): number {
  const normalizedCare = care.toLowerCase();
  const facilityCareTypes = facility.careTypes.map((item) => item.toLowerCase());

  if (normalizedCare.includes("skilled nursing") && facilityCareTypes.includes("skilled nursing")) return 100;
  if ((normalizedCare.includes("supervision") || normalizedCare.includes("medication") || normalizedCare.includes("bathing") || normalizedCare.includes("dressing")) && facilityCareTypes.includes("assisted living")) return 92;
  if (normalizedCare.includes("independent") && facilityCareTypes.includes("independent living")) return 90;
  if (normalizedCare.includes("memory") && facilityCareTypes.includes("memory care")) return 96;
  return 58;
}

type MatchFactor = {
  label: string;
  detail: string;
  score: number;
};

type ExplanationTableRow = {
  label: string;
  evidence: string;
  score: number | string;
};

type ExplanationListItem = {
  title: string;
  detail: string;
};

type PersonalizedExplanation = {
  profileSummary: string;
  fitsYou: string[];
  strengths: ExplanationListItem[];
  weaknesses: ExplanationListItem[];
  tradeoffs: ExplanationListItem[];
  questions: string[];
  strongMatches: string[];
  majorConcerns: string[];
  sourcesAnalyzed: string[];
  confidenceScore: number;
  matchingDimensions: ExplanationTableRow[];
  narrative: string;
};

function sentenceCase(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeWords(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function buildResidentProfileSummary(
  relationship: string,
  age: string,
  care: string,
  memory: string,
  activity: string,
  distance: string,
  notes: string,
): string {
  const noteWords = normalizeWords(notes);
  const profileFacts = [
    `${relationship.toLowerCase()} in the ${age} age range`,
    `${care.toLowerCase()} support needs`,
  ];

  if (!memory.toLowerCase().includes("no") && !memory.toLowerCase().includes("not sure")) {
    profileFacts.push(memory.toLowerCase());
  }

  if (activity) {
    profileFacts.push(`${activity.toLowerCase()} matters day to day`);
  }

  if (distance) {
    profileFacts.push(`family distance target is ${distance.toLowerCase()}`);
  }

  if (noteWords.includes("widowed")) {
    profileFacts.push("recently widowed")
  }

  if (noteWords.includes("jewish")) {
    profileFacts.push("prefers a Jewish environment");
  }

  if (noteWords.includes("hebrew")) {
    profileFacts.push("speaks Hebrew and English");
  }

  if (noteWords.includes("independent") || care.toLowerCase().includes("independent")) {
    profileFacts.push("wants to remain independent");
  }

  if (notes.trim()) {
    profileFacts.push(`additional family note: ${notes.trim()}`);
  }

  return profileFacts.join(", ");
}

function inferCommunitySizeLabel(beds?: number): string {
  if (!beds) return "unknown community size";
  if (beds <= 55) return `small ${beds}-bed community`;
  if (beds <= 120) return `mid-sized ${beds}-bed community`;
  return `large ${beds}-bed campus`;
}

function buildSourcesAnalyzed(facility: SearchFacility): string[] {
  const sources = [
    facility.cms_verified ? "CMS profile" : "",
    facility.license_verified ? "State license profile" : "",
    facility.website_verified ? "Official website" : "",
    facility.phone_verified ? "Phone verification" : "",
    ...(facility.scoreBreakdown?.flatMap((item) => item.dataSource) ?? []),
  ];

  return uniqueStrings(sources);
}

function buildConfidenceScore(facility: SearchFacility, sourcesAnalyzed: string[]): number {
  const sourceBoost = Math.min(18, sourcesAnalyzed.length * 3);
  const ratingBoost = ((facility.overall_rating ?? 0) + (facility.staffing_rating ?? 0) + (facility.inspection_rating ?? 0)) * 2;
  return Math.max(42, Math.min(98, Math.round(facility.verification_score * 0.55 + sourceBoost + ratingBoost)));
}

function buildPersonalizedExplanation(
  facility: SearchFacility,
  context: { relationship: string; age: string; care: string; activity: string; memory: string; budget: number; distance: string; notes: string },
): PersonalizedExplanation {
  const factors = buildMatchFactors(facility, context);
  const notesLower = context.notes.toLowerCase();
  const sourcesAnalyzed = buildSourcesAnalyzed(facility);
  const confidenceScore = buildConfidenceScore(facility, sourcesAnalyzed);
  const communitySize = inferCommunitySizeLabel(facility.beds);
  const hasMemoryCare = facility.careTypes.some((item) => item.toLowerCase().includes("memory"));
  const hasSkilledNursing = facility.careTypes.some((item) => item.toLowerCase().includes("skilled nursing"));
  const hasHebrewSupport = facility.matchBadges.some((badge) => badge.toLowerCase().includes("hebrew"));
  const isSocial = facility.matchBadges.some((badge) => badge.toLowerCase().includes("social") || badge.toLowerCase().includes("active"));
  const priceRange = parsePriceRange(facility.priceRange);
  const averagePrice = priceRange.low && priceRange.high ? Math.round((priceRange.low + priceRange.high) / 2) : 0;
  const overBudget = averagePrice > context.budget;
  const distanceFlexible = context.distance.toLowerCase() === "anywhere";
  const mentionsJewish = notesLower.includes("jewish");
  const mentionsHebrew = notesLower.includes("hebrew");
  const mentionsWidowed = notesLower.includes("widowed");

  const fitsYou = [
    `${sentenceCase(context.relationship)} is looking for ${context.care.toLowerCase()} support, and ${facility.name} explicitly offers ${facility.careTypes.join(", ")}.`,
    `${sentenceCase(context.relationship)} values ${context.activity.toLowerCase()}, and the community profile highlights ${facility.matchBadges[0] ?? "relevant daily programming"}.`,
    `Family distance matters because the stated target is ${context.distance.toLowerCase()}, so the placement conversation should weigh that against ${communitySize} and the current $${context.budget.toLocaleString()} monthly budget.`
  ];

  if (mentionsWidowed) {
    fitsYou.push(`${sentenceCase(context.relationship)} was described as recently widowed, so the social rhythm and daily interaction level matter more than a generic rating.`);
  }

  if (mentionsJewish || mentionsHebrew) {
    fitsYou.push(`${sentenceCase(context.relationship)} also has a cultural or language preference in the profile notes, so visible evidence like ${hasHebrewSupport ? "Hebrew-speaking staff" : "the absence of verified Hebrew-language support"} should be part of the tour discussion.`);
  }

  const strengths: ExplanationListItem[] = [
    {
      title: "Care alignment",
      detail: `${facility.careTypes.join(", ")} directly covers the requested ${context.care.toLowerCase()} support profile.`
    },
    {
      title: "Regulatory quality",
      detail: `The current ratings show overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, and inspection ${facility.inspection_rating ?? "n/a"}/5.`
    },
    {
      title: "Lifestyle signal",
      detail: `${communitySize} with badges such as ${facility.matchBadges.slice(0, 2).join(" and ")} gives a concrete view of how daily life may feel.`
    },
  ];

  if (hasHebrewSupport) {
    strengths.push({
      title: "Language support",
      detail: `The community profile explicitly surfaces Hebrew-speaking staff, which is directly relevant to the resident profile.`
    });
  }

  if (hasMemoryCare && !context.memory.toLowerCase().includes("no")) {
    strengths.push({
      title: "Memory support",
      detail: `Memory care appears in the care mix, which matters because the profile mentions ${context.memory.toLowerCase()}.`
    });
  }

  const weaknesses: ExplanationListItem[] = [];

  if (!hasMemoryCare && !context.memory.toLowerCase().includes("no") && !context.memory.toLowerCase().includes("not sure")) {
    weaknesses.push({
      title: "Limited memory support",
      detail: `The listed care types do not show memory care even though the profile mentions ${context.memory.toLowerCase()}.`
    });
  }

  if (!hasHebrewSupport && (mentionsHebrew || mentionsJewish)) {
    weaknesses.push({
      title: "Unverified cultural match",
      detail: `The current community evidence does not verify Hebrew-speaking staff or a Jewish program, even though the profile notes make that relevant.`
    });
  }

  if (facility.beds && facility.beds > 120) {
    weaknesses.push({
      title: "Large setting",
      detail: `${communitySize} may feel overwhelming if the resident does better in a more intimate environment.`
    });
  }

  if (overBudget) {
    weaknesses.push({
      title: "Budget pressure",
      detail: `The midpoint of ${facility.priceRange} is above the stated $${context.budget.toLocaleString()} monthly budget.`
    });
  }

  if (!weaknesses.length) {
    weaknesses.push({
      title: "Distance clarity needed",
      detail: `The current recommendation view does not verify actual drive time, so family visit practicality still needs confirmation during the tour.`
    });
  }

  const tradeoffs: ExplanationListItem[] = [
    {
      title: "Clinical support vs. familiarity",
      detail: `${hasSkilledNursing ? "Stronger medical support is visible in the care mix" : "The setting leans more residential than clinical"}, but the family still needs to confirm whether that matches the resident's day-to-day comfort.`
    },
    {
      title: "Lifestyle vs. cost",
      detail: `${isSocial ? "The community signals an active social rhythm" : "The lifestyle signal is quieter and less activity-led"}, while ${overBudget ? "pricing may stretch the budget" : "pricing appears more manageable against the stated budget"}.`
    },
    {
      title: "Verification depth",
      detail: `${confidenceScore >= 80 ? "Several verified sources are present" : "Verification is still moderate"}, so some family-specific fit details need live confirmation on the tour.`
    },
  ];

  const questions = uniqueStrings([
    mentionsHebrew ? "Are there Hebrew-speaking residents or staff available during the day and overnight?" : "How do new residents get introduced into daily life and activities during the first month?",
    context.activity.toLowerCase().includes("social") ? "How many residents typically participate in the main social activities each week?" : `How often are ${context.activity.toLowerCase()} options available each week?`,
    !context.memory.toLowerCase().includes("no") ? "How do staff handle changes in memory, confusion, or redirection during evenings?" : "How quickly does staff respond when a resident needs help during evenings or overnight?",
    overBudget ? "Which fees are fixed, and which services could increase the monthly cost over time?" : "What services are included in the current monthly price range, and which ones are billed separately?",
    "How long has the Executive Director and the nursing leadership team been in place?",
  ]).slice(0, 5);

  const strongMatches = uniqueStrings(factors.map((factor) => factor.label).concat(strengths.slice(0, 2).map((item) => item.title))).slice(0, 5);
  const majorConcerns = uniqueStrings(weaknesses.map((item) => item.title)).slice(0, 5);

  const matchingDimensions: ExplanationTableRow[] = [
    ...factors.map((factor) => ({ label: factor.label, evidence: factor.detail, score: factor.score })),
    { label: "Community scale", evidence: communitySize, score: facility.beds ?? "n/a" },
    { label: "Regulatory confidence", evidence: `Overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, inspection ${facility.inspection_rating ?? "n/a"}/5`, score: confidenceScore },
  ].slice(0, 5);

  const profileSummary = buildResidentProfileSummary(
    context.relationship,
    context.age,
    context.care,
    context.memory,
    context.activity,
    context.distance,
    context.notes,
  );

  const narrative = [
    `${sentenceCase(context.relationship)} is not looking for a generic top-rated community. The profile here is more specific: ${profileSummary}. That matters because ${facility.name} needs to be judged on whether its actual operating profile lines up with those lived priorities, not just on a single score. In practical terms, this community appears most aligned where it can directly support ${context.care.toLowerCase()} needs through ${facility.careTypes.join(", ")}, while also showing visible lifestyle signals such as ${facility.matchBadges.slice(0, 3).join(", ")}.`,
    `What stands out for this particular resident is the combination of care coverage and day-to-day environment. The current evidence shows regulatory performance at overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, and inspection ${facility.inspection_rating ?? "n/a"}/5. That gives the family a concrete starting point on safety and staffing. At the same time, ${communitySize} changes how the experience may actually feel. If ${context.activity.toLowerCase()} and regular engagement are important, the social and activity badges matter because they suggest how easy it may be for ${context.relationship.toLowerCase()} to settle into a routine instead of feeling passive or isolated.` ,
    `${mentionsWidowed ? `Because the profile notes mention that ${context.relationship.toLowerCase()} is recently widowed, the emotional side of transition should carry real weight during the visit. ` : ""}${mentionsJewish || mentionsHebrew ? `Because the family also noted a Jewish or Hebrew preference, the team should verify whether that support is truly part of daily life rather than a one-time marketing claim. ` : ""}The limitations are just as important. ${weaknesses[0].detail} ${weaknesses[1]?.detail ?? "There are also still fit questions that cannot be answered from the current data alone."} That means the tour should test the lived experience, not just confirm availability.` ,
    `The real tradeoff here is that ${facility.name} may offer ${hasSkilledNursing ? "stronger medical depth" : "a more residential feel"} while still requiring the family to check whether distance, leadership stability, culture, and pricing work in the resident's actual routine. This is why the recommendation needs to stay personalized: for ${context.relationship.toLowerCase()} in the ${context.age} range, with ${context.care.toLowerCase()} needs and ${context.activity.toLowerCase()} priorities, the question is not whether the community looks good in general. The question is whether this specific place can support a stable first year after move-in.`
  ].join(" ");

  return {
    profileSummary,
    fitsYou,
    strengths,
    weaknesses,
    tradeoffs,
    questions,
    strongMatches,
    majorConcerns,
    sourcesAnalyzed,
    confidenceScore,
    matchingDimensions,
    narrative,
  };
}

function buildMatchFactors(
  facility: SearchFacility,
  context: { budget: number; care: string; activity: string; memory: string; distance: string },
): MatchFactor[] {
  const priceRange = parsePriceRange(facility.priceRange);
  const priceTarget = priceRange.low > 0 && priceRange.high > 0 ? (priceRange.low + priceRange.high) / 2 : context.budget;
  const budgetGap = Math.abs(priceTarget - context.budget);
  const budgetScore = Math.max(40, 100 - Math.round(budgetGap / 180));

  const factors: MatchFactor[] = [
    {
      label: "Budget fit",
      detail: `${facility.priceRange} sits against your $${context.budget.toLocaleString()} budget`,
      score: budgetScore,
    },
    {
      label: "Staffing strength",
      detail: `Staffing rating is ${facility.staffing_rating ?? 0}/5`,
      score: (facility.staffing_rating ?? 0) * 20,
    },
    {
      label: "Activity alignment",
      detail: `${context.activity} preference lines up with ${facility.matchBadges[0] ?? "the community profile"}`,
      score: facility.matchBadges.some((badge) => badge.toLowerCase().includes("social") || badge.toLowerCase().includes("active")) ? 88 : 60,
    },
    {
      label: "Care level fit",
      detail: `${context.care} is supported by ${facility.careTypes.join(", ")}`,
      score: careAlignmentScore(facility, context.care),
    },
    {
      label: "Memory support",
      detail: `${context.memory} matches ${facility.matchBadges.includes("Memory support available") ? "available memory support" : "the current service profile"}`,
      score: context.memory.toLowerCase().includes("memory") ? (facility.matchBadges.includes("Memory support available") ? 94 : 55) : 50,
    },
    {
      label: "Community size",
      detail: `${facility.beds ?? 0} beds defines the community scale`,
      score: facility.beds ? Math.max(50, 100 - Math.abs((facility.beds ?? 0) - 80) / 2) : 40,
    },
    {
      label: "Language support",
      detail: facility.matchBadges.includes("Hebrew speaking staff") ? "Hebrew speaking staff surfaced in the profile" : "No language-specific claim surfaced",
      score: facility.matchBadges.includes("Hebrew speaking staff") ? 93 : 42,
    },
    {
      label: "Distance preference",
      detail: context.distance,
      score: context.distance.toLowerCase() === "anywhere" ? 48 : 72,
    },
  ];

  return factors
    .sort((left, right) => right.score - left.score || left.label.localeCompare(right.label))
    .slice(0, 3);
}

export function ResultsPageClient() {
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();
  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD);
  const [isLoading, setIsLoading] = useState(true);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const loaderRef = useRef<HTMLDivElement | null>(null);

  const selectedRelationship = searchParams.get("relationship") || state.relationship || "";
  const relationship = relationshipCopy(selectedRelationship);
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const activity = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const memory = searchParams.get("memory") || state.memoryStatus || "Not sure";
  const budget = Number(searchParams.get("budget") || state.budget || 7000);
  const distance = searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes";
  const notes = searchParams.get("notes") || state.notes || "";

  const [filters, setFilters] = useState<string[]>([
    `Age: ${age}`,
    `Care: ${care}`,
    `Activities: ${activity}`,
    `Budget: $${budget.toLocaleString()}`,
    `Distance: ${distance}`,
  ]);

  const rankedFacilities = useMemo(
    () =>
      [...facilities]
        .filter((facility) => facility.matching_confidence !== "LOW")
        .sort((left, right) => right.optimeScore - left.optimeScore || left.id - right.id),
    [facilities],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      const data = await fetchSearchFacilities();
      if (isMounted) {
        setFacilities(data);
        setVisibleCount(INITIAL_LOAD);
        setIsLoading(false);
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!loaderRef.current || isLoading) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((current) => Math.min(current + PAGE_SIZE, facilities.length));
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [facilities.length, isLoading]);

  const visibleFacilities = useMemo(() => rankedFacilities.slice(0, visibleCount), [rankedFacilities, visibleCount]);

  const removeFilter = (value: string) => {
    setFilters((current) => current.filter((item) => item !== value));
  };

  const toggleSaved = (id: number) => {
    setSavedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const toggleCompare = (id: number) => {
    setCompareIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const shareFacility = async (facility: SearchFacility) => {
    const message = `${facility.name} - OPTIME Score ${facility.optimeScore}`;
    try {
      await navigator.clipboard.writeText(message);
    } catch {
      // no-op fallback for restricted clipboard contexts
    }
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">These communities best match what matters most to {relationship}.</p>

          <div className="mt-5 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => removeFilter(filter)}
                className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-3 py-1 text-sm text-[#534a3d] hover:bg-[#efe8db]"
              >
                {filter} x
              </button>
            ))}
          </div>
        </header>

        {!isLoading && visibleFacilities.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn't find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          {visibleFacilities.map((facility, index) => (
            <article key={`${facility.id}-${facility.imageUrl}`} className="overflow-hidden rounded-3xl border border-[#e8ddcc] bg-white shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <div className="relative h-64 w-full">
                <Image src={facility.imageUrl} alt={facility.name} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 50vw" />
              </div>

              <div className="p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="mb-2 inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
                    <h2 className="text-2xl font-semibold text-[#2f2a24]">{facility.name}</h2>
                    <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                      {facility.matching_confidence === "HIGH" ? (
                        <p className="rounded-full bg-[#e8f3e7] px-3 py-1 text-[#46694c]">Verified Community</p>
                      ) : facility.matching_confidence === "MEDIUM" ? (
                        <p className="rounded-full bg-[#f6efd7] px-3 py-1 text-[#816a2d]">Name verified with minor variation</p>
                      ) : (
                        <p className="rounded-full bg-[#fde7e2] px-3 py-1 text-[#a54c34]">Community name could not be verified.</p>
                      )}
                    </div>
                  </div>
                  <div className={`rounded-2xl px-3 py-2 text-center ${scoreBadgeStyle(facility.optimeScore)}`}>
                    <p className="text-2xl font-bold leading-none">{facility.optimeScore}</p>
                    <p className="mt-1 text-xs font-semibold">{facility.matching_confidence}</p>
                  </div>
                </div>

                {(() => {
                  const explanation = buildPersonalizedExplanation(facility, {
                    relationship,
                    age,
                    care,
                    activity,
                    memory,
                    budget,
                    distance,
                    notes,
                  });

                  return (
                    <>
                      <div className="mt-4 rounded-2xl border border-[#e8dcc7] bg-[#fbf8f1] p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Why This Place Fits You</p>
                        <p className="mt-2 text-sm text-[#5c5347]">Resident profile: {explanation.profileSummary}</p>
                        <ul className="mt-3 space-y-2 text-sm text-[#5c5347]">
                          {explanation.fitsYou.map((item) => (
                            <li key={`${facility.id}-${item}`}>• {item}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="mt-4 overflow-hidden rounded-2xl border border-[#e7dbc6]">
                        <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Matching dimensions</div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                            <thead className="bg-white/80 text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                              <tr>
                                <th className="px-4 py-3">Dimension</th>
                                <th className="px-4 py-3">Evidence</th>
                                <th className="px-4 py-3">Score</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#efe6d8] bg-white">
                              {explanation.matchingDimensions.map((row) => (
                                <tr key={`${facility.id}-${row.label}`}>
                                  <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.label}</td>
                                  <td className="px-4 py-3">{row.evidence}</td>
                                  <td className="px-4 py-3">{row.score}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  );
                })()}

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
                      ✓ {badge}
                    </span>
                  ))}
                </div>

                <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <button type="button" onClick={() => toggleSaved(facility.id)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    {savedIds.includes(facility.id) ? "Saved" : "Save"}
                  </button>
                  <button type="button" onClick={() => toggleCompare(facility.id)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    {compareIds.includes(facility.id) ? "Compared" : "Compare"}
                  </button>
                  <button type="button" onClick={() => shareFacility(facility)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Share
                  </button>
                  <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer" className="rounded-full border border-[#dccfb9] px-3 py-2 text-center text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Map
                  </a>
                </div>

                <div className="mt-5">
                  <Link href={`/facilities/${facility.id}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                    View Details
                  </Link>
                </div>

                {(() => {
                  const explanation = buildPersonalizedExplanation(facility, {
                    relationship,
                    age,
                    care,
                    activity,
                    memory,
                    budget,
                    distance,
                    notes,
                  });

                  const renderRows = (rows: ExplanationListItem[]) => (
                    <div className="overflow-x-auto rounded-2xl border border-[#e7dbc6]">
                      <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                        <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                          <tr>
                            <th className="px-4 py-3">Dimension</th>
                            <th className="px-4 py-3">Explanation</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#efe6d8] bg-white">
                          {rows.map((row) => (
                            <tr key={`${facility.id}-${row.title}`}>
                              <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.title}</td>
                              <td className="px-4 py-3">{row.detail}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );

                  return (
                    <section className="mt-6 space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdfa] p-4 sm:p-5">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">What This Community Does Well For You</p>
                        <div className="mt-2">{renderRows(explanation.strengths)}</div>
                      </div>

                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">What This Community Does Not Solve</p>
                        <div className="mt-2">{renderRows(explanation.weaknesses)}</div>
                      </div>

                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f657f]">Tradeoffs</p>
                        <div className="mt-2">{renderRows(explanation.tradeoffs)}</div>
                      </div>

                      <div className="rounded-2xl border border-[#e7dbc6] bg-white p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Questions To Ask During The Tour</p>
                        <ul className="mt-3 space-y-2 text-sm text-[#564d42]">
                          {explanation.questions.map((question) => (
                            <li key={`${facility.id}-${question}`}>• {question}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="overflow-hidden rounded-2xl border border-[#e7dbc6]">
                        <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Confidence</div>
                        <div className="overflow-x-auto bg-white">
                          <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                            <tbody className="divide-y divide-[#efe6d8]">
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Match score</td>
                                <td className="px-4 py-3">{facility.optimeScore}</td>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Confidence score</td>
                                <td className="px-4 py-3">{explanation.confidenceScore}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Sources analyzed</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.sourcesAnalyzed.join(", ") || "Current recommendation data only"}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Strong matches</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.strongMatches.join(", ")}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Major concerns</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.majorConcerns.join(", ")}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-[#e7dbc6] bg-white p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Advisor Explanation</p>
                        <p className="mt-3 text-sm leading-7 text-[#554c41]">{explanation.narrative}</p>
                      </div>
                    </section>
                  );
                })()}
              </div>
            </article>
          ))}
        </section>

        <div ref={loaderRef} className="py-10 text-center text-sm text-[#6d655b]">
          {isLoading ? "Loading communities..." : visibleCount < facilities.length ? "Loading more results..." : "End of recommendations"}
        </div>
      </section>
    </main>
  );
}
