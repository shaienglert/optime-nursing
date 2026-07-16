"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";

const TOP_RECOMMENDATION_COUNT = 3;

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

type DistanceProfile = {
  familyVisitExpectation: string;
  familyGeographyModel: {
    involvedFamilyMembers: string;
    familyCenterOfGravity: string;
    multiLocationOptimization: string;
  };
  driveTimes: {
    normal: string;
    rushHour: string;
    emergency: string;
  };
  emotionalDistanceFactors: {
    emergencyAccessImportance: string;
    spontaneousVisitsImportance: string;
    grandchildrenVisitsImportance: string;
  };
  optimizationStrategy: string;
  scores: {
    family_distance_score: number | null;
    visit_probability_score: number | null;
    emergency_access_score: number | null;
    grandchildren_access_score: number | null;
    travel_burden_score: number | null;
    family_engagement_score: number | null;
  };
};

type RelaxationNotice = {
  preference: string;
  originalRequirement: string;
  relaxedRequirement: string;
  impactOnResultsCount: number;
};

type ConstraintClassification = "HARD_CONSTRAINT" | "SOFT_PREFERENCE";

type ConstraintAuditRow = {
  field: string;
  value: string;
  classification: ConstraintClassification;
  reason: string;
};

type RelaxationContext = {
  budget: number;
  care: string;
  memory: string;
  activity: string;
  distance: string;
  notes: string;
  profile: ReturnType<typeof useQuestionnaire>["state"]["humanIntelligenceV2"];
};

function sentenceCase(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeWords(value: string): string[] {
  return value
    .normalize("NFKC")
    .toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean);
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function midpointPrice(priceRange: string): number | null {
  const { low, high } = parsePriceRange(priceRange);
  if (!low || !high) return null;
  return (low + high) / 2;
}

function sizeBucket(beds?: number): "small" | "medium" | "large" | "unknown" {
  if (!beds) return "unknown";
  if (beds <= 55) return "small";
  if (beds <= 120) return "medium";
  return "large";
}

function hasBadgeMatch(facility: SearchFacility, expressions: RegExp[]): boolean {
  const haystack = [...facility.matchBadges, ...facility.careTypes].join(" ").toLowerCase();
  return expressions.some((expression) => expression.test(haystack));
}

function strictBudgetRequested(notes: string): boolean {
  return /(strict|hard|non[- ]negotiable|must|cannot exceed).*budget|budget.*(strict|hard|cap|cannot exceed|must)/i.test(notes);
}

function wheelchairMandatory(notes: string): boolean {
  if (!/wheelchair|accessible|accessibility|ada|mobility/i.test(notes)) {
    return false;
  }
  return /(must|required|non[- ]negotiable|strict|mandatory)/i.test(notes);
}

function buildConstraintAudit(context: RelaxationContext): ConstraintAuditRow[] {
  const profile = context.profile;
  const strictBudget = strictBudgetRequested(context.notes);
  const memoryNeedsMedical = context.memory.toLowerCase().includes("memory") || context.memory.toLowerCase().includes("significant");
  const wheelchairIsHard = wheelchairMandatory(context.notes);

  return [
    { field: "Care level", value: context.care || "Not specified", classification: "HARD_CONSTRAINT", reason: "Clinical care compatibility is mandatory." },
    { field: "State", value: "FL", classification: "HARD_CONSTRAINT", reason: "Current inventory scope is Florida communities." },
    { field: "Medical requirements", value: context.memory || "Not specified", classification: memoryNeedsMedical ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: memoryNeedsMedical ? "Memory-related clinical need requires compatible care type." : "No explicit medical requirement marked mandatory." },
    { field: "Wheelchair accessibility", value: wheelchairIsHard ? "Mandatory from notes" : "Not marked mandatory", classification: wheelchairIsHard ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: wheelchairIsHard ? "User notes marked accessibility as required." : "Defaults to soft unless explicitly mandatory." },
    { field: "Maximum budget", value: `$${context.budget.toLocaleString()}`, classification: strictBudget ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: strictBudget ? "User notes indicate strict budget cap." : "Budget treated as preference unless explicitly strict." },
    { field: "Activities", value: context.activity || "Not specified", classification: "SOFT_PREFERENCE", reason: "Lifestyle preference contributes to score." },
    { field: "Language", value: profile.languageProfile.preferredSpokenLanguage || "Not specified", classification: "SOFT_PREFERENCE", reason: "Language preference is weighted, not hard-filtered." },
    { field: "Religion", value: profile.culturalProfile.religionImportance || "Not specified", classification: "SOFT_PREFERENCE", reason: "Religious fit is weighted preference." },
    { field: "Community size", value: profile.personalityProfile.communitySizePreference || "Not specified", classification: "SOFT_PREFERENCE", reason: "Community size is a style preference." },
    { field: "Distance", value: context.distance || "Not specified", classification: "SOFT_PREFERENCE", reason: "Distance is weighted unless explicitly mandatory." },
    { field: "Food preferences", value: profile.foodProfile.dietaryPreferences.join(", ") || "Not specified", classification: "SOFT_PREFERENCE", reason: "Dietary fit contributes to scoring." },
    { field: "Cultural preferences", value: profile.culturalProfile.whatFeelsLikeHome.join(", ") || "Not specified", classification: "SOFT_PREFERENCE", reason: "Cultural comfort dimensions are scored preferences." },
  ];
}

function buildRelaxedRecommendations(
  facilities: SearchFacility[],
  context: RelaxationContext,
) : { recommendations: SearchFacility[]; relaxations: RelaxationNotice[]; constraintAudit: ConstraintAuditRow[] } {
  const baseFacilities = facilities.filter((facility) => facility.matching_confidence !== "LOW");
  const profile = context.profile;
  const notesLower = context.notes.toLowerCase();
  const auditRows = buildConstraintAudit(context);
  const strictBudget = strictBudgetRequested(context.notes);
  const requiresWheelchair = wheelchairMandatory(context.notes);
  const memoryNeedsMedical = context.memory.toLowerCase().includes("memory") || context.memory.toLowerCase().includes("significant");
  const languagePreference = profile.languageProfile.preferredSpokenLanguage;
  const sizePreference = profile.personalityProfile.communitySizePreference;
  const religionImportant = ["Important", "Very important"].includes(profile.culturalProfile.religionImportance);
  const wantsJewishSetting = profile.culturalProfile.israeliJewishCommunityPreference === "Yes" || notesLower.includes("jewish");
  const hardFiltered = baseFacilities.filter((facility) => {
    const price = midpointPrice(facility.priceRange);
    const budgetMatch = strictBudget ? (price === null ? true : price <= context.budget) : true;
    const careMatch = careAlignmentScore(facility, context.care) >= 80;
    const medicalMatch = memoryNeedsMedical
      ? facility.careTypes.some((item) => item.toLowerCase().includes("memory"))
      : true;
    const geographyMatch = facility.state === "FL";
    const wheelchairMatch = requiresWheelchair
      ? hasBadgeMatch(facility, [/wheelchair/i, /accessible/i, /accessibility/i, /ada/i, /mobility/i])
      : true;
    return medicalMatch && budgetMatch && careMatch && geographyMatch && wheelchairMatch;
  });

  const candidates = hardFiltered.length > 0 ? hardFiltered : baseFacilities;

  const softPreferences: Array<{
    key: string;
    originalRequirement: string;
    relaxedRequirement: string;
    enabled: boolean;
    weight: number;
    score: (facility: SearchFacility) => number;
  }> = [
    {
      key: "activities",
      originalRequirement: context.activity || "Not specified",
      relaxedRequirement: "Activity mix differs from preference",
      enabled: Boolean(context.activity),
      weight: 10,
      score: (facility) => {
        if (!context.activity) return 60;
        const normalized = context.activity.toLowerCase();
        if (normalized.includes("social")) return hasBadgeMatch(facility, [/social/i, /active/i]) ? 100 : 35;
        if (normalized.includes("religious")) return hasBadgeMatch(facility, [/religious/i, /faith/i, /synagogue/i, /jewish/i]) ? 100 : 30;
        if (normalized.includes("music")) return hasBadgeMatch(facility, [/active/i, /program/i]) ? 85 : 45;
        return 55;
      },
    },
    {
      key: "language",
      originalRequirement: languagePreference || "Not specified",
      relaxedRequirement: "Language support may be partial",
      enabled: Boolean(languagePreference && languagePreference !== "English"),
      weight: 12,
      score: (facility) => {
        if (!languagePreference || languagePreference === "English") return 60;
        return hasBadgeMatch(facility, [new RegExp(languagePreference, "i")]) ? 100 : 30;
      },
    },
    {
      key: "religion",
      originalRequirement: wantsJewishSetting ? "Jewish/faith-centered" : profile.culturalProfile.religionImportance || "Not specified",
      relaxedRequirement: "Faith alignment may be partial",
      enabled: Boolean(religionImportant || wantsJewishSetting),
      weight: 12,
      score: (facility) => {
        if (!religionImportant && !wantsJewishSetting) return 60;
        return hasBadgeMatch(facility, [/jewish/i, /religious/i, /faith/i, /synagogue/i, /kosher/i, /hebrew/i]) ? 100 : 25;
      },
    },
    {
      key: "community-size",
      originalRequirement: sizePreference || "Not specified",
      relaxedRequirement: "Community size differs from preference",
      enabled: Boolean(sizePreference && sizePreference !== "No preference"),
      weight: 8,
      score: (facility) => {
        if (!sizePreference || sizePreference === "No preference") return 60;
        const bucket = sizeBucket(facility.beds);
        if (sizePreference === "Small community") return bucket === "small" ? 100 : 35;
        if (sizePreference === "Medium community") return bucket === "medium" ? 100 : 45;
        if (sizePreference === "Large community") return bucket === "large" ? 100 : 45;
        return 55;
      },
    },
    {
      key: "distance",
      originalRequirement: context.distance || "Not specified",
      relaxedRequirement: "Distance preference may be partially met",
      enabled: Boolean(context.distance),
      weight: 9,
      score: (facility) => hasBadgeMatch(facility, [/close to family/i, /family/i, /distance/i]) ? 90 : 45,
    },
    {
      key: "food",
      originalRequirement: profile.foodProfile.dietaryPreferences.join(", ") || "Not specified",
      relaxedRequirement: "Dietary preference fit may be partial",
      enabled: profile.foodProfile.dietaryPreferences.length > 0,
      weight: 9,
      score: (facility) => {
        const foodTerms = profile.foodProfile.dietaryPreferences.map((item) => item.toLowerCase());
        if (foodTerms.length === 0) return 60;
        const matched = foodTerms.some((term) => hasBadgeMatch(facility, [new RegExp(term, "i")]));
        return matched ? 95 : 40;
      },
    },
    {
      key: "cultural",
      originalRequirement: profile.culturalProfile.whatFeelsLikeHome.join(", ") || "Not specified",
      relaxedRequirement: "Cultural comfort fit may be partial",
      enabled: profile.culturalProfile.whatFeelsLikeHome.length > 0,
      weight: 10,
      score: (facility) => {
        const terms = profile.culturalProfile.whatFeelsLikeHome.map((item) => item.toLowerCase());
        if (terms.length === 0) return 60;
        const matched = terms.some((term) => hasBadgeMatch(facility, [new RegExp(term.split(" ")[0], "i")]));
        return matched ? 92 : 42;
      },
    },
    {
      key: "budget",
      originalRequirement: `$${context.budget.toLocaleString()}`,
      relaxedRequirement: strictBudget ? "Strict budget preserved as hard constraint" : "Budget range may be exceeded",
      enabled: !strictBudget,
      weight: 12,
      score: (facility) => {
        const price = midpointPrice(facility.priceRange);
        if (price === null) return 60;
        if (price <= context.budget) return 100;
        if (price <= context.budget * 1.2) return 70;
        if (price <= context.budget * 1.35) return 50;
        return 20;
      },
    },
  ];

  const enabledSoft = softPreferences.filter((preference) => preference.enabled);
  const softWeightTotal = enabledSoft.reduce((acc, preference) => acc + preference.weight, 0) || 1;

  const ranked = [...candidates]
    .map((facility) => {
      const baseScore = facility.optimeScore;
      const softScore = enabledSoft.reduce((acc, preference) => acc + (preference.score(facility) * preference.weight), 0) / softWeightTotal;
      const combined = Math.round(baseScore * 0.7 + softScore * 0.3);
      return { facility, combined, softScore };
    })
    .sort((left, right) => right.combined - left.combined || right.softScore - left.softScore || left.facility.id - right.facility.id)
    .map((item) => item.facility);

  const recommendations = ranked.length > 0 ? ranked : baseFacilities;
  const topForAudit = recommendations.slice(0, Math.min(3, recommendations.length));
  const relaxations: RelaxationNotice[] = enabledSoft
    .map((preference) => {
      const satisfiedCount = topForAudit.filter((facility) => preference.score(facility) >= 70).length;
      return {
        preference: preference.key,
        originalRequirement: preference.originalRequirement,
        relaxedRequirement: preference.relaxedRequirement,
        impactOnResultsCount: satisfiedCount,
      };
    })
    .filter((item) => item.impactOnResultsCount < topForAudit.length);

  if (hardFiltered.length === 0 && baseFacilities.length > 0) {
    relaxations.unshift({
      preference: "hard-constraint-inventory",
      originalRequirement: "All hard constraints",
      relaxedRequirement: "No exact hard-constraint inventory found; returning closest available communities",
      impactOnResultsCount: recommendations.length,
    });
  }

  return { recommendations, relaxations, constraintAudit: auditRows };
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
    profileFacts.push(`family distance preference is ${distance.toLowerCase()}`);
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
  context: {
    relationship: string;
    age: string;
    care: string;
    activity: string;
    memory: string;
    budget: number;
    distance: string;
    notes: string;
    distanceProfile?: DistanceProfile;
  },
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
  const distanceProfile = context.distanceProfile;
  const distanceFlexible = context.distance.toLowerCase() === "anywhere" || distanceProfile?.optimizationStrategy === "Family visit maximization";
  const mentionsJewish = notesLower.includes("jewish");
  const mentionsHebrew = notesLower.includes("hebrew");
  const mentionsWidowed = notesLower.includes("widowed");
  const familyVisitExpectation = distanceProfile?.familyVisitExpectation || context.distance;
  const normalDriveTime = distanceProfile?.driveTimes.normal || "unknown";
  const rushHourDriveTime = distanceProfile?.driveTimes.rushHour || "unknown";
  const emergencyDriveTime = distanceProfile?.driveTimes.emergency || "unknown";
  const familyDistanceScore = distanceProfile?.scores.family_distance_score;
  const familyEngagementScore = distanceProfile?.scores.family_engagement_score;

  const fitsYou = [
    `${sentenceCase(context.relationship)} is looking for ${context.care.toLowerCase()} support, and ${facility.name} explicitly offers ${facility.careTypes.join(", ")}.`,
    `${sentenceCase(context.relationship)} values ${context.activity.toLowerCase()}, and the community profile highlights ${facility.matchBadges[0] ?? "relevant daily programming"}.`,
    `Family distance now includes ${familyVisitExpectation.toLowerCase()} with normal drive time ${normalDriveTime}, rush-hour drive time ${rushHourDriveTime}, and emergency access ${emergencyDriveTime}. That should be weighed against ${communitySize}, the current $${context.budget.toLocaleString()} monthly budget, and the stated family engagement priority${familyEngagementScore ? ` (${familyEngagementScore}/100)` : ""}${familyDistanceScore ? `, family distance score ${familyDistanceScore}/100` : ""}.`
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
    familyVisitExpectation,
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
  context: { budget: number; care: string; activity: string; memory: string; distance: string; distanceProfile?: DistanceProfile },
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
  const [isLoading, setIsLoading] = useState(true);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [compareIds, setCompareIds] = useState<number[]>([]);

  const selectedRelationship = searchParams.get("relationship") || state.relationship || "";
  const relationship = relationshipCopy(selectedRelationship);
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const activity = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const memory = searchParams.get("memory") || state.memoryStatus || "Not sure";
  const budget = Number(searchParams.get("budget") || state.budget || 7000);
  const distance = searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes";
  const notes = searchParams.get("notes") || state.notes || "";
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";

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

  const relaxedAvailability = useMemo(
    () =>
      buildRelaxedRecommendations(rankedFacilities, {
        budget,
        care,
        memory,
        activity,
        distance,
        notes,
        profile: state.humanIntelligenceV2,
      }),
    [rankedFacilities, budget, care, memory, activity, distance, notes, state.humanIntelligenceV2],
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

  const topRecommendations = useMemo(
    () => relaxedAvailability.recommendations.slice(0, TOP_RECOMMENDATION_COUNT),
    [relaxedAvailability.recommendations],
  );
  const remainingRecommendations = useMemo(
    () => relaxedAvailability.recommendations.slice(TOP_RECOMMENDATION_COUNT),
    [relaxedAvailability.recommendations],
  );

  const personalAdvisorSummary = useMemo(() => {
    const profile = state.humanIntelligenceV2;
    const relationshipNarrative = relationship === "You" || relationship === "You both" ? relationship : `your ${relationship.toLowerCase()}`;
    const lonelinessRisk = profile.transitionRiskProfile.lonelinessRisk || "unknown";
    const livingAlone = profile.socialProfile.livingAloneDuration || "unknown duration";
    const social = profile.socialProfile.socialInteractionFrequency || "unknown social rhythm";
    const language = profile.languageProfile.preferredSpokenLanguage || "English";
    const religion = profile.culturalProfile.religionImportance || "not specified";
    const hobbies = profile.socialProfile.hobbyParticipation.join(", ") || "not specified";
    const fear = profile.transitionRiskProfile.biggestFear || "not specified";
    const proximity = profile.distanceProfile.familyVisitExpectation || distance;
    const scoreCard = profile.scoringEngine.outputScores;
    const culturalSignals = profile.scoringEngine.recommendationImpacts.slice(0, 3).join(" ") || "No additional high-impact cultural signals were detected.";

    return `${relationshipNarrative} profile shows ${age} age range, living alone for ${livingAlone}, with social rhythm ${social}. Preferred language is ${language}, religion importance is ${religion}, hobbies include ${hobbies}, and family proximity requirement is ${proximity}. Biggest transition fear is ${fear}. Loneliness risk appears ${lonelinessRisk}. Cultural intelligence outputs: language match ${scoreCard.language_fit_score}, religious fit ${scoreCard.religious_fit_score}, cultural fit ${scoreCard.cultural_fit_score}, food fit ${scoreCard.food_fit_score}, family engagement ${scoreCard.family_engagement_score}, community style ${scoreCard.community_style_score}. Recommendation impacts: ${culturalSignals}`;
  }, [state.humanIntelligenceV2, relationship, age, distance]);

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

        {!isLoading && relaxedAvailability.recommendations.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn't find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        {!isLoading && relaxedAvailability.recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Recommendation Filter Audit</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Hard constraints vs soft preferences</h2>
              <p className="mt-2 text-sm text-[#5c5347]">Default rule applied: everything is SOFT_PREFERENCE unless explicitly mandatory.</p>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                  <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                    <tr>
                      <th className="px-4 py-3">Input field</th>
                      <th className="px-4 py-3">Value</th>
                      <th className="px-4 py-3">Classification</th>
                      <th className="px-4 py-3">Why</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#efe6d8]">
                    {relaxedAvailability.constraintAudit.map((row) => (
                      <tr key={`${row.field}-${row.classification}`}>
                        <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.field}</td>
                        <td className="px-4 py-3">{row.value}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.classification === "HARD_CONSTRAINT" ? "bg-[#fde7e2] text-[#a54c34]" : "bg-[#edf3ea] text-[#4c6f5b]"}`}>
                            {row.classification}
                          </span>
                        </td>
                        <td className="px-4 py-3">{row.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            {relaxedAvailability.relaxations.length > 0 ? (
              <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf2] p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Soft Preference Gaps</p>
                <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Best available communities returned; these preferences are not fully satisfied:</h2>
                <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                  <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                    <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                      <tr>
                        <th className="px-4 py-3">Preference</th>
                        <th className="px-4 py-3">Original requirement</th>
                        <th className="px-4 py-3">Not fully satisfied note</th>
                        <th className="px-4 py-3">Top-3 communities meeting this</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#efe6d8]">
                      {relaxedAvailability.relaxations.map((item) => (
                        <tr key={`${item.preference}-${item.originalRequirement}`}>
                          <td className="px-4 py-3 font-medium text-[#2f2a24]">{item.preference}</td>
                          <td className="px-4 py-3">{item.originalRequirement}</td>
                          <td className="px-4 py-3">{item.relaxedRequirement}</td>
                          <td className="px-4 py-3">{item.impactOnResultsCount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ) : null}

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Expert Advisor Mode</p>
              <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Personal explanation</h2>
              <p className="mt-3 text-sm leading-7 text-[#554c41]">{personalAdvisorSummary}</p>
            </article>

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.35)]">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Cultural Intelligence Scorecard</p>
              <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Belonging and adjustment signals</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                These scores come from direct answers only and support mixed identities and multicultural households.
              </p>

              <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                  <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                    <tr>
                      <th className="px-4 py-3">Output score</th>
                      <th className="px-4 py-3">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#efe6d8]">
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">language_match_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.language_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">religious_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.religious_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">cultural_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.cultural_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">food_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.food_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">family_engagement_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.family_engagement_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">community_style_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.community_style_score}</td></tr>
                  </tbody>
                </table>
              </div>

              {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-[#e7dbc6] bg-[#fffdfa] p-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Recommendation impact</p>
                  <ul className="mt-3 space-y-2 text-sm text-[#564d42]">
                    {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.map((impact) => (
                      <li key={impact}>• {impact}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {state.humanIntelligenceV2.scoringEngine.overallConfidence < state.humanIntelligenceV2.scoringEngine.confidenceThreshold ? (
                <p className="mt-4 text-sm text-[#8c5c40]">
                  Confidence is below threshold; additional question asked: {state.humanIntelligenceV2.scoringEngine.additionalQuestionAsked || "How often do you expect to visit?"}
                </p>
              ) : null}
            </article>

            {topRecommendations.map((facility, index) => {
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
                <div key={`${facility.id}-${facility.imageUrl}`} className="space-y-4">
                  <article className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Recommendation #{index + 1} explanation</p>
                    <p className="mt-3 text-sm text-[#5c5347]">Resident profile: {explanation.profileSummary}</p>
                    <ul className="mt-3 space-y-2 text-sm text-[#5c5347]">
                      {explanation.fitsYou.map((item) => (
                        <li key={`${facility.id}-${item}`}>• {item}</li>
                      ))}
                    </ul>
                  </article>

                  <article className="overflow-hidden rounded-3xl border border-[#e8ddcc] bg-white shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
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
              </div>
            </article>
                </div>
              );
            })}

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <button
                  type="button"
                  onClick={() => setShowMoreCommunities((current) => !current)}
                  className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]"
                >
                  {showMoreCommunities ? "Hide additional communities" : "Show more communities"}
                </button>

                {showMoreCommunities ? (
                  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {remainingRecommendations.map((facility) => (
                      <article key={`compact-${facility.id}`} className="rounded-2xl border border-[#e8ddcc] bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)]">
                        <h3 className="text-lg font-semibold text-[#2f2a24]">{facility.name}</h3>
                        <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                        <p className="mt-2 text-sm text-[#4f6f8f]">{facility.priceRange}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {facility.matchBadges.slice(0, 3).map((badge) => (
                            <span key={`compact-${facility.id}-${badge}`} className="rounded-full bg-[#edf3ea] px-3 py-1 text-xs font-medium text-[#4c6f5b]">
                              {badge}
                            </span>
                          ))}
                        </div>
                        <div className="mt-4 flex items-center justify-between">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${scoreBadgeStyle(facility.optimeScore)}`}>Score {facility.optimeScore}</span>
                          <Link href={`/facilities/${facility.id}`} className="text-sm font-semibold text-[#5f7f6b] hover:text-[#4f6f8f]">
                            View
                          </Link>
                        </div>
                      </article>
                    ))}
                  </section>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">{isLoading ? "Loading communities..." : "End of recommendations"}</div>
      </section>
    </main>
  );
}
