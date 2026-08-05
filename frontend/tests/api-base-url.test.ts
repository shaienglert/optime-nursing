import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchPatientDecisionRecommendations, getApiBaseUrl } from "../src/lib/api";

describe("getApiBaseUrl", () => {
  const env = process.env as Record<string, string | undefined>;
  const originalNodeEnv = process.env.NODE_ENV;
  const originalPublicApiUrl = process.env.NEXT_PUBLIC_API_URL;
  const originalWindow = (globalThis as { window?: unknown }).window;
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    env.NODE_ENV = originalNodeEnv;
    if (originalPublicApiUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = originalPublicApiUrl;
    }

    if (originalWindow === undefined) {
      delete (globalThis as { window?: unknown }).window;
    } else {
      (globalThis as { window?: unknown }).window = originalWindow;
    }

    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("falls back to local backend in development when no NEXT_PUBLIC_API_URL is set", () => {
    env.NODE_ENV = "development";
    delete process.env.NEXT_PUBLIC_API_URL;
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses same-origin proxy in browser even if NEXT_PUBLIC_API_URL points at localhost:3000", () => {
    env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://localhost:3000",
        hostname: "localhost",
      },
    };

    expect(getApiBaseUrl()).toBe("/api/backend");
  });

  it("uses same-origin proxy in browser with loopback alias mismatch", () => {
    env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://127.0.0.1:3000",
        hostname: "127.0.0.1",
      },
    };

    expect(getApiBaseUrl()).toBe("/api/backend");
  });

  it("guards against local frontend :3000 base even when window is unavailable", () => {
    env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:3000";
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses configured backend base when provided", () => {
    env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000";
    delete (globalThis as { window?: unknown }).window;

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("routes Results recommendations request through same-origin backend proxy", async () => {
    env.NODE_ENV = "development";
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:3000";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "http://localhost:3000",
        hostname: "localhost",
      },
    };

    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        patient_needs_profile: {
          generated_from: { questionnaire: true, natural_language: true },
          needs: [],
          need_tags: [],
          priority_parameter_ids: [],
          profile_key: null,
        },
        evaluation_context: {
          available_facilities_count: 0,
          scored_facilities_count: 0,
          filter_exclusion_summary: {
            hard_filter_exclusions: 0,
            soft_penalty_flags: 0,
            unavailable_marked: 0,
            insufficient_evidence_flags: 0,
          },
          assumptions_applied: [],
        },
        result_count: 0,
        total_candidates_scored: 0,
        availability_policy: "",
        results: [],
        recommendation_matrix: [],
        recommendation_trace: [],
      }),
    })) as unknown as typeof fetch;

    globalThis.fetch = fetchMock;

    await fetchPatientDecisionRecommendations({
      questionnaire_state: {
        relationship: "Dad",
        ageGroup: "80-84",
        assistanceLevel: "",
        futureCarePreference: "",
        memoryStatus: "",
        happinessPreferences: [],
        budget: 7000,
        distanceFromFamily: "",
        referenceLocationType: "",
        referenceLocationValue: "",
        locationImportant: "",
        referenceAddress: "",
        maximumDistanceMiles: "",
        customDistanceMiles: "",
        otherInterests: "",
        notes: "",
        humanIntelligenceV2: {
          socialProfile: { livingAloneDuration: "", socialInteractionFrequency: "", newFriendsImportance: "", hobbyParticipation: [], preferredSocialIntensity: "" },
          familyProfile: { involvedFamilyMembers: "", visitFrequencyExpectation: "", grandchildrenPresence: "", grandchildrenImportance: "", familyDecisionDynamics: "", emergencySupportNetwork: "", coupleStayTogetherPreference: "", widowStatus: "", lossTiming: "", socialActivityChangeSinceLoss: "", socialInteractionNeed: "", temporarySeparationAcceptance: "", griefSupportInterest: "" },
          culturalProfile: { religionImportance: "", faithTraditions: [], religiousSupportNeeds: [], kosherRequirements: "", synagogueChurchAccess: "", holidayCelebrations: "", culturalIdentity: "", israeliJewishCommunityPreference: "", whatFeelsLikeHome: [], worshipAccessRequirement: "", jewishProgrammingImportance: "", churchAccessRequirement: "", christianServiceRequirement: "", halalMealsRequirement: "", prayerFacilityRequirement: "" },
          languageProfile: { preferredSpokenLanguage: "", nativeLanguage: "", medicalDiscussionLanguage: "", socialInteractionLanguage: "", languageNeedScope: "", languagesUnderstood: [], familyLanguages: [], bilingualStaffRequired: "" },
          foodProfile: { dietaryPreferences: [] },
          familyCultureProfile: { involvementExpectation: "", decisionRole: "" },
          communityPreferenceProfile: { preferredEnvironment: [] },
          personalityProfile: { introvertExtrovert: "", communitySizePreference: "", privacyImportance: "", structureFlexibilityPreference: "" },
          interestsProfile: [],
          independenceProfile: { drivingImportance: "", cookingImportance: "", abilityToLeaveIndependently: "", petOwnershipImportance: "", hostingFamilyImportance: "" },
          transitionRiskProfile: { biggestFear: "", attitudeTowardMove: "", previousMoves: "", bereavementStatus: "", lonelinessRisk: "", socialIsolationConcern: "", recentHospitalization: "", hospitalizationRecency: "", postHospitalRehabNeed: "", wanderingConcerns: "" },
          futureCareProfile: { agingInPlaceImportance: "", avoidFutureMovesPreference: "", continuumOfCarePreference: "", secureMemoryNeighborhoodNeed: "", familiarLanguageRequirement: "" },
          distanceProfile: {
            referenceLocations: { parentCurrentHome: "", primaryCaregiverHome: "", secondaryFamilyHomes: "", preferredHospital: "", placeOfWorship: "" },
            driveTimes: { normal: "", rushHour: "", emergency: "" },
            familyVisitExpectation: "",
            familyGeographyModel: { involvedFamilyMembers: "", familyCenterOfGravity: "", multiLocationOptimization: "" },
            emotionalDistanceFactors: { emergencyAccessImportance: "", spontaneousVisitsImportance: "", grandchildrenVisitsImportance: "" },
            careLevelWeight: 0,
            optimizationStrategy: "",
            scores: { family_distance_score: null, visit_probability_score: null, emergency_access_score: null, grandchildren_access_score: null, travel_burden_score: null, family_engagement_score: null },
            inferredConfidence: {},
          },
          confidence: {},
          scoringEngine: {
            overallConfidence: 0,
            confidenceThreshold: 0,
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
      },
      natural_language_query: "stroke rehab",
      limit: 50,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestUrl, requestInit] = (fetchMock as unknown as { mock: { calls: unknown[][] } }).mock.calls[0] || [];
    expect(requestUrl).toBe("/api/backend/decision-engine/recommendations");
    expect((requestInit as { method?: string })?.method).toBe("POST");
  });
  
  it("surfaces an error when decision-engine endpoint returns 404", async () => {
    env.NODE_ENV = "production";
    process.env.NEXT_PUBLIC_API_URL = "https://example.test";
    (globalThis as { window?: { location: { origin: string; hostname: string } } }).window = {
      location: {
        origin: "https://optime-nursing.vercel.app",
        hostname: "optime-nursing.vercel.app",
      },
    };

    const calls: string[] = [];
    const fetchMock = vi.fn(async (input: string) => {
      calls.push(String(input));

      if (String(input).endsWith("/decision-engine/recommendations")) {
        return {
          ok: false,
          status: 404,
          json: async () => ({ detail: "Not Found" }),
        };
      }

      if (String(input).endsWith("/facilities")) {
        return {
          ok: true,
          status: 200,
          json: async () => ([
            {
              id: 1,
              cms_id: "105000",
              name: "Facility One",
              city: "Miami",
              state: "FL",
              address: "Addr 1",
              zip_code: "33101",
              phone: null,
              overall_rating: 4,
              staffing_rating: 4,
              quality_rating: 4,
              inspection_rating: 4,
              beds: 120,
              medical_quality_score: 80,
              staffing_score: 80,
              safety_score: 80,
              overall_optime_score: 80,
              confidence_level: "MEDIUM",
              intelligence_confidence: 0.7,
              intelligence_sources_used: [],
              intelligence_positive_signals: [],
              intelligence_negative_signals: [],
              intelligence_signal_details: [],
              family_satisfaction_index: 0,
              staff_stability_index: 0,
              regulatory_risk_index: 0,
              litigation_risk_index: 0,
              social_energy_index: 0,
              community_engagement_index: 0,
              reputation_index: 0,
              cultural_match_signals: 0,
            },
          ]),
        };
      }

      if (String(input).endsWith("/governance/runtime-context")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            generated_at_utc: new Date().toISOString(),
            professional_rule_registry: {
              version: "test",
              rule_count: 0,
              hash: "test",
              rules: [],
              validator_policy: {},
            },
            canonical_coverage: {
              canonical_total: 1,
              runtime_total: 1,
              confirmed_canonical_identity: 1,
              unresolved_identity: 0,
            },
          }),
        };
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: "Not Found" }),
      };
    }) as unknown as typeof fetch;

    globalThis.fetch = fetchMock;

    await expect(fetchPatientDecisionRecommendations({
      questionnaire_state: {
        relationship: "Dad",
        ageGroup: "80-84",
        assistanceLevel: "24/7 support required",
        futureCarePreference: "No preference",
        memoryStatus: "No",
        happinessPreferences: [],
        budget: 7000,
        distanceFromFamily: "Balanced location",
        referenceLocationType: "",
        referenceLocationValue: "Miami",
        locationImportant: "",
        referenceAddress: "",
        maximumDistanceMiles: "",
        customDistanceMiles: "",
        otherInterests: "",
        notes: "Stroke rehab",
        humanIntelligenceV2: {
          socialProfile: { livingAloneDuration: "", socialInteractionFrequency: "", newFriendsImportance: "", hobbyParticipation: [], preferredSocialIntensity: "" },
          familyProfile: { involvedFamilyMembers: "", visitFrequencyExpectation: "", grandchildrenPresence: "", grandchildrenImportance: "", familyDecisionDynamics: "", emergencySupportNetwork: "", coupleStayTogetherPreference: "", widowStatus: "", lossTiming: "", socialActivityChangeSinceLoss: "", socialInteractionNeed: "", temporarySeparationAcceptance: "", griefSupportInterest: "" },
          culturalProfile: { religionImportance: "", faithTraditions: [], religiousSupportNeeds: [], kosherRequirements: "", synagogueChurchAccess: "", holidayCelebrations: "", culturalIdentity: "", israeliJewishCommunityPreference: "", whatFeelsLikeHome: [], worshipAccessRequirement: "", jewishProgrammingImportance: "", churchAccessRequirement: "", christianServiceRequirement: "", halalMealsRequirement: "", prayerFacilityRequirement: "" },
          languageProfile: { preferredSpokenLanguage: "", nativeLanguage: "", medicalDiscussionLanguage: "", socialInteractionLanguage: "", languageNeedScope: "", languagesUnderstood: [], familyLanguages: [], bilingualStaffRequired: "" },
          foodProfile: { dietaryPreferences: [] },
          familyCultureProfile: { involvementExpectation: "", decisionRole: "" },
          communityPreferenceProfile: { preferredEnvironment: [] },
          personalityProfile: { introvertExtrovert: "", communitySizePreference: "", privacyImportance: "", structureFlexibilityPreference: "" },
          interestsProfile: [],
          independenceProfile: { drivingImportance: "", cookingImportance: "", abilityToLeaveIndependently: "", petOwnershipImportance: "", hostingFamilyImportance: "" },
          transitionRiskProfile: { biggestFear: "", attitudeTowardMove: "", previousMoves: "", bereavementStatus: "", lonelinessRisk: "", socialIsolationConcern: "", recentHospitalization: "", hospitalizationRecency: "", postHospitalRehabNeed: "", wanderingConcerns: "" },
          futureCareProfile: { agingInPlaceImportance: "", avoidFutureMovesPreference: "", continuumOfCarePreference: "", secureMemoryNeighborhoodNeed: "", familiarLanguageRequirement: "" },
          distanceProfile: {
            referenceLocations: { parentCurrentHome: "", primaryCaregiverHome: "", secondaryFamilyHomes: "", preferredHospital: "", placeOfWorship: "" },
            driveTimes: { normal: "", rushHour: "", emergency: "" },
            familyVisitExpectation: "",
            familyGeographyModel: { involvedFamilyMembers: "", familyCenterOfGravity: "", multiLocationOptimization: "" },
            emotionalDistanceFactors: { emergencyAccessImportance: "", spontaneousVisitsImportance: "", grandchildrenVisitsImportance: "" },
            careLevelWeight: 0,
            optimizationStrategy: "",
            scores: { family_distance_score: null, visit_probability_score: null, emergency_access_score: null, grandchildren_access_score: null, travel_burden_score: null, family_engagement_score: null },
            inferredConfidence: {},
          },
          confidence: {},
          scoringEngine: {
            overallConfidence: 0,
            confidenceThreshold: 0,
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
      },
      natural_language_query: "stroke rehab",
      limit: 10,
    })).rejects.toThrow("API request failed (404)");

    expect(calls).toEqual(["/api/backend/decision-engine/recommendations"]);
  });
});
