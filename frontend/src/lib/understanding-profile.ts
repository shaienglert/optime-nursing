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
};

type DomainAssessment = {
  key: DomainKey;
  label: string;
  covered: boolean;
  signalCount: number;
  quality: number;
  weight: number;
  isCritical: boolean;
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

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
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
    financialProfile: countActiveSignals([inputs.budget]),
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
    { key: "careNeeds", label: "Care needs", signalCount: domainSignals.careNeeds, quality: qualityFromSignals(domainSignals.careNeeds), weight: DOMAIN_WEIGHTS.careNeeds, covered: domainSignals.careNeeds > 0, isCritical: true },
    { key: "lifestyle", label: "Lifestyle", signalCount: domainSignals.lifestyle, quality: qualityFromSignals(domainSignals.lifestyle), weight: DOMAIN_WEIGHTS.lifestyle, covered: domainSignals.lifestyle > 0, isCritical: false },
    { key: "socialPreferences", label: "Social preferences", signalCount: domainSignals.socialPreferences, quality: qualityFromSignals(domainSignals.socialPreferences), weight: DOMAIN_WEIGHTS.socialPreferences, covered: domainSignals.socialPreferences > 0, isCritical: false },
    { key: "financialProfile", label: "Financial profile", signalCount: domainSignals.financialProfile, quality: qualityFromSignals(domainSignals.financialProfile), weight: DOMAIN_WEIGHTS.financialProfile, covered: domainSignals.financialProfile > 0, isCritical: true },
    { key: "culturalPreferences", label: "Cultural preferences", signalCount: domainSignals.culturalPreferences, quality: qualityFromSignals(domainSignals.culturalPreferences), weight: DOMAIN_WEIGHTS.culturalPreferences, covered: domainSignals.culturalPreferences > 0, isCritical: false },
    { key: "familyProximity", label: "Family proximity", signalCount: domainSignals.familyProximity, quality: qualityFromSignals(domainSignals.familyProximity), weight: DOMAIN_WEIGHTS.familyProximity, covered: domainSignals.familyProximity > 0, isCritical: true },
    { key: "futureCarePlanning", label: "Future care planning", signalCount: domainSignals.futureCarePlanning, quality: qualityFromSignals(domainSignals.futureCarePlanning), weight: DOMAIN_WEIGHTS.futureCarePlanning, covered: domainSignals.futureCarePlanning > 0, isCritical: false },
  ];

  const rawScore = domains.reduce((sum, domain) => sum + domain.weight * domain.quality, 0);
  const missingCriticalCount = CRITICAL_DOMAINS.filter((key) => !domains.find((domain) => domain.key === key)?.covered).length;
  const criticalPenaltyMultiplier = [1, 0.72, 0.52, 0.38][missingCriticalCount] ?? 0.38;
  const understandingScore = clampScore(rawScore * criticalPenaltyMultiplier - missingCriticalCount * 6);

  const completedDomainCount = domains.filter((domain) => domain.covered).length;
  const criticalCoverageRate = (CRITICAL_DOMAINS.length - missingCriticalCount) / CRITICAL_DOMAINS.length;
  const domainCoverageRate = completedDomainCount / domains.length;
  const recommendationConfidence = clampScore(
    understandingScore * 0.55 +
      domainCoverageRate * 25 +
      criticalCoverageRate * 20 -
      missingCriticalCount * 8,
  );

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
      active: domains.find((domain) => domain.key === "familyProximity")?.covered ?? false,
    },
    {
      icon: "🏥",
      label: "Future care continuity",
      active: domains.find((domain) => domain.key === "futureCarePlanning")?.covered ?? false,
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
