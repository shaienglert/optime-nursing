type DomainKey =
  | "careNeeds"
  | "lifestyle"
  | "socialPreferences"
  | "financialProfile"
  | "culturalPreferences"
  | "familyProximity"
  | "futureCarePlanning";

export type UnderstandingInputs = {
  relationship: string;
  primaryAssistanceLevel: string;
  futureCarePreference: string;
  memoryStatus: string;
  budget: number;
  happinessPreferences: string[];
  preferredEnvironment: string[];
  socialInteractionFrequency: string;
  newFriendsImportance: string;
  preferredSocialIntensity: string;
  hobbyParticipation: string[];
  religionImportance: string;
  preferredSpokenLanguage: string;
  faithTraditions: string[];
  dietaryPreferences: string[];
  whatFeelsLikeHome: string[];
  familyVisitExpectation: string;
  visitFrequencyExpectation: string;
  normalDriveTime: string;
  parentCurrentHome: string;
  primaryCaregiverHome: string;
  familyCenterOfGravity: string;
  agingInPlaceImportance: string;
  avoidFutureMovesPreference: string;
  continuumOfCarePreference: string;
  secureMemoryNeighborhoodNeed: string;
  familiarLanguageRequirement: string;
  petOwnershipImportance: string;
  distancePreference?: string;
  languagePreferenceImportance?: string;
  petPreferenceImportance?: string;
};

export type CoverageState = "UNKNOWN" | "NOT_IMPORTANT" | "PROVIDED";

type DomainAssessment = {
  key: DomainKey;
  label: string;
  covered: boolean;
  signalCount: number;
  quality: number;
  weight: number;
  isCritical: boolean;
  coverageScore: number;
  reason: string;
  penaltyApplied: number;
  intentionalOmission: boolean;
  coverageState: CoverageState;
};

export type JourneyIcon = {
  icon: string;
  label: string;
  active: boolean;
};

export type UnderstandingProfile = {
  understandingScore: number;
  recommendationConfidence: number;
  statusText: string;
  colorBand: {
    label: string;
    textClass: string;
    bgClass: string;
    ringClass: string;
  };
  personIcon: string;
  journeyIcons: JourneyIcon[];
  journeyProgressPercent: number;
  completedDomainCount: number;
  domains: DomainAssessment[];
};

export type UnderstandingDomainContribution = {
  domainName: string;
  coverageScore: number;
  reason: string;
  penaltyApplied: number;
  intentionalOmission: boolean;
  coverageState: CoverageState;
};

export type UnderstandingDiagnostics = {
  legacyUnderstandingScore: number;
  correctedUnderstandingScore: number;
  correctedRecommendationConfidence: number;
  delta: number;
  domainContributions: UnderstandingDomainContribution[];
  penalties: Array<{ domainName: string; penaltyApplied: number; reason: string }>;
};

const DOMAIN_WEIGHTS: Record<DomainKey, number> = {
  careNeeds: 26,
  lifestyle: 13,
  socialPreferences: 12,
  financialProfile: 14,
  culturalPreferences: 11,
  familyProximity: 14,
  futureCarePlanning: 10,
};

const CRITICAL_DOMAINS: DomainKey[] = ["careNeeds", "financialProfile", "familyProximity"];
const DEFAULT_BUDGET = 7000;

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function normalizeText(value: string): string {
  return value.trim().toLowerCase();
}

function isNotImportantText(value: string): boolean {
  const normalized = normalizeText(value);
  if (!normalized) return false;
  return [
    "not important",
    "no preference",
    "none",
    "not used",
    "distance not used",
    "distance not important",
    "not needed",
    "no religion preference",
    "no language preference",
    "no pet preference",
  ].some((token) => normalized.includes(token));
}

function signalStatus(value: string | number | string[] | undefined | null, treatZeroAsUnknown = true): CoverageState {
  if (Array.isArray(value)) {
    return value.length > 0 ? "PROVIDED" : "UNKNOWN";
  }
  if (typeof value === "number") {
    if (treatZeroAsUnknown && value <= 0) return "UNKNOWN";
    return "PROVIDED";
  }
  if (typeof value === "string") {
    if (!value.trim()) return "UNKNOWN";
    return isNotImportantText(value) ? "NOT_IMPORTANT" : "PROVIDED";
  }
  return "UNKNOWN";
}

function isAnswered(value: string | number | string[] | undefined | null, defaultValue: string | number | undefined = undefined): boolean {
  if (value === undefined || value === null) return false;

  if (typeof value === "string") {
    return value.trim().length > 0;
  }

  if (Array.isArray(value)) {
    return value.length > 0;
  }

  if (defaultValue !== undefined) {
    return value !== defaultValue;
  }

  return true;
}

function signalStatusFromMultiple(values: Array<string | number | string[] | undefined | null>): CoverageState {
  if (values.some((value) => signalStatus(value) === "PROVIDED")) return "PROVIDED";
  if (values.some((value) => signalStatus(value) === "NOT_IMPORTANT")) return "NOT_IMPORTANT";
  return "UNKNOWN";
}

function scoreFromStatuses(statuses: CoverageState[]): number {
  if (statuses.length === 0) return 0;
  const knownCount = statuses.filter((status) => status !== "UNKNOWN").length;
  return Math.round((knownCount / statuses.length) * 100);
}

function qualityFromCoverageScore(coverageScore: number): number {
  return Math.max(0, Math.min(1, coverageScore / 100));
}

function countActiveSignals(values: Array<string | number | string[] | undefined | null>): number {
  return values.reduce<number>((count, value) => {
    if (Array.isArray(value)) {
      return count + (value.length > 0 ? 1 : 0);
    }
    if (typeof value === "number") {
      return count + (value > 0 ? 1 : 0);
    }
    if (typeof value === "string") {
      return count + (value.trim() ? 1 : 0);
    }
    return count;
  }, 0);
}

function qualityFromSignals(signalCount: number): number {
  if (signalCount <= 0) return 0;
  return Math.min(1, 0.45 + (signalCount - 1) * 0.18);
}

function calculateLegacyUnderstandingScore(inputs: UnderstandingInputs): number {
  const domainSignals: Record<DomainKey, number> = {
    careNeeds: countActiveSignals([
      inputs.primaryAssistanceLevel,
      inputs.memoryStatus,
      inputs.agingInPlaceImportance,
      inputs.secureMemoryNeighborhoodNeed,
    ]),
    lifestyle: countActiveSignals([
      inputs.happinessPreferences,
      inputs.preferredEnvironment,
    ]),
    socialPreferences: countActiveSignals([
      inputs.socialInteractionFrequency,
      inputs.newFriendsImportance,
      inputs.preferredSocialIntensity,
      inputs.hobbyParticipation,
    ]),
    financialProfile: countActiveSignals([isAnswered(inputs.budget, DEFAULT_BUDGET) ? inputs.budget : undefined]),
    culturalPreferences: countActiveSignals([
      inputs.religionImportance,
      inputs.preferredSpokenLanguage,
      inputs.faithTraditions,
      inputs.dietaryPreferences,
      inputs.whatFeelsLikeHome,
    ]),
    familyProximity: countActiveSignals([
      inputs.familyVisitExpectation || inputs.visitFrequencyExpectation,
      inputs.normalDriveTime,
      inputs.parentCurrentHome,
      inputs.primaryCaregiverHome,
      inputs.familyCenterOfGravity,
    ]),
    futureCarePlanning: countActiveSignals([
      inputs.futureCarePreference,
      inputs.avoidFutureMovesPreference,
      inputs.continuumOfCarePreference,
      inputs.familiarLanguageRequirement,
    ]),
  };

  const domains: DomainAssessment[] = [
    { key: "careNeeds", label: "Care needs", signalCount: domainSignals.careNeeds, quality: qualityFromSignals(domainSignals.careNeeds), weight: DOMAIN_WEIGHTS.careNeeds, covered: domainSignals.careNeeds > 0, isCritical: true, coverageScore: Math.round(qualityFromSignals(domainSignals.careNeeds) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.careNeeds > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "lifestyle", label: "Lifestyle", signalCount: domainSignals.lifestyle, quality: qualityFromSignals(domainSignals.lifestyle), weight: DOMAIN_WEIGHTS.lifestyle, covered: domainSignals.lifestyle > 0, isCritical: false, coverageScore: Math.round(qualityFromSignals(domainSignals.lifestyle) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.lifestyle > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "socialPreferences", label: "Social preferences", signalCount: domainSignals.socialPreferences, quality: qualityFromSignals(domainSignals.socialPreferences), weight: DOMAIN_WEIGHTS.socialPreferences, covered: domainSignals.socialPreferences > 0, isCritical: false, coverageScore: Math.round(qualityFromSignals(domainSignals.socialPreferences) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.socialPreferences > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "financialProfile", label: "Financial profile", signalCount: domainSignals.financialProfile, quality: qualityFromSignals(domainSignals.financialProfile), weight: DOMAIN_WEIGHTS.financialProfile, covered: domainSignals.financialProfile > 0, isCritical: true, coverageScore: Math.round(qualityFromSignals(domainSignals.financialProfile) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.financialProfile > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "culturalPreferences", label: "Cultural preferences", signalCount: domainSignals.culturalPreferences, quality: qualityFromSignals(domainSignals.culturalPreferences), weight: DOMAIN_WEIGHTS.culturalPreferences, covered: domainSignals.culturalPreferences > 0, isCritical: false, coverageScore: Math.round(qualityFromSignals(domainSignals.culturalPreferences) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.culturalPreferences > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "familyProximity", label: "Family proximity", signalCount: domainSignals.familyProximity, quality: qualityFromSignals(domainSignals.familyProximity), weight: DOMAIN_WEIGHTS.familyProximity, covered: domainSignals.familyProximity > 0, isCritical: true, coverageScore: Math.round(qualityFromSignals(domainSignals.familyProximity) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.familyProximity > 0 ? "PROVIDED" : "UNKNOWN" },
    { key: "futureCarePlanning", label: "Future care planning", signalCount: domainSignals.futureCarePlanning, quality: qualityFromSignals(domainSignals.futureCarePlanning), weight: DOMAIN_WEIGHTS.futureCarePlanning, covered: domainSignals.futureCarePlanning > 0, isCritical: false, coverageScore: Math.round(qualityFromSignals(domainSignals.futureCarePlanning) * 100), reason: "Legacy scoring", penaltyApplied: 0, intentionalOmission: false, coverageState: domainSignals.futureCarePlanning > 0 ? "PROVIDED" : "UNKNOWN" },
  ];

  const rawScore = domains.reduce((sum, domain) => sum + domain.weight * domain.quality, 0);
  const missingCriticalCount = CRITICAL_DOMAINS.filter((key) => !domains.find((domain) => domain.key === key)?.covered).length;
  const criticalPenaltyMultiplier = [1, 0.72, 0.52, 0.38][missingCriticalCount] ?? 0.38;
  return clampScore(rawScore * criticalPenaltyMultiplier - missingCriticalCount * 6);
}

function buildDomainAssessments(inputs: UnderstandingInputs): DomainAssessment[] {
  const careStatuses: CoverageState[] = [
    signalStatus(inputs.primaryAssistanceLevel),
    signalStatus(inputs.memoryStatus),
    signalStatus(inputs.agingInPlaceImportance),
    signalStatus(inputs.secureMemoryNeighborhoodNeed),
  ];

  const lifestyleStatuses: CoverageState[] = [
    signalStatus(inputs.happinessPreferences),
    signalStatus(inputs.preferredEnvironment),
    signalStatus(inputs.petPreferenceImportance || inputs.petOwnershipImportance),
  ];

  const socialStatuses: CoverageState[] = [
    signalStatus(inputs.socialInteractionFrequency),
    signalStatus(inputs.newFriendsImportance),
    signalStatus(inputs.preferredSocialIntensity),
    signalStatus(inputs.hobbyParticipation),
  ];

  const financialStatuses: CoverageState[] = [signalStatus(isAnswered(inputs.budget, DEFAULT_BUDGET) ? inputs.budget : undefined)];

  const culturalStatuses: CoverageState[] = [
    signalStatus(inputs.religionImportance),
    signalStatus(inputs.languagePreferenceImportance || inputs.preferredSpokenLanguage),
    signalStatus(inputs.faithTraditions),
    signalStatus(inputs.dietaryPreferences),
    signalStatus(inputs.whatFeelsLikeHome),
  ];

  const familyPreferenceStatus = signalStatusFromMultiple([
    inputs.distancePreference,
    inputs.familyVisitExpectation,
    inputs.visitFrequencyExpectation,
  ]);
  const familyStatuses: CoverageState[] = [
    familyPreferenceStatus,
    signalStatus(inputs.normalDriveTime),
    signalStatus(inputs.parentCurrentHome),
    signalStatus(inputs.primaryCaregiverHome),
    signalStatus(inputs.familyCenterOfGravity),
  ];

  const futureStatuses: CoverageState[] = [
    signalStatus(inputs.futureCarePreference),
    signalStatus(inputs.avoidFutureMovesPreference),
    signalStatus(inputs.continuumOfCarePreference),
    signalStatus(inputs.familiarLanguageRequirement),
  ];

  const familyIntentionalOmission = familyPreferenceStatus === "NOT_IMPORTANT";

  const domains: DomainAssessment[] = [
    {
      key: "careNeeds",
      label: "Care needs",
      signalCount: careStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(careStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(careStatuses)),
      weight: DOMAIN_WEIGHTS.careNeeds,
      covered: scoreFromStatuses(careStatuses) >= 100,
      isCritical: true,
      coverageState: careStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : careStatuses.some((status) => status === "PROVIDED") ? "PROVIDED" : "NOT_IMPORTANT",
      intentionalOmission: false,
      penaltyApplied: 0,
      reason: scoreFromStatuses(careStatuses) >= 100 ? "All care understanding signals are answered." : "Some care understanding signals are still unknown.",
    },
    {
      key: "lifestyle",
      label: "Lifestyle",
      signalCount: lifestyleStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(lifestyleStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(lifestyleStatuses)),
      weight: DOMAIN_WEIGHTS.lifestyle,
      covered: scoreFromStatuses(lifestyleStatuses) >= 100,
      isCritical: false,
      coverageState: lifestyleStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : lifestyleStatuses.some((status) => status === "PROVIDED") ? "PROVIDED" : "NOT_IMPORTANT",
      intentionalOmission: lifestyleStatuses.every((status) => status === "NOT_IMPORTANT"),
      penaltyApplied: 0,
      reason: lifestyleStatuses.every((status) => status === "NOT_IMPORTANT")
        ? "Lifestyle preferences were intentionally marked as not important."
        : scoreFromStatuses(lifestyleStatuses) >= 100
          ? "Lifestyle understanding is complete."
          : "Some lifestyle details remain unknown.",
    },
    {
      key: "socialPreferences",
      label: "Social preferences",
      signalCount: socialStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(socialStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(socialStatuses)),
      weight: DOMAIN_WEIGHTS.socialPreferences,
      covered: scoreFromStatuses(socialStatuses) >= 100,
      isCritical: false,
      coverageState: socialStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : socialStatuses.some((status) => status === "PROVIDED") ? "PROVIDED" : "NOT_IMPORTANT",
      intentionalOmission: socialStatuses.every((status) => status === "NOT_IMPORTANT"),
      penaltyApplied: 0,
      reason: scoreFromStatuses(socialStatuses) >= 100 ? "Social preference understanding is complete." : "Some social preference details remain unknown.",
    },
    {
      key: "financialProfile",
      label: "Financial profile",
      signalCount: financialStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(financialStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(financialStatuses)),
      weight: DOMAIN_WEIGHTS.financialProfile,
      covered: scoreFromStatuses(financialStatuses) >= 100,
      isCritical: true,
      coverageState: financialStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : "PROVIDED",
      intentionalOmission: false,
      penaltyApplied: 0,
      reason: scoreFromStatuses(financialStatuses) >= 100 ? "Budget information is provided." : "Budget information is missing.",
    },
    {
      key: "culturalPreferences",
      label: "Cultural preferences",
      signalCount: culturalStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(culturalStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(culturalStatuses)),
      weight: DOMAIN_WEIGHTS.culturalPreferences,
      covered: scoreFromStatuses(culturalStatuses) >= 100,
      isCritical: false,
      coverageState: culturalStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : culturalStatuses.some((status) => status === "PROVIDED") ? "PROVIDED" : "NOT_IMPORTANT",
      intentionalOmission: culturalStatuses.some((status) => status === "NOT_IMPORTANT"),
      penaltyApplied: 0,
      reason: culturalStatuses.some((status) => status === "NOT_IMPORTANT")
        ? "Religion/language was explicitly marked as not important and receives full coverage credit for those signals."
        : scoreFromStatuses(culturalStatuses) >= 100
          ? "Cultural preference understanding is complete."
          : "Some cultural preference details remain unknown.",
    },
    {
      key: "familyProximity",
      label: "Family proximity",
      signalCount: familyStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: familyIntentionalOmission ? 100 : scoreFromStatuses(familyStatuses),
      quality: qualityFromCoverageScore(familyIntentionalOmission ? 100 : scoreFromStatuses(familyStatuses)),
      weight: DOMAIN_WEIGHTS.familyProximity,
      covered: (familyIntentionalOmission ? 100 : scoreFromStatuses(familyStatuses)) >= 100,
      isCritical: true,
      coverageState: familyIntentionalOmission
        ? "NOT_IMPORTANT"
        : familyStatuses.every((status) => status === "UNKNOWN")
          ? "UNKNOWN"
          : familyStatuses.some((status) => status === "PROVIDED")
            ? "PROVIDED"
            : "NOT_IMPORTANT",
      intentionalOmission: familyIntentionalOmission,
      penaltyApplied: 0,
      reason: familyIntentionalOmission
        ? "Distance was intentionally marked as not used; no understanding penalty is applied."
        : scoreFromStatuses(familyStatuses) >= 100
          ? "Family proximity understanding is complete."
          : "Family proximity still has unknown signals.",
    },
    {
      key: "futureCarePlanning",
      label: "Future care planning",
      signalCount: futureStatuses.filter((status) => status !== "UNKNOWN").length,
      coverageScore: scoreFromStatuses(futureStatuses),
      quality: qualityFromCoverageScore(scoreFromStatuses(futureStatuses)),
      weight: DOMAIN_WEIGHTS.futureCarePlanning,
      covered: scoreFromStatuses(futureStatuses) >= 100,
      isCritical: false,
      coverageState: futureStatuses.every((status) => status === "UNKNOWN") ? "UNKNOWN" : futureStatuses.some((status) => status === "PROVIDED") ? "PROVIDED" : "NOT_IMPORTANT",
      intentionalOmission: futureStatuses.every((status) => status === "NOT_IMPORTANT"),
      penaltyApplied: 0,
      reason: scoreFromStatuses(futureStatuses) >= 100 ? "Future care planning is fully specified." : "Some future care preferences remain unknown.",
    },
  ];

  return domains.map((domain) => {
    const penaltyApplied = Math.max(0, Math.round((domain.weight - domain.weight * domain.quality) * 100) / 100);
    return {
      ...domain,
      penaltyApplied,
    };
  });
}

export function calculateUnderstandingDiagnostics(inputs: UnderstandingInputs): UnderstandingDiagnostics {
  const legacyUnderstandingScore = calculateLegacyUnderstandingScore(inputs);
  const domains = buildDomainAssessments(inputs);
  const correctedUnderstandingScore = clampScore(domains.reduce((sum, domain) => sum + domain.weight * domain.quality, 0));
  const completedDomainCount = domains.filter((domain) => domain.coverageScore >= 100).length;
  const criticalCoverageRate = CRITICAL_DOMAINS.filter((key) => (domains.find((domain) => domain.key === key)?.coverageScore ?? 0) >= 100).length / CRITICAL_DOMAINS.length;
  const domainCoverageRate = completedDomainCount / domains.length;
  const correctedRecommendationConfidence = clampScore(
    correctedUnderstandingScore * 0.6 + domainCoverageRate * 20 + criticalCoverageRate * 20,
  );

  const domainContributions: UnderstandingDomainContribution[] = domains.map((domain) => ({
    domainName: domain.label,
    coverageScore: domain.coverageScore,
    reason: domain.reason,
    penaltyApplied: domain.penaltyApplied,
    intentionalOmission: domain.intentionalOmission,
    coverageState: domain.coverageState,
  }));

  return {
    legacyUnderstandingScore,
    correctedUnderstandingScore,
    correctedRecommendationConfidence,
    delta: correctedUnderstandingScore - legacyUnderstandingScore,
    domainContributions,
    penalties: domainContributions
      .filter((domain) => domain.penaltyApplied > 0)
      .map((domain) => ({ domainName: domain.domainName, penaltyApplied: domain.penaltyApplied, reason: domain.reason })),
  };
}

function statusFromScore(score: number): string {
  if (score < 30) return "Getting to know you";
  if (score < 60) return "Building your lifestyle profile";
  if (score < 85) return "Understanding what matters most";
  return "Ready for advisor-level recommendations";
}

function colorBandFromScore(score: number): UnderstandingProfile["colorBand"] {
  if (score < 20) {
    return {
      label: "Red",
      textClass: "text-[#b4332f]",
      bgClass: "from-[#ef7670] to-[#d8453f]",
      ringClass: "ring-[#e8b3b0]",
    };
  }
  if (score < 40) {
    return {
      label: "Orange",
      textClass: "text-[#a85018]",
      bgClass: "from-[#f3a35d] to-[#dc6e2f]",
      ringClass: "ring-[#e9c19f]",
    };
  }
  if (score < 60) {
    return {
      label: "Yellow",
      textClass: "text-[#8a6a05]",
      bgClass: "from-[#f5d862] to-[#e3b72c]",
      ringClass: "ring-[#eadca8]",
    };
  }
  if (score < 80) {
    return {
      label: "Green",
      textClass: "text-[#2f6f3d]",
      bgClass: "from-[#67c287] to-[#37985f]",
      ringClass: "ring-[#b6dcc2]",
    };
  }
  return {
    label: "Blue-green",
    textClass: "text-[#136972]",
    bgClass: "from-[#3ec8bd] to-[#1e9ea2]",
    ringClass: "ring-[#a9dedd]",
  };
}

export function calculateUnderstandingProfile(inputs: UnderstandingInputs): UnderstandingProfile {
  const diagnostics = calculateUnderstandingDiagnostics(inputs);
  const domains = buildDomainAssessments(inputs);
  const understandingScore = diagnostics.correctedUnderstandingScore;
  const recommendationConfidence = diagnostics.correctedRecommendationConfidence;
  const completedDomainCount = domains.filter((domain) => domain.coverageScore >= 100).length;

  const journeyIcons: JourneyIcon[] = [
    {
      icon: "🌳",
      label: "Outdoor preference",
      active: inputs.happinessPreferences.includes("Outdoor activities") || inputs.preferredEnvironment.includes("Quiet community"),
    },
    {
      icon: "🎭",
      label: "Social activities",
      active: inputs.happinessPreferences.includes("Social activities") || inputs.hobbyParticipation.includes("Social activities") || inputs.socialInteractionFrequency === "Daily",
    },
    {
      icon: "☕",
      label: "Cafe lifestyle",
      active: inputs.happinessPreferences.includes("Good food") || inputs.preferredEnvironment.includes("Large active community"),
    },
    {
      icon: "🐕",
      label: "Pets",
      active: ["Important", "Very important", "High", "Very high"].includes(inputs.petOwnershipImportance),
    },
    {
      icon: "👨‍👩‍👧",
      label: "Family proximity",
      active: (domains.find((domain) => domain.key === "familyProximity")?.coverageScore ?? 0) >= 100,
    },
    {
      icon: "🏥",
      label: "Future care continuity",
      active: (domains.find((domain) => domain.key === "futureCarePlanning")?.coverageScore ?? 0) >= 100,
    },
  ];

  return {
    understandingScore,
    recommendationConfidence,
    statusText: statusFromScore(understandingScore),
    colorBand: colorBandFromScore(understandingScore),
    personIcon: inputs.relationship === "Couple" ? "👵👴" : "👵",
    journeyIcons,
    journeyProgressPercent: Math.round((completedDomainCount / domains.length) * 100),
    completedDomainCount,
    domains,
  };
}
