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
    coupleStayTogetherPreference: string;
    widowStatus: string;
    lossTiming: string;
    socialActivityChangeSinceLoss: string;
    socialInteractionNeed: string;
  };
  culturalProfile: {
    religionImportance: string;
    faithTraditions: string[];
    religiousSupportNeeds: string[];
    kosherRequirements: string;
    synagogueChurchAccess: string;
    holidayCelebrations: string;
    culturalIdentity: string;
    israeliJewishCommunityPreference: string;
    whatFeelsLikeHome: string[];
  };
  languageProfile: {
    preferredSpokenLanguage: string;
    nativeLanguage: string;
    medicalDiscussionLanguage: string;
    socialInteractionLanguage: string;
    languageNeedScope: string;
    languagesUnderstood: string[];
    familyLanguages: string[];
  };
  foodProfile: {
    dietaryPreferences: string[];
  };
  familyCultureProfile: {
    involvementExpectation: string;
    decisionRole: string;
  };
  communityPreferenceProfile: {
    preferredEnvironment: string[];
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
    socialIsolationConcern: string;
    recentHospitalization: string;
    hospitalizationRecency: string;
    postHospitalRehabNeed: string;
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
  scoringEngine: {
    overallConfidence: number;
    confidenceThreshold: number;
    adaptiveSignals: Array<{
      questionKey: string;
      answer: string;
      signalType: string;
      weights: Record<string, number>;
      impactExplanation: string;
      infoGain: number;
    }>;
    scoringWeights: Record<string, number>;
    outputScores: {
      social_fit_score: number;
      family_fit_score: number;
      language_fit_score: number;
      cultural_fit_score: number;
        religious_fit_score: number;
        food_fit_score: number;
        family_engagement_score: number;
        community_style_score: number;
      independence_fit_score: number;
      transition_success_probability: number;
      loneliness_risk_score: number;
    };
    recommendationImpacts: string[];
    additionalQuestionAsked: string;
  };
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
      coupleStayTogetherPreference: "",
      widowStatus: "",
      lossTiming: "",
      socialActivityChangeSinceLoss: "",
      socialInteractionNeed: "",
    },
    culturalProfile: {
      religionImportance: "",
      faithTraditions: [],
      religiousSupportNeeds: [],
      kosherRequirements: "",
      synagogueChurchAccess: "",
      holidayCelebrations: "",
      culturalIdentity: "",
      israeliJewishCommunityPreference: "",
      whatFeelsLikeHome: [],
    },
    languageProfile: {
      preferredSpokenLanguage: "",
      nativeLanguage: "",
      medicalDiscussionLanguage: "",
      socialInteractionLanguage: "",
      languageNeedScope: "",
      languagesUnderstood: [],
      familyLanguages: [],
    },
    foodProfile: {
      dietaryPreferences: [],
    },
    familyCultureProfile: {
      involvementExpectation: "",
      decisionRole: "",
    },
    communityPreferenceProfile: {
      preferredEnvironment: [],
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
      socialIsolationConcern: "",
      recentHospitalization: "",
      hospitalizationRecency: "",
      postHospitalRehabNeed: "",
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
    scoringEngine: {
      overallConfidence: 0,
      confidenceThreshold: 72,
      adaptiveSignals: [],
      scoringWeights: {},
      outputScores: {
        social_fit_score: 0,
        family_fit_score: 0,
        language_fit_score: 0,
        cultural_fit_score: 0,
        religious_fit_score: 0,
        food_fit_score: 0,
        family_engagement_score: 0,
        community_style_score: 0,
        independence_fit_score: 0,
        transition_success_probability: 0,
        loneliness_risk_score: 0,
      },
      recommendationImpacts: [],
      additionalQuestionAsked: "",
    },
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
