"use client";

import { createContext, useContext, useMemo, useState } from "react";

export type QuestionnaireState = {
  relationship: string;
  gender: string;
  coupleAssistance: string;
  ageGroup: string;
  assistanceLevel: string;
  memoryStatus: string;
  happinessPreferences: string[];
  budget: number;
  distanceFromFamily: string;
  referenceLocationType: string;
  referenceLocationValue: string;
  notes: string;
  humanIntelligenceV2: HumanIntelligenceV2;
};

export type HumanIntelligenceV2 = {
  socialProfile: {
    livingAloneDuration: string;
    socialInteractionFrequency: string;
    newFriendsImportance: string;
    hobbyParticipation: string[];
    preferredSocialIntensity: string;
  };
  familyProfile: {
    involvedFamilyMembers: string;
    visitFrequencyExpectation: string;
    grandchildrenPresence: string;
    grandchildrenImportance: string;
    familyDecisionDynamics: string;
    emergencySupportNetwork: string;
    widowStatus: string;
    lossTiming: string;
    socialActivityChangeSinceLoss: string;
    socialInteractionNeed: string;
  };
  culturalProfile: {
    religionImportance: string;
    kosherRequirements: string;
    synagogueChurchAccess: string;
    holidayCelebrations: string;
    culturalIdentity: string;
    israeliJewishCommunityPreference: string;
  };
  languageProfile: {
    preferredSpokenLanguage: string;
    nativeLanguage: string;
    medicalDiscussionLanguage: string;
    socialInteractionLanguage: string;
    languageNeedScope: string;
  };
  personalityProfile: {
    introvertExtrovert: string;
    communitySizePreference: string;
    privacyImportance: string;
    structureFlexibilityPreference: string;
  };
  interestsProfile: string[];
  independenceProfile: {
    drivingImportance: string;
    cookingImportance: string;
    abilityToLeaveIndependently: string;
    petOwnershipImportance: string;
    hostingFamilyImportance: string;
  };
  transitionRiskProfile: {
    biggestFear: string;
    attitudeTowardMove: string;
    previousMoves: string;
    bereavementStatus: string;
    lonelinessRisk: string;
    wanderingConcerns: string;
  };
  futureCareProfile: {
    agingInPlaceImportance: string;
    avoidFutureMovesPreference: string;
    continuumOfCarePreference: string;
    secureMemoryNeighborhoodNeed: string;
    familiarLanguageRequirement: string;
  };
  distanceProfile: {
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
    scores: {
      family_distance_score: number | null;
      visit_probability_score: number | null;
      emergency_access_score: number | null;
      grandchildren_access_score: number | null;
      travel_burden_score: number | null;
      family_engagement_score: number | null;
    };
    inferredConfidence: Record<string, number>;
  };
  confidence: Record<string, number>;
};

const DEFAULT_STATE: QuestionnaireState = {
  relationship: "",
  gender: "",
  coupleAssistance: "",
  ageGroup: "",
  assistanceLevel: "",
  memoryStatus: "",
  happinessPreferences: [],
  budget: 7000,
  distanceFromFamily: "",
  referenceLocationType: "",
  referenceLocationValue: "",
  notes: "",
  humanIntelligenceV2: {
    socialProfile: {
      livingAloneDuration: "",
      socialInteractionFrequency: "",
      newFriendsImportance: "",
      hobbyParticipation: [],
      preferredSocialIntensity: "",
    },
    familyProfile: {
      involvedFamilyMembers: "",
      visitFrequencyExpectation: "",
      grandchildrenPresence: "",
      grandchildrenImportance: "",
      familyDecisionDynamics: "",
      emergencySupportNetwork: "",
      widowStatus: "",
      lossTiming: "",
      socialActivityChangeSinceLoss: "",
      socialInteractionNeed: "",
    },
    culturalProfile: {
      religionImportance: "",
      kosherRequirements: "",
      synagogueChurchAccess: "",
      holidayCelebrations: "",
      culturalIdentity: "",
      israeliJewishCommunityPreference: "",
    },
    languageProfile: {
      preferredSpokenLanguage: "",
      nativeLanguage: "",
      medicalDiscussionLanguage: "",
      socialInteractionLanguage: "",
      languageNeedScope: "",
    },
    personalityProfile: {
      introvertExtrovert: "",
      communitySizePreference: "",
      privacyImportance: "",
      structureFlexibilityPreference: "",
    },
    interestsProfile: [],
    independenceProfile: {
      drivingImportance: "",
      cookingImportance: "",
      abilityToLeaveIndependently: "",
      petOwnershipImportance: "",
      hostingFamilyImportance: "",
    },
    transitionRiskProfile: {
      biggestFear: "",
      attitudeTowardMove: "",
      previousMoves: "",
      bereavementStatus: "",
      lonelinessRisk: "",
      wanderingConcerns: "",
    },
    futureCareProfile: {
      agingInPlaceImportance: "",
      avoidFutureMovesPreference: "",
      continuumOfCarePreference: "",
      secureMemoryNeighborhoodNeed: "",
      familiarLanguageRequirement: "",
    },
    distanceProfile: {
      referenceLocations: {
        parentCurrentHome: "",
        primaryCaregiverHome: "",
        secondaryFamilyHomes: "",
        preferredHospital: "",
        placeOfWorship: "",
      },
      driveTimes: {
        normal: "",
        rushHour: "",
        emergency: "",
      },
      familyVisitExpectation: "",
      familyGeographyModel: {
        involvedFamilyMembers: "",
        familyCenterOfGravity: "",
        multiLocationOptimization: "",
      },
      emotionalDistanceFactors: {
        emergencyAccessImportance: "",
        spontaneousVisitsImportance: "",
        grandchildrenVisitsImportance: "",
      },
      careLevelWeight: 0,
      optimizationStrategy: "",
      scores: {
        family_distance_score: null,
        visit_probability_score: null,
        emergency_access_score: null,
        grandchildren_access_score: null,
        travel_burden_score: null,
        family_engagement_score: null,
      },
      inferredConfidence: {},
    },
    confidence: {},
  },
};

type QuestionnaireContextValue = {
  state: QuestionnaireState;
  setState: (next: QuestionnaireState) => void;
};

const QuestionnaireContext = createContext<QuestionnaireContextValue | undefined>(undefined);

export function QuestionnaireProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<QuestionnaireState>(DEFAULT_STATE);

  const value = useMemo(() => ({ state, setState }), [state]);

  return (
    <QuestionnaireContext.Provider value={value}>
      {children}
    </QuestionnaireContext.Provider>
  );
}

export function useQuestionnaire() {
  const context = useContext(QuestionnaireContext);
  if (!context) {
    throw new Error("useQuestionnaire must be used within QuestionnaireProvider");
  }

  return context;
}
