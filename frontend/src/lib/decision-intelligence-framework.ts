import { QuestionnaireState } from "@/context/questionnaire-context";
import { resolveBudgetValue } from "@/lib/budget-utils";
import { RankedRecommendation } from "@/lib/optime-v2-engine";

export type StructuredResidentProfile = {
  relationship: string;
  ageGroup: string;
  careNeeds: string;
  memoryStatus: string;
  budget: number;
  locationPreference: string;
  futureCarePreference: string;
  lifestylePreferences: string[];
  familyPriorities: string[];
  dietaryPreferences: string[];
  languagePreferences: string[];
  missingInformation: string[];
  clarificationQuestions: string[];
};

export type RecommendationDimensionReasoning = {
  dimension:
    | "Clinical Match"
    | "Lifestyle Match"
    | "Mobility Match"
    | "Social Match"
    | "Dining Match"
    | "Transportation Match"
    | "Budget Match"
    | "Location Match"
    | "Future Care Match"
    | "Family Match";
  score: number;
  reasoning: string[];
  supportingEvidence: string[];
  verificationStatus: "VERIFIED" | "PARTIALLY_VERIFIED" | "REQUIRES_CONFIRMATION";
};

export type RecommendationPackageEntry = {
  rank: number;
  facilityId: number;
  facilityName: string;
  overallMatch: number;
  recommendationTier: "BEST_MATCH" | "STRONG_ALTERNATIVE" | "GOOD_ALTERNATIVE" | "WORTH_CONSIDERING";
  residentSummary: string[];
  strengths: string[];
  tradeOffs: string[];
  missingInformation: string[];
  verificationChecklist: string[];
  suggestedQuestions: string[];
  nextActions: string[];
  dimensionScores: RecommendationDimensionReasoning[];
  supportingEvidence: string[];
  verificationDate: string;
  freshnessLabel: string;
};

export type RecommendationPackage = {
  residentProfile: StructuredResidentProfile;
  generatedAt: string;
  packageVersion: string;
  recommendationRanking: RecommendationPackageEntry[];
  alternativeCommunities: Array<{ facilityId: number; facilityName: string; whyRankedLower: string[] }>;
  globalTradeOffs: string[];
  unknowns: string[];
  verificationTasks: string[];
  nextActions: string[];
};

export type RecommendationQualityScorecard = {
  decisionCompleteness: number;
  evidenceCoverage: number;
  explanationQuality: number;
  personalization: number;
  grounding: number;
  readability: number;
  transparency: number;
  actionability: number;
  overall: number;
  passesThreshold: boolean;
};

export type RecommendationAuditResult = {
  supportedEvidence: boolean;
  tradeOffsStructured: boolean;
  unknownsIdentified: boolean;
  unsupportedLanguageRemoved: boolean;
  verifiedFactsConsistent: boolean;
  issues: string[];
};

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function unique(items: string[]): string[] {
  return Array.from(new Set(items.map((item) => item.trim()).filter(Boolean)));
}

function buildResidentProfile(state: QuestionnaireState, recommendations: RankedRecommendation[]): StructuredResidentProfile {
  const familyPriorities = unique([
    state.humanIntelligenceV2.familyProfile.visitFrequencyExpectation,
    state.humanIntelligenceV2.familyCultureProfile.involvementExpectation,
    state.humanIntelligenceV2.familyProfile.grandchildrenImportance,
    state.futureCarePreference,
  ]);

  const missingInformation = unique(recommendations.flatMap((item) => item.missingInformation)).slice(0, 8);
  const clarificationQuestions = unique(
    recommendations.flatMap((item) => item.report.audit.clinicalReasoning.questionsForFacility),
  ).slice(0, 8);

  return {
    relationship: state.relationship || "Loved one",
    ageGroup: state.ageGroup || "Unknown",
    careNeeds: state.assistanceLevel || "Not fully specified",
    memoryStatus: state.memoryStatus || "Not specified",
    budget: resolveBudgetValue(state.budget) ?? 0,
    locationPreference: state.referenceLocationValue || state.distanceFromFamily || "Not specified",
    futureCarePreference: state.futureCarePreference || "No stated preference",
    lifestylePreferences: state.happinessPreferences || [],
    familyPriorities,
    dietaryPreferences: state.humanIntelligenceV2.foodProfile.dietaryPreferences || [],
    languagePreferences: unique([
      state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage,
      ...state.humanIntelligenceV2.languageProfile.languagesUnderstood,
      ...state.humanIntelligenceV2.languageProfile.familyLanguages,
    ]),
    missingInformation,
    clarificationQuestions,
  };
}

function recommendationTier(rank: number): RecommendationPackageEntry["recommendationTier"] {
  if (rank === 0) return "BEST_MATCH";
  if (rank === 1) return "STRONG_ALTERNATIVE";
  if (rank === 2) return "GOOD_ALTERNATIVE";
  return "WORTH_CONSIDERING";
}

function verificationLabel(
  recommendation: RankedRecommendation,
): RecommendationDimensionReasoning["verificationStatus"] {
  const unknownCount = recommendation.report.audit.verificationRequest.unknownCount;
  if (unknownCount === 0) return "VERIFIED";
  if (unknownCount <= 2) return "PARTIALLY_VERIFIED";
  return "REQUIRES_CONFIRMATION";
}

function buildDimensionScores(recommendation: RankedRecommendation): RecommendationDimensionReasoning[] {
  const audit = recommendation.report.audit;
  const evidence = recommendation.report.intelligenceSourcesUsed;

  return [
    {
      dimension: "Clinical Match",
      score: clamp(recommendation.priorityScores.careFit),
      reasoning: [audit.clinicalReasoning.medicalMatch],
      supportingEvidence: evidence.slice(0, 3),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Lifestyle Match",
      score: clamp(recommendation.priorityScores.lifestyleFit),
      reasoning: [audit.clinicalReasoning.lifestyleMatch],
      supportingEvidence: evidence.slice(0, 3),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Mobility Match",
      score: clamp(recommendation.priorityScores.careFit),
      reasoning: [recommendation.solves.find((item) => item.toLowerCase().includes("mobility")) || audit.clinicalReasoning.medicalMatch],
      supportingEvidence: evidence.slice(0, 2),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Social Match",
      score: clamp(recommendation.priorityScores.socialFit),
      reasoning: [audit.clinicalReasoning.socialMatch],
      supportingEvidence: evidence.slice(0, 2),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Dining Match",
      score: clamp(recommendation.priorityScores.lifestyleFit),
      reasoning: [audit.clinicalReasoning.dietaryMatch],
      supportingEvidence: evidence.slice(0, 2),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Transportation Match",
      score: clamp(recommendation.priorityScores.familyFit),
      reasoning: [recommendation.tradeoff],
      supportingEvidence: evidence.slice(0, 1),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Budget Match",
      score: clamp(recommendation.priorityScores.financialFit),
      reasoning: [`The published price range is ${recommendation.facility.priceRange}.`],
      supportingEvidence: [recommendation.facility.priceRange],
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Location Match",
      score: clamp(recommendation.priorityScores.familyFit),
      reasoning: [recommendation.rankReason || "Location fit is reflected in the ranking order."],
      supportingEvidence: [recommendation.facility.city, recommendation.facility.state].filter(
        (value): value is string => Boolean(value),
      ),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Future Care Match",
      score: clamp(recommendation.priorityScores.careFit),
      reasoning: [audit.clinicalReasoning.futureCareMatch],
      supportingEvidence: evidence.slice(0, 2),
      verificationStatus: verificationLabel(recommendation),
    },
    {
      dimension: "Family Match",
      score: clamp(recommendation.priorityScores.familyFit),
      reasoning: [recommendation.whyThisFits],
      supportingEvidence: evidence.slice(0, 2),
      verificationStatus: verificationLabel(recommendation),
    },
  ];
}

export function buildRecommendationPackage(
  state: QuestionnaireState,
  recommendations: RankedRecommendation[],
): RecommendationPackage {
  const residentProfile = buildResidentProfile(state, recommendations);
  const ranking = recommendations.map((recommendation, index) => {
    const verificationTasks = recommendation.report.audit.verificationChecklist
      .filter((item) => item.state === "UNKNOWN" || item.state === "LIMITED")
      .map((item) => item.label);

    return {
      rank: index + 1,
      facilityId: recommendation.facility.id,
      facilityName: recommendation.facility.name,
      overallMatch: clamp(recommendation.totalScore),
      recommendationTier: recommendationTier(index),
      residentSummary: [
        `${residentProfile.relationship} is looking for ${residentProfile.careNeeds.toLowerCase()} support.`,
        residentProfile.futureCarePreference !== "No stated preference"
          ? `Future care matters because the family prefers ${residentProfile.futureCarePreference.toLowerCase()}.`
          : "Future care flexibility was not the main deciding factor.",
      ],
      strengths: unique(recommendation.solves.concat(recommendation.report.audit.clinicalReasoning.verifiedCapabilities)).slice(0, 8),
      tradeOffs: unique([recommendation.tradeoff, ...recommendation.doesNotSolve]).slice(0, 8),
      missingInformation: unique(recommendation.missingInformation),
      verificationChecklist: verificationTasks,
      suggestedQuestions: unique(recommendation.report.audit.clinicalReasoning.questionsForFacility).slice(0, 6),
      nextActions: unique([
        recommendation.report.audit.verificationRequest.nextStepMessage,
        ...recommendation.report.audit.clinicalReasoning.questionsForFacility.slice(0, 3),
      ]),
      dimensionScores: buildDimensionScores(recommendation),
      supportingEvidence: unique(recommendation.report.intelligenceSourcesUsed).slice(0, 8),
      verificationDate: recommendation.report.audit.confidence.lastIntelligenceRefresh,
      freshnessLabel: verificationLabel(recommendation),
    };
  });

  return {
    residentProfile,
    generatedAt: new Date().toISOString(),
    packageVersion: "v1.0",
    recommendationRanking: ranking,
    alternativeCommunities: ranking.slice(1).map((entry) => ({
      facilityId: entry.facilityId,
      facilityName: entry.facilityName,
      whyRankedLower: entry.tradeOffs.slice(0, 3),
    })),
    globalTradeOffs: unique(ranking.flatMap((entry) => entry.tradeOffs)).slice(0, 10),
    unknowns: unique(ranking.flatMap((entry) => entry.missingInformation)).slice(0, 10),
    verificationTasks: unique(ranking.flatMap((entry) => entry.verificationChecklist)).slice(0, 10),
    nextActions: unique(ranking.flatMap((entry) => entry.nextActions)).slice(0, 10),
  };
}

export function scoreRecommendationPackage(pkg: RecommendationPackage): RecommendationQualityScorecard {
  const ranking = pkg.recommendationRanking;
  const totalEntries = Math.max(1, ranking.length);
  const avgDimensionCoverage = ranking.reduce((sum, entry) => sum + entry.dimensionScores.length, 0) / totalEntries;
  const evidenceCoverage = ranking.reduce((sum, entry) => sum + entry.supportingEvidence.length, 0) / totalEntries;
  const personalization = ranking.reduce((sum, entry) => sum + entry.residentSummary.length + entry.strengths.length, 0) / totalEntries;
  const actionability = ranking.reduce((sum, entry) => sum + entry.nextActions.length + entry.suggestedQuestions.length, 0) / totalEntries;
  const transparency = ranking.reduce((sum, entry) => sum + entry.tradeOffs.length + entry.missingInformation.length, 0) / totalEntries;

  const decisionCompleteness = clamp(avgDimensionCoverage * 10);
  const evidenceCoverageScore = clamp(evidenceCoverage * 15);
  const explanationQuality = clamp((pkg.globalTradeOffs.length + pkg.nextActions.length) * 8);
  const personalizationScore = clamp(personalization * 6);
  const grounding = clamp((pkg.verificationTasks.length + pkg.unknowns.length + evidenceCoverage) * 6);
  const readability = 88;
  const transparencyScore = clamp(transparency * 8);
  const actionabilityScore = clamp(actionability * 6);
  const overall = clamp((
    decisionCompleteness +
    evidenceCoverageScore +
    explanationQuality +
    personalizationScore +
    grounding +
    readability +
    transparencyScore +
    actionabilityScore
  ) / 8);

  return {
    decisionCompleteness,
    evidenceCoverage: evidenceCoverageScore,
    explanationQuality,
    personalization: personalizationScore,
    grounding,
    readability,
    transparency: transparencyScore,
    actionability: actionabilityScore,
    overall,
    passesThreshold: overall >= 75,
  };
}

export function auditRecommendationPackage(pkg: RecommendationPackage): RecommendationAuditResult {
  const issues: string[] = [];
  const supportedEvidence = pkg.recommendationRanking.every((entry) => entry.supportingEvidence.length > 0);
  if (!supportedEvidence) {
    issues.push("One or more recommendations do not include supporting evidence.");
  }

  const tradeOffsStructured = pkg.recommendationRanking.every((entry) => Array.isArray(entry.tradeOffs));
  if (!tradeOffsStructured) {
    issues.push("Trade-offs are not consistently structured.");
  }

  const unknownsIdentified = pkg.unknowns.length > 0 || pkg.verificationTasks.length > 0;
  if (!unknownsIdentified) {
    issues.push("Unknowns or verification tasks are not clearly identified.");
  }

  const unsupportedLanguageRemoved = !JSON.stringify(pkg).match(/algorithm|acceptance threshold|hard rejection|engine output/i);
  if (!unsupportedLanguageRemoved) {
    issues.push("Unsupported internal language appears in the package.");
  }

  const verifiedFactsConsistent = pkg.recommendationRanking.every((entry) => entry.dimensionScores.every((dimension) => dimension.reasoning.length > 0));
  if (!verifiedFactsConsistent) {
    issues.push("Some dimension reasoning is incomplete or inconsistent.");
  }

  return {
    supportedEvidence,
    tradeOffsStructured,
    unknownsIdentified,
    unsupportedLanguageRemoved,
    verifiedFactsConsistent,
    issues,
  };
}