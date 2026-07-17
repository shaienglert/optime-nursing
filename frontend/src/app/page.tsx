"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { calculateUnderstandingProfile } from "@/lib/understanding-profile";
import { QUESTION_GRAPH, buildVisibilityAudit, validateQuestionGraph } from "@/lib/questionnaire-graph";
import { persistAdaptiveQuestionSignal, persistHumanIntelligenceScores } from "@/lib/api";

validateQuestionGraph(QUESTION_GRAPH);

const relationshipOptions = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Myself", "Couple", "Relative", "Friend"];

const genderOptions = ["Male", "Female", "Prefer not to say"];

const coupleAssistanceOptions = ["Husband", "Wife", "Both equally"];

const ageGroupOptions = ["60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"];

const assistanceOptions = [
  "Fully independent",
  "Light assistance",
  "Help with bathing",
  "Help with dressing",
  "Help with medications",
  "Daytime supervision",
  "24/7 support required",
  "Skilled nursing care",
];

const memoryOptions = ["No", "Occasionally forgetful", "Mild memory issues", "Significant memory issues", "Not sure"];

const happinessOptions = [
  "Social activities",
  "Movies",
  "Music",
  "Games",
  "Outdoor activities",
  "Quiet environment",
  "Religious community",
  "Exercise and wellness",
  "Good food",
  "Cultural activities",
];

const livingAloneOptions = ["Less than 1 year", "1-3 years", "3-5 years", "5+ years", "Not living alone"];

const socialInteractionOptions = ["Daily", "Several times weekly", "Weekly", "Biweekly", "Monthly or less"];

const importanceOptions = ["Not important", "Low", "Medium", "High", "Very high"];

const familyInvolvementOptions = ["1", "2", "3", "4", "5+"];

const visitExpectationOptions = ["Daily", "Several times weekly", "Weekly", "Biweekly", "Monthly"];

const widowStatusOptions = ["Yes", "No", "Not sure"];

const lossTimingOptions = ["Within 6 months", "6-12 months", "1-3 years", "Longer ago", "Not sure"];

const hospitalizationTimingOptions = ["Within 30 days", "1-3 months", "3-6 months", "More than 6 months ago"];

const socialChangeOptions = ["Much less social", "Somewhat less social", "About the same", "More social", "Not sure"];

const isolationConcernOptions = ["No", "Mild concern", "Moderate concern", "High concern"];

const decisionDynamicsOptions = ["Single decision maker", "Shared with spouse", "Shared among siblings", "Consensus", "Uncertain"];

const supportNetworkOptions = ["Strong", "Moderate", "Limited", "Emergency only"];

const coupleStayTogetherOptions = ["Must stay together", "Prefer staying together", "Open to separate care if needed"];

const religionImportanceOptions = ["Not important", "Somewhat important", "Important", "Very important"];

const yesNoOptions = ["Yes", "No", "Sometimes"];

const languageOptions = ["English", "Hebrew", "Spanish", "Russian", "French", "Portuguese", "Arabic", "Other"];

const languageCatalogOptions = [
  "English",
  "Spanish",
  "Hebrew",
  "Russian",
  "Mandarin",
  "Cantonese",
  "Arabic",
  "French",
  "Portuguese",
  "Haitian Creole",
  "Persian",
  "Yiddish",
  "Other",
];

const faithTraditionOptions = [
  "Jewish",
  "Catholic",
  "Protestant",
  "Orthodox Christian",
  "Muslim",
  "Hindu",
  "Buddhist",
  "Sikh",
  "No religion",
  "Other",
];

const religiousSupportNeedsOptions = [
  "Religious services",
  "Place of worship",
  "Chaplain",
  "Prayer space",
  "Holiday celebrations",
  "Dietary accommodations",
];

const homeComfortOptions = [
  "Familiar food",
  "Familiar language",
  "Shared traditions",
  "Similar cultural background",
  "Music",
  "Holidays",
  "Community celebrations",
  "Religious practices",
  "Family-centered culture",
];

const dietaryPreferenceOptions = [
  "Kosher",
  "Halal",
  "Vegetarian",
  "Vegan",
  "Mediterranean",
  "Asian cuisine",
  "Latin cuisine",
  "Low sodium",
  "Diabetic",
  "Gluten free",
  "Other",
];

const familyInvolvementExpectationOptions = ["Daily visits", "Multiple weekly visits", "Weekly visits", "Monthly visits"];

const familyDecisionRoleOptions = ["Resident decides", "Shared decision", "Family led"];

const communityEnvironmentOptions = [
  "Large active community",
  "Small family atmosphere",
  "Luxury environment",
  "Faith community",
  "Multicultural environment",
  "Language-specific community",
  "Quiet community",
];

const languageNeedScopeOptions = ["Social life", "Medical care", "Both", "Just daily comfort"];

const personalityOptions = ["Introvert", "Balanced", "Extrovert"];

const sizePreferenceOptions = ["Small community", "Medium community", "Large community", "No preference"];

const privacyOptions = ["Low", "Medium", "High", "Very high"];

const structureOptions = ["Structure", "Flexibility", "Balanced"];

const independenceOptions = ["Not important", "Somewhat important", "Important", "Very important"];

const attitudeOptions = ["Positive", "Cautious", "Anxious", "Reluctant", "Unsure"];

const bereavementOptions = ["No", "Yes, within 1 year", "Yes, within 3 years", "Yes, longer ago"];

const lonelinessOptions = ["Low", "Moderate", "High", "Very high"];

const memorySafetyOptions = ["Yes", "No", "Maybe"];

const familiarLanguageRequirementOptions = ["Yes", "No", "Maybe"];

const carePreferenceOptions = ["Not important", "Somewhat important", "Important", "Very important"];

const futureCarePreferenceOptions = [
  {
    label: "Independent communities only",
    description: "Show only communities designed for fully independent residents.",
  },
  {
    label: "Independent today, support available later",
    description: "Show communities that are independent today but offer assisted living or nursing care later if needed.",
  },
  {
    label: "Full continuum of care on one campus",
    description: "Prefer communities offering a complete care journey in one campus, including independent living, assisted living, memory care and skilled nursing.",
  },
  {
    label: "No preference",
    description: "Do not filter communities based on future care availability.",
  },
];

const DEFAULT_BUDGET = 7000;

const separationAcceptanceOptions = ["Yes", "No", "Only temporary"];

const distanceStrategyOptions = ["Closest to resident", "Closest to family", "Balanced location", "Emergency priority", "Family visit maximization"];

const careLevelWeights: Record<string, number> = {
  "Fully independent": 10,
  "Light assistance": 20,
  "Help with bathing": 20,
  "Help with dressing": 20,
  "Help with medications": 20,
  "Daytime supervision": 35,
  "24/7 support required": 40,
  "Skilled nursing care": 40,
};

function pickPrimaryAssistanceLevel(levels: string[]): string {
  if (levels.length === 0) return "";
  return [...levels].sort((left, right) => (careLevelWeights[right] || 0) - (careLevelWeights[left] || 0))[0];
}

function isAnswered(value: unknown, defaultValue: unknown = undefined): boolean {
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

type DistanceIntelligenceScores = {
  family_distance_score: number | null;
  visit_probability_score: number | null;
  emergency_access_score: number | null;
  grandchildren_access_score: number | null;
  travel_burden_score: number | null;
  family_engagement_score: number | null;
};

type DistanceIntelligenceInputs = {
  referenceLocations: {
    parentCurrentHome: string;
    primaryCaregiverHome: string;
    secondaryFamilyHomes: string;
    preferredHospital: string;
    placeOfWorship: string;
  };
  driveTimes: {
    normal: string;
    rushHour: string;
    emergency: string;
  };
  familyVisitExpectation: string;
  familyGeographyModel: {
    involvedFamilyMembers: string;
    familyCenterOfGravity: string;
    multiLocationOptimization: string;
  };
  emotionalDistanceFactors: {
    emergencyAccessImportance: string;
    spontaneousVisitsImportance: string;
    grandchildrenVisitsImportance: string;
  };
  careLevelWeight: number;
  optimizationStrategy: string;
  scores: DistanceIntelligenceScores;
  inferredConfidence: Record<string, number>;
};

function importanceToWeight(value: string): number {
  switch (value) {
    case "Very high":
    case "Very important":
    case "High":
    case "Important":
      return 1;
    case "Medium":
    case "Somewhat important":
      return 0.7;
    case "Low":
    case "Not important":
      return 0.4;
    default:
      return 0.5;
  }
}

function expectationToScore(value: string): number {
  switch (value) {
    case "Daily":
      return 100;
    case "Several times weekly":
      return 88;
    case "Weekly":
      return 76;
    case "Biweekly":
      return 62;
    case "Monthly":
      return 48;
    default:
      return 55;
  }
}

function driveTextToMinutes(value: string): number | null {
  const match = value.match(/(\d+)/);
  if (match) {
    return Number(match[1]);
  }
  if (value.toLowerCase().includes("daily") || value.toLowerCase().includes("close")) return 10;
  if (value.toLowerCase().includes("hour")) return 60;
  return null;
}

function optimizationStrategyBoost(strategy: string): number {
  switch (strategy) {
    case "Closest to resident":
      return 8;
    case "Closest to family":
      return 10;
    case "Balanced location":
      return 12;
    case "Emergency priority":
      return 14;
    case "Family visit maximization":
      return 15;
    default:
      return 0;
  }
}

function deriveCareLevelWeight(assistanceLevel: string, memoryStatus: string): number {
  if (assistanceLevel === "Skilled nursing care" || assistanceLevel === "24/7 support required") return 40;
  if (assistanceLevel === "Daytime supervision" || assistanceLevel === "Help with medications") return 35;
  if (memoryStatus !== "No" && memoryStatus !== "Not sure") return 35;
  if (assistanceLevel === "Fully independent") return 10;
  return 20;
}

function buildDistanceIntelligence(
  inputs: DistanceIntelligenceInputs,
): DistanceIntelligenceInputs {
  const normal = driveTextToMinutes(inputs.driveTimes.normal);
  const rush = driveTextToMinutes(inputs.driveTimes.rushHour);
  const emergency = driveTextToMinutes(inputs.driveTimes.emergency);
  const expectationScore = expectationToScore(inputs.familyVisitExpectation);
  const careWeight = inputs.careLevelWeight || 20;
  const strategyBoost = optimizationStrategyBoost(inputs.optimizationStrategy);
  const involvedFamilyMembers = Number.parseInt(inputs.familyGeographyModel.involvedFamilyMembers || "0", 10);
  const familyMemberCount = Number.isFinite(involvedFamilyMembers) ? involvedFamilyMembers : 0;
  const emergencyImportance = importanceToWeight(inputs.emotionalDistanceFactors.emergencyAccessImportance);
  const spontaneousImportance = importanceToWeight(inputs.emotionalDistanceFactors.spontaneousVisitsImportance);
  const grandchildrenImportance = importanceToWeight(inputs.emotionalDistanceFactors.grandchildrenVisitsImportance);

  const travelBurden = normal === null ? null : Math.max(0, 100 - normal * 2 - Math.max(0, (rush ?? normal) - normal) - Math.max(0, (emergency ?? normal) - normal));
  const emergencyAccess = emergency === null ? null : Math.max(0, Math.min(100, 100 - emergency + Math.round(emergencyImportance * 15) + (inputs.optimizationStrategy === "Emergency priority" ? 10 : 0)));
  const grandchildrenAccess = normal === null ? null : Math.max(0, Math.min(100, 100 - normal + Math.round(grandchildrenImportance * 12) + (inputs.optimizationStrategy === "Family visit maximization" ? 8 : 0)));

  const familyEngagement = Math.max(
    0,
    Math.min(
      100,
      Math.round((expectationScore * 0.35) + (familyMemberCount * 6) + (spontaneousImportance * 12) + (grandchildrenImportance * 10) + strategyBoost - Math.max(0, careWeight - 10) * 0.2),
    ),
  );

  const familyDistanceScore = normal === null ? null : Math.max(0, Math.min(100, Math.round(100 - normal + strategyBoost - Math.max(0, careWeight - 10) * 0.3)));
  const visitProbabilityScore = Math.max(0, Math.min(100, Math.round((expectationScore * 0.45) + (familyMemberCount * 4) + (spontaneousImportance * 10) + (strategyBoost * 0.7))));

  return {
    ...inputs,
    scores: {
      family_distance_score: familyDistanceScore,
      visit_probability_score: visitProbabilityScore,
      emergency_access_score: emergencyAccess,
      grandchildren_access_score: grandchildrenAccess,
      travel_burden_score: travelBurden,
      family_engagement_score: familyEngagement,
    },
    inferredConfidence: {
      family_distance_score: normal === null ? 30 : 90,
      visit_probability_score: expectationScore ? 80 : 25,
      emergency_access_score: emergency === null ? 25 : 85,
      grandchildren_access_score: normal === null ? 25 : 75,
      travel_burden_score: normal === null ? 20 : 80,
      family_engagement_score: familyMemberCount > 0 ? 75 : 30,
    },
    careLevelWeight: careWeight,
  };
}

function OptionChip({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
        isActive
          ? "border-[#7f9f88] bg-[#7f9f88] text-white shadow-[0_10px_24px_-12px_rgba(90,120,98,0.65)]"
          : "border-[#ddd2bf] bg-white text-[#5e5346] hover:border-[#97a89a] hover:text-[#516c5a]"
      }`}
    >
      {label}
    </button>
  );
}

function toggleOption(current: string[], option: string): string[] {
  return current.includes(option) ? current.filter((item) => item !== option) : [...current, option];
}

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function importanceRank(value: string): number {
  switch (value) {
    case "Not important":
      return 0;
    case "Low":
    case "Somewhat important":
      return 1;
    case "Medium":
    case "Important":
      return 2;
    case "High":
    case "Very important":
    case "Very high":
      return 3;
    default:
      return -1;
  }
}

function ctaCopy(relationship: string): string {
  if (relationship === "Myself") return "Find the right home for me";
  if (relationship === "Couple") return "Find the right home for us";
  if (relationship) return `Find the right home for ${relationship}`;
  return "Find the right home";
}

function scoreFromImportance(value: string): number {
  switch (value) {
    case "Very high":
    case "Very important":
      return 95;
    case "High":
    case "Important":
      return 82;
    case "Medium":
      return 68;
    case "Low":
    case "Somewhat important":
      return 52;
    case "Not important":
      return 35;
    default:
      return 50;
  }
}

function scoreFromFrequency(value: string): number {
  switch (value) {
    case "Daily":
      return 90;
    case "Several times weekly":
      return 80;
    case "Weekly":
      return 70;
    case "Biweekly":
      return 58;
    case "Monthly":
    case "Monthly or less":
      return 45;
    default:
      return 50;
  }
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function scoreFromReligionImportance(value: string): number {
  switch (value) {
    case "Very important":
      return 95;
    case "Important":
      return 82;
    case "Somewhat important":
      return 64;
    case "Not important":
      return 40;
    default:
      return 52;
  }
}

type CulturalSignalsInput = {
  widowStatus: string;
  lossTiming: string;
  livingAloneDuration: string;
  preferredSpokenLanguage: string;
  languagesUnderstood: string[];
  familyLanguages: string[];
  grandchildrenImportance: string;
  religionImportance: string;
  religiousSupportNeeds: string[];
  preferredSocialIntensity: string;
  introvertExtrovert: string;
  biggestFear: string;
  communitySizePreference: string;
};

function buildAdaptiveSignals(input: CulturalSignalsInput): Array<{
  questionKey: string;
  answer: string;
  signalType: string;
  weights: Record<string, number>;
  impactExplanation: string;
  infoGain: number;
}> {
  const signals: Array<{
    questionKey: string;
    answer: string;
    signalType: string;
    weights: Record<string, number>;
    impactExplanation: string;
    infoGain: number;
  }> = [];

  if (input.widowStatus === "Yes" && ["Within 6 months", "6-12 months"].includes(input.lossTiming)) {
    signals.push({
      questionKey: "widow_recent_loss",
      answer: `${input.widowStatus}:${input.lossTiming}`,
      signalType: "transition-risk",
      weights: {
        loneliness_risk: 30,
        social_match_weight: 20,
        family_proximity_weight: 15,
      },
      impactExplanation: "Recent partner loss increases emotional-transition support needs and prioritizes stronger social and family proximity matches.",
      infoGain: 28,
    });
  }

  if (["3-5 years", "5+ years"].includes(input.livingAloneDuration)) {
    signals.push({
      questionKey: "living_alone_long_term",
      answer: input.livingAloneDuration,
      signalType: "transition-risk",
      weights: {
        transition_risk: 15,
        community_size_preference_smaller: 20,
      },
      impactExplanation: "Long-term solo living suggests prioritizing easier transitions and smaller, relationship-oriented communities.",
      infoGain: 22,
    });
  }

  if (input.preferredSpokenLanguage === "Hebrew" || input.languagesUnderstood.includes("Hebrew") || input.familyLanguages.includes("Hebrew")) {
    signals.push({
      questionKey: "hebrew_required",
      answer: "Hebrew",
      signalType: "language-fit",
      weights: {
        language_match_weight: 20,
      },
      impactExplanation: "Hebrew communication needs increase priority for communities with Hebrew-speaking residents and staff support.",
      infoGain: 24,
    });
  }

  if (["High", "Very high"].includes(input.grandchildrenImportance)) {
    signals.push({
      questionKey: "grandchildren_high_involvement",
      answer: input.grandchildrenImportance,
      signalType: "family-engagement",
      weights: {
        family_distance_weight: 20,
        intergenerational_program_weight: 15,
      },
      impactExplanation: "Frequent grandchild involvement increases value of family-access geography and intergenerational programming.",
      infoGain: 20,
    });
  }

  if (["Important", "Very important"].includes(input.religionImportance)) {
    signals.push({
      questionKey: "religion_important",
      answer: input.religionImportance,
      signalType: "religious-fit",
      weights: {
        synagogue_weight: 15,
        kosher_weight: input.religiousSupportNeeds.includes("Dietary accommodations") ? 15 : 0,
        jewish_community_weight: 20,
      },
      impactExplanation: "Religious continuity is a strong comfort factor, increasing priority for faith services, faith community access, and dietary accommodations.",
      infoGain: 26,
    });
  }

  if (input.preferredSocialIntensity === "Extrovert" || input.introvertExtrovert === "Extrovert") {
    signals.push({
      questionKey: "highly_social_personality",
      answer: "Extrovert",
      signalType: "social-fit",
      weights: {
        activity_score_weight: 20,
        resident_engagement_weight: 15,
      },
      impactExplanation: "A highly social profile favors communities with robust daily activities and resident engagement culture.",
      infoGain: 18,
    });
  }

  if (input.preferredSocialIntensity === "Introvert" || input.introvertExtrovert === "Introvert") {
    signals.push({
      questionKey: "introverted_personality",
      answer: "Introvert",
      signalType: "community-style",
      weights: {
        small_community_weight: 20,
        privacy_weight: 15,
      },
      impactExplanation: "An introverted profile increases fit for quieter, smaller communities with privacy support.",
      infoGain: 16,
    });
  }

  if (input.biggestFear.toLowerCase().includes("independence")) {
    signals.push({
      questionKey: "fear_losing_independence",
      answer: input.biggestFear,
      signalType: "independence-fit",
      weights: {
        independence_support_weight: 20,
        autonomy_score_weight: 15,
      },
      impactExplanation: "Fear of losing independence increases weighting for autonomy-supportive programming and resident-directed routines.",
      infoGain: 21,
    });
  }

  if (input.communitySizePreference === "Small community") {
    signals.push({
      questionKey: "small_community_preference",
      answer: input.communitySizePreference,
      signalType: "community-style",
      weights: {
        small_community_weight: 18,
      },
      impactExplanation: "A small-community preference shifts matching toward lower-scale, relationship-dense settings.",
      infoGain: 14,
    });
  }

  return signals;
}

export default function Home() {
  const router = useRouter();
  const { setState } = useQuestionnaire();

  const [relationship, setRelationship] = useState("");
  const [gender, setGender] = useState("");
  const [coupleAssistance, setCoupleAssistance] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [assistanceLevels, setAssistanceLevels] = useState<string[]>([]);
  const [futureCarePreference, setFutureCarePreference] = useState("");
  const [memoryStatus, setMemoryStatus] = useState("");
  const [happinessPreferences, setHappinessPreferences] = useState<string[]>([]);
  const [budget, setBudget] = useState(DEFAULT_BUDGET);
  const [livingAloneDuration, setLivingAloneDuration] = useState("");
  const [socialInteractionFrequency, setSocialInteractionFrequency] = useState("");
  const [newFriendsImportance, setNewFriendsImportance] = useState("");
  const [hobbyParticipation, setHobbyParticipation] = useState<string[]>([]);
  const [preferredSocialIntensity, setPreferredSocialIntensity] = useState("");
  const [involvedFamilyMembers, setInvolvedFamilyMembers] = useState("");
  const [visitFrequencyExpectation, setVisitFrequencyExpectation] = useState("");
  const [grandchildrenPresence, setGrandchildrenPresence] = useState("");
  const [grandchildrenImportance, setGrandchildrenImportance] = useState("");
  const [familyDecisionDynamics, setFamilyDecisionDynamics] = useState("");
  const [emergencySupportNetwork, setEmergencySupportNetwork] = useState("");
  const [coupleStayTogetherPreference, setCoupleStayTogetherPreference] = useState("");
  const [coupleSameCareLevel, setCoupleSameCareLevel] = useState("");
  const [temporarySeparationAcceptance, setTemporarySeparationAcceptance] = useState("");
  const [widowStatus, setWidowStatus] = useState("");
  const [lossTiming, setLossTiming] = useState("");
  const [socialActivityChangeSinceLoss, setSocialActivityChangeSinceLoss] = useState("");
  const [socialInteractionNeed, setSocialInteractionNeed] = useState("");
  const [griefSupportInterest, setGriefSupportInterest] = useState("");
  const [religionImportance, setReligionImportance] = useState("");
  const [kosherRequirements, setKosherRequirements] = useState("");
  const [synagogueChurchAccess, setSynagogueChurchAccess] = useState("");
  const [holidayCelebrations, setHolidayCelebrations] = useState("");
  const [culturalIdentity, setCulturalIdentity] = useState("");
  const [israeliJewishCommunityPreference, setIsraeliJewishCommunityPreference] = useState("");
  const [jewishProgrammingImportance, setJewishProgrammingImportance] = useState("");
  const [churchAccessRequirement, setChurchAccessRequirement] = useState("");
  const [christianServiceRequirement, setChristianServiceRequirement] = useState("");
  const [halalMealsRequirement, setHalalMealsRequirement] = useState("");
  const [prayerFacilityRequirement, setPrayerFacilityRequirement] = useState("");
  const [preferredSpokenLanguage, setPreferredSpokenLanguage] = useState("");
  const [nativeLanguage, setNativeLanguage] = useState("");
  const [medicalDiscussionLanguage, setMedicalDiscussionLanguage] = useState("");
  const [socialInteractionLanguage, setSocialInteractionLanguage] = useState("");
  const [languageNeedScope, setLanguageNeedScope] = useState("");
  const [bilingualStaffRequired, setBilingualStaffRequired] = useState("");
  const [languagesUnderstood, setLanguagesUnderstood] = useState<string[]>([]);
  const [familyLanguages, setFamilyLanguages] = useState<string[]>([]);
  const [faithTraditions, setFaithTraditions] = useState<string[]>([]);
  const [religiousSupportNeeds, setReligiousSupportNeeds] = useState<string[]>([]);
  const [whatFeelsLikeHome, setWhatFeelsLikeHome] = useState<string[]>([]);
  const [dietaryPreferences, setDietaryPreferences] = useState<string[]>([]);
  const [familyInvolvementExpectation, setFamilyInvolvementExpectation] = useState("");
  const [familyDecisionRole, setFamilyDecisionRole] = useState("");
  const [preferredEnvironment, setPreferredEnvironment] = useState<string[]>([]);
  const [introvertExtrovert, setIntrovertExtrovert] = useState("");
  const [communitySizePreference, setCommunitySizePreference] = useState("");
  const [privacyImportance, setPrivacyImportance] = useState("");
  const [structureFlexibilityPreference, setStructureFlexibilityPreference] = useState("");
  const [independenceInterests, setIndependenceInterests] = useState<string[]>([]);
  const [drivingImportance, setDrivingImportance] = useState("");
  const [cookingImportance, setCookingImportance] = useState("");
  const [abilityToLeaveIndependently, setAbilityToLeaveIndependently] = useState("");
  const [petOwnershipImportance, setPetOwnershipImportance] = useState("");
  const [hostingFamilyImportance, setHostingFamilyImportance] = useState("");
  const [biggestFear, setBiggestFear] = useState("");
  const [attitudeTowardMove, setAttitudeTowardMove] = useState("");
  const [previousMoves, setPreviousMoves] = useState("");
  const [bereavementStatus, setBereavementStatus] = useState("");
  const [lonelinessRisk, setLonelinessRisk] = useState("");
  const [socialIsolationConcern, setSocialIsolationConcern] = useState("");
  const [recentHospitalization, setRecentHospitalization] = useState("");
  const [hospitalizationRecency, setHospitalizationRecency] = useState("");
  const [postHospitalRehabNeed, setPostHospitalRehabNeed] = useState("");
  const [wanderingConcerns, setWanderingConcerns] = useState("");
  const [agingInPlaceImportance, setAgingInPlaceImportance] = useState("");
  const [avoidFutureMovesPreference, setAvoidFutureMovesPreference] = useState("");
  const [continuumOfCarePreference, setContinuumOfCarePreference] = useState("");
  const [secureMemoryNeighborhoodNeed, setSecureMemoryNeighborhoodNeed] = useState("");
  const [familiarLanguageRequirement, setFamiliarLanguageRequirement] = useState("");
  const [parentCurrentHome, setParentCurrentHome] = useState("");
  const [primaryCaregiverHome, setPrimaryCaregiverHome] = useState("");
  const [secondaryFamilyHomes, setSecondaryFamilyHomes] = useState("");
  const [preferredHospital, setPreferredHospital] = useState("");
  const [placeOfWorship, setPlaceOfWorship] = useState("");
  const [normalDriveTime, setNormalDriveTime] = useState("");
  const [rushHourDriveTime, setRushHourDriveTime] = useState("");
  const [emergencyDriveTime, setEmergencyDriveTime] = useState("");
  const [familyVisitExpectation, setFamilyVisitExpectation] = useState("");
  const [familyCenterOfGravity, setFamilyCenterOfGravity] = useState("");
  const [multiLocationOptimization, setMultiLocationOptimization] = useState("");
  const [emergencyAccessImportance, setEmergencyAccessImportance] = useState("");
  const [spontaneousVisitsImportance, setSpontaneousVisitsImportance] = useState("");
  const [grandchildrenVisitsImportance, setGrandchildrenVisitsImportance] = useState("");
  const [optimizationStrategy, setOptimizationStrategy] = useState("Balanced location");
  const [notes, setNotes] = useState("");
  const [showAuditMode, setShowAuditMode] = useState(false);

  const relationshipLabel = relationshipCopy(relationship);

  const ctaText = useMemo(() => ctaCopy(relationship), [relationship]);
  const isFamilyStoryRelationship = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse"].includes(relationship);
  const isMotherOrGrandmother = ["Mom", "Grandma"].includes(relationship);
  const shouldAskPartnerLossFollowUps = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse"].includes(relationship) && relationship !== "Couple";
  const shouldAskReligionFollowUps = importanceRank(religionImportance) > 0;
  const shouldAskGrandchildrenFollowUps = grandchildrenImportance === "Very important" || grandchildrenImportance === "High" || grandchildrenVisitsImportance === "Very important" || grandchildrenVisitsImportance === "High";
  const shouldAskLanguageFollowUps = preferredSpokenLanguage && preferredSpokenLanguage !== "English";
  const shouldAskMemoryFollowUps = memoryStatus !== "No" && memoryStatus !== "Not sure";
  const shouldAskWidowFollowUps = widowStatus === "Yes";
  const shouldAskCoupleFollowUps = relationship === "Couple";
  const shouldAskLivingAloneFollowUps = ["3-5 years", "5+ years"].includes(livingAloneDuration);
  const shouldAskSocialIsolationFollowUps =
    socialInteractionFrequency === "Biweekly" ||
    socialInteractionFrequency === "Monthly or less" ||
    socialInteractionNeed === "Much less social" ||
    socialInteractionNeed === "Somewhat less social" ||
    shouldAskLivingAloneFollowUps;
  const primaryAssistanceLevel = useMemo(() => pickPrimaryAssistanceLevel(assistanceLevels), [assistanceLevels]);
  const shouldAskRecentHospitalizationFollowUps = recentHospitalization === "Yes" || assistanceLevels.includes("Skilled nursing care");
  const shouldAskFutureCarePreference = primaryAssistanceLevel === "Fully independent";
  const isJewishBranch = faithTraditions.includes("Jewish");
  const isChristianBranch = faithTraditions.some((faith) => ["Catholic", "Protestant", "Orthodox Christian"].includes(faith));
  const isMuslimBranch = faithTraditions.includes("Muslim");

  const understandingBudget = isAnswered(budget, DEFAULT_BUDGET) ? budget : 0;

  const legacyProfileUnderstanding = useMemo(() => {
    const careLevel = primaryAssistanceLevel ? 25 : 0;
    const futureCare = primaryAssistanceLevel === "Fully independent" ? (futureCarePreference ? 20 : 0) : 20;
    const budgetQuality = understandingBudget > 0 ? 20 : 0;
    const lifestyle = (happinessPreferences.length > 0 || socialInteractionFrequency || preferredSocialIntensity) ? 15 : 0;
    const location = (familyVisitExpectation || visitFrequencyExpectation || normalDriveTime || parentCurrentHome || primaryCaregiverHome) ? 10 : 0;
    const culture = (religionImportance || preferredSpokenLanguage || faithTraditions.length > 0 || dietaryPreferences.length > 0) ? 10 : 0;
    const score = clampScore(careLevel + futureCare + budgetQuality + lifestyle + location + culture);

    return {
      score,
      segments: [
        { label: "Care level", value: careLevel },
        { label: "Future care preference", value: futureCare },
        { label: "Budget", value: budgetQuality },
        { label: "Lifestyle", value: lifestyle },
        { label: "Location", value: location },
        { label: "Culture", value: culture },
      ],
    };
  }, [
    primaryAssistanceLevel,
    futureCarePreference,
    understandingBudget,
    happinessPreferences.length,
    socialInteractionFrequency,
    preferredSocialIntensity,
    familyVisitExpectation,
    visitFrequencyExpectation,
    normalDriveTime,
    parentCurrentHome,
    primaryCaregiverHome,
    religionImportance,
    preferredSpokenLanguage,
    faithTraditions.length,
    dietaryPreferences.length,
  ]);

  const understandingProfile = useMemo(() => calculateUnderstandingProfile({
    relationship,
    primaryAssistanceLevel,
    futureCarePreference,
    memoryStatus,
    budget: understandingBudget,
    happinessPreferences,
    preferredEnvironment,
    socialInteractionFrequency,
    newFriendsImportance,
    preferredSocialIntensity,
    hobbyParticipation,
    religionImportance,
    preferredSpokenLanguage,
    faithTraditions,
    dietaryPreferences,
    whatFeelsLikeHome,
    familyVisitExpectation,
    visitFrequencyExpectation,
    normalDriveTime,
    parentCurrentHome,
    primaryCaregiverHome,
    familyCenterOfGravity,
    agingInPlaceImportance,
    avoidFutureMovesPreference,
    continuumOfCarePreference,
    secureMemoryNeighborhoodNeed,
    familiarLanguageRequirement,
    petOwnershipImportance,
    distancePreference: familyVisitExpectation || visitFrequencyExpectation,
    languagePreferenceImportance: preferredSpokenLanguage,
    petPreferenceImportance: petOwnershipImportance,
  }), [
    relationship,
    primaryAssistanceLevel,
    futureCarePreference,
    memoryStatus,
    understandingBudget,
    happinessPreferences,
    preferredEnvironment,
    socialInteractionFrequency,
    newFriendsImportance,
    preferredSocialIntensity,
    hobbyParticipation,
    religionImportance,
    preferredSpokenLanguage,
    faithTraditions,
    dietaryPreferences,
    whatFeelsLikeHome,
    familyVisitExpectation,
    visitFrequencyExpectation,
    normalDriveTime,
    parentCurrentHome,
    primaryCaregiverHome,
    familyCenterOfGravity,
    agingInPlaceImportance,
    avoidFutureMovesPreference,
    continuumOfCarePreference,
    secureMemoryNeighborhoodNeed,
    familiarLanguageRequirement,
    petOwnershipImportance,
    familyVisitExpectation,
    visitFrequencyExpectation,
    preferredSpokenLanguage,
  ]);

  const questionAuditRows = useMemo(
    () =>
      buildVisibilityAudit(QUESTION_GRAPH, {
        relationship,
        assistance_level: primaryAssistanceLevel,
        widow_status: widowStatus,
        religion_importance: religionImportance,
        faith_traditions: faithTraditions,
        preferred_spoken_language: preferredSpokenLanguage,
      }),
    [relationship, primaryAssistanceLevel, widowStatus, religionImportance, faithTraditions, preferredSpokenLanguage],
  );

  const handleFindHome = () => {
    const distanceIntelligence = buildDistanceIntelligence({
      referenceLocations: {
        parentCurrentHome,
        primaryCaregiverHome,
        secondaryFamilyHomes,
        preferredHospital,
        placeOfWorship,
      },
      driveTimes: {
        normal: normalDriveTime,
        rushHour: rushHourDriveTime,
        emergency: emergencyDriveTime,
      },
      familyVisitExpectation,
      familyGeographyModel: {
        involvedFamilyMembers,
        familyCenterOfGravity,
        multiLocationOptimization,
      },
      emotionalDistanceFactors: {
        emergencyAccessImportance,
        spontaneousVisitsImportance,
        grandchildrenVisitsImportance,
      },
      careLevelWeight: deriveCareLevelWeight(primaryAssistanceLevel, memoryStatus),
      optimizationStrategy,
      scores: {
        family_distance_score: null,
        visit_probability_score: null,
        emergency_access_score: null,
        grandchildren_access_score: null,
        travel_burden_score: null,
        family_engagement_score: null,
      },
      inferredConfidence: {},
    });

    const languageOverlap = familyLanguages.filter((language) =>
      [nativeLanguage, preferredSpokenLanguage, socialInteractionLanguage, ...languagesUnderstood].includes(language),
    ).length;
    const languageCoverage = [nativeLanguage, socialInteractionLanguage, medicalDiscussionLanguage].filter(Boolean).length;
    const languageMatchScore = clampScore(45 + languageCoverage * 12 + languagesUnderstood.length * 4 + languageOverlap * 8);
    const religiousFitScore = clampScore(
      scoreFromReligionImportance(religionImportance) * 0.55 + faithTraditions.length * 6 + religiousSupportNeeds.length * 5,
    );
    const culturalFitScore = clampScore(
      40 + whatFeelsLikeHome.length * 6 + (whatFeelsLikeHome.includes("Familiar language") ? 8 : 0) + (whatFeelsLikeHome.includes("Family-centered culture") ? 8 : 0),
    );
    const foodFitScore = clampScore(48 + dietaryPreferences.length * 7);
    const familyVisitBase = scoreFromFrequency(
      familyInvolvementExpectation === "Daily visits"
        ? "Daily"
        : familyInvolvementExpectation === "Multiple weekly visits"
          ? "Several times weekly"
          : familyInvolvementExpectation === "Weekly visits"
            ? "Weekly"
            : familyInvolvementExpectation === "Monthly visits"
              ? "Monthly"
              : (familyVisitExpectation || visitFrequencyExpectation),
    );
    const familyDecisionBoost = familyDecisionRole === "Shared decision" ? 12 : familyDecisionRole === "Family led" ? 8 : 6;
    const familyEngagementScore = clampScore(familyVisitBase * 0.82 + familyDecisionBoost + scoreFromImportance(grandchildrenImportance) * 0.12);
    const communityStyleScore = clampScore(
      44 + preferredEnvironment.length * 7 + (introvertExtrovert === "Introvert" && preferredEnvironment.includes("Quiet community") ? 10 : 0) + (introvertExtrovert === "Extrovert" && preferredEnvironment.includes("Large active community") ? 10 : 0),
    );

    const socialProfileScorePreview = Math.round((
      scoreFromFrequency(socialInteractionFrequency) * 0.35 +
      scoreFromImportance(newFriendsImportance) * 0.35 +
      scoreFromImportance(preferredSocialIntensity === "Extrovert" ? "High" : preferredSocialIntensity === "Balanced" ? "Medium" : "Low") * 0.3
    ));

    const lonelinessRiskScorePreview = Math.round((
      scoreFromFrequency(socialInteractionFrequency) * 0.35 +
      scoreFromImportance(lonelinessRisk === "Very high" ? "Very high" : lonelinessRisk === "High" ? "High" : lonelinessRisk === "Moderate" ? "Medium" : "Low") * 0.45 +
      scoreFromFrequency(familyVisitExpectation || visitFrequencyExpectation) * 0.2
    ));

    const transitionRiskScorePreview = Math.round((
      scoreFromImportance(attitudeTowardMove === "Reluctant" ? "Very high" : attitudeTowardMove === "Anxious" ? "High" : attitudeTowardMove === "Cautious" ? "Medium" : "Low") * 0.45 +
      scoreFromImportance(widowStatus === "Yes" ? "High" : "Medium") * 0.2 +
      scoreFromImportance(biggestFear ? "High" : "Medium") * 0.35
    ));

    const adaptiveSignals = buildAdaptiveSignals({
      widowStatus,
      lossTiming,
      livingAloneDuration,
      preferredSpokenLanguage,
      languagesUnderstood,
      familyLanguages,
      grandchildrenImportance,
      religionImportance,
      religiousSupportNeeds,
      preferredSocialIntensity,
      introvertExtrovert,
      biggestFear,
      communitySizePreference,
    });

    const scoringWeights = adaptiveSignals.reduce<Record<string, number>>((acc, signal) => {
      for (const [weightKey, value] of Object.entries(signal.weights)) {
        acc[weightKey] = (acc[weightKey] || 0) + value;
      }
      return acc;
    }, {});
    const overallConfidence = clampScore(Math.max(legacyProfileUnderstanding.score, 62 + Math.min(24, adaptiveSignals.length * 3) + languageCoverage * 2));

    setState({
      relationship,
      gender,
      coupleAssistance,
      ageGroup,
      assistanceLevel: primaryAssistanceLevel,
      futureCarePreference,
      memoryStatus,
      happinessPreferences,
      budget,
      distanceFromFamily: familyVisitExpectation || optimizationStrategy,
      referenceLocationType: "family-geography",
      referenceLocationValue: familyCenterOfGravity || parentCurrentHome || primaryCaregiverHome || "",
      notes,
      humanIntelligenceV2: {
        socialProfile: {
          livingAloneDuration,
          socialInteractionFrequency,
          newFriendsImportance,
          hobbyParticipation,
          preferredSocialIntensity,
        },
        familyProfile: {
          involvedFamilyMembers,
          visitFrequencyExpectation: familyVisitExpectation || visitFrequencyExpectation,
          grandchildrenPresence,
          grandchildrenImportance,
          familyDecisionDynamics,
          emergencySupportNetwork,
          coupleStayTogetherPreference,
          widowStatus,
          lossTiming,
          socialActivityChangeSinceLoss,
          socialInteractionNeed,
          temporarySeparationAcceptance,
          griefSupportInterest,
        },
        culturalProfile: {
          religionImportance,
          faithTraditions,
          religiousSupportNeeds,
          kosherRequirements,
          synagogueChurchAccess,
          holidayCelebrations,
          culturalIdentity,
          israeliJewishCommunityPreference,
          whatFeelsLikeHome,
          worshipAccessRequirement: synagogueChurchAccess,
          jewishProgrammingImportance,
          churchAccessRequirement,
          christianServiceRequirement,
          halalMealsRequirement,
          prayerFacilityRequirement,
        },
        languageProfile: {
          preferredSpokenLanguage,
          nativeLanguage,
          medicalDiscussionLanguage,
          socialInteractionLanguage,
          languageNeedScope,
          languagesUnderstood,
          familyLanguages,
          bilingualStaffRequired,
        },
        foodProfile: {
          dietaryPreferences,
        },
        familyCultureProfile: {
          involvementExpectation: familyInvolvementExpectation,
          decisionRole: familyDecisionRole,
        },
        communityPreferenceProfile: {
          preferredEnvironment,
        },
        personalityProfile: {
          introvertExtrovert,
          communitySizePreference,
          privacyImportance,
          structureFlexibilityPreference,
        },
        interestsProfile: independenceInterests,
        independenceProfile: {
          drivingImportance,
          cookingImportance,
          abilityToLeaveIndependently,
          petOwnershipImportance,
          hostingFamilyImportance,
        },
        transitionRiskProfile: {
          biggestFear,
          attitudeTowardMove,
          previousMoves,
          bereavementStatus,
          lonelinessRisk,
          socialIsolationConcern,
          recentHospitalization,
          hospitalizationRecency,
          postHospitalRehabNeed,
          wanderingConcerns,
        },
        futureCareProfile: {
          agingInPlaceImportance,
          avoidFutureMovesPreference,
          continuumOfCarePreference,
          secureMemoryNeighborhoodNeed,
          familiarLanguageRequirement,
        },
        distanceProfile: {
          referenceLocations: {
            parentCurrentHome,
            primaryCaregiverHome,
            secondaryFamilyHomes,
            preferredHospital,
            placeOfWorship,
          },
          driveTimes: {
            normal: normalDriveTime,
            rushHour: rushHourDriveTime,
            emergency: emergencyDriveTime,
          },
          familyVisitExpectation,
          familyGeographyModel: {
            involvedFamilyMembers,
            familyCenterOfGravity,
            multiLocationOptimization,
          },
          emotionalDistanceFactors: {
            emergencyAccessImportance,
            spontaneousVisitsImportance,
            grandchildrenVisitsImportance,
          },
          careLevelWeight: deriveCareLevelWeight(primaryAssistanceLevel, memoryStatus),
          optimizationStrategy,
          scores: distanceIntelligence.scores,
          inferredConfidence: distanceIntelligence.inferredConfidence,
        },
        confidence: {
          socialProfile: 70,
          familyProfile: 80,
          culturalProfile: 75,
          languageProfile: 65,
          personalityProfile: 60,
          interestsProfile: 55,
          independenceProfile: 70,
          transitionRiskProfile: 60,
          futureCareProfile: 55,
          distanceProfile: 85,
        },
        scoringEngine: {
          overallConfidence,
          confidenceThreshold: 72,
          adaptiveSignals,
          scoringWeights,
          outputScores: {
            social_fit_score: socialProfileScorePreview,
            family_fit_score: familyEngagementScore,
            language_fit_score: languageMatchScore,
            cultural_fit_score: culturalFitScore,
            religious_fit_score: religiousFitScore,
            food_fit_score: foodFitScore,
            family_engagement_score: familyEngagementScore,
            community_style_score: communityStyleScore,
            independence_fit_score: scoreFromImportance(drivingImportance) * 0.45 + scoreFromImportance(abilityToLeaveIndependently === "Yes" ? "Very high" : abilityToLeaveIndependently === "Sometimes" ? "Medium" : "Low") * 0.55,
            transition_success_probability: clampScore(100 - transitionRiskScorePreview * 0.58 + socialProfileScorePreview * 0.24 + familyEngagementScore * 0.18),
            loneliness_risk_score: lonelinessRiskScorePreview,
          },
          recommendationImpacts: adaptiveSignals.map((signal) => signal.impactExplanation),
          additionalQuestionAsked: shouldAskFutureCarePreference ? "When thinking about the future, which approach feels right for you?" : "",
        },
      },
    });

    const params = new URLSearchParams();
    if (relationship) params.set("relationship", relationship);
    if (gender) params.set("gender", gender);
    if (coupleAssistance) params.set("coupleAssistance", coupleAssistance);
    if (ageGroup) params.set("age", ageGroup);
    if (primaryAssistanceLevel) params.set("care", primaryAssistanceLevel);
    if (futureCarePreference) params.set("futureCarePreference", futureCarePreference);
    if (memoryStatus) params.set("memory", memoryStatus);
    if (happinessPreferences.length > 0) params.set("activities", happinessPreferences.join(","));
    params.set("budget", String(budget));
    if (familyVisitExpectation) params.set("distance", familyVisitExpectation);
    if (optimizationStrategy) params.set("distanceStrategy", optimizationStrategy);
    if (notes.trim()) params.set("notes", notes.trim());

    const socialProfileScore = Math.round((
      scoreFromFrequency(socialInteractionFrequency) * 0.35 +
      scoreFromImportance(newFriendsImportance) * 0.35 +
      scoreFromImportance(preferredSocialIntensity === "Extrovert" ? "High" : preferredSocialIntensity === "Balanced" ? "Medium" : "Low") * 0.3
    ));

    const familySupportScore = Math.round((
      scoreFromFrequency(familyVisitExpectation || visitFrequencyExpectation) * 0.45 +
      scoreFromImportance(grandchildrenImportance) * 0.25 +
      scoreFromImportance(emergencySupportNetwork === "Strong" ? "Very high" : emergencySupportNetwork === "Moderate" ? "High" : emergencySupportNetwork === "Limited" ? "Medium" : "Low") * 0.3
    ));

    const culturalMatchScore = Math.round((
      scoreFromImportance(religionImportance) * 0.45 +
      scoreFromImportance(kosherRequirements === "Yes" ? "Very high" : kosherRequirements === "Sometimes" ? "Medium" : "Low") * 0.25 +
      scoreFromImportance(israeliJewishCommunityPreference === "Yes" ? "High" : israeliJewishCommunityPreference === "Sometimes" ? "Medium" : "Low") * 0.3
    ));

    const lonelinessRiskScore = Math.round((
      scoreFromFrequency(socialInteractionFrequency) * 0.35 +
      scoreFromImportance(lonelinessRisk === "Very high" ? "Very high" : lonelinessRisk === "High" ? "High" : lonelinessRisk === "Moderate" ? "Medium" : "Low") * 0.45 +
      scoreFromFrequency(familyVisitExpectation || visitFrequencyExpectation) * 0.2
    ));

    const transitionRiskScore = Math.round((
      scoreFromImportance(attitudeTowardMove === "Reluctant" ? "Very high" : attitudeTowardMove === "Anxious" ? "High" : attitudeTowardMove === "Cautious" ? "Medium" : "Low") * 0.45 +
      scoreFromImportance(widowStatus === "Yes" ? "High" : "Medium") * 0.2 +
      scoreFromImportance(biggestFear ? "High" : "Medium") * 0.35
    ));

    const futureCareScore = Math.round((
      scoreFromImportance(agingInPlaceImportance) * 0.4 +
      scoreFromImportance(continuumOfCarePreference) * 0.35 +
      scoreFromImportance(avoidFutureMovesPreference === "Yes" ? "High" : avoidFutureMovesPreference === "Sometimes" ? "Medium" : "Low") * 0.25
    ));

    const residentKey = `${relationship || "resident"}-${ageGroup || "unknown"}-${Date.now()}`;

    void Promise.allSettled(
      adaptiveSignals.map((signal) =>
        persistAdaptiveQuestionSignal({
          resident_key: residentKey,
          question_key: signal.questionKey,
          answer: signal.answer,
          signal_type: signal.signalType,
          signal_json: JSON.stringify(signal),
          weights_json: JSON.stringify(signal.weights),
          impact_explanation: signal.impactExplanation,
          info_gain_score: signal.infoGain,
        }),
      ),
    );

    void persistHumanIntelligenceScores({
      resident_key: residentKey,
      relationship,
      age_group: ageGroup,
      social_profile_score: socialProfileScore,
      family_support_score: familySupportScore,
      cultural_match_score: culturalMatchScore,
      loneliness_risk_score: lonelinessRiskScore,
      transition_risk_score: transitionRiskScore,
      future_care_score: futureCareScore,
      language_match_score: languageMatchScore,
      religious_fit_score: religiousFitScore,
      language_fit_score: languageMatchScore,
      cultural_fit_score: culturalFitScore,
      food_fit_score: foodFitScore,
      family_engagement_score: familyEngagementScore,
      community_style_score: communityStyleScore,
      social_fit_score: socialProfileScore,
      family_fit_score: familyEngagementScore,
      independence_fit_score: clampScore(
        scoreFromImportance(drivingImportance) * 0.45 +
        scoreFromImportance(abilityToLeaveIndependently === "Yes" ? "Very high" : abilityToLeaveIndependently === "Sometimes" ? "Medium" : "Low") * 0.55,
      ),
      transition_success_probability: clampScore(100 - transitionRiskScore * 0.58 + socialProfileScore * 0.24 + familyEngagementScore * 0.18),
      metadata_json: JSON.stringify({
        livingAloneDuration,
        visitFrequencyExpectation: familyVisitExpectation || visitFrequencyExpectation,
        religionImportance,
        faithTraditions,
        jewishProgrammingImportance,
        churchAccessRequirement,
        christianServiceRequirement,
        halalMealsRequirement,
        prayerFacilityRequirement,
        preferredSpokenLanguage,
        assistanceLevels,
        future_care_preference: futureCarePreference,
        memoryStatus,
        nativeLanguage,
        socialInteractionLanguage,
        medicalDiscussionLanguage,
        bilingualStaffRequired,
        languagesUnderstood,
        familyLanguages,
        religiousSupportNeeds,
        whatFeelsLikeHome,
        dietaryPreferences,
        familyInvolvementExpectation,
        familyDecisionRole,
        preferredEnvironment,
        adaptiveSignals,
      }),
    }).catch(() => {
      // non-blocking by design; recommendation flow should continue even if backend persistence is unavailable
    });

    router.push(`/results?${params.toString()}`);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f3eee1_0%,#fffaf2_36%,#ffffff_74%)] px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl">
        <div className="rounded-3xl border border-[#e8dcc9] bg-white/92 p-4 shadow-[0_24px_80px_-38px_rgba(96,80,56,0.38)] backdrop-blur sm:p-6">
          <section className="relative overflow-hidden rounded-3xl border border-[#e7dcc9] bg-[#f8f3e8]">
            <img
              src="/hero-reference.png"
              alt="OPTIME hero reference image"
              className="h-[420px] w-full object-cover object-[62%_center] sm:h-[470px]"
            />
            <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(246,241,232,0.9)_0%,rgba(246,241,232,0.66)_42%,rgba(246,241,232,0.2)_70%,rgba(246,241,232,0.06)_100%)]" />
            <div className="absolute inset-y-0 left-0 z-10 w-full rounded-3xl bg-[rgba(255,251,244,0.76)] backdrop-blur-[1.5px] sm:w-[64%]" />

            <div className="absolute inset-y-0 left-0 z-20 flex w-full items-center px-6 py-6 sm:w-[64%] sm:px-10 lg:px-12">
              <div className="w-full max-w-2xl">
                <div className="flex items-center gap-3 text-[#62816c]">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#a6bea8] bg-white/85 text-lg">✤</span>
                  <div>
                    <p className="text-2xl font-semibold tracking-[0.16em]">OPTIME</p>
                    <p className="text-sm text-[#70856f]">Better choices. Better lives.</p>
                  </div>
                </div>

                <h1 className="mt-5 text-4xl font-semibold leading-[1.05] text-[#1f392a] sm:text-6xl">
                  Find the right home,
                  <br />
                  not just the best-rated one.
                </h1>

                <div className="mt-5 h-1 w-16 rounded-full bg-[#c9a15d]" />

                <p className="mt-5 text-lg leading-relaxed text-[#4f5d4d]">
                  A simple, family-friendly questionnaire built for clear decisions with less stress.
                </p>

                <div className="mt-7 flex flex-wrap gap-2.5 text-sm">
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Personalized Matching</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Transparent Scoring</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Family First</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ AI Assisted Decisions</p>
                </div>
              </div>
            </div>
          </section>

          <div className="mt-6 grid gap-5">
            <aside className="sticky top-4 z-30 rounded-2xl border border-[#d4e5df] bg-white/95 p-4 shadow-[0_14px_36px_-20px_rgba(25,85,73,0.48)] backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#4b6f6a]">OPTIME Understanding Journey</p>
                  <p className={`mt-1 text-base font-semibold ${understandingProfile.colorBand.textClass}`}>{understandingProfile.statusText}</p>
                </div>
                <div className="rounded-full border border-[#d8e6e2] bg-[#f3faf8] px-3 py-1 text-sm font-semibold text-[#2c5650]">
                  Understanding score {understandingProfile.understandingScore}%
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[#dce9e5] bg-[#f8fcfb] p-3">
                <p className="text-xs font-semibold uppercase tracking-[0.13em] text-[#5f7e79]">Understanding Score</p>
                <p className={`mt-1 text-xl font-semibold ${understandingProfile.colorBand.textClass}`}>{understandingProfile.understandingScore}%</p>
                <div className={`mt-2 h-2.5 overflow-hidden rounded-full bg-[#e7efec] ring-1 ${understandingProfile.colorBand.ringClass}`}>
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${understandingProfile.colorBand.bgClass} transition-all duration-700 ease-out`}
                    style={{ width: `${understandingProfile.understandingScore}%` }}
                  />
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-[#dbe7e4] bg-white p-3">
                <div className="flex items-center gap-2 text-lg">
                  {understandingProfile.journeyIcons.map((journeyIcon) => (
                    <span
                      key={journeyIcon.label}
                      title={journeyIcon.label}
                      className={`inline-flex transition-all duration-500 ${journeyIcon.active ? "opacity-100 scale-100" : "opacity-40 scale-90 grayscale"}`}
                    >
                      {journeyIcon.icon}
                    </span>
                  ))}
                </div>
                <div className="relative mt-3">
                  <div className="h-10 rounded-full border border-[#d7e4df] bg-[#f4faf8] px-3">
                    <div className="relative h-full">
                      <div className="absolute left-8 right-20 top-1/2 h-[2px] -translate-y-1/2 bg-[#bdd4cd]" />
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 text-lg">🏠</div>
                      <div
                        className="absolute top-1/2 -translate-y-1/2 text-lg transition-all duration-700 ease-out"
                        style={{ left: `calc(16px + (${understandingProfile.journeyProgressPercent}% * (100% - 104px) / 100))` }}
                      >
                        {understandingProfile.personIcon}
                      </div>
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 text-lg">🏘️🌳☕🎭</div>
                    </div>
                  </div>
                </div>
              </div>
            </aside>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">1. Who are you searching for?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {relationshipOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={relationship === option}
                    onClick={() => {
                      setRelationship(option);
                      if (option !== "Myself") setGender("");
                      if (option !== "Couple") setCoupleAssistance("");
                    }}
                  />
                ))}
              </div>
            </article>

            {relationship === "Myself" ? (
              <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
                <h3 className="text-lg font-semibold text-[#2f2a24]">Gender</h3>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  {genderOptions.map((option) => (
                    <OptionChip key={option} label={option} isActive={gender === option} onClick={() => setGender(option)} />
                  ))}
                </div>
              </article>
            ) : null}

            {relationship === "Couple" ? (
              <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
                <h3 className="text-lg font-semibold text-[#2f2a24]">Who needs more assistance?</h3>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  {coupleAssistanceOptions.map((option) => (
                    <OptionChip
                      key={option}
                      label={option}
                      isActive={coupleAssistance === option}
                      onClick={() => setCoupleAssistance(option)}
                    />
                  ))}
                </div>
              </article>
            ) : null}

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">2. Age Group</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {ageGroupOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={ageGroup === option} onClick={() => setAgeGroup(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">3. How much daily assistance is needed?</h3>
              <p className="mt-1 text-sm text-[#6c6358]">Select all that apply.</p>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {assistanceOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={assistanceLevels.includes(option)}
                    onClick={() => setAssistanceLevels((current) => toggleOption(current, option))}
                  />
                ))}
              </div>
            </article>

            {shouldAskFutureCarePreference ? (
              <article className="rounded-2xl border border-[#dbe4d5] bg-[#f8fcf5] p-5">
                <h3 className="text-lg font-semibold text-[#2f2a24]">3A. When thinking about the future, which approach feels right for you?</h3>
                <p className="mt-1 text-sm text-[#6c6358]">This follow-up appears only for fully independent profiles.</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {futureCarePreferenceOptions.map((option) => {
                    const isActive = futureCarePreference === option.label;
                    return (
                      <button
                        key={option.label}
                        type="button"
                        onClick={() => setFutureCarePreference(option.label)}
                        className={`rounded-2xl border p-4 text-left transition ${isActive ? "border-[#6d8f72] bg-[#edf6ea] shadow-[0_10px_24px_-18px_rgba(76,111,91,0.55)]" : "border-[#d7decd] bg-white hover:border-[#b7c7b0] hover:bg-[#fbfdf8]"}`}
                      >
                        <p className="text-sm font-semibold text-[#2f2a24]">{option.label}</p>
                        <p className="mt-1 text-sm text-[#625a4f]">{option.description}</p>
                      </button>
                    );
                  })}
                </div>
              </article>
            ) : null}

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">4. Are there memory or confusion issues?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {memoryOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={memoryStatus === option} onClick={() => setMemoryStatus(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">5. What would make {relationshipLabel} happiest?</h3>
              <p className="mt-1 text-sm text-[#6c6358]">Select all that apply.</p>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {happinessOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={happinessPreferences.includes(option)}
                    onClick={() => setHappinessPreferences((current) => toggleOption(current, option))}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">6. Monthly budget</h3>
              <p className="mt-1 text-sm text-[#6c6358]">$3,000 - $15,000</p>
              <div className="mt-5">
                <input
                  type="range"
                  min={3000}
                  max={15000}
                  step={100}
                  value={budget}
                  onChange={(event) => setBudget(Number(event.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-[#e7ddd0] accent-[#6f8fb1]"
                />
                <p className="mt-3 text-base font-semibold text-[#5b7d9f]">${budget.toLocaleString()}</p>
              </div>
            </article>

            {relationship ? (
              <article className="rounded-2xl border border-[#dcd1bf] bg-[#fdfaf4] p-5 shadow-[0_18px_36px_-28px_rgba(106,88,60,0.28)]">
                <h3 className="text-lg font-semibold text-[#2f2a24]">7. Follow-up questions based on what matters most</h3>
                <p className="mt-1 text-sm text-[#6c6358]">These appear only when the previous answers suggest they matter for adjustment and long-term fit.</p>

                {isFamilyStoryRelationship ? (
                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">Are grandchildren important?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {importanceOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={grandchildrenImportance === option} onClick={() => setGrandchildrenImportance(option)} />
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">How much do family and decision-making dynamics matter?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {decisionDynamicsOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={familyDecisionDynamics === option} onClick={() => setFamilyDecisionDynamics(option)} />
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}

                {shouldAskCoupleFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Couples decision tree</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Is staying together essential?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {coupleStayTogetherOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={coupleStayTogetherPreference === option} onClick={() => setCoupleStayTogetherPreference(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Do both need the same level of care?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={`same-care-${option}`} label={option} isActive={coupleSameCareLevel === option} onClick={() => setCoupleSameCareLevel(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Would you accept temporary separation if one requires higher care?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {separationAcceptanceOptions.map((option) => (
                            <OptionChip key={`separation-${option}`} label={option} isActive={temporarySeparationAcceptance === option} onClick={() => setTemporarySeparationAcceptance(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Is future care continuity important?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {carePreferenceOptions.map((option) => (
                            <OptionChip key={`couple-continuum-${option}`} label={option} isActive={continuumOfCarePreference === option} onClick={() => setContinuumOfCarePreference(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {shouldAskPartnerLossFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Widowhood and transition</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Has there been a loss of a spouse or long-term partner?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {widowStatusOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={widowStatus === option} onClick={() => setWidowStatus(option)} />
                          ))}
                        </div>
                      </div>
                    </div>

                    {shouldAskWidowFollowUps ? (
                      <div className="mt-4 grid gap-4 sm:grid-cols-2">
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">How long ago was the loss?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {lossTimingOptions.map((option) => (
                              <OptionChip key={option} label={option} isActive={lossTiming === option} onClick={() => setLossTiming(option)} />
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">Has social activity changed since then?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {socialChangeOptions.map((option) => (
                              <OptionChip key={option} label={option} isActive={socialActivityChangeSinceLoss === option} onClick={() => setSocialActivityChangeSinceLoss(option)} />
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">Is loneliness a concern?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {lonelinessOptions.map((option) => (
                              <OptionChip key={option} label={option} isActive={lonelinessRisk === option} onClick={() => setLonelinessRisk(option)} />
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">Would grief support groups help?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {yesNoOptions.map((option) => (
                              <OptionChip key={`grief-${option}`} label={option} isActive={griefSupportInterest === option} onClick={() => setGriefSupportInterest(option)} />
                            ))}
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {shouldAskSocialIsolationFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Social isolation tree</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Current isolation concern</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {isolationConcernOptions.map((option) => (
                            <OptionChip key={`isolation-${option}`} label={option} isActive={socialIsolationConcern === option} onClick={() => setSocialIsolationConcern(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">How much structured social programming is needed?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {importanceOptions.map((option) => (
                            <OptionChip key={`structured-${option}`} label={option} isActive={preferredSocialIntensity === option} onClick={() => setPreferredSocialIntensity(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {shouldAskReligionFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Religion and spirituality</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Which religion or tradition?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {faithTraditionOptions.map((option) => (
                            <OptionChip key={`followup-faith-${option}`} label={option} isActive={faithTraditions.includes(option)} onClick={() => setFaithTraditions((current) => toggleOption(current, option))} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">How important is religious community?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {importanceOptions.map((option) => (
                            <OptionChip key={`community-importance-${option}`} label={option} isActive={holidayCelebrations === option} onClick={() => setHolidayCelebrations(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Dietary requirements?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {dietaryPreferenceOptions.map((option) => (
                            <OptionChip key={`religion-diet-${option}`} label={option} isActive={dietaryPreferences.includes(option)} onClick={() => setDietaryPreferences((current) => toggleOption(current, option))} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Worship access requirements?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={`worship-${option}`} label={option} isActive={synagogueChurchAccess === option} onClick={() => setSynagogueChurchAccess(option)} />
                          ))}
                        </div>
                      </div>
                      {isJewishBranch ? (
                        <>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Kosher meals?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {yesNoOptions.map((option) => (
                                <OptionChip key={`kosher-${option}`} label={option} isActive={kosherRequirements === option} onClick={() => setKosherRequirements(option)} />
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Synagogue access?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {yesNoOptions.map((option) => (
                                <OptionChip key={`synagogue-${option}`} label={option} isActive={synagogueChurchAccess === option} onClick={() => setSynagogueChurchAccess(option)} />
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Jewish programming importance?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {importanceOptions.map((option) => (
                                <OptionChip key={`jewish-program-${option}`} label={option} isActive={jewishProgrammingImportance === option} onClick={() => setJewishProgrammingImportance(option)} />
                              ))}
                            </div>
                          </div>
                        </>
                      ) : null}
                      {isChristianBranch ? (
                        <>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Church access requirement?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {yesNoOptions.map((option) => (
                                <OptionChip key={`church-${option}`} label={option} isActive={churchAccessRequirement === option} onClick={() => setChurchAccessRequirement(option)} />
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Christian services importance?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {importanceOptions.map((option) => (
                                <OptionChip key={`christian-service-${option}`} label={option} isActive={christianServiceRequirement === option} onClick={() => setChristianServiceRequirement(option)} />
                              ))}
                            </div>
                          </div>
                        </>
                      ) : null}
                      {isMuslimBranch ? (
                        <>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Halal meals?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {yesNoOptions.map((option) => (
                                <OptionChip key={`halal-${option}`} label={option} isActive={halalMealsRequirement === option} onClick={() => setHalalMealsRequirement(option)} />
                              ))}
                            </div>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#5e5346]">Prayer facilities required?</p>
                            <div className="mt-3 flex flex-wrap gap-2.5">
                              {yesNoOptions.map((option) => (
                                <OptionChip key={`prayer-${option}`} label={option} isActive={prayerFacilityRequirement === option} onClick={() => setPrayerFacilityRequirement(option)} />
                              ))}
                            </div>
                          </div>
                        </>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {shouldAskGrandchildrenFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Grandchildren and intergenerational life</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Desired visit frequency</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {visitExpectationOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={grandchildrenPresence === option} onClick={() => setGrandchildrenPresence(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Importance of intergenerational programs</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {importanceOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={grandchildrenVisitsImportance === option} onClick={() => setGrandchildrenVisitsImportance(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {shouldAskLanguageFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Language support</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Is language required for social life or medical care only?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {languageNeedScopeOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={languageNeedScope === option} onClick={() => setLanguageNeedScope(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Preferred social interaction language</p>
                        <input value={socialInteractionLanguage} onChange={(event) => setSocialInteractionLanguage(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="English, Hebrew, Spanish..." />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Medical communication language</p>
                        <input value={medicalDiscussionLanguage} onChange={(event) => setMedicalDiscussionLanguage(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="English, Hebrew, Spanish..." />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Is bilingual staff required?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={`bilingual-${option}`} label={option} isActive={bilingualStaffRequired === option} onClick={() => setBilingualStaffRequired(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {shouldAskMemoryFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Memory and safety</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Wandering concerns?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {memorySafetyOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={wanderingConcerns === option} onClick={() => setWanderingConcerns(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Need a secure memory neighborhood?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {memorySafetyOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={secureMemoryNeighborhoodNeed === option} onClick={() => setSecureMemoryNeighborhoodNeed(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                  <h4 className="text-base font-semibold text-[#2f2a24]">Recent hospitalization</h4>
                  <div className="mt-3 grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">Has there been a recent hospitalization?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {yesNoOptions.map((option) => (
                          <OptionChip key={`hospital-${option}`} label={option} isActive={recentHospitalization === option} onClick={() => setRecentHospitalization(option)} />
                        ))}
                      </div>
                    </div>

                    {shouldAskRecentHospitalizationFollowUps ? (
                      <>
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">How recent was it?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {hospitalizationTimingOptions.map((option) => (
                              <OptionChip key={option} label={option} isActive={hospitalizationRecency === option} onClick={() => setHospitalizationRecency(option)} />
                            ))}
                          </div>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[#5e5346]">Will post-hospital rehab or close monitoring be needed?</p>
                          <div className="mt-3 flex flex-wrap gap-2.5">
                            {yesNoOptions.map((option) => (
                              <OptionChip key={`rehab-${option}`} label={option} isActive={postHospitalRehabNeed === option} onClick={() => setPostHospitalRehabNeed(option)} />
                            ))}
                          </div>
                        </div>
                      </>
                    ) : null}
                  </div>
                </div>
              </article>
            ) : null}

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">7. Social life and friendships</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {!isFamilyStoryRelationship && relationship !== "Couple" ? (
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">How long has {relationshipLabel} lived alone?</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {livingAloneOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={livingAloneDuration === option} onClick={() => setLivingAloneDuration(option)} />
                    ))}
                  </div>
                </div>
                ) : null}
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">How often does {relationshipLabel} want social interaction?</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {socialInteractionOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={socialInteractionFrequency === option} onClick={() => setSocialInteractionFrequency(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">How important is making new friends?</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {importanceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={newFriendsImportance === option} onClick={() => setNewFriendsImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Preferred social intensity</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {personalityOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={preferredSocialIntensity === option} onClick={() => setPreferredSocialIntensity(option)} />
                    ))}
                  </div>
                </div>
              </div>
              <p className="mt-4 text-sm font-medium text-[#5e5346]">Favorite activities and interests</p>
              <div className="mt-3 flex flex-wrap gap-2.5">
                {happinessOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={hobbyParticipation.includes(option)} onClick={() => setHobbyParticipation((current) => toggleOption(current, option))} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">8. Family, culture, and language</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">How many family members are actively involved?</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {familyInvolvementOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={involvedFamilyMembers === option} onClick={() => setInvolvedFamilyMembers(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Religion or faith importance</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {religionImportanceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={religionImportance === option} onClick={() => setReligionImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Primary language</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {languageOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={preferredSpokenLanguage === option} onClick={() => setPreferredSpokenLanguage(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Introvert or extrovert</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {personalityOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={introvertExtrovert === option} onClick={() => setIntrovertExtrovert(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Community size preference</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {sizePreferenceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={communitySizePreference === option} onClick={() => setCommunitySizePreference(option)} />
                    ))}
                  </div>
                </div>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">9. Cultural intelligence profile (asked for everyone)</h3>
              <p className="mt-1 text-sm text-[#6c6358]">We never infer culture from name, ethnicity, or religion. We ask directly and support mixed identities.</p>

              {shouldAskReligionFollowUps ? (
                <div className="mt-5 grid gap-5 sm:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium text-[#5e5346]">Faith traditions (select multiple)</p>
                    <div className="mt-3 flex flex-wrap gap-2.5">
                      {faithTraditionOptions.map((option) => (
                        <OptionChip
                          key={`faith-${option}`}
                          label={option}
                          isActive={faithTraditions.includes(option)}
                          onClick={() => setFaithTraditions((current) => toggleOption(current, option))}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="sm:col-span-2">
                    <p className="text-sm font-medium text-[#5e5346]">Spiritual support needs (select multiple)</p>
                    <div className="mt-3 flex flex-wrap gap-2.5">
                      {religiousSupportNeedsOptions.map((option) => (
                        <OptionChip
                          key={`support-${option}`}
                          label={option}
                          isActive={religiousSupportNeeds.includes(option)}
                          onClick={() => setReligiousSupportNeeds((current) => toggleOption(current, option))}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="mt-5 grid gap-5 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">What makes this person feel at home? (select multiple)</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {homeComfortOptions.map((option) => (
                      <OptionChip
                        key={`home-${option}`}
                        label={option}
                        isActive={whatFeelsLikeHome.includes(option)}
                        onClick={() => setWhatFeelsLikeHome((current) => toggleOption(current, option))}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Dietary preferences (select multiple)</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {dietaryPreferenceOptions.map((option) => (
                      <OptionChip
                        key={`diet-${option}`}
                        label={option}
                        isActive={dietaryPreferences.includes(option)}
                        onClick={() => setDietaryPreferences((current) => toggleOption(current, option))}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-5 grid gap-5 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Family involvement expectations</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {familyInvolvementExpectationOptions.map((option) => (
                      <OptionChip key={`family-expectation-${option}`} label={option} isActive={familyInvolvementExpectation === option} onClick={() => setFamilyInvolvementExpectation(option)} />
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Family role in decisions</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {familyDecisionRoleOptions.map((option) => (
                      <OptionChip key={`family-role-${option}`} label={option} isActive={familyDecisionRole === option} onClick={() => setFamilyDecisionRole(option)} />
                    ))}
                  </div>
                </div>

                <div className="sm:col-span-2">
                  <p className="text-sm font-medium text-[#5e5346]">Preferred community environment (select multiple)</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {communityEnvironmentOptions.map((option) => (
                      <OptionChip
                        key={`environment-${option}`}
                        label={option}
                        isActive={preferredEnvironment.includes(option)}
                        onClick={() => setPreferredEnvironment((current) => toggleOption(current, option))}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">10. Independence and transition</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Driving matters</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {independenceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={drivingImportance === option} onClick={() => setDrivingImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Cooking matters</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {independenceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={cookingImportance === option} onClick={() => setCookingImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Leave independently</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {yesNoOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={abilityToLeaveIndependently === option} onClick={() => setAbilityToLeaveIndependently(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Hosting family matters</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {independenceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={hostingFamilyImportance === option} onClick={() => setHostingFamilyImportance(option)} />
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Biggest fear about the move</p>
                  <input value={biggestFear} onChange={(event) => setBiggestFear(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="Losing independence, loneliness, unfamiliarity..." />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Attitude toward the move</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {attitudeOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={attitudeTowardMove === option} onClick={() => setAttitudeTowardMove(option)} />
                    ))}
                  </div>
                </div>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">11. Future care and distance intelligence</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Primary reference location</p>
                  <input value={parentCurrentHome} onChange={(event) => setParentCurrentHome(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="Home address, city, or neighborhood" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Primary caregiver home</p>
                  <input value={primaryCaregiverHome} onChange={(event) => setPrimaryCaregiverHome(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="Address or city" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Normal drive time to family</p>
                  <input value={normalDriveTime} onChange={(event) => setNormalDriveTime(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="25 minutes, 1 hour, close by" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Rush hour drive time</p>
                  <input value={rushHourDriveTime} onChange={(event) => setRushHourDriveTime(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="40 minutes, 1.5 hours..." />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Emergency drive time</p>
                  <input value={emergencyDriveTime} onChange={(event) => setEmergencyDriveTime(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="20 minutes, 45 minutes..." />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Optimization strategy</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {distanceStrategyOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={optimizationStrategy === option} onClick={() => setOptimizationStrategy(option)} />
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Family visit expectation</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {visitExpectationOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={familyVisitExpectation === option} onClick={() => setFamilyVisitExpectation(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Emergency access importance</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {importanceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={emergencyAccessImportance === option} onClick={() => setEmergencyAccessImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Spontaneous visits importance</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {importanceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={spontaneousVisitsImportance === option} onClick={() => setSpontaneousVisitsImportance(option)} />
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Aging in place importance</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {carePreferenceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={agingInPlaceImportance === option} onClick={() => setAgingInPlaceImportance(option)} />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Avoid future moves</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {yesNoOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={avoidFutureMovesPreference === option} onClick={() => setAvoidFutureMovesPreference(option)} />
                    ))}
                  </div>
                </div>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">12. Anything else we should know?</h3>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Anything important to your family or loved one that we should consider during matching."
                className="mt-4 min-h-32 w-full resize-y rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition placeholder:text-[#9f9384] focus:ring-2"
              />
              <p className="mt-3 text-xs text-[#8b7f71]">Examples: Loves old movies, Must have Hebrew speaking staff, Wants a Jewish community, Doesn&apos;t like noisy environments, Loves gardening</p>
            </article>

            <article className="rounded-2xl border border-[#d7dde8] bg-[#f8fbff] p-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#4b6688]">Audit Mode</p>
                  <h3 className="mt-1 text-lg font-semibold text-[#2f2a24]">Adaptive visibility and source-of-truth audit</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAuditMode((current) => !current)}
                  className="rounded-full border border-[#bfcddd] bg-white px-4 py-2 text-sm font-semibold text-[#405a7a] hover:bg-[#f0f6ff]"
                >
                  {showAuditMode ? "Hide audit" : "Show audit"}
                </button>
              </div>

              {showAuditMode ? (
                <div className="mt-4 overflow-x-auto rounded-2xl border border-[#d5e0ef] bg-white">
                  <table className="min-w-full divide-y divide-[#e4ecf6] text-sm text-[#334155]">
                    <thead className="bg-[#edf4fd] text-left text-xs uppercase tracking-[0.14em] text-[#5f738d]">
                      <tr>
                        <th className="px-4 py-3">question_id</th>
                        <th className="px-4 py-3">visible</th>
                        <th className="px-4 py-3">hidden_reason</th>
                        <th className="px-4 py-3">writes_to</th>
                        <th className="px-4 py-3">source_of_truth</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#edf2f8]">
                      {questionAuditRows.map((row) => (
                        <tr key={row.question_id}>
                          <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.question_id}</td>
                          <td className="px-4 py-3">{row.visible ? "true" : "false"}</td>
                          <td className="px-4 py-3">{row.hidden_reason || ""}</td>
                          <td className="px-4 py-3">{row.writes_to}</td>
                          <td className="px-4 py-3">{row.source_of_truth ? "true" : "false"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </article>
          </div>

          <div className="mt-8">
            <button
              type="button"
              onClick={handleFindHome}
              className="w-full rounded-full bg-[#7a9d87] px-6 py-4 text-base font-semibold text-white transition hover:bg-[#6b8b76] sm:w-auto"
            >
              {ctaText}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
