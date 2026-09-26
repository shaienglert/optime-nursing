import type { QuestionnaireState } from "@/context/questionnaire-context";
import { applyCanonicalIdentity } from "@/lib/canonical-intake-state";

/**
 * The structured intake as data.
 *
 * The intake used to be hardcoded JSX: every question was a literal block inside one
 * component, and the answers lived in a draft object plus seventeen separate hooks. That
 * shape made it impossible to show one question at a time — there was no ordered list to
 * step through and no id to address a question by — so the whole interview rendered as a
 * single scrolling page.
 *
 * Here the interview is an ordered list of questions, each of which knows when it applies,
 * how to read its answer and how to record one. Rendering one question, rendering all of
 * them, validating, and resuming at the first unanswered question are then all the same
 * operation over this list.
 */

export type IntakeExtras = {
  assistance: string[];
  activities: string[];
  dietary: string[];
  religiousCommunity: string;
  religion: string;
  religiousNeeds: string[];
  socialFrequency: string;
  communityStyle: string;
  moveAttitude: string;
  recentHospitalization: string;
  rehabNeed: string;
  hospitalTiming: string;
  memoryWandering: string;
  secureMemory: string;
  language: string;
  processLanguage: string;
  medicalLanguage: string;
  continuum: string;
};

export type IntakeContext = { draft: QuestionnaireState; extras: IntakeExtras };

export type IntakeAnswer = string | string[] | number;

export type IntakeQuestion = {
  id: string;
  /** Conversational heading the question belongs to, shown once per run of questions. */
  section: string;
  prompt: string;
  kind: "single" | "multi" | "text" | "number";
  options?: string[];
  placeholder?: string;
  /** Explanatory copy shown above the options (the two-approaches note). */
  note?: string;
  required: boolean;
  /** Human-readable name used when reporting what is still missing. */
  label: string;
  visible: (context: IntakeContext) => boolean;
  get: (context: IntakeContext) => IntakeAnswer;
  set: (context: IntakeContext, value: IntakeAnswer) => IntakeContext;
};

export const assistanceOptions = [
  "Fully independent",
  "Light assistance",
  "Help with bathing",
  "Help with dressing",
  "Help with toileting",
  "Help with medications",
  "Daytime supervision",
  "24/7 support required",
  "Skilled nursing care",
];

export const medicalOptions = [
  "Dialysis",
  "Oxygen",
  "Wound care",
  "Injections or infusions",
  "Complex medication management",
  "Complex chronic condition",
  "Permanent medical equipment",
  "Nursing supervision",
];

export const moveConcernOptions = [
  "Good food",
  "Privacy",
  "Independence",
  "Social life",
  "Existing friends",
  "A specific class or activity",
  "Ability to go out independently",
  "Proximity to family",
  "My language or culture",
  "Daily routine",
  "Space for visitors",
  "A pet",
  "Transportation",
  "Other",
];

export const activityOptions = ["Music", "Movies", "Games", "Exercise", "Outdoor activities", "Religious life", "Cultural activities", "Classes", "Volunteering"];
export const dietaryOptions = ["Kosher", "Halal", "Vegetarian", "Vegan", "Low sodium", "Diabetic", "Gluten free", "Other"];

export const COMPLEX_MEDICAL_NEEDS = ["Complex chronic condition", "Complex medication management", "Injections or infusions", "Permanent medical equipment", "Nursing supervision"];

const SECTION_PERSON = "Let’s start with who we’re helping";
const SECTION_MEDICAL = "Now let’s understand the medical side";
const SECTION_TIMING = "Let’s talk about timing and budget";
const SECTION_FIT = "Now the part that makes a place feel right";
const SECTION_PRACTICAL = "A few practical things before we wrap up";

export function createExtras(state: QuestionnaireState): IntakeExtras {
  const human = state.humanIntelligenceV2;
  const religionImportance = human.culturalProfile.religionImportance;
  return {
    assistance: state.assistanceLevel ? state.assistanceLevel.split(", ") : [],
    activities: state.happinessPreferences || [],
    dietary: human.foodProfile.dietaryPreferences || [],
    religiousCommunity: religionImportance === "Yes" ? "Yes" : religionImportance === "No" ? "No" : "",
    religion: human.culturalProfile.faithTraditions[0] || "",
    religiousNeeds: human.culturalProfile.religiousSupportNeeds || [],
    socialFrequency: human.socialProfile.socialInteractionFrequency || "",
    communityStyle: human.personalityProfile.communitySizePreference || "",
    moveAttitude: human.transitionRiskProfile.attitudeTowardMove || "",
    recentHospitalization: human.transitionRiskProfile.recentHospitalization || "",
    rehabNeed: human.transitionRiskProfile.postHospitalRehabNeed || "",
    hospitalTiming: human.transitionRiskProfile.hospitalizationRecency || "",
    memoryWandering: human.transitionRiskProfile.wanderingConcerns || "",
    secureMemory: human.futureCareProfile.secureMemoryNeighborhoodNeed || "",
    language: human.languageProfile.preferredSpokenLanguage || "",
    processLanguage: human.languageProfile.processLanguage || "",
    medicalLanguage: human.languageProfile.medicalDiscussionLanguage || "",
    continuum: human.futureCareProfile.avoidFutureMovesPreference || "",
  };
}

// --- derived conditions, named exactly as the questions read them -------------------

export const needsMobilityFollowUp = ({ extras }: IntakeContext) => extras.assistance.some((item) => item !== "Fully independent");
export const hasMemoryConcern = ({ draft }: IntakeContext) => Boolean(draft.memoryStatus && !["No", "Not sure"].includes(draft.memoryStatus));
export const needsMedicalDetails = ({ draft }: IntakeContext) => draft.medicalCareProfile.hasOngoingMedicalNeeds === "Yes";
const hasMedicalNeed = (context: IntakeContext, need: string) => needsMedicalDetails(context) && context.draft.medicalCareProfile.needs.includes(need);
export const isCouple = ({ draft }: IntakeContext) => draft.relationship === "Couple";

// --- small helpers for reading and writing nested state ----------------------------

const setDraft = (context: IntakeContext, patch: Partial<QuestionnaireState>): IntakeContext => ({ ...context, draft: { ...context.draft, ...patch } });

const setMedical = (context: IntakeContext, patch: Partial<QuestionnaireState["medicalCareProfile"]>): IntakeContext => ({
  ...context,
  draft: { ...context.draft, medicalCareProfile: { ...context.draft.medicalCareProfile, ...patch } },
});

const setExtra = (context: IntakeContext, patch: Partial<IntakeExtras>): IntakeContext => ({ ...context, extras: { ...context.extras, ...patch } });

const setIndependence = (context: IntakeContext, patch: Partial<QuestionnaireState["humanIntelligenceV2"]["independenceProfile"]>): IntakeContext => ({
  ...context,
  draft: {
    ...context.draft,
    humanIntelligenceV2: {
      ...context.draft.humanIntelligenceV2,
      independenceProfile: { ...context.draft.humanIntelligenceV2.independenceProfile, ...patch },
    },
  },
});

const setTransitionRisk = (context: IntakeContext, patch: Partial<QuestionnaireState["humanIntelligenceV2"]["transitionRiskProfile"]>): IntakeContext => ({
  ...context,
  draft: {
    ...context.draft,
    humanIntelligenceV2: {
      ...context.draft.humanIntelligenceV2,
      transitionRiskProfile: { ...context.draft.humanIntelligenceV2.transitionRiskProfile, ...patch },
    },
  },
});

const text = (value: IntakeAnswer): string => (typeof value === "string" ? value : String(value ?? ""));
const list = (value: IntakeAnswer): string[] => (Array.isArray(value) ? value : []);

export const QUESTIONS: IntakeQuestion[] = [
  {
    id: "relationship",
    section: SECTION_PERSON,
    prompt: "Who are we finding the right place for?",
    kind: "single",
    options: ["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Myself", "Couple", "Relative", "Friend"],
    required: true,
    label: "who the search is for",
    visible: () => true,
    get: ({ draft }) => draft.relationship,
    // A manual relationship change invalidates gender derived from the previous one.
    set: (context, value) => ({ ...context, draft: applyCanonicalIdentity({ ...context.draft, gender: "" }, text(value)) }),
  },
  {
    id: "ageGroup",
    section: SECTION_PERSON,
    prompt: "About how old are they?",
    kind: "single",
    options: ["60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"],
    required: true,
    label: "age group",
    visible: () => true,
    get: ({ draft }) => draft.ageGroup,
    set: (context, value) => setDraft(context, { ageGroup: text(value) }),
  },
  {
    id: "searchState",
    section: SECTION_PERSON,
    prompt: "Which state are you looking in?",
    kind: "single",
    options: ["Nevada", "Florida", "California", "Arizona", "Texas", "New York", "New Jersey", "Illinois", "Pennsylvania", "Massachusetts", "Other"],
    required: true,
    label: "search state",
    visible: () => true,
    get: ({ draft }) => draft.searchState,
    set: (context, value) => setDraft(context, { searchState: text(value) }),
  },
  {
    id: "assistance",
    section: SECTION_PERSON,
    prompt: "What kind of help makes everyday life easier? Choose anything that fits.",
    kind: "multi",
    options: assistanceOptions,
    required: true,
    label: "daily assistance",
    visible: () => true,
    get: ({ extras }) => extras.assistance,
    set: (context, value) => {
      const next = list(value);
      // "Fully independent" cannot coexist with a specific support need.
      const added = next.find((item) => !context.extras.assistance.includes(item));
      if (added === "Fully independent") return setExtra(context, { assistance: ["Fully independent"] });
      return setExtra(context, { assistance: next.filter((item) => item !== "Fully independent") });
    },
  },
  {
    id: "mobilityMethod",
    section: SECTION_PERSON,
    prompt: "How do they usually get around?",
    kind: "single",
    options: ["Independent", "Cane", "Walker", "Wheelchair", "Mostly in bed"],
    required: true,
    label: "mobility",
    visible: needsMobilityFollowUp,
    get: ({ draft }) => draft.medicalCareProfile.mobilityMethod,
    set: (context, value) => setMedical(context, { mobilityMethod: text(value) }),
  },
  {
    id: "transferAssistance",
    section: SECTION_PERSON,
    prompt: "Do they need help getting up, sitting down, or transferring?",
    kind: "single",
    options: ["No", "One person", "Two people", "Mechanical lift", "Not sure"],
    required: true,
    label: "transfer assistance",
    visible: needsMobilityFollowUp,
    get: ({ draft }) => draft.medicalCareProfile.transferAssistance,
    set: (context, value) => setMedical(context, { transferAssistance: text(value) }),
  },
  {
    id: "recentFalls",
    section: SECTION_PERSON,
    prompt: "Have there been any falls in the last six months?",
    kind: "single",
    options: ["No", "One", "More than one", "Not sure"],
    required: true,
    label: "recent falls",
    visible: needsMobilityFollowUp,
    get: ({ draft }) => draft.medicalCareProfile.recentFalls,
    set: (context, value) => setMedical(context, { recentFalls: text(value) }),
  },
  {
    id: "memoryStatus",
    section: SECTION_PERSON,
    prompt: "Have you noticed any changes in memory or confusion lately?",
    kind: "single",
    options: ["No", "Occasionally forgetful", "Mild memory issues", "Significant memory issues", "Not sure"],
    required: true,
    label: "memory status",
    visible: () => true,
    get: ({ draft }) => draft.memoryStatus,
    set: (context, value) => setDraft(context, { memoryStatus: text(value) }),
  },
  {
    id: "memoryWandering",
    section: SECTION_PERSON,
    prompt: "Is there any concern about wandering or getting lost?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "wandering concern",
    visible: hasMemoryConcern,
    get: ({ extras }) => extras.memoryWandering,
    set: (context, value) => setExtra(context, { memoryWandering: text(value) }),
  },
  {
    id: "secureMemory",
    section: SECTION_PERSON,
    prompt: "Based on their memory and safety needs, is a secure memory-care setting actually needed?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "secure memory-care need",
    visible: hasMemoryConcern,
    get: ({ extras }) => extras.secureMemory,
    set: (context, value) => setExtra(context, { secureMemory: text(value) }),
  },
  {
    id: "hasOngoingMedicalNeeds",
    section: SECTION_MEDICAL,
    prompt: "Is there any ongoing medical care the community would need to provide or coordinate?",
    kind: "single",
    options: ["No", "Yes", "Not sure"],
    required: true,
    label: "ongoing medical needs",
    visible: () => true,
    get: ({ draft }) => draft.medicalCareProfile.hasOngoingMedicalNeeds,
    set: (context, value) => setMedical(context, { hasOngoingMedicalNeeds: text(value), needs: text(value) === "No" ? [] : context.draft.medicalCareProfile.needs }),
  },
  {
    id: "medicalNeeds",
    section: SECTION_MEDICAL,
    prompt: "Which of these are part of the current routine?",
    kind: "multi",
    options: medicalOptions,
    required: true,
    label: "medical need type",
    visible: needsMedicalDetails,
    get: ({ draft }) => draft.medicalCareProfile.needs,
    set: (context, value) => setMedical(context, { needs: list(value) }),
  },
  {
    id: "dialysisFrequency",
    section: SECTION_MEDICAL,
    prompt: "How often is dialysis needed?",
    kind: "text",
    placeholder: "e.g. three times weekly",
    required: true,
    label: "dialysis frequency",
    visible: (context) => hasMedicalNeed(context, "Dialysis"),
    get: ({ draft }) => draft.medicalCareProfile.dialysisFrequency,
    set: (context, value) => setMedical(context, { dialysisFrequency: text(value) }),
  },
  {
    id: "dialysisCenter",
    section: SECTION_MEDICAL,
    prompt: "Which dialysis center is used today?",
    kind: "text",
    placeholder: "Name or location",
    required: false,
    label: "dialysis center",
    visible: (context) => hasMedicalNeed(context, "Dialysis"),
    get: ({ draft }) => draft.medicalCareProfile.dialysisCenter,
    set: (context, value) => setMedical(context, { dialysisCenter: text(value) }),
  },
  {
    id: "dialysisTransportation",
    section: SECTION_MEDICAL,
    prompt: "Would transportation to dialysis be needed?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "dialysis transportation",
    visible: (context) => hasMedicalNeed(context, "Dialysis"),
    get: ({ draft }) => draft.medicalCareProfile.dialysisTransportation,
    set: (context, value) => setMedical(context, { dialysisTransportation: text(value) }),
  },
  {
    id: "oxygenUse",
    section: SECTION_MEDICAL,
    prompt: "How is oxygen used day to day?",
    kind: "single",
    options: ["Continuously", "At night", "As needed", "Not sure"],
    required: true,
    label: "oxygen details",
    visible: (context) => hasMedicalNeed(context, "Oxygen"),
    get: ({ draft }) => draft.medicalCareProfile.oxygenUse,
    set: (context, value) => setMedical(context, { oxygenUse: text(value) }),
  },
  {
    id: "woundCareFrequency",
    section: SECTION_MEDICAL,
    prompt: "How often is wound care required?",
    kind: "text",
    placeholder: "Daily, three times weekly...",
    required: true,
    label: "wound-care details",
    visible: (context) => hasMedicalNeed(context, "Wound care"),
    get: ({ draft }) => draft.medicalCareProfile.woundCareFrequency,
    set: (context, value) => setMedical(context, { woundCareFrequency: text(value) }),
  },
  {
    id: "complexConditionDetails",
    section: SECTION_MEDICAL,
    prompt: "Describe what the community must provide or coordinate.",
    kind: "text",
    placeholder: "Condition, treatment, equipment, nursing task...",
    required: true,
    label: "complex medical details",
    visible: (context) => needsMedicalDetails(context) && context.draft.medicalCareProfile.needs.some((item) => COMPLEX_MEDICAL_NEEDS.includes(item)),
    get: ({ draft }) => draft.medicalCareProfile.complexConditionDetails,
    set: (context, value) => setMedical(context, { complexConditionDetails: text(value) }),
  },
  {
    id: "complexConditionSupportLevel",
    section: SECTION_MEDICAL,
    prompt: "Do they manage this equipment or condition independently, or do they need help with it?",
    kind: "single",
    options: ["Independently", "Some daily help", "Clinical or nursing help", "Not sure"],
    required: true,
    label: "support needed for medical equipment or chronic condition",
    visible: (context) => needsMedicalDetails(context) && context.draft.medicalCareProfile.needs.some((item) => COMPLEX_MEDICAL_NEEDS.includes(item)),
    get: ({ draft }) => draft.medicalCareProfile.complexConditionSupportLevel,
    set: (context, value) => setMedical(context, { complexConditionSupportLevel: text(value) }),
  },
  {
    id: "physicianCoordination",
    section: SECTION_MEDICAL,
    prompt: "Would it help if the community coordinated doctors, appointments, tests, or medication changes?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "medical coordination",
    visible: needsMedicalDetails,
    get: ({ draft }) => draft.medicalCareProfile.physicianCoordination,
    set: (context, value) => setMedical(context, { physicianCoordination: text(value) }),
  },
  {
    id: "recentHospitalization",
    section: SECTION_MEDICAL,
    prompt: "Has there been a hospital stay recently?",
    kind: "single",
    options: ["No", "Yes", "Not sure"],
    required: true,
    label: "recent hospitalization",
    visible: () => true,
    get: ({ extras }) => extras.recentHospitalization,
    set: (context, value) => setExtra(context, { recentHospitalization: text(value) }),
  },
  {
    id: "hospitalTiming",
    section: SECTION_MEDICAL,
    prompt: "Roughly when was that?",
    kind: "single",
    options: ["Within 30 days", "1-3 months", "3-6 months", "More than 6 months"],
    required: true,
    label: "hospitalization timing",
    visible: ({ extras }) => extras.recentHospitalization === "Yes",
    get: ({ extras }) => extras.hospitalTiming,
    set: (context, value) => setExtra(context, { hospitalTiming: text(value) }),
  },
  {
    id: "rehabNeed",
    section: SECTION_MEDICAL,
    prompt: "Is rehabilitation or closer monitoring still needed?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "rehabilitation need",
    visible: ({ extras }) => extras.recentHospitalization === "Yes",
    get: ({ extras }) => extras.rehabNeed,
    set: (context, value) => setExtra(context, { rehabNeed: text(value) }),
  },
  {
    id: "rehabServicesNeeded",
    section: SECTION_MEDICAL,
    prompt: "Which rehabilitation services are actually needed now?",
    kind: "multi",
    options: ["Physical therapy", "Occupational therapy", "Speech therapy", "Not sure"],
    required: true,
    label: "rehabilitation services needed",
    visible: ({ extras }) => extras.rehabNeed === "Yes",
    get: ({ draft }) => draft.medicalCareProfile.rehabServicesNeeded,
    set: (context, value) => setMedical(context, { rehabServicesNeeded: list(value) }),
  },
  {
    id: "medicareStatus",
    section: SECTION_MEDICAL,
    prompt: "What’s the current Medicare situation?",
    kind: "single",
    options: ["Original Medicare", "Medicare Advantage", "No Medicare", "Not sure"],
    required: true,
    label: "Medicare situation",
    visible: ({ extras }) => extras.rehabNeed === "Yes",
    get: ({ draft }) => draft.medicareStatus,
    set: (context, value) => setDraft(context, { medicareStatus: text(value) }),
  },
  {
    id: "medicaidStatus",
    section: SECTION_MEDICAL,
    prompt: "And what’s the Medicaid situation?",
    kind: "single",
    options: ["Approved", "Application pending", "May qualify", "Not eligible", "Not sure"],
    required: true,
    label: "Medicaid situation",
    visible: () => true,
    get: ({ draft }) => draft.medicaidStatus,
    set: (context, value) => setDraft(context, { medicaidStatus: text(value) }),
  },
  {
    id: "budget",
    section: SECTION_TIMING,
    prompt: "What monthly budget would feel comfortable?",
    kind: "number",
    placeholder: "Monthly amount in dollars",
    required: true,
    label: "monthly budget",
    visible: () => true,
    get: ({ draft }) => draft.budget,
    set: (context, value) => setDraft(context, { budget: Math.max(0, Number(value) || 0) }),
  },
  {
    id: "moveTiming",
    section: SECTION_TIMING,
    prompt: "When would you ideally like the move to happen?",
    kind: "single",
    options: ["Immediately", "Within 30 days", "1-3 months", "3-6 months", "Planning ahead", "Not sure"],
    required: true,
    label: "move timing",
    visible: () => true,
    get: ({ draft }) => draft.moveTiming,
    set: (context, value) => setDraft(context, { moveTiming: text(value) }),
  },
  {
    id: "moveAttitude",
    section: SECTION_TIMING,
    prompt: "How do they feel about the idea of moving?",
    kind: "single",
    options: ["Wants to move", "Positive", "Cautious but open", "Anxious", "Resistant", "Not sure"],
    required: true,
    label: "attitude to moving",
    visible: () => true,
    get: ({ extras }) => extras.moveAttitude,
    set: (context, value) => setExtra(context, { moveAttitude: text(value) }),
  },
  {
    id: "socialFrequency",
    section: SECTION_FIT,
    prompt: "How social would they like everyday life to be?",
    kind: "single",
    options: ["Daily", "Several times weekly", "Weekly", "Occasionally", "Very little"],
    required: true,
    label: "social preference",
    visible: () => true,
    get: ({ extras }) => extras.socialFrequency,
    set: (context, value) => setExtra(context, { socialFrequency: text(value) }),
  },
  {
    id: "communityStyle",
    section: SECTION_FIT,
    prompt: "What kind of community would feel most comfortable?",
    kind: "single",
    options: ["Small and familiar", "Medium", "Large and active", "Quiet", "No preference"],
    required: true,
    label: "community style",
    visible: () => true,
    get: ({ extras }) => extras.communityStyle,
    set: (context, value) => setExtra(context, { communityStyle: text(value) }),
  },
  {
    id: "activities",
    section: SECTION_FIT,
    prompt: "What do they genuinely enjoy doing? Choose anything that matters.",
    kind: "multi",
    options: activityOptions,
    required: true,
    label: "activities enjoyed",
    visible: () => true,
    get: ({ extras }) => extras.activities,
    set: (context, value) => setExtra(context, { activities: list(value) }),
  },
  {
    id: "moveLossConcerns",
    section: SECTION_FIT,
    prompt: "What would you hate for them to lose after the move?",
    kind: "multi",
    options: moveConcernOptions,
    required: true,
    label: "move concerns",
    visible: () => true,
    get: ({ draft }) => draft.moveLossConcerns,
    set: (context, value) => setDraft(context, { moveLossConcerns: list(value) }),
  },
  {
    id: "otherInterests",
    section: SECTION_FIT,
    prompt: "Anything specific we should preserve?",
    kind: "text",
    placeholder: "A particular class, food, routine, pet, or activity",
    required: false,
    label: "things to preserve",
    visible: () => true,
    get: ({ draft }) => draft.otherInterests,
    set: (context, value) => setDraft(context, { otherInterests: text(value) }),
  },
  {
    id: "processLanguage",
    section: SECTION_FIT,
    prompt: "Which language would you like to use with Oomnik?",
    kind: "single",
    options: ["English", "Spanish", "Chinese", "Vietnamese", "Korean", "Russian", "Tagalog / Filipino", "Arabic", "Haitian Creole", "Portuguese", "Polish", "Persian / Farsi", "Hindi", "Gujarati", "Ukrainian", "French", "Hebrew", "Other"],
    required: true,
    label: "language for the Oomnik process",
    visible: () => true,
    get: ({ extras }) => extras.processLanguage,
    set: (context, value) => setExtra(context, { processLanguage: text(value) }),
  },
  {
    id: "language",
    section: SECTION_FIT,
    prompt: "What language feels most natural day to day?",
    kind: "single",
    options: ["English", "Spanish", "Hebrew", "Russian", "Mandarin", "Arabic", "Other"],
    required: true,
    label: "preferred language",
    visible: () => true,
    get: ({ extras }) => extras.language,
    set: (context, value) => setExtra(context, { language: text(value) }),
  },
  {
    id: "medicalLanguage",
    section: SECTION_FIT,
    prompt: "Which language is needed for medical communication?",
    kind: "text",
    placeholder: "Language or 'English is fine'",
    required: true,
    label: "medical communication language",
    visible: ({ extras }) => Boolean(extras.language) && extras.language !== "English",
    get: ({ extras }) => extras.medicalLanguage,
    set: (context, value) => setExtra(context, { medicalLanguage: text(value) }),
  },
  {
    id: "dietary",
    section: SECTION_FIT,
    prompt: "Are there food preferences or requirements we should respect?",
    kind: "multi",
    options: dietaryOptions,
    required: false,
    label: "dietary preferences",
    visible: () => true,
    get: ({ extras }) => extras.dietary,
    set: (context, value) => setExtra(context, { dietary: list(value) }),
  },
  {
    id: "religiousCommunity",
    section: SECTION_FIT,
    prompt: "Would a religious or faith community be important?",
    kind: "single",
    options: ["No", "Yes"],
    required: true,
    label: "religious-community preference",
    visible: () => true,
    get: ({ extras }) => extras.religiousCommunity,
    set: (context, value) => setExtra(context, { religiousCommunity: text(value) }),
  },
  {
    id: "religion",
    section: SECTION_FIT,
    prompt: "Which religion or tradition?",
    kind: "text",
    required: true,
    label: "religion or tradition",
    visible: ({ extras }) => extras.religiousCommunity === "Yes",
    get: ({ extras }) => extras.religion,
    set: (context, value) => setExtra(context, { religion: text(value) }),
  },
  {
    id: "religiousNeeds",
    section: SECTION_FIT,
    prompt: "What is needed?",
    kind: "multi",
    options: ["Services", "Place of worship", "Prayer space", "Holiday celebrations", "Dietary accommodation", "Chaplain"],
    required: true,
    label: "religious support needed",
    visible: ({ extras }) => extras.religiousCommunity === "Yes",
    get: ({ extras }) => extras.religiousNeeds,
    set: (context, value) => setExtra(context, { religiousNeeds: list(value) }),
  },
  {
    id: "petOwnershipImportance",
    section: SECTION_PRACTICAL,
    prompt: "Would a pet need to move with them?",
    kind: "single",
    options: ["Yes", "No", "Not sure"],
    required: true,
    label: "pet needs",
    visible: () => true,
    get: ({ draft }) => draft.humanIntelligenceV2.independenceProfile.petOwnershipImportance,
    set: (context, value) => setIndependence(context, { petOwnershipImportance: text(value) }),
  },
  {
    id: "abilityToLeaveIndependently",
    section: SECTION_PRACTICAL,
    prompt: "Can they go out independently?",
    kind: "single",
    options: ["Yes", "With support", "No", "Not sure"],
    required: true,
    label: "independent outings",
    visible: () => true,
    get: ({ draft }) => draft.humanIntelligenceV2.independenceProfile.abilityToLeaveIndependently,
    set: (context, value) => setIndependence(context, { abilityToLeaveIndependently: text(value) }),
  },
  {
    id: "biggestFear",
    section: SECTION_PRACTICAL,
    prompt: "What worries them most about moving?",
    kind: "text",
    placeholder: "Tell me in your own words, or say none or not sure",
    required: true,
    label: "biggest move concern",
    visible: () => true,
    get: ({ draft }) => draft.humanIntelligenceV2.transitionRiskProfile.biggestFear,
    set: (context, value) => setTransitionRisk(context, { biggestFear: text(value) }),
  },
  {
    id: "parkingRequirement",
    section: SECTION_PRACTICAL,
    prompt: "Will they need parking at the community?",
    kind: "single",
    options: ["No", "Regular parking", "Accessible parking", "Covered parking", "Not sure"],
    required: true,
    label: "parking requirement",
    visible: () => true,
    get: ({ draft }) => draft.parkingRequirement,
    set: (context, value) => setDraft(context, { parkingRequirement: text(value) }),
  },
  {
    id: "parkingVehicleCount",
    section: SECTION_PRACTICAL,
    prompt: "Would that be for one car or two?",
    kind: "single",
    options: ["One vehicle", "Two vehicles"],
    required: true,
    label: "number of parking spaces",
    visible: (context) => isCouple(context) && Boolean(context.draft.parkingRequirement) && context.draft.parkingRequirement !== "No",
    get: ({ draft }) => draft.parkingVehicleCount,
    set: (context, value) => setDraft(context, { parkingVehicleCount: text(value) }),
  },
  {
    id: "continuum",
    section: SECTION_PRACTICAL,
    prompt: "Would you prefer a place that can provide more care later, so another move may be avoided?",
    kind: "single",
    options: ["Required", "Preferred", "Not important", "Not sure"],
    required: true,
    label: "future care continuity",
    visible: () => true,
    get: ({ extras }) => extras.continuum,
    set: (context, value) => setExtra(context, { continuum: text(value) }),
  },
  {
    id: "careSearchApproach",
    section: SECTION_PRACTICAL,
    prompt: "How broadly would you like me to search?",
    note: "Based on what you’ve told me, a more independent senior community may work today if the extra help needed — such as bathing or medication support — is provided by an outside care provider. The alternative is a community that provides that support itself and can potentially increase care later. A more independent setting may preserve more freedom now, but if care needs become significantly greater, another move could eventually be necessary.",
    kind: "single",
    options: ["Show me both approaches", "Care provided by the community", "Independent living + outside support"],
    required: false,
    label: "search approach",
    visible: ({ extras }) => extras.assistance.length > 0 && !extras.assistance.includes("Skilled nursing"),
    get: ({ draft }) => draft.careSearchApproach,
    set: (context, value) => setDraft(context, { careSearchApproach: text(value) }),
  },
  {
    id: "locationImportant",
    section: SECTION_PRACTICAL,
    prompt: "Does staying near a particular area or person matter?",
    kind: "single",
    options: ["Yes", "No"],
    required: true,
    label: "location importance",
    visible: () => true,
    get: ({ draft }) => draft.locationImportant,
    set: (context, value) => setDraft(context, { locationImportant: text(value) }),
  },
  {
    id: "referenceAddress",
    section: SECTION_PRACTICAL,
    prompt: "Which address or area should I measure from?",
    kind: "text",
    placeholder: "Address, ZIP, city, or neighborhood",
    required: true,
    label: "reference address",
    visible: ({ draft }) => draft.locationImportant === "Yes",
    get: ({ draft }) => draft.referenceAddress,
    set: (context, value) => setDraft(context, { referenceAddress: text(value), referenceLocationValue: text(value) }),
  },
  {
    id: "maximumDistanceMiles",
    section: SECTION_PRACTICAL,
    prompt: "How far would still feel close enough?",
    kind: "single",
    options: ["10", "20", "30", "50", "100"],
    required: true,
    label: "maximum distance",
    visible: ({ draft }) => draft.locationImportant === "Yes",
    get: ({ draft }) => draft.maximumDistanceMiles,
    set: (context, value) => setDraft(context, { maximumDistanceMiles: text(value) }),
  },
];

export function isAnswered(question: IntakeQuestion, context: IntakeContext): boolean {
  const value = question.get(context);
  if (Array.isArray(value)) return value.length > 0;
  if (question.kind === "number") return Number(value) > 0;
  return String(value ?? "").trim().length > 0;
}

/** The questions that apply to this case, in interview order. */
export function visibleQuestions(context: IntakeContext): IntakeQuestion[] {
  return QUESTIONS.filter((question) => question.visible(context));
}

/** Required questions that apply and are still unanswered. */
export function missingQuestions(context: IntakeContext): IntakeQuestion[] {
  return visibleQuestions(context).filter((question) => question.required && !isAnswered(question, context));
}

/**
 * Build the questionnaire state to submit.
 *
 * Follow-up answers whose parent answer no longer requires them are cleared, so a
 * reconsidered answer cannot leave stale, contradictory facts in the profile shown on the
 * confirmation screen and sent to the decision engine.
 */
export function buildSubmission(context: IntakeContext): QuestionnaireState {
  const { draft, extras } = context;
  const mobility = needsMobilityFollowUp(context);
  const memory = hasMemoryConcern(context);
  const medicalDetails = needsMedicalDetails(context);
  const dialysis = hasMedicalNeed(context, "Dialysis");
  const oxygen = hasMedicalNeed(context, "Oxygen");
  const wound = hasMedicalNeed(context, "Wound care");
  const complex = medicalDetails && draft.medicalCareProfile.needs.some((item) => COMPLEX_MEDICAL_NEEDS.includes(item));

  return {
    ...draft,
    assistanceLevel: extras.assistance.join(", "),
    happinessPreferences: extras.activities,
    medicareStatus: extras.rehabNeed === "Yes" ? draft.medicareStatus : "",
    questionnaireCompletion: {
      mandatoryComplete: true,
      conditionalFollowUpsComplete: true,
      clientSummaryConfirmed: false,
      confirmedAt: "",
    },
    medicalCareProfile: {
      ...draft.medicalCareProfile,
      mobilityMethod: mobility ? draft.medicalCareProfile.mobilityMethod : "",
      transferAssistance: mobility ? draft.medicalCareProfile.transferAssistance : "",
      recentFalls: mobility ? draft.medicalCareProfile.recentFalls : "",
      dialysisFrequency: dialysis ? draft.medicalCareProfile.dialysisFrequency : "",
      dialysisCenter: dialysis ? draft.medicalCareProfile.dialysisCenter : "",
      dialysisTransportation: dialysis ? draft.medicalCareProfile.dialysisTransportation : "",
      oxygenUse: oxygen ? draft.medicalCareProfile.oxygenUse : "",
      woundCareFrequency: wound ? draft.medicalCareProfile.woundCareFrequency : "",
      complexConditionDetails: complex ? draft.medicalCareProfile.complexConditionDetails : "",
      complexConditionSupportLevel: complex ? draft.medicalCareProfile.complexConditionSupportLevel : "",
      physicianCoordination: medicalDetails ? draft.medicalCareProfile.physicianCoordination : "",
      rehabServicesNeeded: extras.rehabNeed === "Yes" ? draft.medicalCareProfile.rehabServicesNeeded : [],
    },
    humanIntelligenceV2: {
      ...draft.humanIntelligenceV2,
      socialProfile: { ...draft.humanIntelligenceV2.socialProfile, socialInteractionFrequency: extras.socialFrequency, hobbyParticipation: extras.activities },
      culturalProfile: {
        ...draft.humanIntelligenceV2.culturalProfile,
        religionImportance: extras.religiousCommunity,
        faithTraditions: extras.religiousCommunity === "Yes" ? [extras.religion] : [],
        religiousSupportNeeds: extras.religiousCommunity === "Yes" ? extras.religiousNeeds : [],
      },
      languageProfile: { ...draft.humanIntelligenceV2.languageProfile, processLanguage: extras.processLanguage, preferredSpokenLanguage: extras.language, medicalDiscussionLanguage: extras.medicalLanguage },
      foodProfile: { dietaryPreferences: extras.dietary },
      personalityProfile: { ...draft.humanIntelligenceV2.personalityProfile, communitySizePreference: extras.communityStyle },
      transitionRiskProfile: {
        ...draft.humanIntelligenceV2.transitionRiskProfile,
        attitudeTowardMove: extras.moveAttitude,
        recentHospitalization: extras.recentHospitalization,
        hospitalizationRecency: extras.recentHospitalization === "Yes" ? extras.hospitalTiming : "",
        postHospitalRehabNeed: extras.recentHospitalization === "Yes" ? extras.rehabNeed : "",
        wanderingConcerns: memory ? extras.memoryWandering : "",
      },
      futureCareProfile: {
        ...draft.humanIntelligenceV2.futureCareProfile,
        avoidFutureMovesPreference: extras.continuum,
        continuumOfCarePreference: extras.continuum,
        secureMemoryNeighborhoodNeed: memory ? extras.secureMemory : "",
      },
    },
  };
}