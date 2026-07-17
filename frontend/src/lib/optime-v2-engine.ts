import { QuestionnaireState } from "@/context/questionnaire-context";
import { SearchFacility } from "@/lib/api";
import { QUESTION_GRAPH } from "@/lib/questionnaire-graph";

type EngineRunMode = "production" | "simulation";

type EngineRunOptions = {
  mode?: EngineRunMode;
};

type SignalRole = "score contribution" | "explanation contribution" | "rejection rationale" | "missing information analysis";

type PersonaType =
  | "Independent Active Senior"
  | "Independent Social Senior"
  | "Independent Quiet Senior"
  | "Cultural Family Senior"
  | "Early Memory Support"
  | "Memory Care"
  | "Assisted Living"
  | "Skilled Nursing"
  | "Rehabilitation"
  | "High Clinical Complexity"
  | "Family-Centered Senior";

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

type WeightProfile = PriorityScores;

type PersonaProfile = {
  personaType: PersonaType;
  rankingStrategy: string;
  weights: WeightProfile;
  activeWeights: Array<{ label: string; weight: number }>;
  whySelected: string[];
  whatWouldChangeThisRanking: string[];
};

type Contribution = {
  label: string;
  value: number;
};

type MatchQualityTier = "MANDATORY" | "CRITICAL" | "IMPORTANT" | "OPTIONAL";

type MatchQualityCriterion = {
  name: string;
  tier: MatchQualityTier;
  score: number;
  matched: boolean;
  applicable: boolean;
  rationale: string;
  source: string;
};

type MatchQualityTierSummary = {
  tier: MatchQualityTier;
  matched: number;
  total: number;
  averageScore: number;
  mismatchPenalty: number;
};

type MatchQualityResult = {
  score: number;
  criteria: MatchQualityCriterion[];
  tierSummaries: MatchQualityTierSummary[];
  explanation: string;
};

type FutureCarePreferenceEvaluation = {
  preference: string;
  adjustment: number;
  score: number;
  explanation: string;
  source: string;
  contributorLabel: string;
  rejectionReasons: string[];
};

type ReportContributor = {
  signal: string;
  source: string;
  weight: number;
  scoreContribution: number;
};

type ReportBreakdownItem = {
  name: string;
  score: number;
  maxScore: number;
  source: string;
  rationale: string;
  weightedContribution: number;
};

type AuditCategoryRow = {
  name: string;
  rawScore: number;
  weight: number;
  weightedScore: number;
  finalContribution: number;
  source: string;
};

type AuditAdjustmentRow = {
  name: string;
  rawScore: number;
  value: number;
  source: string;
  applied: boolean;
};

type AuditConfidence = {
  confidenceScore: number;
  missingDataImpact: string;
  sourceCoverage: string;
  lastIntelligenceRefresh: string;
};

type AuditFormula = {
  executedFormula: string;
  finalScore: number;
  categoryRows: AuditCategoryRow[];
  bonuses: AuditAdjustmentRow[];
  penalties: AuditAdjustmentRow[];
  criteria: MatchQualityCriterion[];
  tierSummaries: MatchQualityTierSummary[];
  matchQualityExplanation: string;
  confidence: AuditConfidence;
};

export type IntelligenceScoringReport = {
  finalMatchScore: number;
  confidenceScore: number;
  rankingPosition: number | null;
  rankingExplanation: string;
  personaType: PersonaType;
  rankingStrategy: string;
  activeWeights: Array<{ label: string; weight: number }>;
  whyWeightsSelected: string[];
  whatWouldChangeThisRanking: string[];
  scoreBreakdown: ReportBreakdownItem[];
  positiveContributors: ReportContributor[];
  negativeContributors: ReportContributor[];
  intelligenceSourcesUsed: string[];
  missingIntelligence: string[];
  humanNarrativeExplanation: string;
  scoreTraceability: string[];
  audit: AuditFormula;
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
  report: IntelligenceScoringReport;
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
  persona: PersonaProfile;
};

const PERSONA_WEIGHT_PROFILES: Record<PersonaType, WeightProfile> = {
  "Independent Active Senior": {
    careFit: 0.14,
    lifestyleFit: 0.22,
    socialFit: 0.14,
    culturalFit: 0.06,
    familyFit: 0.08,
    financialFit: 0.12,
    clinicalQuality: 0.08,
    luxuryAmenities: 0.16,
  },
  "Independent Social Senior": {
    careFit: 0.12,
    lifestyleFit: 0.2,
    socialFit: 0.26,
    culturalFit: 0.06,
    familyFit: 0.1,
    financialFit: 0.1,
    clinicalQuality: 0.05,
    luxuryAmenities: 0.11,
  },
  "Independent Quiet Senior": {
    careFit: 0.15,
    lifestyleFit: 0.17,
    socialFit: 0.07,
    culturalFit: 0.08,
    familyFit: 0.12,
    financialFit: 0.12,
    clinicalQuality: 0.13,
    luxuryAmenities: 0.16,
  },
  "Cultural Family Senior": {
    careFit: 0.14,
    lifestyleFit: 0.08,
    socialFit: 0.12,
    culturalFit: 0.24,
    familyFit: 0.18,
    financialFit: 0.08,
    clinicalQuality: 0.06,
    luxuryAmenities: 0.1,
  },
  "Early Memory Support": {
    careFit: 0.28,
    lifestyleFit: 0.09,
    socialFit: 0.08,
    culturalFit: 0.05,
    familyFit: 0.14,
    financialFit: 0.07,
    clinicalQuality: 0.22,
    luxuryAmenities: 0.07,
  },
  "Memory Care": {
    careFit: 0.3,
    lifestyleFit: 0.05,
    socialFit: 0.05,
    culturalFit: 0.05,
    familyFit: 0.1,
    financialFit: 0.05,
    clinicalQuality: 0.25,
    luxuryAmenities: 0.15,
  },
  "Assisted Living": {
    careFit: 0.22,
    lifestyleFit: 0.16,
    socialFit: 0.14,
    culturalFit: 0.08,
    familyFit: 0.1,
    financialFit: 0.1,
    clinicalQuality: 0.1,
    luxuryAmenities: 0.1,
  },
  "Skilled Nursing": {
    careFit: 0.35,
    lifestyleFit: 0.05,
    socialFit: 0.05,
    culturalFit: 0.05,
    familyFit: 0.1,
    financialFit: 0.05,
    clinicalQuality: 0.25,
    luxuryAmenities: 0.1,
  },
  Rehabilitation: {
    careFit: 0.28,
    lifestyleFit: 0.05,
    socialFit: 0.05,
    culturalFit: 0.05,
    familyFit: 0.1,
    financialFit: 0.05,
    clinicalQuality: 0.32,
    luxuryAmenities: 0.1,
  },
  "High Clinical Complexity": {
    careFit: 0.25,
    lifestyleFit: 0.04,
    socialFit: 0.04,
    culturalFit: 0.05,
    familyFit: 0.08,
    financialFit: 0.05,
    clinicalQuality: 0.39,
    luxuryAmenities: 0.1,
  },
  "Family-Centered Senior": {
    careFit: 0.1,
    lifestyleFit: 0.12,
    socialFit: 0.08,
    culturalFit: 0.06,
    familyFit: 0.28,
    financialFit: 0.12,
    clinicalQuality: 0.08,
    luxuryAmenities: 0.16,
  },
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

function weightedTotal(scores: PriorityScores, weights: WeightProfile): number {
  return clamp(
    scores.careFit * weights.careFit +
      scores.lifestyleFit * weights.lifestyleFit +
      scores.socialFit * weights.socialFit +
      scores.culturalFit * weights.culturalFit +
      scores.familyFit * weights.familyFit +
      scores.financialFit * weights.financialFit +
      scores.clinicalQuality * weights.clinicalQuality +
      scores.luxuryAmenities * weights.luxuryAmenities,
  );
}

function average(values: number[], fallback: number): number {
  if (values.length === 0) return fallback;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function buildCriterion(name: string, tier: MatchQualityTier, score: number, threshold: number, rationale: string, source: string, applicable = true): MatchQualityCriterion {
  const normalized = clamp(score);
  return {
    name,
    tier,
    score: normalized,
    matched: applicable ? normalized >= threshold : false,
    applicable,
    rationale,
    source,
  };
}

function confidenceMultiplier(confidenceScore: number): number {
  return 0.7 + (clamp(confidenceScore) / 100) * 0.3;
}

function hasDistanceConstraint(state: QuestionnaireState): boolean {
  return Boolean(
    state.distanceFromFamily ||
      state.humanIntelligenceV2.distanceProfile.driveTimes.normal ||
      state.humanIntelligenceV2.distanceProfile.familyVisitExpectation ||
      state.humanIntelligenceV2.familyProfile.visitFrequencyExpectation,
  );
}

function hasCulturalConstraint(state: QuestionnaireState): boolean {
  return Boolean(
    state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage ||
      state.humanIntelligenceV2.culturalProfile.culturalIdentity ||
      state.humanIntelligenceV2.culturalProfile.faithTraditions.length > 0 ||
      state.humanIntelligenceV2.foodProfile.dietaryPreferences.length > 0,
  );
}

function hasFamilyPriority(state: QuestionnaireState): boolean {
  return Boolean(
    state.humanIntelligenceV2.familyProfile.visitFrequencyExpectation ||
      state.humanIntelligenceV2.distanceProfile.familyVisitExpectation ||
      state.humanIntelligenceV2.familyProfile.involvedFamilyMembers ||
      state.humanIntelligenceV2.familyCultureProfile.involvementExpectation,
  );
}

function scoreMemoryNeedCriterion(facility: SearchFacility, state: QuestionnaireState): number {
  const memory = state.memoryStatus;
  if (memory === "No" || memory === "Not sure" || !memory) return 100;

  if (memory === "Significant memory issues") {
    if (facility.careTypes.includes("Memory Care")) return 96;
    if (facility.careTypes.includes("Assisted Living")) return 62;
    return 18;
  }

  if (facility.careTypes.includes("Memory Care")) return 92;
  if (facility.careTypes.includes("Assisted Living")) return 82;
  if (facility.careTypes.includes("Skilled Nursing")) return 55;
  return 28;
}

function scoreIndependenceCriterion(facility: SearchFacility, state: QuestionnaireState): number {
  if (state.assistanceLevel !== "Fully independent") return 100;

  const futureCare = evaluateFutureCarePreference(facility, state);
  if (state.futureCarePreference === "Independent only") {
    return futureCare.rejectionReasons.length === 0 ? 98 : 0;
  }

  if (facility.careTypes.includes("Independent Living") || facility.careTypes.includes("Active Adult 55+")) {
    if (facility.careTypes.includes("CCRC") || facility.careTypes.includes("Continuing Care")) return 96;
    if (facility.careTypes.includes("Assisted Living")) return 84;
    return 92;
  }

  if (facility.careTypes.includes("Assisted Living")) return 56;
  if (facility.careTypes.includes("Memory Care")) return 24;
  if (facility.careTypes.includes("Skilled Nursing") || facility.careTypes.includes("Rehabilitation")) return 6;
  return 40;
}

function buildOptionalCriteria(facility: SearchFacility, state: QuestionnaireState, priorityScores: PriorityScores): MatchQualityCriterion[] {
  const text = joinedFacilityText(facility);
  const criteria: MatchQualityCriterion[] = [];

  if (state.humanIntelligenceV2.communityPreferenceProfile.preferredEnvironment.includes("Luxury environment")) {
    criteria.push(buildCriterion("Luxury amenities", "OPTIONAL", priorityScores.luxuryAmenities, 65, "Luxury is treated as a low-value optional preference.", "Luxury cues in facility metadata"));
  }

  if (["Important", "Very important"].includes(state.humanIntelligenceV2.independenceProfile.petOwnershipImportance)) {
    criteria.push(buildCriterion("Pet friendliness", "OPTIONAL", includesAny(text, ["pet", "dog", "cat", "pet-friendly"]) ? 90 : 28, 60, "Pet support influences score minimally.", "Pet cues in facility metadata"));
  }

  if (state.happinessPreferences.includes("Good food") || state.humanIntelligenceV2.foodProfile.dietaryPreferences.length > 0) {
    criteria.push(buildCriterion("Dining preferences", "OPTIONAL", includesAny(text, ["dining", "chef", "restaurant", "cuisine", "kosher", "halal"]) ? 88 : 34, 60, "Dining preferences are optional quality-of-life signals.", "Dining cues in facility metadata"));
  }

  if (state.happinessPreferences.includes("Exercise and wellness") || state.happinessPreferences.includes("Outdoor activities")) {
    criteria.push(buildCriterion("Wellness amenities", "OPTIONAL", includesAny(text, ["fitness", "wellness", "pool", "spa", "garden", "walking", "golf"]) ? 90 : 35, 60, "Wellness amenities are optional and never outweigh core fit.", "Wellness cues in facility metadata"));
  }

  if (includesAny(state.notes.toLowerCase(), ["golf", "pool", "spa"])) {
    criteria.push(buildCriterion("Specific amenity request", "OPTIONAL", includesAny(text, ["golf", "pool", "spa"]) ? 92 : 30, 60, "Specific amenity requests remain optional preferences.", "Amenity cues in facility metadata"));
  }

  return criteria;
}

function summarizeTier(criteria: MatchQualityCriterion[], tier: MatchQualityTier, fallbackAverage: number, mismatchPenaltyPerItem: number): MatchQualityTierSummary {
  const applicable = criteria.filter((item) => item.tier === tier && item.applicable);
  const matched = applicable.filter((item) => item.matched).length;
  const mismatches = applicable.length - matched;
  return {
    tier,
    matched,
    total: applicable.length,
    averageScore: Math.round(average(applicable.map((item) => item.score), fallbackAverage)),
    mismatchPenalty: Number((mismatches * mismatchPenaltyPerItem).toFixed(2)),
  };
}

function buildMatchQualityResult(facility: SearchFacility, state: QuestionnaireState, priorityScores: PriorityScores): MatchQualityResult {
  const futureCare = evaluateFutureCarePreference(facility, state);
  const mandatoryCriteria: MatchQualityCriterion[] = [
    buildCriterion("Required care level", "MANDATORY", priorityScores.careFit, 70, "Required care support is mandatory.", "Care-fit model output"),
    buildCriterion("Budget affordability", "MANDATORY", priorityScores.financialFit, 70, "Budget affordability is mandatory.", "Financial-fit model output"),
  ];

  const criticalCriteria: MatchQualityCriterion[] = [];

  if (state.assistanceLevel === "Fully independent") {
    criticalCriteria.push(buildCriterion("Independence level", "CRITICAL", scoreIndependenceCriterion(facility, state), 70, "Independence support is treated as critical for fully independent profiles.", futureCare.source || "Care taxonomy and future-care preference"));
  }

  if (state.memoryStatus && state.memoryStatus !== "No" && state.memoryStatus !== "Not sure") {
    mandatoryCriteria.push(buildCriterion("Memory care requirement", "MANDATORY", scoreMemoryNeedCriterion(facility, state), 70, "Memory care support is mandatory when cognitive needs are present.", "Memory-support cues in facility care types"));
  }

  if (hasDistanceConstraint(state)) {
    mandatoryCriteria.push(buildCriterion("Geographic radius", "MANDATORY", priorityScores.familyFit, 60, "Travel burden and geographic access constraints are mandatory when supplied.", "Family-fit and distance model output"));
  }

  criticalCriteria.push(buildCriterion("Social lifestyle importance", "CRITICAL", priorityScores.socialFit, 60, "Social lifestyle alignment is critical when community rhythm matters.", "Social-fit model output", Boolean(state.humanIntelligenceV2.socialProfile.socialInteractionFrequency || state.happinessPreferences.includes("Social activities") || state.humanIntelligenceV2.socialProfile.hobbyParticipation.length > 0)));
  criticalCriteria.push(buildCriterion("Cultural or religious requirements", "CRITICAL", priorityScores.culturalFit, 60, "Cultural and religious requirements are critical when explicitly requested.", "Cultural-fit model output", hasCulturalConstraint(state)));
  if (state.futureCarePreference && state.futureCarePreference !== "No preference") {
    criticalCriteria.push(buildCriterion("Future care preference", "CRITICAL", futureCare.score, 60, "Future care planning is critical when explicitly requested.", futureCare.source));
  }

  const importantCriteria: MatchQualityCriterion[] = [
    buildCriterion("Family proximity", "IMPORTANT", priorityScores.familyFit, 60, "Family proximity affects suitability after critical care requirements are satisfied.", "Family-fit and distance model output", hasFamilyPriority(state)),
    buildCriterion("Dining quality", "IMPORTANT", includesAny(joinedFacilityText(facility), ["dining", "restaurant", "chef", "cuisine", "food"]) ? 85 : 45, 60, "Dining quality matters, but it should not outweigh critical fit.", "Dining cues in facility metadata", state.happinessPreferences.includes("Good food") || state.humanIntelligenceV2.foodProfile.dietaryPreferences.length > 0),
    buildCriterion("Activity intensity", "IMPORTANT", priorityScores.lifestyleFit, 60, "Activity intensity supports day-to-day satisfaction after core needs are met.", "Lifestyle-fit model output", state.happinessPreferences.length > 0),
    buildCriterion("Outdoor environment", "IMPORTANT", includesAny(joinedFacilityText(facility), ["garden", "walking", "outdoor", "nature", "courtyard"]) ? 88 : 42, 60, "Outdoor environment is important when lifestyle preferences point to it.", "Outdoor environment cues in facility metadata", state.happinessPreferences.includes("Outdoor activities") || state.humanIntelligenceV2.communityPreferenceProfile.preferredEnvironment.includes("Quiet community")),
  ];

  const optionalCriteria = buildOptionalCriteria(facility, state, priorityScores);
  const criteria = mandatoryCriteria.concat(criticalCriteria, importantCriteria, optionalCriteria);

  const mandatorySummary = summarizeTier(criteria, "MANDATORY", 100, 40);
  const criticalSummary = summarizeTier(criteria, "CRITICAL", 85, 10);
  const importantSummary = summarizeTier(criteria, "IMPORTANT", 80, 2.5);
  const optionalSummary = summarizeTier(criteria, "OPTIONAL", 75, 0.5);
  const tierSummaries = [mandatorySummary, criticalSummary, importantSummary, optionalSummary];

  const confidenceScore = clamp(40 + (average(criteria.filter((item) => item.applicable).map((item) => item.score), 60) * 0.6));
  const baseScore =
    mandatorySummary.averageScore * 0.45 +
    criticalSummary.averageScore * 0.3 +
    importantSummary.averageScore * 0.2 +
    optionalSummary.averageScore * 0.05;

  const penalty = mandatorySummary.mismatchPenalty + criticalSummary.mismatchPenalty + importantSummary.mismatchPenalty + optionalSummary.mismatchPenalty;
  let score = clamp((baseScore - penalty) * confidenceMultiplier(confidenceScore));

  if (mandatorySummary.matched < mandatorySummary.total) {
    score = 0;
  } else if (criticalSummary.matched < criticalSummary.total) {
    score = Math.min(score, 65);
  }

  return {
    score,
    criteria,
    tierSummaries,
    explanation: "This score reflects how well the community matches what matters most to you, not how many features it offers.",
  };
}

function buildWeightEntries(weights: WeightProfile): Array<{ label: string; weight: number }> {
  return [
    { label: "Care Fit", weight: weights.careFit },
    { label: "Lifestyle Fit", weight: weights.lifestyleFit },
    { label: "Social Fit", weight: weights.socialFit },
    { label: "Cultural Fit", weight: weights.culturalFit },
    { label: "Family Fit", weight: weights.familyFit },
    { label: "Financial Fit", weight: weights.financialFit },
    { label: "Clinical Quality", weight: weights.clinicalQuality },
    { label: "Luxury Amenities", weight: weights.luxuryAmenities },
  ].sort((left, right) => right.weight - left.weight);
}

function careTypeTotalAdjustment(facility: SearchFacility, state: QuestionnaireState): number {
  let adjustment = 0;

  if (state.assistanceLevel === "Fully independent") {
    if (facility.careTypes.includes("Skilled Nursing")) adjustment -= 40;
    if (facility.careTypes.includes("Rehabilitation")) adjustment -= 35;
    if (facility.careTypes.includes("Memory Care")) adjustment -= 20;
    if (facility.careTypes.includes("UNKNOWN")) adjustment -= 15;
    if (facility.careTypes.includes("Independent Living")) adjustment += 20;
    if (facility.careTypes.includes("Active Adult 55+")) adjustment += 18;
    if (facility.careTypes.includes("CCRC")) adjustment += 12;
  }

  if (state.memoryStatus === "Mild memory issues" || state.memoryStatus === "Occasionally forgetful" || state.memoryStatus === "Significant memory issues") {
    if (facility.careTypes.includes("Memory Care")) adjustment += 30;
    if (facility.careTypes.includes("Assisted Living")) adjustment += 15;
    if (facility.careTypes.includes("Skilled Nursing")) adjustment += 5;
    if (facility.careTypes.includes("Independent Living")) adjustment -= 20;
    if (facility.careTypes.includes("Active Adult 55+")) adjustment -= 20;
    if (facility.careTypes.includes("Rehabilitation") && state.memoryStatus !== "Significant memory issues") adjustment -= 12;
  }

  adjustment += evaluateFutureCarePreference(facility, state).adjustment;

  return adjustment;
}

function hasAnyCareType(facility: SearchFacility, expected: string[]): boolean {
  return facility.careTypes.some((careType) => expected.includes(careType));
}

function isStandaloneClinicalCommunity(facility: SearchFacility, careType: "Skilled Nursing" | "Rehabilitation"): boolean {
  const clinicalOnlyTypes = ["Skilled Nursing", "Rehabilitation", "Hospice", "UNKNOWN"];
  return facility.careTypes.includes(careType) && facility.careTypes.every((item) => clinicalOnlyTypes.includes(item));
}

function isContinuumCampus(facility: SearchFacility): boolean {
  const hasIndependent = hasAnyCareType(facility, ["Independent Living", "Active Adult 55+"]);
  const hasContinuumLabel = hasAnyCareType(facility, ["CCRC", "Continuing Care"]);
  const hasProgressiveSupport = hasAnyCareType(facility, ["Assisted Living", "Memory Care", "Skilled Nursing", "Rehabilitation"]);
  return hasContinuumLabel || (hasIndependent && hasProgressiveSupport && facility.careTypes.length >= 3);
}

function evaluateFutureCarePreference(facility: SearchFacility, state: QuestionnaireState): FutureCarePreferenceEvaluation {
  const preference = state.futureCarePreference;
  const source = preference ? `Future care preference: ${preference}` : "Future care preference not selected";

  if (state.assistanceLevel !== "Fully independent" || !preference || preference === "No preference") {
    return {
      preference,
      adjustment: 0,
      score: 50,
      explanation: preference === "No preference" ? "No future-care filtering was applied." : "Future-care preference did not affect ranking.",
      source,
      contributorLabel: "Future care preference",
      rejectionReasons: [],
    };
  }

  const facilityText = [facility.name, facility.careTypes.join(" "), facility.matchBadges.join(" ")].join(" ").toLowerCase();
  const hasIndependentOnlyMatch = hasAnyCareType(facility, ["Independent Living", "Active Adult 55+"]);
  const hasContinuum = hasAnyCareType(facility, ["CCRC", "Continuing Care"]);
  const continuumCampus = isContinuumCampus(facility);
  const standaloneSkilledNursing = isStandaloneClinicalCommunity(facility, "Skilled Nursing");
  const standaloneRehabilitation = isStandaloneClinicalCommunity(facility, "Rehabilitation");
  const rejectionReasons: string[] = [];
  let adjustment = 0;
  let score = 50;
  let explanation = "Future-care preference did not materially affect this ranking.";

  if (preference === "Independent only") {
    if (!hasIndependentOnlyMatch) {
      rejectionReasons.push("Independent only preference requires communities designed for fully independent residents.");
    }
    if (facility.careTypes.includes("Skilled Nursing")) {
      rejectionReasons.push("Independent only preference excludes communities that include skilled nursing care.");
    }
    if (facility.careTypes.includes("Rehabilitation") || facilityText.includes("post-acute")) {
      rejectionReasons.push("Independent only preference excludes rehabilitation or post-acute communities.");
    }
    if (facility.careTypes.includes("Memory Care")) {
      rejectionReasons.push("Independent only preference excludes memory care communities.");
    }

    adjustment = rejectionReasons.length === 0 ? (facility.careTypes.includes("Active Adult 55+") ? 18 : 14) : 0;
    score = rejectionReasons.length === 0 ? 95 : 0;
    explanation = rejectionReasons.length === 0
      ? "Matched the Independent only preference because the community is designed for fully independent residents."
      : rejectionReasons.join(" ");
  }

  if (preference === "Future support available") {
    if (hasContinuum) adjustment += 18;
    else if (hasIndependentOnlyMatch) adjustment += 10;
    if (continuumCampus) adjustment += 8;
    if (standaloneSkilledNursing) adjustment -= 18;
    if (standaloneRehabilitation) adjustment -= 18;

    score = clamp(60 + adjustment * 1.5);
    if (adjustment > 0) {
      explanation = hasContinuum
        ? "Boosted because the community supports independent living now and offers future care progression on the same campus."
        : "Boosted because the community supports independent living with some future care flexibility."
    } else if (adjustment < 0) {
      explanation = "Penalized because the facility reads like a standalone clinical setting rather than an independence-first campus with future support."
    } else {
      explanation = "No additional future-support boost or penalty applied."
    }
  }

  if (preference === "Full continuum of care") {
    if (hasContinuum) adjustment += 28;
    else if (continuumCampus) adjustment += 20;
    else if (hasIndependentOnlyMatch && facility.careTypes.includes("Assisted Living")) adjustment += 8;

    score = clamp(55 + adjustment * 1.4);
    explanation = adjustment > 0
      ? "Boosted because the community offers a stronger continuum-of-care path on one campus."
      : "No continuum-of-care boost was available for this community."
  }

  return {
    preference,
    adjustment,
    score,
    explanation,
    source,
    contributorLabel: `Future care preference: ${preference}`,
    rejectionReasons,
  };
}

const TRUSTED_INTELLIGENCE_SOURCES = ["CMS", "Medicare Care Compare", "State inspections", "AHCA", "Public court records"];
const ALLOWED_PROVENANCE = ["REAL", "SYNTHETIC", "HEURISTIC", "INFERRED"] as const;

function clampIntelligenceDelta(value: number, trusted: boolean): number {
  const cap = trusted ? 15 : 10;
  return clamp(value, -cap, cap);
}

function hasTrustedIntelligence(facility: SearchFacility): boolean {
  return facility.intelligenceSnapshot?.sources_used.some((source) => TRUSTED_INTELLIGENCE_SOURCES.includes(source)) || false;
}

function provenanceCap(provenance: string, mode: EngineRunMode): number {
  if (provenance === "REAL") return 15;
  if (provenance === "HEURISTIC") return 2;
  if (provenance === "INFERRED") return 5;
  if (provenance === "SYNTHETIC") return mode === "simulation" ? 10 : 0;
  return 0;
}

function sumSignalImpact(facility: SearchFacility, categories: string[], mode: EngineRunMode): number {
  const signalDetails = facility.intelligenceSnapshot?.signal_details || [];
  const totals: Record<string, number> = {};

  signalDetails.forEach((signal) => {
    const category = (signal.category || "").toLowerCase();
    if (!categories.includes(category)) return;

    const provenance = String(signal.provenance || "INFERRED").toUpperCase();
    if (!ALLOWED_PROVENANCE.includes(provenance as (typeof ALLOWED_PROVENANCE)[number])) return;
    if (provenance === "SYNTHETIC" && mode === "production") return;

    const rawImpact = Number(signal.impact_score || 0);
    const signedImpact = signal.polarity === "negative" && rawImpact > 0 ? -rawImpact : rawImpact;
    totals[provenance] = (totals[provenance] || 0) + signedImpact;
  });

  return Object.entries(totals).reduce((sum, [provenance, value]) => {
    const cap = provenanceCap(provenance, mode);
    return sum + clamp(value, -cap, cap);
  }, 0);
}

function applyIntelligenceOverlay(priorityScores: PriorityScores, facility: SearchFacility, mode: EngineRunMode): PriorityScores {
  const snapshot = facility.intelligenceSnapshot;
  if (!snapshot) return priorityScores;

  const trusted = hasTrustedIntelligence(facility);
  const familyDelta = clampIntelligenceDelta(sumSignalImpact(facility, ["family_sentiment"], mode) + ((snapshot.family_satisfaction_index - 50) * 0.06), false);
  const socialDelta = clampIntelligenceDelta(sumSignalImpact(facility, ["social_signals"], mode) + ((((snapshot.social_energy_index + snapshot.community_engagement_index) / 2) - 50) * 0.06), false);
  const culturalDelta = clampIntelligenceDelta(sumSignalImpact(facility, ["social_signals"], mode) * 0.5 + ((snapshot.cultural_match_signals - 50) * 0.08), false);
  const reputationDelta = clampIntelligenceDelta(sumSignalImpact(facility, ["news"], mode) + ((snapshot.reputation_index - 50) * 0.08), false);
  const staffDelta = clampIntelligenceDelta(sumSignalImpact(facility, ["employee_intelligence"], mode) + ((snapshot.staff_stability_index - 50) * 0.08), false);
  const trustedRiskDelta = clampIntelligenceDelta(
    sumSignalImpact(facility, ["regulatory", "legal"], mode) + ((50 - snapshot.regulatory_risk_index) * 0.18) + ((50 - snapshot.litigation_risk_index) * 0.14),
    trusted,
  );

  return {
    ...priorityScores,
    familyFit: clamp(priorityScores.familyFit + familyDelta),
    socialFit: clamp(priorityScores.socialFit + socialDelta),
    culturalFit: clamp(priorityScores.culturalFit + culturalDelta),
    clinicalQuality: clamp(priorityScores.clinicalQuality + staffDelta + trustedRiskDelta),
    lifestyleFit: clamp(priorityScores.lifestyleFit + reputationDelta),
  };
}

function detectPersonaType(state: QuestionnaireState): PersonaType {
  const assistance = state.assistanceLevel;
  const memory = state.memoryStatus;
  const social = state.humanIntelligenceV2.socialProfile;
  const family = state.humanIntelligenceV2.familyProfile;
  const cultural = state.humanIntelligenceV2.culturalProfile;
  const language = state.humanIntelligenceV2.languageProfile;
  const interests = state.happinessPreferences.map((item) => item.toLowerCase());
  const notes = state.notes.toLowerCase();

  if (memory === "Significant memory issues") return "Memory Care";
  if (assistance === "Skilled nursing care") return /rehab|rehabilitation|post[- ]?hospital/.test(notes) ? "Rehabilitation" : "Skilled Nursing";
  if (/rehab|rehabilitation|post[- ]?hospital/.test(notes)) return "Rehabilitation";
  if (memory === "Mild memory issues" || memory === "Occasionally forgetful") return "Early Memory Support";
  if (assistance && assistance !== "Fully independent") return "Assisted Living";
  if (
    assistance === "Fully independent" &&
    language.preferredSpokenLanguage &&
    language.preferredSpokenLanguage !== "English" &&
    (cultural.religionImportance === "High" || cultural.religionImportance === "Very high" || cultural.faithTraditions.length > 0) &&
    (family.visitFrequencyExpectation === "Daily" || family.visitFrequencyExpectation === "Weekly" || family.involvedFamilyMembers === "5+")
  ) {
    return "Cultural Family Senior";
  }
  if (family.visitFrequencyExpectation === "Daily" || family.involvedFamilyMembers === "5+" || family.grandchildrenImportance === "High") return "Family-Centered Senior";
  if (social.socialInteractionFrequency === "Daily" || social.newFriendsImportance === "High" || interests.some((item) => /social|activity|music|games/.test(item))) return "Independent Social Senior";
  if (social.socialInteractionFrequency === "Monthly or less" || social.newFriendsImportance === "Low" || interests.some((item) => /quiet|calm|peaceful/.test(item))) return "Independent Quiet Senior";
  return /active|exercise|wellness/.test(interests.join(" ")) ? "Independent Active Senior" : "Independent Active Senior";
}

function buildPersonaProfile(state: QuestionnaireState): PersonaProfile {
  const personaType = detectPersonaType(state);
  const weights = PERSONA_WEIGHT_PROFILES[personaType];

  const profiles: Record<PersonaType, Omit<PersonaProfile, "personaType" | "weights" | "activeWeights">> = {
    "Independent Active Senior": {
      rankingStrategy: "Person-first active lifestyle ranking.",
      whySelected: ["Fully independent or lightly supported profile.", "Values activity, movement, and a full daily routine.", "Clinical needs are not the primary driver."],
      whatWouldChangeThisRanking: ["If clinical needs increase, Clinical Quality and Care Fit would dominate.", "If social needs increase, Social Fit would rise.", "If family distance becomes primary, Family Fit would gain weight."],
    },
    "Independent Social Senior": {
      rankingStrategy: "Person-first social lifestyle ranking.",
      whySelected: ["Fully independent profile.", "Values frequent social interaction.", "Community activity matters more than clinical intensity."],
      whatWouldChangeThisRanking: ["If clinical needs increase, Care Fit and Clinical Quality would dominate.", "If quiet preference grows, Social Fit would drop.", "If family proximity becomes mandatory, Family Fit would rise."],
    },
    "Independent Quiet Senior": {
      rankingStrategy: "Person-first calm-environment ranking.",
      whySelected: ["Fully independent profile.", "Prefers a quieter environment.", "Social stimulation should stay modest."],
      whatWouldChangeThisRanking: ["If social engagement becomes a priority, Social Fit would rise.", "If family involvement increases, Family Fit would become stronger.", "If clinical needs increase, Clinical Quality would rise."],
    },
    "Cultural Family Senior": {
      rankingStrategy: "Cultural and family continuity ranking.",
      whySelected: ["Language and faith cues are explicit.", "Family involvement is a primary decision driver.", "The score should reflect culture and belonging before amenities."],
      whatWouldChangeThisRanking: ["If clinical needs rise, Care Fit and Clinical Quality would become dominant.", "If family access becomes less important, Social Fit would gain share.", "If language and faith needs relax, the engine would shift toward independence and lifestyle."],
    },
    "Early Memory Support": {
      rankingStrategy: "Memory-aware early support ranking.",
      whySelected: ["Memory concerns are present but not yet full memory care.", "Safety and day-to-day support matter more.", "Care needs are trending upward."],
      whatWouldChangeThisRanking: ["If memory loss worsens, Memory Care would take over.", "If rehabilitation is needed, Clinical Quality would rise.", "If the person remains highly independent, Lifestyle Fit would gain share."],
    },
    "Memory Care": {
      rankingStrategy: "Memory-first safety and support ranking.",
      whySelected: ["Significant memory needs are present.", "Safety and supervision are critical.", "Care quality outweighs lifestyle preferences."],
      whatWouldChangeThisRanking: ["If clinical complexity rises, Skilled Nursing or High Clinical Complexity would take priority.", "If family visits become the main concern, Family Fit would rise.", "If memory concerns ease, Lifestyle and Social Fit would gain weight."],
    },
    "Assisted Living": {
      rankingStrategy: "Supportive independence ranking.",
      whySelected: ["Some daily support is needed.", "Independence still matters.", "Balanced social and lifestyle fit is important."],
      whatWouldChangeThisRanking: ["If skilled nursing is needed, Skilled Nursing would replace Assisted Living.", "If memory concerns deepen, Memory Care would dominate.", "If the person becomes more independent, Independence-oriented personas would take over."],
    },
    "Skilled Nursing": {
      rankingStrategy: "Clinical support ranking.",
      whySelected: ["Skilled nursing needs are explicit.", "Clinical quality and staffing should dominate.", "Family and lifestyle remain secondary."],
      whatWouldChangeThisRanking: ["If rehabilitation is the main goal, Rehabilitation would outrank it.", "If clinical complexity becomes extreme, High Clinical Complexity would take over.", "If needs reduce, Assisted Living would become more appropriate."],
    },
    Rehabilitation: {
      rankingStrategy: "Recovery-focused ranking.",
      whySelected: ["Post-acute or rehab needs are present.", "Clinical quality and staffing are central.", "Short-term recovery matters more than amenities."],
      whatWouldChangeThisRanking: ["If recovery stabilizes, Assisted Living or Independence personas would rise.", "If memory issues intensify, Memory Care would dominate.", "If clinical complexity increases, High Clinical Complexity would gain weight."],
    },
    "High Clinical Complexity": {
      rankingStrategy: "High-acuity clinical ranking.",
      whySelected: ["Clinical complexity is the primary driver.", "Staffing and safety are critical.", "Lifestyle preferences are secondary."],
      whatWouldChangeThisRanking: ["If acuity decreases, Skilled Nursing or Assisted Living would become more relevant.", "If memory issues emerge, Memory Care would rise.", "If family proximity becomes the top need, Family Fit would increase."],
    },
    "Family-Centered Senior": {
      rankingStrategy: "Family-access ranking.",
      whySelected: ["Family visits and involvement are central.", "Proximity and communication matter most.", "Social fit should support shared family life."],
      whatWouldChangeThisRanking: ["If clinical needs increase, Care Fit and Clinical Quality would rise.", "If independence becomes dominant, Independence-oriented personas would replace it.", "If distance stops mattering, Social and Lifestyle weights would increase."],
    },
  };

  return {
    personaType,
    weights,
    activeWeights: buildWeightEntries(weights),
    ...profiles[personaType],
  };
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
  const probabilities = facility.careTypeProbabilities;
  const independentProbability = probabilities["Independent Living"];
  const activeAdultProbability = probabilities["Active Adult 55+"];
  const assistedLivingProbability = probabilities["Assisted Living"];
  const memoryCareProbability = probabilities["Memory Care"];
  const skilledNursingProbability = probabilities["Skilled Nursing"];
  const rehabilitationProbability = probabilities.Rehabilitation;
  const ccrcProbability = probabilities.CCRC;
  const continuingCareProbability = probabilities["Continuing Care"];
  const hospiceProbability = probabilities.Hospice;
  const unknownProbability = probabilities.UNKNOWN;

  if (assistance === "Fully independent") {
    let independentScore = 15;
    independentScore += independentProbability * 95;
    independentScore += activeAdultProbability * 90;
    independentScore += ccrcProbability * 76;
    independentScore += continuingCareProbability * 70;
    independentScore += assistedLivingProbability * 40;
    independentScore -= skilledNursingProbability * 40;
    independentScore -= rehabilitationProbability * 35;
    independentScore -= memoryCareProbability * 20;
    independentScore -= unknownProbability * 15;
    independentScore -= hospiceProbability * 50;
    if (careText.includes("independent")) independentScore += 8;
    if (careText.includes("active adult")) independentScore += 6;
    if (facility.careTypes.includes("Skilled Nursing")) independentScore -= 40;
    if (facility.careTypes.includes("Rehabilitation")) independentScore -= 35;
    if (facility.careTypes.includes("Memory Care")) independentScore -= 20;
    if (facility.careTypes.includes("UNKNOWN")) independentScore -= 15;
    return clamp(independentScore);
  }

  if (assistance === "Skilled nursing care") {
    let score = 12;
    score += skilledNursingProbability * 85;
    score += rehabilitationProbability * 70;
    score += memoryCareProbability * 10;
    score += assistedLivingProbability * 8;
    score -= independentProbability * 30;
    score -= activeAdultProbability * 25;
    return clamp(score);
  }

  if (memory === "Significant memory issues") {
    let score = 10;
    score += memoryCareProbability * 95;
    score += assistedLivingProbability * 50;
    score += skilledNursingProbability * 25;
    score -= independentProbability * 25;
    score -= activeAdultProbability * 20;
    if (!careText.includes("memory")) score -= 15;
    return clamp(score);
  }

  let score = 18;
  score += assistedLivingProbability * 58;
  score += memoryCareProbability * (memory === "Mild memory issues" || memory === "Occasionally forgetful" ? 30 : 8);
  score += skilledNursingProbability * (memory === "Mild memory issues" || memory === "Occasionally forgetful" ? 5 : 10);
  score += continuingCareProbability * 18;
  score += ccrcProbability * 14;
  score -= independentProbability * 10;
  score -= activeAdultProbability * 10;
  score -= unknownProbability * 12;

  if (memory === "Mild memory issues" || memory === "Occasionally forgetful") {
    score += memoryCareProbability * 55;
    score += assistedLivingProbability * 30;
    score += skilledNursingProbability * 5;
    score -= rehabilitationProbability * 20;
    score -= independentProbability * 12;
    if (facility.careTypes.includes("Memory Care")) score += 30;
    if (facility.careTypes.includes("Assisted Living")) score += 15;
    if (facility.careTypes.includes("Skilled Nursing")) score += 5;
  }

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
  reasons.push(...evaluateFutureCarePreference(facility, state).rejectionReasons);

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
    "futureCarePreference",
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
  const futureCare = state.futureCarePreference;

  const clauses: string[] = [];
  if (livedAlone) clauses.push(`has lived alone for ${livedAlone.toLowerCase()}`);
  if (socialNeed) clauses.push(`prefers ${socialNeed.toLowerCase()} social interaction`);
  if (topActivity) clauses.push(`values ${topActivity.toLowerCase()}`);
  if (futureCare && futureCare !== "No preference") clauses.push(`wants a future-care path of ${futureCare.toLowerCase()}`);

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

  if (state.assistanceLevel === "Fully independent" && !state.futureCarePreference) {
    missing.push("Add the future care preference to clarify whether results should stay independence-only or include continuum options.");
  }

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

function summarizeContributions(scores: PriorityScores, weights: WeightProfile): Contribution[] {
  const weighted = [
    { label: "Care fit", value: scores.careFit * weights.careFit },
    { label: "Lifestyle fit", value: scores.lifestyleFit * weights.lifestyleFit },
    { label: "Social fit", value: scores.socialFit * weights.socialFit },
    { label: "Cultural fit", value: scores.culturalFit * weights.culturalFit },
    { label: "Family fit", value: scores.familyFit * weights.familyFit },
    { label: "Financial fit", value: scores.financialFit * weights.financialFit },
    { label: "Clinical quality", value: scores.clinicalQuality * weights.clinicalQuality },
    { label: "Luxury amenities", value: scores.luxuryAmenities * weights.luxuryAmenities },
  ];

  return weighted.sort((a, b) => b.value - a.value);
}

function roundContribution(value: number): number {
  return Math.round(value * 100) / 100;
}

function buildIntelligenceSourcesUsed(facility: SearchFacility): string[] {
  const sources = new Set<string>(["Questionnaire answers", "Facility metadata"]);
  facility.scoreBreakdown?.forEach((item) => item.dataSource.forEach((source) => sources.add(source)));
  facility.intelligenceSnapshot?.sources_used.forEach((source) => sources.add(source));
  return [...sources];
}

function buildReportBreakdown(
  facility: SearchFacility,
  state: QuestionnaireState,
  priorityScores: PriorityScores,
  weights: WeightProfile,
  contributions: Contribution[],
  matchQuality: MatchQualityResult,
): ReportBreakdownItem[] {
  const facilityText = joinedFacilityText(facility);
  const language = state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage;
  const preferredActivities = state.happinessPreferences;
  const careNeed = state.assistanceLevel || "general support";
  const futureCarePreference = evaluateFutureCarePreference(facility, state);
  const futureCareCue = futureCarePreference.preference || state.memoryStatus || state.humanIntelligenceV2.transitionRiskProfile.lonelinessRisk || "future care planning";
  const staffingFit = facility.staffing_rating ? clamp(facility.staffing_rating * 20) : 50;
  const regulatoryFit = facility.inspection_rating ? clamp(facility.inspection_rating * 20) : 50;
  const reputationFit = facility.overall_rating ? clamp(facility.overall_rating * 20) : 50;
  const languageFit = language ? (includesAny(facilityText, [language]) ? 92 : 48) : 50;
  const activityFit = preferredActivities.length > 0 ? clamp(35 + preferredActivities.filter((activity) => includesAny(facilityText, [activity])).length * 18) : 50;
  const futureCareFit = clamp((priorityScores.careFit * 0.65) + (priorityScores.clinicalQuality * 0.35));

  return [
    {
      name: "Mandatory criteria matched",
      score: matchQuality.tierSummaries[0]?.matched || 0,
      maxScore: matchQuality.tierSummaries[0]?.total || 0,
      source: "Tiered match quality model",
      rationale: "Mandatory mismatches trigger immediate rejection.",
      weightedContribution: roundContribution(matchQuality.tierSummaries[0]?.averageScore || 0),
    },
    {
      name: "Critical criteria matched",
      score: matchQuality.tierSummaries[1]?.matched || 0,
      maxScore: matchQuality.tierSummaries[1]?.total || 0,
      source: "Tiered match quality model",
      rationale: "Critical mismatches drive large penalties and cap the maximum score.",
      weightedContribution: roundContribution(matchQuality.tierSummaries[1]?.averageScore || 0),
    },
    {
      name: "Important criteria matched",
      score: matchQuality.tierSummaries[2]?.matched || 0,
      maxScore: matchQuality.tierSummaries[2]?.total || 0,
      source: "Tiered match quality model",
      rationale: "Important preferences shape the score after mandatory and critical fit are satisfied.",
      weightedContribution: roundContribution(matchQuality.tierSummaries[2]?.averageScore || 0),
    },
    {
      name: "Optional criteria matched",
      score: matchQuality.tierSummaries[3]?.matched || 0,
      maxScore: matchQuality.tierSummaries[3]?.total || 0,
      source: "Tiered match quality model",
      rationale: "Optional preferences have minimal influence on match quality.",
      weightedContribution: roundContribution(matchQuality.tierSummaries[3]?.averageScore || 0),
    },
    {
      name: "Medical Fit",
      score: Math.round(clamp((priorityScores.careFit * 0.7) + (priorityScores.clinicalQuality * 0.3))),
      maxScore: 100,
      source: "Facility care types + clinical quality signals",
      rationale: `Matches the requested care level of ${careNeed}.`,
      weightedContribution: roundContribution(priorityScores.careFit * weights.careFit + priorityScores.clinicalQuality * weights.clinicalQuality),
    },
    {
      name: "Lifestyle Fit",
      score: Math.round(priorityScores.lifestyleFit),
      maxScore: 100,
      source: "Preference matching against facility metadata",
      rationale: preferredActivities.length > 0 ? `Reflects alignment with ${preferredActivities[0]}.` : "No explicit lifestyle preference was provided.",
      weightedContribution: roundContribution(priorityScores.lifestyleFit * weights.lifestyleFit),
    },
    {
      name: "Social Fit",
      score: Math.round(priorityScores.socialFit),
      maxScore: 100,
      source: "Social and community cues in facility metadata",
      rationale: "Measures the community's social engagement signal against the stated social profile.",
      weightedContribution: roundContribution(priorityScores.socialFit * weights.socialFit),
    },
    {
      name: "Family Fit",
      score: Math.round(priorityScores.familyFit),
      maxScore: 100,
      source: "Distance and visit-frequency preferences",
      rationale: "Captures family access and visit cadence from the questionnaire.",
      weightedContribution: roundContribution(priorityScores.familyFit * weights.familyFit),
    },
    {
      name: "Cultural Fit",
      score: Math.round(priorityScores.culturalFit),
      maxScore: 100,
      source: "Cultural and faith preferences + facility metadata",
      rationale: "Measures how closely the community aligns with identity and faith preferences.",
      weightedContribution: roundContribution(priorityScores.culturalFit * weights.culturalFit),
    },
    {
      name: "Language Fit",
      score: Math.round(languageFit),
      maxScore: 100,
      source: language ? `Preferred language: ${language}` : "No language preference supplied",
      rationale: language ? "Language support is inferred from the facility's searchable metadata." : "Missing language preference lowers confidence, not score.",
      weightedContribution: 0,
    },
    {
      name: "Activity Fit",
      score: Math.round(activityFit),
      maxScore: 100,
      source: "Happiness preferences + facility activity cues",
      rationale: preferredActivities.length > 0 ? `Looks for programming around ${preferredActivities[0]}.` : "No explicit activity preference was provided.",
      weightedContribution: 0,
    },
    {
      name: "Future Care Fit",
      score: Math.round(futureCarePreference.preference && futureCarePreference.preference !== "No preference" ? futureCarePreference.score : futureCareFit),
      maxScore: 100,
      source: futureCarePreference.source,
      rationale: `Uses current care needs and future-care signal: ${futureCareCue}. ${futureCarePreference.explanation}`,
      weightedContribution: 0,
    },
    {
      name: "Employee Intelligence",
      score: Math.round(staffingFit),
      maxScore: 100,
      source: "Facility staffing rating",
      rationale: "Represents the strength of staffing signals available in the facility dataset.",
      weightedContribution: 0,
    },
    {
      name: "Regulatory Intelligence",
      score: Math.round(regulatoryFit),
      maxScore: 100,
      source: "Facility inspection rating",
      rationale: "Represents how strong the public regulatory signal looks in the current dataset.",
      weightedContribution: 0,
    },
    {
      name: "Legal Risk",
      score: 0,
      maxScore: 0,
      source: "No legal record source in the current search payload",
      rationale: "No hidden legal penalty is applied unless a hard rejection reason exists.",
      weightedContribution: 0,
    },
    {
      name: "Reputation Intelligence",
      score: Math.round(reputationFit),
      maxScore: 100,
      source: "Facility overall rating and match badges",
      rationale: "Combines the visible reputation signal available in the facility dataset.",
      weightedContribution: 0,
    },
  ];
}

function buildContributorRows(contributions: Contribution[], totalScore: number, source: string, positive: boolean): ReportContributor[] {
  return contributions.slice(positive ? 0 : -3).map((item) => ({
    signal: item.label,
    source,
    weight: totalScore > 0 ? Number(((Math.abs(item.value) / totalScore) * 100).toFixed(2)) : 0,
    scoreContribution: positive ? Math.round(item.value) : -Math.round(item.value),
  }));
}

function buildHumanNarrative(facility: SearchFacility, state: QuestionnaireState): string {
  const relationship = state.relationship ? state.relationship.toLowerCase() : "your loved one";
  const careNeed = state.assistanceLevel ? state.assistanceLevel.toLowerCase() : "the current care need";
  const socialNeed = state.humanIntelligenceV2.socialProfile.socialInteractionFrequency || "a specific social rhythm";
  const activity = state.happinessPreferences[0];
  const distance = state.humanIntelligenceV2.distanceProfile.driveTimes.normal || state.distanceFromFamily;
  const futureCare = evaluateFutureCarePreference(facility, state);
  const distanceCopy = distance ? ` The distance signal is ${distance.toLowerCase()}.` : " Distance was not supplied, so it did not change the score.";

  const activityCopy = activity ? ` The community's lifestyle cues were compared against ${activity.toLowerCase()}.` : " No single activity preference dominated the score.";
  const futureCareCopy = futureCare.preference && futureCare.preference !== "No preference"
    ? ` Future care preference was set to ${futureCare.preference.toLowerCase()}, so ${futureCare.explanation.toLowerCase()}`
    : "";

  return `We prioritized this community because ${relationship} has ${careNeed} needs and prefers ${socialNeed.toLowerCase()} social interaction. ${facility.name} scored well on the strongest fit dimensions, which kept it near the top of the ranking. This score reflects how well the community matches what matters most to you, not how many features it offers.${activityCopy}${distanceCopy}${futureCareCopy}`;
}

function buildRankingExplanation(accepted: RankedRecommendation[], index: number): string {
  const current = accepted[index];
  const above = accepted[index - 1];
  const below = accepted[index + 1];

  if (!above && below) {
    return `Ranked #1 because it has the highest weighted fit score and the strongest top-two contributor balance.`;
  }

  if (above) {
    return `Ranked #${index + 1} because it trails #${index} on ${current.contributionHighlights.at(-1)?.label.toLowerCase() || "its weakest fit dimension"}, but stays competitive on ${current.contributionHighlights[0]?.label.toLowerCase() || "its strongest fit dimension"}.`;
  }

  if (!below) {
    return `Ranked #${index + 1} after higher-ranked options showed stronger weighted fit coverage.`;
  }

  return `Ranked #${index + 1} by the current weighted fit formula.`;
}

function buildIntelligenceReport(
  facility: SearchFacility,
  state: QuestionnaireState,
  priorityScores: PriorityScores,
  persona: PersonaProfile,
  contributions: Contribution[],
  totalScore: number,
  confidenceScore: number,
  accepted: RankedRecommendation[],
  index: number,
  missingInformation: string[],
  positiveSignals: string[],
  negativeSignals: string[],
  matchQuality: MatchQualityResult,
): IntelligenceScoringReport {
  const scoreBreakdown = buildReportBreakdown(facility, state, priorityScores, persona.weights, contributions, matchQuality);
  const sourcesUsed = buildIntelligenceSourcesUsed(facility);
  const missingIntelligence = [...missingInformation];
  const facilityText = joinedFacilityText(facility);
  const distanceEvaluation = parseDistancePoints(state);
  const languagePreference = state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage;
  const preferredActivities = state.happinessPreferences;
  const staffQualityScore = Math.round(facility.staffing_rating ? facility.staffing_rating * 20 : 50);
  const reviewSentimentScore = Math.round(facility.overall_rating ? facility.overall_rating * 20 : 50);
  const regulatoryQualityScore = Math.round(facility.inspection_rating ? facility.inspection_rating * 20 : 50);
  const futureCareScore = Math.round(clamp((priorityScores.careFit * 0.65) + (priorityScores.clinicalQuality * 0.35)));
  const languageFitScore = languagePreference ? (includesAny(facilityText, [languagePreference]) ? 92 : 48) : 50;
  const activityFitScore = preferredActivities.length > 0 ? clamp(35 + preferredActivities.filter((activity) => includesAny(facilityText, [activity])).length * 18) : 50;
  const futureCarePreference = evaluateFutureCarePreference(facility, state);

  if (!sourcesUsed.some((source) => /review|ratings?/i.test(source))) {
    missingIntelligence.push("No public review source is connected in the current search payload.");
  }
  if (!sourcesUsed.some((source) => /indeed|glassdoor|linkedin/i.test(source))) {
    missingIntelligence.push("No employee intelligence source is connected in the current search payload.");
  }
  if (!sourcesUsed.some((source) => /court|lawsuit|legal/i.test(source))) {
    missingIntelligence.push("No legal source is connected in the current search payload.");
  }
  if (!sourcesUsed.some((source) => /facebook|instagram|social/i.test(source))) {
    missingIntelligence.push("No public social channel source is connected in the current search payload.");
  }

  let careTaxonomyPenalty = 0;
  if (facility.careTypes.includes("UNKNOWN")) {
    missingIntelligence.push("Care taxonomy is unknown in the current dataset, so care-fit confidence is reduced.");
    careTaxonomyPenalty = 10;
  } else if (facility.careTypeConfidence === "MEDIUM") {
    careTaxonomyPenalty = 4;
  }

  const confidencePenalty = Math.min(40, missingIntelligence.length * 3 + careTaxonomyPenalty);
  const adjustedConfidence = clamp(confidenceScore - confidencePenalty);

  const categoryRows: AuditCategoryRow[] = [
    {
      name: "Medical Fit",
      rawScore: priorityScores.careFit,
      weight: persona.weights.careFit,
      weightedScore: roundContribution(priorityScores.careFit * persona.weights.careFit),
      finalContribution: roundContribution(priorityScores.careFit * persona.weights.careFit),
      source: "Care type matching from the current questionnaire and facility care types",
    },
    {
      name: "Lifestyle Fit",
      rawScore: priorityScores.lifestyleFit,
      weight: persona.weights.lifestyleFit,
      weightedScore: roundContribution(priorityScores.lifestyleFit * persona.weights.lifestyleFit),
      finalContribution: roundContribution(priorityScores.lifestyleFit * persona.weights.lifestyleFit),
      source: "Activity preference matching against facility text",
    },
    {
      name: "Social Fit",
      rawScore: priorityScores.socialFit,
      weight: persona.weights.socialFit,
      weightedScore: roundContribution(priorityScores.socialFit * persona.weights.socialFit),
      finalContribution: roundContribution(priorityScores.socialFit * persona.weights.socialFit),
      source: "Social and community cues in the current facility metadata",
    },
    {
      name: "Family Proximity",
      rawScore: priorityScores.familyFit,
      weight: persona.weights.familyFit,
      weightedScore: roundContribution(priorityScores.familyFit * persona.weights.familyFit),
      finalContribution: roundContribution(priorityScores.familyFit * persona.weights.familyFit),
      source: `Distance and visit cadence; ${distanceEvaluation.note}`,
    },
    {
      name: "Cultural Fit",
      rawScore: priorityScores.culturalFit,
      weight: persona.weights.culturalFit,
      weightedScore: roundContribution(priorityScores.culturalFit * persona.weights.culturalFit),
      finalContribution: roundContribution(priorityScores.culturalFit * persona.weights.culturalFit),
      source: "Cultural, faith, language, and food preference matching",
    },
    {
      name: "Language Fit",
      rawScore: languageFitScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: languagePreference ? `Preferred language check for ${languagePreference}` : "No language preference was supplied",
    },
    {
      name: "Activities Fit",
      rawScore: activityFitScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: preferredActivities.length > 0 ? "Lifestyle activity cues are already captured in the current ranking formula" : "No activity preference was supplied",
    },
    {
      name: "Future Care Fit",
      rawScore: futureCarePreference.preference && futureCarePreference.preference !== "No preference" ? futureCarePreference.score : futureCareScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: futureCarePreference.source,
    },
    {
      name: "Clinical Quality",
      rawScore: priorityScores.clinicalQuality,
      weight: persona.weights.clinicalQuality,
      weightedScore: roundContribution(priorityScores.clinicalQuality * persona.weights.clinicalQuality),
      finalContribution: roundContribution(priorityScores.clinicalQuality * persona.weights.clinicalQuality),
      source: "Facility clinical quality signals",
    },
    {
      name: "Staff Quality",
      rawScore: staffQualityScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: "Staff quality is visible in the runtime audit but not separately weighted in the current engine",
    },
    {
      name: "Review Sentiment",
      rawScore: reviewSentimentScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: "Review sentiment is not separately weighted in the current engine",
    },
    {
      name: "Regulatory Quality",
      rawScore: regulatoryQualityScore,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: "Regulatory quality is visible in the audit but not separately weighted in the current engine",
    },
    {
      name: "Legal Risk",
      rawScore: 0,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: "No legal source is connected in the current search payload",
    },
    {
      name: "Distance Adjustment",
      rawScore: distanceEvaluation.points,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: `Distance adjustment is already folded into family proximity in the current formula; ${distanceEvaluation.note}`,
    },
    {
      name: "Unknown Data Penalty",
      rawScore: missingIntelligence.length,
      weight: 0,
      weightedScore: 0,
      finalContribution: 0,
      source: "Missing intelligence lowers confidence only; it never lowers score",
    },
  ];

  const bonuses: AuditAdjustmentRow[] = [
    {
      name: "independent living match",
      rawScore: facility.careTypes.some((care) => /independent|active adult/i.test(care)) ? 1 : 0,
      value: facility.careTypes.some((care) => /independent|active adult/i.test(care)) && state.assistanceLevel === "Fully independent" ? 8 : 0,
      source: "Facility care types and independence requirement",
      applied: facility.careTypes.some((care) => /independent|active adult/i.test(care)) && state.assistanceLevel === "Fully independent",
    },
    {
      name: "strong social activity",
      rawScore: priorityScores.socialFit,
      value: priorityScores.socialFit >= 60 ? 7 : 0,
      source: "Current social fit score",
      applied: priorityScores.socialFit >= 60,
    },
    {
      name: "excellent reviews",
      rawScore: reviewSentimentScore,
      value: reviewSentimentScore >= 80 ? 6 : 0,
      source: "Overall facility rating",
      applied: reviewSentimentScore >= 80,
    },
    {
      name: "bilingual staff",
      rawScore: languageFitScore,
      value: languagePreference && includesAny(facilityText, [languagePreference]) ? 5 : 0,
      source: "Preferred language match in facility metadata",
      applied: Boolean(languagePreference && includesAny(facilityText, [languagePreference])),
    },
    {
      name: "continuum of care",
      rawScore: facility.careTypes.length,
      value: futureCarePreference.adjustment > 0 ? futureCarePreference.adjustment : facility.careTypes.length > 1 ? 4 : 0,
      source: futureCarePreference.preference && futureCarePreference.preference !== "No preference" ? futureCarePreference.explanation : "Multiple care types in the current facility profile",
      applied: futureCarePreference.adjustment > 0 || facility.careTypes.length > 1,
    },
  ];

  const penalties: AuditAdjustmentRow[] = [
    {
      name: "no movie activities found",
      rawScore: includesAny(facilityText, ["movie", "cinema"]) ? 0 : 1,
      value: preferredActivities.includes("Movies") && !includesAny(facilityText, ["movie", "cinema"]) ? 2 : 0,
      source: "Lifestyle preference check against current facility text",
      applied: preferredActivities.includes("Movies") && !includesAny(facilityText, ["movie", "cinema"]),
    },
    {
      name: "no Hebrew support found",
      rawScore: languagePreference && /hebrew/i.test(languagePreference) ? 1 : 0,
      value: languagePreference && /hebrew/i.test(languagePreference) && !includesAny(facilityText, ["hebrew", "עברית"]) ? 3 : 0,
      source: "Language preference check against current facility text",
      applied: Boolean(languagePreference && /hebrew/i.test(languagePreference) && !includesAny(facilityText, ["hebrew", "עברית"])),
    },
    {
      name: "distance exceeds target",
      rawScore: distanceEvaluation.points,
      value: distanceEvaluation.points < 0 ? Math.abs(distanceEvaluation.points) : 0,
      source: distanceEvaluation.note,
      applied: distanceEvaluation.points < 0,
    },
    {
      name: "missing employee reviews",
      rawScore: sourcesUsed.some((source) => /indeed|glassdoor|linkedin/i.test(source)) ? 1 : 0,
      value: sourcesUsed.some((source) => /indeed|glassdoor|linkedin/i.test(source)) ? 0 : 2,
      source: "Employee intelligence source availability",
      applied: !sourcesUsed.some((source) => /indeed|glassdoor|linkedin/i.test(source)),
    },
    {
      name: "staffing concerns",
      rawScore: staffQualityScore,
      value: staffQualityScore < 60 ? 5 : 0,
      source: "Staff quality score derived from current facility metadata",
      applied: staffQualityScore < 60,
    },
    {
      name: "future care preference mismatch",
      rawScore: futureCarePreference.score,
      value: futureCarePreference.adjustment < 0 ? Math.abs(futureCarePreference.adjustment) : 0,
      source: futureCarePreference.explanation,
      applied: futureCarePreference.adjustment < 0,
    },
  ];

  const traceability = [
    `Final score = tiered match quality model with critical, important, and optional criteria.`,
    `Mandatory criteria matched: ${matchQuality.tierSummaries[0]?.matched || 0}/${matchQuality.tierSummaries[0]?.total || 0}; Critical criteria matched: ${matchQuality.tierSummaries[1]?.matched || 0}/${matchQuality.tierSummaries[1]?.total || 0}; Important criteria matched: ${matchQuality.tierSummaries[2]?.matched || 0}/${matchQuality.tierSummaries[2]?.total || 0}; Optional criteria matched: ${matchQuality.tierSummaries[3]?.matched || 0}/${matchQuality.tierSummaries[3]?.total || 0}.`,
    `Supporting fit signals: ${contributions.map((item) => `${item.label}=${item.value.toFixed(2)}`).join(", ")}.`,
    `Missing intelligence affects confidence only, never the score.`,
    `This score reflects how well the community matches what matters most to you, not how many features it offers.`,
  ];

  const audit: AuditFormula = {
    executedFormula: "final_score = tiered_match_quality(critical, important, optional) - mismatch_penalties",
    finalScore: Math.round(totalScore),
    categoryRows,
    bonuses,
    penalties,
    criteria: matchQuality.criteria,
    tierSummaries: matchQuality.tierSummaries,
    matchQualityExplanation: matchQuality.explanation,
    confidence: {
      confidenceScore: adjustedConfidence,
      missingDataImpact: `${missingIntelligence.length} missing intelligence item(s); confidence reduced by ${confidencePenalty}`,
      sourceCoverage: `${sourcesUsed.length} source bucket(s) connected`,
      lastIntelligenceRefresh: new Date().toISOString(),
    },
  };

  const positiveContributors = buildContributorRows(contributions, totalScore, "Weighted person-fit formula", true).slice(0, 4);
  const negativeContributors = buildContributorRows(contributions, totalScore, "Lower weighted fit dimensions", false).slice(0, 3);
  const futureCareContributor = futureCarePreference.preference && futureCarePreference.preference !== "No preference" && futureCarePreference.adjustment !== 0
    ? {
        signal: futureCarePreference.contributorLabel,
        source: futureCarePreference.explanation,
        weight: totalScore > 0 ? Number(((Math.abs(futureCarePreference.adjustment) / totalScore) * 100).toFixed(2)) : 0,
        scoreContribution: futureCarePreference.adjustment,
      }
    : null;

  return {
    finalMatchScore: Math.round(totalScore),
    confidenceScore: adjustedConfidence,
    rankingPosition: index + 1,
    rankingExplanation: buildRankingExplanation(accepted, index),
    personaType: persona.personaType,
    rankingStrategy: persona.rankingStrategy,
    activeWeights: persona.activeWeights,
    whyWeightsSelected: persona.whySelected,
    whatWouldChangeThisRanking: persona.whatWouldChangeThisRanking,
    scoreBreakdown,
    positiveContributors: (futureCareContributor && futureCareContributor.scoreContribution > 0 ? [futureCareContributor] : []).concat(positiveContributors.length > 0 ? positiveContributors : contributions.slice(0, 3).map((item) => ({
      signal: item.label,
      source: "Weighted person-fit formula",
      weight: Number(item.value.toFixed(2)),
      scoreContribution: Math.round(item.value),
    }))).slice(0, 4),
    negativeContributors: (futureCareContributor && futureCareContributor.scoreContribution < 0 ? [futureCareContributor] : []).concat(negativeContributors.length > 0 ? negativeContributors : contributions.slice(-3).map((item) => ({
      signal: item.label,
      source: "Lower weighted fit dimensions",
      weight: Number(item.value.toFixed(2)),
      scoreContribution: -Math.round(item.value),
    }))).slice(0, 4),
    intelligenceSourcesUsed: sourcesUsed,
    missingIntelligence,
    humanNarrativeExplanation: buildHumanNarrative(facility, state),
    scoreTraceability: traceability
      .concat(futureCarePreference.preference && futureCarePreference.preference !== "No preference" ? [`Future care preference: ${futureCarePreference.preference}. ${futureCarePreference.explanation}`] : [])
      .concat(positiveSignals.length > 0 ? [`Positive signals observed: ${positiveSignals.slice(0, 3).join("; ")}.`] : [])
      .concat(negativeSignals.length > 0 ? [`Negative signals observed: ${negativeSignals.slice(0, 3).join("; ")}.`] : []),
    audit,
  };
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

export function runOptimeV2Engine(facilities: SearchFacility[], state: QuestionnaireState, options?: EngineRunOptions): EngineOutput {
  const mode: EngineRunMode = options?.mode || "production";
  const answeredSignals = flattenAnsweredSignals(state);
  const signalRoles = answeredSignals.map((signal) => ({
    key: signal.key,
    role: roleForSignalKey(signal.key),
  }));
  const persona = buildPersonaProfile(state);

  const recommendations = facilities.map((facility) => {
    const careFit = scoreCareFit(facility, state);
    const lifestyleFit = scoreLifestyleFit(facility, state);
    const socialFit = scoreSocialFit(facility, state);
    const culturalFit = scoreCulturalFit(facility, state);
    const family = scoreFamilyFit(state);
    const financialFit = scoreFinancialFit(facility, state);
    const clinicalQuality = scoreClinicalQuality(facility);
    const luxuryAmenities = scoreLuxuryAmenities(facility);

    const basePriorityScores: PriorityScores = {
      careFit,
      lifestyleFit,
      socialFit,
      culturalFit,
      familyFit: family.score,
      financialFit,
      clinicalQuality,
      luxuryAmenities,
    };

    const priorityScores = applyIntelligenceOverlay(basePriorityScores, facility, mode);
    const matchQuality = buildMatchQualityResult(facility, state, priorityScores);
    const totalScore = clamp(matchQuality.score);

    const hardRejectionReasons = collectHardRejectionReasons(facility, state);
    const contributions = summarizeContributions(priorityScores, persona.weights);

    const positives = contributions.slice(0, 3).map((item) => `${item.label} contributed strongly.`);
    const negatives = contributions.slice(-3).reverse().map((item) => `${item.label} is relatively weak for this person.`);

    const confidenceMatched = signalRoles.filter((signal) => signal.role !== "missing information analysis").length;
    const confidenceTotal = signalRoles.length || 1;
    const confidencePercent = Math.round((confidenceMatched / confidenceTotal) * 100);
    const report: IntelligenceScoringReport = {
      finalMatchScore: Math.round(totalScore),
      confidenceScore: confidencePercent,
      rankingPosition: null,
      rankingExplanation: "",
      personaType: persona.personaType,
      rankingStrategy: persona.rankingStrategy,
      activeWeights: persona.activeWeights,
      whyWeightsSelected: persona.whySelected,
      whatWouldChangeThisRanking: persona.whatWouldChangeThisRanking,
      scoreBreakdown: [],
      positiveContributors: [],
      negativeContributors: [],
      intelligenceSourcesUsed: buildIntelligenceSourcesUsed(facility),
      missingIntelligence: [],
      humanNarrativeExplanation: "",
      scoreTraceability: [],
      audit: {
        executedFormula: "final_score = tiered_match_quality(critical, important, optional) - mismatch_penalties",
        finalScore: Math.round(totalScore),
        categoryRows: [],
        bonuses: [],
        penalties: [],
        criteria: [],
        tierSummaries: [],
        matchQualityExplanation: "",
        confidence: {
          confidenceScore: confidencePercent,
          missingDataImpact: "",
          sourceCoverage: "",
          lastIntelligenceRefresh: new Date().toISOString(),
        },
      },
    };

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
      report,
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
    } else if (above) {
      item.rankReason = `Ranked #${index + 1} because it trails #${index} mainly on ${item.contributionHighlights[item.contributionHighlights.length - 1].label.toLowerCase()}, but stays competitive on ${item.contributionHighlights[0].label.toLowerCase()}.`;
    } else if (!below) {
      item.rankReason = `Ranked #${index + 1} after higher-ranked options showed stronger person-fit coverage.`;
    }

    item.report = buildIntelligenceReport(
      item.facility,
      state,
      item.priorityScores,
      persona,
      item.contributionHighlights,
      item.totalScore,
      item.report.confidenceScore,
      accepted,
      index,
      item.missingInformation,
      item.positives,
      item.negatives,
      buildMatchQualityResult(item.facility, state, item.priorityScores),
    );
  });

  const qualityCheck = buildQualityCheck(accepted, signalRoles);

  return {
    accepted,
    rejected,
    qualityCheck,
    persona,
  };
}
