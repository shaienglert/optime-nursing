"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { persistHumanIntelligenceScores } from "@/lib/api";

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

const socialChangeOptions = ["Much less social", "Somewhat less social", "About the same", "More social", "Not sure"];

const decisionDynamicsOptions = ["Single decision maker", "Shared with spouse", "Shared among siblings", "Consensus", "Uncertain"];

const supportNetworkOptions = ["Strong", "Moderate", "Limited", "Emergency only"];

const religionImportanceOptions = ["Not important", "Somewhat important", "Important", "Very important"];

const yesNoOptions = ["Yes", "No", "Sometimes"];

const languageOptions = ["English", "Hebrew", "Spanish", "Russian", "French", "Portuguese", "Arabic", "Other"];

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

export default function Home() {
  const router = useRouter();
  const { setState } = useQuestionnaire();

  const [relationship, setRelationship] = useState("");
  const [gender, setGender] = useState("");
  const [coupleAssistance, setCoupleAssistance] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [assistanceLevel, setAssistanceLevel] = useState("");
  const [memoryStatus, setMemoryStatus] = useState("");
  const [happinessPreferences, setHappinessPreferences] = useState<string[]>([]);
  const [budget, setBudget] = useState(7000);
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
  const [widowStatus, setWidowStatus] = useState("");
  const [lossTiming, setLossTiming] = useState("");
  const [socialActivityChangeSinceLoss, setSocialActivityChangeSinceLoss] = useState("");
  const [socialInteractionNeed, setSocialInteractionNeed] = useState("");
  const [religionImportance, setReligionImportance] = useState("");
  const [kosherRequirements, setKosherRequirements] = useState("");
  const [synagogueChurchAccess, setSynagogueChurchAccess] = useState("");
  const [holidayCelebrations, setHolidayCelebrations] = useState("");
  const [culturalIdentity, setCulturalIdentity] = useState("");
  const [israeliJewishCommunityPreference, setIsraeliJewishCommunityPreference] = useState("");
  const [preferredSpokenLanguage, setPreferredSpokenLanguage] = useState("");
  const [nativeLanguage, setNativeLanguage] = useState("");
  const [medicalDiscussionLanguage, setMedicalDiscussionLanguage] = useState("");
  const [socialInteractionLanguage, setSocialInteractionLanguage] = useState("");
  const [languageNeedScope, setLanguageNeedScope] = useState("");
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

  const relationshipLabel = relationshipCopy(relationship);

  const ctaText = useMemo(() => ctaCopy(relationship), [relationship]);
  const isFamilyStoryRelationship = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Couple"].includes(relationship);
  const isMotherOrGrandmother = ["Mom", "Grandma"].includes(relationship);
  const shouldAskReligionFollowUps = importanceRank(religionImportance) > importanceRank("Medium");
  const shouldAskGrandchildrenFollowUps = grandchildrenImportance === "Very important" || grandchildrenImportance === "High" || grandchildrenVisitsImportance === "Very important" || grandchildrenVisitsImportance === "High";
  const shouldAskLanguageFollowUps = preferredSpokenLanguage && preferredSpokenLanguage !== "English";
  const shouldAskMemoryFollowUps = memoryStatus !== "No" && memoryStatus !== "Not sure";
  const shouldAskWidowFollowUps = widowStatus === "Yes";

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
      careLevelWeight: deriveCareLevelWeight(assistanceLevel, memoryStatus),
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

    setState({
      relationship,
      gender,
      coupleAssistance,
      ageGroup,
      assistanceLevel,
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
          visitFrequencyExpectation,
          grandchildrenPresence,
          grandchildrenImportance,
          familyDecisionDynamics,
          emergencySupportNetwork,
          widowStatus,
          lossTiming,
          socialActivityChangeSinceLoss,
          socialInteractionNeed,
        },
        culturalProfile: {
          religionImportance,
          kosherRequirements,
          synagogueChurchAccess,
          holidayCelebrations,
          culturalIdentity,
          israeliJewishCommunityPreference,
        },
        languageProfile: {
          preferredSpokenLanguage,
          nativeLanguage,
          medicalDiscussionLanguage,
          socialInteractionLanguage,
          languageNeedScope,
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
          careLevelWeight: deriveCareLevelWeight(assistanceLevel, memoryStatus),
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
      },
    });

    const params = new URLSearchParams();
    if (relationship) params.set("relationship", relationship);
    if (gender) params.set("gender", gender);
    if (coupleAssistance) params.set("coupleAssistance", coupleAssistance);
    if (ageGroup) params.set("age", ageGroup);
    if (assistanceLevel) params.set("care", assistanceLevel);
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
      scoreFromFrequency(visitFrequencyExpectation) * 0.45 +
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
      scoreFromFrequency(visitFrequencyExpectation) * 0.2
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
      metadata_json: JSON.stringify({
        livingAloneDuration,
        visitFrequencyExpectation,
        religionImportance,
        preferredSpokenLanguage,
        memoryStatus,
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
              <div className="mt-4 flex flex-wrap gap-2.5">
                {assistanceOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={assistanceLevel === option} onClick={() => setAssistanceLevel(option)} />
                ))}
              </div>
            </article>

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
                      <p className="text-sm font-medium text-[#5e5346]">How long has {isMotherOrGrandmother ? "she" : relationshipLabel.toLowerCase()} lived alone?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {livingAloneOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={livingAloneDuration === option} onClick={() => setLivingAloneDuration(option)} />
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">How often does family visit?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {visitExpectationOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={visitFrequencyExpectation === option} onClick={() => setVisitFrequencyExpectation(option)} />
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">Does she miss social interaction?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {socialChangeOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={socialInteractionNeed === option} onClick={() => setSocialInteractionNeed(option)} />
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">Are grandchildren important?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {importanceOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={grandchildrenImportance === option} onClick={() => setGrandchildrenImportance(option)} />
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#5e5346]">Does religion play a role?</p>
                      <div className="mt-3 flex flex-wrap gap-2.5">
                        {religionImportanceOptions.map((option) => (
                          <OptionChip key={option} label={option} isActive={religionImportance === option} onClick={() => setReligionImportance(option)} />
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

                {isMotherOrGrandmother || relationship === "Spouse" ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Widowhood and transition</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Has there been a loss of a spouse?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {widowStatusOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={widowStatus === option} onClick={() => setWidowStatus(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">How recent was the loss?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {lossTimingOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={lossTiming === option} onClick={() => setLossTiming(option)} />
                          ))}
                        </div>
                      </div>
                    </div>

                    {shouldAskWidowFollowUps ? (
                      <div className="mt-4 grid gap-4 sm:grid-cols-2">
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
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {shouldAskReligionFollowUps ? (
                  <div className="mt-5 rounded-2xl border border-[#e8dcc9] bg-white p-4">
                    <h4 className="text-base font-semibold text-[#2f2a24]">Religion and Jewish life</h4>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Kosher?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={kosherRequirements === option} onClick={() => setKosherRequirements(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Synagogue access?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={synagogueChurchAccess === option} onClick={() => setSynagogueChurchAccess(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Religious services?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {importanceOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={holidayCelebrations === option} onClick={() => setHolidayCelebrations(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Jewish community?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {yesNoOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={israeliJewishCommunityPreference === option} onClick={() => setIsraeliJewishCommunityPreference(option)} />
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Holiday celebrations?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {importanceOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={culturalIdentity === option} onClick={() => setCulturalIdentity(option)} />
                          ))}
                        </div>
                      </div>
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
                      <div>
                        <p className="text-sm font-medium text-[#5e5346]">Familiar language requirement?</p>
                        <div className="mt-3 flex flex-wrap gap-2.5">
                          {familiarLanguageRequirementOptions.map((option) => (
                            <OptionChip key={option} label={option} isActive={familiarLanguageRequirement === option} onClick={() => setFamiliarLanguageRequirement(option)} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            ) : null}

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">7. Social life and friendships</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">How long has {relationshipLabel} lived alone?</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {livingAloneOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={livingAloneDuration === option} onClick={() => setLivingAloneDuration(option)} />
                    ))}
                  </div>
                </div>
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
                  <p className="text-sm font-medium text-[#5e5346]">Expected visit frequency</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {visitExpectationOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={visitFrequencyExpectation === option} onClick={() => setVisitFrequencyExpectation(option)} />
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
                  <p className="text-sm font-medium text-[#5e5346]">Preferred spoken language</p>
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
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Native language</p>
                  <input value={nativeLanguage} onChange={(event) => setNativeLanguage(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="English, Hebrew, Spanish..." />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Language for medical discussions</p>
                  <input value={medicalDiscussionLanguage} onChange={(event) => setMedicalDiscussionLanguage(event.target.value)} className="mt-2 w-full rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition focus:ring-2" placeholder="English, Hebrew, translated support..." />
                </div>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">9. Independence and transition</h3>
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
              <h3 className="text-lg font-semibold text-[#2f2a24]">10. Future care and distance intelligence</h3>
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
                <div>
                  <p className="text-sm font-medium text-[#5e5346]">Grandchildren visits importance</p>
                  <div className="mt-3 flex flex-wrap gap-2.5">
                    {importanceOptions.map((option) => (
                      <OptionChip key={option} label={option} isActive={grandchildrenVisitsImportance === option} onClick={() => setGrandchildrenVisitsImportance(option)} />
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
              <h3 className="text-lg font-semibold text-[#2f2a24]">11. Anything else we should know?</h3>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Anything important to your family or loved one that we should consider during matching."
                className="mt-4 min-h-32 w-full resize-y rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition placeholder:text-[#9f9384] focus:ring-2"
              />
              <p className="mt-3 text-xs text-[#8b7f71]">Examples: Loves old movies, Must have Hebrew speaking staff, Wants a Jewish community, Doesn't like noisy environments, Loves gardening</p>
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
