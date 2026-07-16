import { QuestionnaireState } from "@/context/questionnaire-context";
import { SearchFacility } from "@/lib/api";
import { QUESTION_GRAPH } from "@/lib/questionnaire-graph";

type SignalRole = "score contribution" | "explanation contribution" | "rejection rationale" | "missing information analysis";

type PriorityScores = {
  careFit: number;
  lifestyleFit: number;
  socialFit: number;
  culturalFit: number;
  familyFit: number;
  financialFit: number;
  clinicalQuality: number;
  luxuryAmenities: number;
};

type Contribution = {
  label: string;
  value: number;
};

export type RankedRecommendation = {
  facility: SearchFacility;
  totalScore: number;
  priorityScores: PriorityScores;
  positives: string[];
  negatives: string[];
  solves: string[];
  doesNotSolve: string[];
  tradeoff: string;
  whyThisFits: string;
  rankReason: string;
  confidenceExplanation: string;
  missingInformation: string[];
  hardRejectionReasons: string[];
  contributionHighlights: Contribution[];
};

export type EngineQualityCheck = {
  passed: boolean;
  failures: string[];
  signalRoles: Array<{ key: string; role: SignalRole }>;
};

export type EngineOutput = {
  accepted: RankedRecommendation[];
  rejected: RankedRecommendation[];
  qualityCheck: EngineQualityCheck;
};

const PRIORITY_WEIGHTS = {
  careFit: 0.28,
  lifestyleFit: 0.18,
  socialFit: 0.15,
  culturalFit: 0.12,
  familyFit: 0.1,
  financialFit: 0.08,
  clinicalQuality: 0.06,
  luxuryAmenities: 0.03,
};

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}

function parseFirstNumber(value: string): number | null {
  const match = value.match(/\d+/);
  return match ? Number(match[0]) : null;
}

function parsePriceRange(range: string): { min: number; max: number } | null {
  const numbers = range.replace(/[^\d-]/g, "").split("-").map((value) => Number(value)).filter((value) => Number.isFinite(value));
  if (numbers.length < 2) return null;
  return { min: numbers[0], max: numbers[1] };
}

function joinedFacilityText(facility: SearchFacility): string {
  return [
    facility.name,
    facility.city || "",
    facility.state || "",
    facility.shortExplanation || "",
    ...facility.careTypes,
    ...facility.matchBadges,
    ...(facility.searchTokens || []),
  ]
    .join(" ")
    .toLowerCase();
}

function includesAny(text: string, terms: string[]): boolean {
  return terms.some((term) => text.includes(term.toLowerCase()));
}

function parseDistancePoints(state: QuestionnaireState): { points: number; note: string } {
  const fromDriveTime = parseFirstNumber(state.humanIntelligenceV2.distanceProfile.driveTimes.normal);
  const fromLegacy = parseFirstNumber(state.distanceFromFamily);
  const minutes = fromDriveTime ?? fromLegacy;
  if (minutes === null) {
    return {
      points: 0,
      note: "Distance data is incomplete, so distance impact is kept neutral.",
    };
  }

  if (minutes <= 15) return { points: 15, note: "Estimated travel time is in the 0-15 minute range." };
  if (minutes <= 30) return { points: 10, note: "Estimated travel time is in the 15-30 minute range." };
  if (minutes <= 45) return { points: 5, note: "Estimated travel time is in the 30-45 minute range." };
  if (minutes <= 60) return { points: -5, note: "Estimated travel time is in the 45-60 minute range." };
  if (minutes <= 90) return { points: -15, note: "Estimated travel time is in the 60-90 minute range." };
  return { points: -20, note: "Estimated travel time is above 90 minutes." };
}

function scoreCareFit(facility: SearchFacility, state: QuestionnaireState): number {
  const assistance = state.assistanceLevel;
  const memory = state.memoryStatus;
  const careText = facility.careTypes.join(" ").toLowerCase();

  if (assistance === "Fully independent") {
    let independentScore = 50;
    if (careText.includes("independent")) independentScore += 50;
    if (careText.includes("active adult")) independentScore += 40;
    if (careText.includes("assisted living")) independentScore -= 20;
    if (careText.includes("memory care")) independentScore -= 60;
    if (careText.includes("skilled nursing")) independentScore -= 80;
    return clamp(independentScore);
  }

  if (assistance === "Skilled nursing care") {
    let score = 35;
    if (careText.includes("skilled nursing")) score += 50;
    if (careText.includes("memory care")) score += 10;
    if (careText.includes("independent")) score -= 30;
    return clamp(score);
  }

  if (memory === "Significant memory issues") {
    let score = 30;
    if (careText.includes("memory care")) score += 55;
    if (careText.includes("skilled nursing")) score += 15;
    if (!careText.includes("memory")) score -= 35;
    return clamp(score);
  }

  let score = 55;
  if (careText.includes("assisted living")) score += 20;
  if (careText.includes("skilled nursing") && assistance !== "24/7 support required") score -= 10;
  return clamp(score);
}

function scoreLifestyleFit(facility: SearchFacility, state: QuestionnaireState): number {
  const text = joinedFacilityText(facility);
  const preferences = state.happinessPreferences;
  if (preferences.length === 0) return 50;

  const matched = preferences.filter((item) => includesAny(text, [item, item.replace(" and ", " ")]));
  return clamp(35 + (matched.length / preferences.length) * 65);
}

function scoreSocialFit(facility: SearchFacility, state: QuestionnaireState): number {
  const social = state.humanIntelligenceV2.socialProfile;
  const transition = state.humanIntelligenceV2.transitionRiskProfile;
  const text = joinedFacilityText(facility);
  let score = 45;

  if (social.socialInteractionFrequency === "Daily" || social.socialInteractionFrequency === "Several times weekly") {
    score += includesAny(text, ["community", "social", "group", "activities"]) ? 25 : -10;
  }

  if (social.newFriendsImportance === "High" || social.newFriendsImportance === "Very high") {
    score += includesAny(text, ["community", "activities", "social"]) ? 20 : -10;
  }

  if (transition.lonelinessRisk === "High" || transition.lonelinessRisk === "Very high") {
    score += includesAny(text, ["social", "community", "engagement"]) ? 15 : -10;
  }

  return clamp(score);
}

function scoreCulturalFit(facility: SearchFacility, state: QuestionnaireState): number {
  const text = joinedFacilityText(facility);
  const culture = state.humanIntelligenceV2.culturalProfile;
  const language = state.humanIntelligenceV2.languageProfile;
  const food = state.humanIntelligenceV2.foodProfile;
  let score = 45;

  const cultureTerms = [
    culture.culturalIdentity,
    ...culture.faithTraditions,
    ...culture.whatFeelsLikeHome,
    language.preferredSpokenLanguage,
    language.nativeLanguage,
    ...language.languagesUnderstood,
    ...food.dietaryPreferences,
  ].filter(Boolean);

  if (cultureTerms.length > 0) {
    const hits = cultureTerms.filter((term) => includesAny(text, [String(term)]));
    score += Math.min(40, hits.length * 8);
    score -= Math.max(0, Math.min(15, (cultureTerms.length - hits.length) * 2));
  }

  return clamp(score);
}

function scoreFamilyFit(state: QuestionnaireState): { score: number; detail: string } {
  const distance = parseDistancePoints(state);
  const visit = state.humanIntelligenceV2.distanceProfile.familyVisitExpectation || state.humanIntelligenceV2.familyProfile.visitFrequencyExpectation;
  let score = 55 + distance.points;

  if (visit === "Daily") score += 10;
  else if (visit === "Several times weekly") score += 6;
  else if (visit === "Monthly") score -= 6;

  return {
    score: clamp(score),
    detail: distance.note,
  };
}

function scoreFinancialFit(facility: SearchFacility, state: QuestionnaireState): number {
  const budget = state.budget || 7000;
  const parsed = parsePriceRange(facility.priceRange);
  if (!parsed) return 50;

  if (budget >= parsed.max) return 95;
  if (budget >= parsed.min) return 75;
  const overshoot = parsed.min - budget;
  return clamp(70 - overshoot / 120);
}

function scoreClinicalQuality(facility: SearchFacility): number {
  const parts = [facility.overall_rating, facility.quality_rating, facility.inspection_rating, facility.staffing_rating]
    .filter((value): value is number => typeof value === "number")
    .map((value) => value * 20);

  if (parts.length === 0) return clamp(facility.optimeScore);
  const avg = parts.reduce((sum, value) => sum + value, 0) / parts.length;
  return clamp(avg);
}

function scoreLuxuryAmenities(facility: SearchFacility): number {
  const text = joinedFacilityText(facility);
  let score = 35;
  if (includesAny(text, ["luxury", "premium", "resort"])) score += 35;
  if ((facility.beds || 0) < 100) score += 10;
  return clamp(score);
}

function collectHardRejectionReasons(facility: SearchFacility, state: QuestionnaireState): string[] {
  const reasons: string[] = [];
  const careText = facility.careTypes.join(" ").toLowerCase();
  const notes = state.notes.toLowerCase();

  const memoryRequired = state.memoryStatus === "Significant memory issues";
  if (memoryRequired && !careText.includes("memory care")) {
    reasons.push("Memory care is required but this community does not explicitly indicate memory care support.");
  }

  const skilledRequired = state.assistanceLevel === "Skilled nursing care";
  if (skilledRequired && !careText.includes("skilled nursing")) {
    reasons.push("Skilled nursing is required but this community does not explicitly indicate skilled nursing support.");
  }

  const budgetStrict = notes.includes("strict budget") || notes.includes("hard budget") || notes.includes("must stay under") || notes.includes("תקציב קשיח");
  if (budgetStrict) {
    const parsed = parsePriceRange(facility.priceRange);
    if (parsed && parsed.min > (state.budget || 0)) {
      reasons.push("Strict budget requirement is not met.");
    }
  }

  const wheelchairRequired = notes.includes("wheelchair") || notes.includes("accessible") || notes.includes("נגישות") || notes.includes("כיסא גלגלים");
  if (wheelchairRequired) {
    const text = joinedFacilityText(facility);
    if (!includesAny(text, ["wheelchair", "accessible", "accessibility"])) {
      reasons.push("Wheelchair accessibility is marked as required but is not confirmed for this community.");
    }
  }

  return reasons;
}

function flattenAnsweredSignals(input: unknown, prefix = ""): Array<{ key: string; value: string }> {
  if (input === null || input === undefined) return [];

  if (typeof input === "string") {
    const trimmed = input.trim();
    return trimmed ? [{ key: prefix, value: trimmed }] : [];
  }

  if (typeof input === "number" || typeof input === "boolean") {
    return [{ key: prefix, value: String(input) }];
  }

  if (Array.isArray(input)) {
    if (input.length === 0) return [];
    return [{ key: prefix, value: input.map((item) => String(item)).join(", ") }];
  }

  if (typeof input === "object") {
    return Object.entries(input as Record<string, unknown>).flatMap(([key, value]) => {
      const next = prefix ? `${prefix}.${key}` : key;
      return flattenAnsweredSignals(value, next);
    });
  }

  return [];
}

function roleForSignalKey(key: string): SignalRole {
  const scoreSignals = [
    "assistanceLevel",
    "memoryStatus",
    "happinessPreferences",
    "budget",
    "humanIntelligenceV2.socialProfile",
    "humanIntelligenceV2.culturalProfile",
    "humanIntelligenceV2.languageProfile",
    "humanIntelligenceV2.foodProfile",
    "humanIntelligenceV2.distanceProfile",
    "humanIntelligenceV2.familyProfile",
  ];

  if (scoreSignals.some((prefix) => key.startsWith(prefix))) {
    return "score contribution";
  }

  if (key.startsWith("notes")) {
    return "rejection rationale";
  }

  if (key.startsWith("relationship") || key.startsWith("ageGroup")) {
    return "explanation contribution";
  }

  return "missing information analysis";
}

function buildPersonalWhy(facility: SearchFacility, state: QuestionnaireState): string {
  const who = state.relationship ? state.relationship.toLowerCase() : "your loved one";
  const livedAlone = state.humanIntelligenceV2.socialProfile.livingAloneDuration;
  const socialNeed = state.humanIntelligenceV2.socialProfile.socialInteractionFrequency;
  const topActivity = state.happinessPreferences[0];

  const clauses: string[] = [];
  if (livedAlone) clauses.push(`has lived alone for ${livedAlone.toLowerCase()}`);
  if (socialNeed) clauses.push(`prefers ${socialNeed.toLowerCase()} social interaction`);
  if (topActivity) clauses.push(`values ${topActivity.toLowerCase()}`);

  const context = clauses.length > 0 ? clauses.join(" and ") : "has specific personal priorities";
  return `Because ${who} ${context}, ${facility.name} is positioned to support daily routine fit rather than only clinical rankings.`;
}

function buildSolves(state: QuestionnaireState, facility: SearchFacility): string[] {
  const solves: string[] = [];
  if (state.humanIntelligenceV2.transitionRiskProfile.lonelinessRisk) solves.push("Loneliness risk with stronger social engagement structure");
  if (state.assistanceLevel) solves.push(`Care support aligned to ${state.assistanceLevel.toLowerCase()} needs`);
  if (state.humanIntelligenceV2.familyProfile.visitFrequencyExpectation || state.humanIntelligenceV2.distanceProfile.familyVisitExpectation) {
    solves.push("Family visit rhythm and practical access planning");
  }
  if (state.humanIntelligenceV2.culturalProfile.religionImportance !== "Not important") solves.push("Religious and cultural continuity");
  if (facility.careTypes.some((care) => care.toLowerCase().includes("memory"))) solves.push("Cognitive support readiness");
  return solves.slice(0, 4);
}

function buildNotSolved(state: QuestionnaireState, facility: SearchFacility): string[] {
  const notSolved: string[] = [];
  const text = joinedFacilityText(facility);

  if (state.happinessPreferences.includes("Movies") && !includesAny(text, ["movie", "cinema"])) {
    notSolved.push("No clear movie or cinema programming signal");
  }

  if (state.happinessPreferences.includes("Outdoor activities") && !includesAny(text, ["outdoor", "garden", "walking"])) {
    notSolved.push("Limited evidence for outdoor activity programming");
  }

  if (state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage && !includesAny(text, [state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage])) {
    notSolved.push("Preferred language support is not explicitly confirmed");
  }

  if (state.humanIntelligenceV2.culturalProfile.faithTraditions.length > 0 && !state.humanIntelligenceV2.culturalProfile.faithTraditions.some((faith) => includesAny(text, [faith]))) {
    notSolved.push("Faith-specific programming is not explicitly confirmed");
  }

  if (notSolved.length === 0) {
    notSolved.push("Some lifestyle details still need direct confirmation with the community.");
  }

  return notSolved.slice(0, 3);
}

function buildTradeoff(priorityScores: PriorityScores): string {
  if (priorityScores.clinicalQuality >= 80 && priorityScores.careFit < 55) {
    return "Provides strong clinical quality, but care profile may be heavier than the current personal need.";
  }

  if (priorityScores.culturalFit >= 75 && priorityScores.financialFit < 55) {
    return "Cultural alignment is strong, but monthly cost fit may require budget tradeoffs.";
  }

  if (priorityScores.familyFit < 45) {
    return "This match offers stronger person-fit dimensions, but family travel burden appears higher.";
  }

  return "Balanced option with moderate tradeoffs across cost, care intensity, and social fit.";
}

function buildMissingInformation(state: QuestionnaireState, signalRoles: Array<{ key: string; role: SignalRole }>): string[] {
  const missing: string[] = [];

  const language = state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage;
  if (!language) missing.push("Tell us preferred spoken language to improve cultural matching precision.");

  const cultureIdentity = state.humanIntelligenceV2.culturalProfile.culturalIdentity;
  if (!cultureIdentity) missing.push("Add cultural identity priorities to improve community-level fit signals.");

  const driveTime = state.humanIntelligenceV2.distanceProfile.driveTimes.normal;
  if (!driveTime) missing.push("Add expected normal drive time so distance impact can be personalized.");

  const unmetSignals = signalRoles.filter((signal) => signal.role === "missing information analysis").slice(0, 2);
  unmetSignals.forEach((signal) => {
    missing.push(`Signal ${signal.key} is captured but needs more facility metadata for direct matching.`);
  });

  return missing.slice(0, 4);
}

function summarizeContributions(scores: PriorityScores): Contribution[] {
  const weighted = [
    { label: "Care fit", value: scores.careFit * PRIORITY_WEIGHTS.careFit },
    { label: "Lifestyle fit", value: scores.lifestyleFit * PRIORITY_WEIGHTS.lifestyleFit },
    { label: "Social fit", value: scores.socialFit * PRIORITY_WEIGHTS.socialFit },
    { label: "Cultural fit", value: scores.culturalFit * PRIORITY_WEIGHTS.culturalFit },
    { label: "Family fit", value: scores.familyFit * PRIORITY_WEIGHTS.familyFit },
    { label: "Financial fit", value: scores.financialFit * PRIORITY_WEIGHTS.financialFit },
    { label: "Clinical quality", value: scores.clinicalQuality * PRIORITY_WEIGHTS.clinicalQuality },
    { label: "Luxury amenities", value: scores.luxuryAmenities * PRIORITY_WEIGHTS.luxuryAmenities },
  ];

  return weighted.sort((a, b) => b.value - a.value);
}

function buildQualityCheck(
  accepted: RankedRecommendation[],
  signalRoles: Array<{ key: string; role: SignalRole }>,
): EngineQualityCheck {
  const failures: string[] = [];

  const duplicateWrites = QUESTION_GRAPH
    .reduce<Record<string, number>>((acc, node) => {
      acc[node.writes_to] = (acc[node.writes_to] || 0) + 1;
      return acc;
    }, {});
  if (Object.values(duplicateWrites).some((count) => count > 1)) {
    failures.push("Duplicate question concepts detected in questionnaire graph.");
  }

  if (signalRoles.length === 0) {
    failures.push("No user answers were captured for scoring.");
  }

  if (signalRoles.some((signal) => !signal.role)) {
    failures.push("At least one answer is not mapped to score, explanation, rejection, or missing information analysis.");
  }

  if (accepted.length === 0) {
    failures.push("No recommendations remained after hard requirement checks.");
  }

  if (accepted.length > 0) {
    const top = accepted[0];
    if (top.priorityScores.careFit < 30) {
      failures.push("Top recommendation does not sufficiently match care-level needs.");
    }

    if (!accepted.some((item) => item.tradeoff.length > 0)) {
      failures.push("At least one tradeoff must be shown.");
    }

    if (!accepted.some((item) => item.doesNotSolve.length > 0)) {
      failures.push("At least one weakness must be shown.");
    }

    if (!accepted.some((item) => item.whyThisFits.toLowerCase().includes("because"))) {
      failures.push("Personal explanation is too generic.");
    }

    if (accepted.some((item) => item.hardRejectionReasons.some((reason) => reason.toLowerCase().includes("distance")))) {
      failures.push("Distance is incorrectly used as a hard rejection rule.");
    }
  }

  return {
    passed: failures.length === 0,
    failures,
    signalRoles,
  };
}

export function runOptimeV2Engine(facilities: SearchFacility[], state: QuestionnaireState): EngineOutput {
  const answeredSignals = flattenAnsweredSignals(state);
  const signalRoles = answeredSignals.map((signal) => ({
    key: signal.key,
    role: roleForSignalKey(signal.key),
  }));

  const recommendations = facilities.map((facility) => {
    const careFit = scoreCareFit(facility, state);
    const lifestyleFit = scoreLifestyleFit(facility, state);
    const socialFit = scoreSocialFit(facility, state);
    const culturalFit = scoreCulturalFit(facility, state);
    const family = scoreFamilyFit(state);
    const financialFit = scoreFinancialFit(facility, state);
    const clinicalQuality = scoreClinicalQuality(facility);
    const luxuryAmenities = scoreLuxuryAmenities(facility);

    const priorityScores: PriorityScores = {
      careFit,
      lifestyleFit,
      socialFit,
      culturalFit,
      familyFit: family.score,
      financialFit,
      clinicalQuality,
      luxuryAmenities,
    };

    const totalScore = clamp(
      priorityScores.careFit * PRIORITY_WEIGHTS.careFit +
        priorityScores.lifestyleFit * PRIORITY_WEIGHTS.lifestyleFit +
        priorityScores.socialFit * PRIORITY_WEIGHTS.socialFit +
        priorityScores.culturalFit * PRIORITY_WEIGHTS.culturalFit +
        priorityScores.familyFit * PRIORITY_WEIGHTS.familyFit +
        priorityScores.financialFit * PRIORITY_WEIGHTS.financialFit +
        priorityScores.clinicalQuality * PRIORITY_WEIGHTS.clinicalQuality +
        priorityScores.luxuryAmenities * PRIORITY_WEIGHTS.luxuryAmenities,
    );

    const hardRejectionReasons = collectHardRejectionReasons(facility, state);
    const contributions = summarizeContributions(priorityScores);

    const positives = contributions.slice(0, 3).map((item) => `${item.label} contributed strongly.`);
    const negatives = contributions.slice(-3).reverse().map((item) => `${item.label} is relatively weak for this person.`);

    const confidenceMatched = signalRoles.filter((signal) => signal.role !== "missing information analysis").length;
    const confidenceTotal = signalRoles.length || 1;
    const confidencePercent = Math.round((confidenceMatched / confidenceTotal) * 100);

    return {
      facility,
      totalScore,
      priorityScores,
      positives,
      negatives,
      solves: buildSolves(state, facility),
      doesNotSolve: buildNotSolved(state, facility),
      tradeoff: buildTradeoff(priorityScores),
      whyThisFits: buildPersonalWhy(facility, state),
      rankReason: "",
      confidenceExplanation: `Confidence is ${confidencePercent >= 75 ? "high" : confidencePercent >= 55 ? "moderate" : "limited"} because ${confidenceMatched} of ${confidenceTotal} captured preferences are directly modeled.`,
      missingInformation: buildMissingInformation(state, signalRoles),
      hardRejectionReasons,
      contributionHighlights: contributions,
    };
  });

  const accepted = recommendations
    .filter((recommendation) => recommendation.hardRejectionReasons.length === 0)
    .sort((a, b) => b.totalScore - a.totalScore || b.priorityScores.careFit - a.priorityScores.careFit || b.priorityScores.socialFit - a.priorityScores.socialFit);

  const rejected = recommendations.filter((recommendation) => recommendation.hardRejectionReasons.length > 0);

  accepted.forEach((item, index) => {
    const above = accepted[index - 1];
    const below = accepted[index + 1];

    if (!above && below) {
      item.rankReason = `Ranked #1 because it leads in ${item.contributionHighlights[0].label.toLowerCase()} and beats #2 on person-first fit balance.`;
      return;
    }

    if (above) {
      item.rankReason = `Ranked #${index + 1} because it trails #${index} mainly on ${item.contributionHighlights[item.contributionHighlights.length - 1].label.toLowerCase()}, but stays competitive on ${item.contributionHighlights[0].label.toLowerCase()}.`;
      return;
    }

    if (!below) {
      item.rankReason = `Ranked #${index + 1} after higher-ranked options showed stronger person-fit coverage.`;
    }
  });

  const qualityCheck = buildQualityCheck(accepted, signalRoles);

  return {
    accepted,
    rejected,
    qualityCheck,
  };
}
