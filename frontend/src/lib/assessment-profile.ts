import type { QuestionnaireState } from "../context/questionnaire-context";
import { ACTIVE_ASSESSMENT_REGION } from "./assessment-region";
import { ASSESSMENT_SCHEMA_VERSION, UNKNOWN_FROM_FAMILY, type AssessmentAnswers } from "./assessment-schema";

const LANGUAGE_LABELS: Record<string, string> = {
  ENGLISH: "English",
  SPANISH: "Spanish",
  HEBREW: "Hebrew",
  RUSSIAN: "Russian",
  HAITIAN_CREOLE: "Haitian Creole",
  OTHER: "Other",
};

const DIET_LABELS: Record<string, string> = {
  GLUTEN_FREE: "Gluten free",
  KOSHER: "Kosher",
  HALAL: "Halal",
  DIABETIC: "Diabetic",
  LOW_SODIUM: "Low sodium",
  TEXTURE_MODIFIED: "Texture modified",
};

const BUDGET_VALUES: Record<string, number> = {
  UNDER_5000: 4500,
  "5000_7500": 6250,
  "7500_10000": 8750,
  "10000_15000": 12500,
  OVER_15000: 15000,
};

const DISTANCE_LABELS: Record<string, string> = {
  "15_MIN": "Within 15 minutes",
  "30_MIN": "Within 30 minutes",
  "60_MIN": "Within 60 minutes",
  BEST_FIT: "Best fit matters more than distance",
};

const REGION_AREA_LABELS = Object.fromEntries(ACTIVE_ASSESSMENT_REGION.areas.map((area) => [area.value, area.label]));

function list(answers: AssessmentAnswers, key: string): string[] {
  return Array.isArray(answers[key]) ? (answers[key] as string[]) : [];
}

function value(answers: AssessmentAnswers, key: string): string {
  return typeof answers[key] === "string" ? String(answers[key]) : "";
}

function locationValue(answers: AssessmentAnswers): string {
  const selected = list(answers, "preferred_search_area").filter((item) => item !== UNKNOWN_FROM_FAMILY);
  if (!selected.length) return value(answers, "preferred_search_area");
  const areas = selected.map((item) => REGION_AREA_LABELS[item] || item);
  return selected.includes(ACTIVE_ASSESSMENT_REGION.allAreasValue)
    ? `${ACTIVE_ASSESSMENT_REGION.regionName}, ${ACTIVE_ASSESSMENT_REGION.state}`
    : `${areas.join(", ")}, ${ACTIVE_ASSESSMENT_REGION.marketName}`;
}

function assistanceLevel(answers: AssessmentAnswers): string {
  const nursing = list(answers, "nursing_needs");
  const medication = value(answers, "medication_support");
  const mobility = list(answers, "mobility");
  const legacyMobility = value(answers, "mobility");
  const dailyActivities = list(answers, "daily_activities");

  if (nursing.includes("24_7") || nursing.includes("WOUND") || nursing.includes("IV") || nursing.includes("RESPIRATORY")) return "24/7 support required";
  if (medication === "ADMINISTRATION" || medication === "COMPLEX") return "Help with medications";
  if (dailyActivities.includes("BATHING")) return "Help with bathing";
  if (dailyActivities.includes("DRESSING")) return "Help with dressing";
  if (mobility.some((item) => ["SOME_HELP", "SIGNIFICANT_HELP", "FULLY_DEPENDENT", "DEVICE"].includes(item))) return "Light assistance";
  if (mobility.includes(UNKNOWN_FROM_FAMILY) || legacyMobility === UNKNOWN_FROM_FAMILY) return UNKNOWN_FROM_FAMILY;
  if (mobility.includes("INDEPENDENT") || legacyMobility === "INDEPENDENT") return "Fully independent";
  return ["SOME_HELP", "SIGNIFICANT_HELP", "FULLY_DEPENDENT", "DEVICE"].includes(legacyMobility) ? "Light assistance" : "";
}

function memoryStatus(answers: AssessmentAnswers): string {
  const mapping: Record<string, string> = {
    NO_CONCERNS: "No",
    OCCASIONAL: "Occasionally forgetful",
    MILD: "Mild memory issues",
    SIGNIFICANT: "Significant memory issues",
    [UNKNOWN_FROM_FAMILY]: UNKNOWN_FROM_FAMILY,
  };
  return mapping[value(answers, "cognitive_status")] || "";
}

function buildNaturalLanguageQuery(answers: AssessmentAnswers): string {
  const statements: string[] = [];
  const preferredArea = locationValue(answers);
  if (preferredArea) statements.push(`Preferred search area: ${preferredArea}.`);
  const rehabilitationServices = list(answers, "rehabilitation_services");
  if (rehabilitationServices.includes("PHYSICAL_THERAPY") || value(answers, "physical_therapy") === "YES") statements.push("Physical therapy is needed.");
  if (rehabilitationServices.includes("OCCUPATIONAL_THERAPY") || value(answers, "occupational_therapy") === "YES") statements.push("Occupational therapy is needed.");
  if (rehabilitationServices.includes("SPEECH_THERAPY") || value(answers, "speech_therapy") === "YES") statements.push("Speech therapy is needed.");
  if (value(answers, "stroke_recovery") === "YES") statements.push("A dedicated stroke rehabilitation program is needed.");
  if (value(answers, "neurological_rehabilitation") === "YES") statements.push("A neurological rehabilitation program is needed.");
  if (value(answers, "transfer_assistance") && !["INDEPENDENT", UNKNOWN_FROM_FAMILY].includes(value(answers, "transfer_assistance"))) statements.push("Transfer assistance is needed.");
  if (["ADMINISTRATION", "COMPLEX"].includes(value(answers, "medication_support"))) statements.push("Medication management support is needed.");
  const dailyActivities = list(answers, "daily_activities");
  if (dailyActivities.some((item) => !["NONE", UNKNOWN_FROM_FAMILY].includes(item))) statements.push("ADL support is needed.");
  return statements.join(" ");
}

export type AssessmentProfileConversion = {
  questionnaireState: QuestionnaireState;
  naturalLanguageQuery: string;
};

export function convertAssessmentToQuestionnaireState(
  answers: AssessmentAnswers,
  currentState: QuestionnaireState,
  recordedAt = new Date().toISOString(),
): AssessmentProfileConversion {
  const languages = list(answers, "language_needs").filter((item) => item !== UNKNOWN_FROM_FAMILY).map((item) => LANGUAGE_LABELS[item] || item);
  const diets = list(answers, "dietary_requirements").filter((item) => !["NONE", UNKNOWN_FROM_FAMILY].includes(item)).map((item) => DIET_LABELS[item] || item);
  const priorities = list(answers, "family_priorities");
  const activities = list(answers, "social_activity_preferences").filter((item) => item !== UNKNOWN_FROM_FAMILY);
  const monthlyBudget = BUDGET_VALUES[value(answers, "monthly_budget")] || 0;
  const preferredArea = locationValue(answers);
  const nextState: QuestionnaireState = {
    ...currentState,
    relationship: value(answers, "who_needs_care"),
    assistanceLevel: assistanceLevel(answers),
    memoryStatus: memoryStatus(answers),
    budget: monthlyBudget,
    distanceFromFamily: DISTANCE_LABELS[value(answers, "distance_from_family")] || value(answers, "distance_from_family"),
    referenceAddress: preferredArea,
    referenceLocationType: "Preferred search area",
    referenceLocationValue: preferredArea,
    locationImportant: preferredArea ? "Yes" : "",
    happinessPreferences: activities,
    otherInterests: priorities.join(", "),
    notes: buildNaturalLanguageQuery(answers),
    assessmentV2: {
      version: ASSESSMENT_SCHEMA_VERSION,
      recordedAt,
      provenance: "FAMILY_QUESTIONNAIRE",
      answers,
    },
    humanIntelligenceV2: {
      ...currentState.humanIntelligenceV2,
      languageProfile: {
        ...currentState.humanIntelligenceV2.languageProfile,
        preferredSpokenLanguage: languages[0] || "",
        languagesUnderstood: languages,
        bilingualStaffRequired: value(answers, "hebrew_support") ? "Yes" : "",
      },
      foodProfile: {
        dietaryPreferences: diets,
      },
      culturalProfile: {
        ...currentState.humanIntelligenceV2.culturalProfile,
        religionImportance: value(answers, "culture_importance"),
        culturalIdentity: list(answers, "cultural_preferences").join(", "),
        faithTraditions: list(answers, "cultural_preferences"),
      },
      interestsProfile: activities,
      distanceProfile: {
        ...currentState.humanIntelligenceV2.distanceProfile,
        referenceLocations: {
          ...currentState.humanIntelligenceV2.distanceProfile.referenceLocations,
          parentCurrentHome: "",
          primaryCaregiverHome: preferredArea,
        },
        familyVisitExpectation: DISTANCE_LABELS[value(answers, "distance_from_family")] || "",
      },
      transitionRiskProfile: {
        ...currentState.humanIntelligenceV2.transitionRiskProfile,
        postHospitalRehabNeed: "",
      },
    },
  };

  return { questionnaireState: nextState, naturalLanguageQuery: nextState.notes };
}