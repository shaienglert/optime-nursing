import { describe, expect, it } from "vitest";

import { UNKNOWN_FROM_FAMILY } from "../src/lib/assessment-schema";
import { convertAssessmentToQuestionnaireState } from "../src/lib/assessment-profile";
import type { QuestionnaireState } from "../src/context/questionnaire-context";

function questionnaireStateFixture(): QuestionnaireState {
  return {
    relationship: "", gender: "", coupleAssistance: "", ageGroup: "", assistanceLevel: "", futureCarePreference: "", memoryStatus: "",
    happinessPreferences: [], budget: 0, distanceFromFamily: "", referenceLocationType: "", referenceLocationValue: "", locationImportant: "",
    referenceAddress: "", maximumDistanceMiles: "", customDistanceMiles: "", otherInterests: "", notes: "",
    humanIntelligenceV2: {
      languageProfile: { preferredSpokenLanguage: "", nativeLanguage: "", medicalDiscussionLanguage: "", socialInteractionLanguage: "", languageNeedScope: "", languagesUnderstood: [], familyLanguages: [], bilingualStaffRequired: "" },
      foodProfile: { dietaryPreferences: [] },
      culturalProfile: { religionImportance: "", faithTraditions: [], religiousSupportNeeds: [], kosherRequirements: "", synagogueChurchAccess: "", holidayCelebrations: "", culturalIdentity: "", israeliJewishCommunityPreference: "", whatFeelsLikeHome: [], worshipAccessRequirement: "", jewishProgrammingImportance: "", churchAccessRequirement: "", christianServiceRequirement: "", halalMealsRequirement: "", prayerFacilityRequirement: "" },
      interestsProfile: [],
      distanceProfile: { referenceLocations: { parentCurrentHome: "", primaryCaregiverHome: "", secondaryFamilyHomes: "", preferredHospital: "", placeOfWorship: "" }, driveTimes: { normal: "", rushHour: "", emergency: "" }, familyVisitExpectation: "", familyGeographyModel: { involvedFamilyMembers: "", familyCenterOfGravity: "", multiLocationOptimization: "" }, emotionalDistanceFactors: { emergencyAccessImportance: "", spontaneousVisitsImportance: "", grandchildrenVisitsImportance: "" }, careLevelWeight: 0, optimizationStrategy: "", scores: { family_distance_score: null, visit_probability_score: null, emergency_access_score: null, grandchildren_access_score: null, travel_burden_score: null, family_engagement_score: null }, inferredConfidence: {} },
      transitionRiskProfile: { biggestFear: "", attitudeTowardMove: "", previousMoves: "", bereavementStatus: "", lonelinessRisk: "", socialIsolationConcern: "", recentHospitalization: "", hospitalizationRecency: "", postHospitalRehabNeed: "", wanderingConcerns: "" },
    } as unknown as QuestionnaireState["humanIntelligenceV2"],
  };
}

describe("assessment profile conversion", () => {
  it("preserves family uncertainty instead of converting it to no", () => {
    const result = convertAssessmentToQuestionnaireState({ mobility: UNKNOWN_FROM_FAMILY, cognitive_status: UNKNOWN_FROM_FAMILY }, questionnaireStateFixture(), "2026-08-02T00:00:00.000Z");
    expect(result.questionnaireState.assistanceLevel).toBe(UNKNOWN_FROM_FAMILY);
    expect(result.questionnaireState.memoryStatus).toBe(UNKNOWN_FROM_FAMILY);
    expect(result.questionnaireState.assessmentV2?.answers.cognitive_status).toBe(UNKNOWN_FROM_FAMILY);
  });

  it("keeps therapy disciplines separate in the existing natural-language handoff", () => {
    const result = convertAssessmentToQuestionnaireState({ rehabilitation_needed: "YES", physical_therapy: "YES", occupational_therapy: "NO", speech_therapy: UNKNOWN_FROM_FAMILY }, questionnaireStateFixture());
    expect(result.naturalLanguageQuery).toContain("Physical therapy is needed.");
    expect(result.naturalLanguageQuery).not.toContain("Occupational therapy is needed.");
    expect(result.naturalLanguageQuery).not.toContain("Speech therapy is needed.");
    expect(result.questionnaireState.humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed).toBe("");
  });

  it("serializes Las Vegas selections and consolidated therapy into existing fields", () => {
    const result = convertAssessmentToQuestionnaireState({
      preferred_search_area: ["SUMMERLIN", "HENDERSON"],
      avoid_search_areas: ["PARADISE"],
      mobility: ["DEVICE", "SOME_HELP"],
      rehabilitation_services: ["PHYSICAL_THERAPY", "SPEECH_THERAPY"],
    }, questionnaireStateFixture());
    expect(result.questionnaireState.referenceLocationValue).toBe("Summerlin, Henderson, Las Vegas, Nevada");
    expect(result.questionnaireState.assistanceLevel).toBe("Light assistance");
    expect(result.naturalLanguageQuery).toContain("Physical therapy is needed.");
    expect(result.naturalLanguageQuery).toContain("Speech therapy is needed.");
    expect(result.naturalLanguageQuery).not.toContain("Paradise");
    expect(result.questionnaireState.assessmentV2?.answers.avoid_search_areas).toEqual(["PARADISE"]);
  });

  it("preserves legacy scalar location and mobility drafts", () => {
    const result = convertAssessmentToQuestionnaireState({ preferred_search_area: "Legacy area", mobility: "DEVICE" }, questionnaireStateFixture());
    expect(result.questionnaireState.referenceLocationValue).toBe("Legacy area");
    expect(result.questionnaireState.assistanceLevel).toBe("Light assistance");
  });
});