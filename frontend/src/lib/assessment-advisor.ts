import parameterIntelligence from "@/data/assessment-advisor-parameter-intelligence.json";
import { ACTIVE_ASSESSMENT_REGION } from "@/lib/assessment-region";
import {
  ASSESSMENT_QUESTIONS,
  UNKNOWN_FROM_FAMILY,
  getVisibleQuestions,
  type AssessmentAnswer,
  type AssessmentAnswers,
  type AssessmentQuestion,
} from "@/lib/assessment-schema";

export type AdvisorKnowledgeSource =
  | "previous answers"
  | "canonical parameter definitions"
  | "evidence rules"
  | "facility knowledge"
  | "facility evidence rules"
  | "care-path knowledge"
  | "rehabilitation knowledge"
  | "payment knowledge"
  | "geographic knowledge"
  | "language support knowledge"
  | "dietary support knowledge"
  | "ranking priorities"
  | "verification workflow"
  | "accumulated institutional intelligence";

export type AdvisorTurn = {
  question: AssessmentQuestion;
  prompt: string;
  rationale: string;
  knownFacts: string[];
  uncertainties: string[];
  knowledgeSources: AdvisorKnowledgeSource[];
  informationGainScore: number;
  decisionFactors: string[];
  canonicalParameters: AdvisorCanonicalParameter[];
};

type PersonLanguage = { object: string; subject: string; possessive: string };

export type AdvisorCanonicalParameter = {
  parameterId: string;
  family: string;
  displayName: string;
  consumerDescription: string;
  rankingEligible: boolean;
  hardFilterEligible: boolean;
  requiresFacilityConfirmation: boolean;
  dynamic: boolean;
  personalizationTags: string[];
  freshnessRule: string;
  criticality: string;
  sourceAuthority: string;
  currentCoveragePercent: number;
  recommendedActionWhenMissing: string;
};

export type AdvisorCompletionSummary = {
  confidence: "Strong" | "Developing" | "Limited";
  stillNeedsConfirmation: string[];
  automaticVerification: string[];
};

type ParameterIntelligenceRecord = (typeof parameterIntelligence.records)[number];

export const ADVISOR_PARAMETER_COUNT = parameterIntelligence.record_count;

const PARAMETER_BY_ID = new Map(parameterIntelligence.records.map((record) => [record.parameter_id, record]));
const CANONICAL_MAPPING_ALIASES: Record<string, string[]> = {
  "recommendation_constraints.immediate_availability": ["current_availability", "earliest_admission_date", "waiting_list"],
};

const BASE_IMPACT: Record<string, number> = {
  who_needs_care: 10000,
  preferred_search_area: 9000,
  avoid_search_areas: 8900,
  urgency: 9300,
  rehabilitation_needed: 8600,
  mobility: 8500,
  cognitive_status: 8400,
  nursing_needs: 8300,
  daily_activities: 8200,
  medication_support: 8100,
  payment_method: 8000,
  distance_from_family: 7800,
  transfer_assistance: 7700,
  family_priorities: 7500,
  dietary_requirements: 6400,
  language_needs: 6300,
  room_preference: 6200,
  culture_importance: 6000,
  current_living_situation: 5000,
  social_activity_preferences: 4200,
  deal_breakers: 4000,
  continue_method: 100,
};

const UNCERTAINTY_BY_QUESTION: Record<string, string> = {
  preferred_search_area: "which geographic market should anchor the recommendations",
  avoid_search_areas: "whether any Las Vegas Valley areas should be excluded",
  urgency: "how quickly a safe care option may be needed",
  urgent_availability: "whether immediate availability is a hard requirement",
  mobility: "which mobility capabilities a community must safely support",
  daily_activities: "which daily support services are required",
  transfer_assistance: "the staffing or equipment needed for safe transfers",
  medication_support: "the required level of medication management",
  cognitive_status: "whether memory or cognitive support should shape the care path",
  nursing_needs: "which nursing capabilities must be evidenced",
  rehabilitation_needed: "whether rehabilitation belongs in the care path",
  rehabilitation_focus: "which rehabilitation specialty matters most",
  rehabilitation_services: "which therapy services are part of the care plan",
  stroke_recovery: "whether a dedicated stroke program is required",
  neurological_rehabilitation: "whether a neurological rehabilitation program is required",
  dietary_requirements: "which dietary capabilities need verification",
  gluten_free_details: "the required level of gluten-free safety",
  language_needs: "which languages matter in daily and clinical communication",
  hebrew_support: "where verified Hebrew-speaking support matters most",
  payment_method: "which payment paths are realistic",
  monthly_budget: "which private-pay options are financially workable",
  family_priorities: "which proven differences should drive recommendation order",
  deal_breakers: "which constraints should rule a community out",
};

function hasAnswer(answer: AssessmentAnswer | undefined): boolean {
  if (Array.isArray(answer)) return answer.length > 0;
  if (typeof answer === "number") return Number.isFinite(answer);
  return typeof answer === "string" && answer.trim().length > 0;
}

function isUnknown(answer: AssessmentAnswer | undefined): boolean {
  return answer === UNKNOWN_FROM_FAMILY || (Array.isArray(answer) && answer.includes(UNKNOWN_FROM_FAMILY));
}

export function isAdvisorQuestionRelevant(question: AssessmentQuestion): boolean {
  return ["who_needs_care", "avoid_search_areas"].includes(question.id) || question.rankingRelevant || question.eligibilityRelevant;
}

export function getAdvisorInteractionMetrics(): { totalQuestions: number; selectionBasedQuestions: number; selectionPercentage: number } {
  const questions = ASSESSMENT_QUESTIONS.filter(isAdvisorQuestionRelevant);
  const selectionBasedQuestions = questions.filter((question) => question.answerType !== "text" || question.id === "preferred_search_area").length;
  return {
    totalQuestions: questions.length,
    selectionBasedQuestions,
    selectionPercentage: questions.length ? Math.round((selectionBasedQuestions / questions.length) * 100) : 100,
  };
}

function personLanguage(answer: AssessmentAnswer | undefined): PersonLanguage {
  if (answer === "Mom") return { object: "your mom", subject: "she", possessive: "her" };
  if (answer === "Dad") return { object: "your dad", subject: "he", possessive: "his" };
  if (answer === "Spouse") return { object: "your partner", subject: "they", possessive: "their" };
  if (answer === "Myself") return { object: "you", subject: "you", possessive: "your" };
  if (answer === "Grandparent") return { object: "your grandparent", subject: "they", possessive: "their" };
  return { object: "your loved one", subject: "they", possessive: "their" };
}

function contextBonus(question: AssessmentQuestion, answers: AssessmentAnswers): number {
  const preferredAreasSelected = Array.isArray(answers.preferred_search_area) ? answers.preferred_search_area.length > 0 : typeof answers.preferred_search_area === "string" && answers.preferred_search_area.trim().length > 0;
  if (question.id === "avoid_search_areas" && preferredAreasSelected) return 14600;
  if (question.id === "urgency" && preferredAreasSelected) return 14300;
  if (question.id === "urgent_availability" && ["IMMEDIATE", "WITHIN_30_DAYS"].includes(String(answers.urgency))) return 14500;
  if (question.id === "rehabilitation_focus" && answers.rehabilitation_needed === "YES") return 14200;
  if (question.id === "stroke_recovery" && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) return 15000;
  if (question.id === "neurological_rehabilitation" && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("NEUROLOGICAL")) return 14900;
  if (question.id === "rehabilitation_services" && answers.rehabilitation_needed === "YES") return 13500;
  if (question.id === "gluten_free_details" && Array.isArray(answers.dietary_requirements) && answers.dietary_requirements.includes("GLUTEN_FREE")) return 14000;
  if (question.id === "hebrew_support" && Array.isArray(answers.language_needs) && answers.language_needs.includes("HEBREW")) return 14000;
  if (question.id === "monthly_budget" && Array.isArray(answers.payment_method) && answers.payment_method.includes("PRIVATE_PAY")) return 14000;
  if (question.id === "cultural_preferences" && ["SOMEWHAT", "IMPORTANT", "VERY_IMPORTANT"].includes(String(answers.culture_importance))) return 12500;
  return 0;
}

function parameterRecordsFor(question: AssessmentQuestion): ParameterIntelligenceRecord[] {
  const parameterIds = question.canonicalMappings.flatMap((mapping) => {
    if (mapping.startsWith("parameters.")) return [mapping.slice("parameters.".length)];
    return CANONICAL_MAPPING_ALIASES[mapping] || [];
  });
  return Array.from(new Set(parameterIds)).map((parameterId) => PARAMETER_BY_ID.get(parameterId)).filter((record): record is ParameterIntelligenceRecord => Boolean(record));
}

function parameterInfluence(question: AssessmentQuestion): number {
  return parameterRecordsFor(question).reduce((score, record) => score
    + (record.hard_filter_eligibility ? 120 : 0)
    + (record.ranking_eligibility ? 60 : 0)
    + (record.requires_facility_confirmation ? 50 : 0)
    + (record.dynamic ? 70 : 0)
    + (record.criticality === "CRITICAL" ? 50 : 0)
    + (record.ranking_eligibility || record.hard_filter_eligibility ? Math.min(80, Math.round(Number(record.current_coverage_percent || 0) * 0.8)) : 0), 0);
}

function questionScore(question: AssessmentQuestion, answers: AssessmentAnswers): number {
  const governedImpact = (question.eligibilityRelevant ? 500 : 0) + (question.rankingRelevant ? 250 : 0) + (question.required ? 50 : 0);
  const canonicalDepth = Math.min(150, question.canonicalMappings.length * 50);
  return Math.max(BASE_IMPACT[question.id] || 3000, contextBonus(question, answers)) + governedImpact + canonicalDepth + parameterInfluence(question);
}

function knownFacts(answers: AssessmentAnswers): string[] {
  const person = personLanguage(answers.who_needs_care);
  const facts: string[] = [];
  const mobility = Array.isArray(answers.mobility) ? answers.mobility : [answers.mobility].filter(Boolean);
  if (hasAnswer(answers.who_needs_care) && !isUnknown(answers.who_needs_care)) facts.push(`This search is for ${person.object}.`);
  if (Array.isArray(answers.preferred_search_area) && answers.preferred_search_area.length) facts.push(`The family selected the ${ACTIVE_ASSESSMENT_REGION.regionName} search area.`);
  else if (typeof answers.preferred_search_area === "string" && answers.preferred_search_area.trim()) facts.push(`The preferred search area is ${answers.preferred_search_area.trim()}.`);
  if (["IMMEDIATE", "WITHIN_30_DAYS"].includes(String(answers.urgency))) facts.push("The family may need a safe option soon.");
  if (mobility.includes("DEVICE")) facts.push(`${person.subject === "you" ? "You use" : `${person.subject} uses`} a cane, walker, or wheelchair.`);
  if (mobility.includes("SOME_HELP")) facts.push(`${person.subject === "you" ? "You need" : `${person.subject} needs`} some mobility help.`);
  if (Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) facts.push("Stroke recovery is part of the care path.");
  if (Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("NEUROLOGICAL")) facts.push("Neurological rehabilitation is part of the care path.");
  if (Array.isArray(answers.payment_method) && answers.payment_method.includes("PRIVATE_PAY")) facts.push("Private pay may be part of the payment plan.");
  if (Array.isArray(answers.language_needs) && answers.language_needs.includes("HEBREW")) facts.push("Hebrew support matters for communication.");
  if (Array.isArray(answers.dietary_requirements) && answers.dietary_requirements.includes("GLUTEN_FREE")) facts.push("Gluten-free food support matters.");
  return facts;
}

function uncertainties(question: AssessmentQuestion, answers: AssessmentAnswers): string[] {
  const unresolved = ASSESSMENT_QUESTIONS
    .filter((candidate) => isUnknown(answers[candidate.id]))
    .map((candidate) => `${candidate.englishLabel.replace(/\?$/, "")} remains unknown and will stay open for verification.`);
  unresolved.push(UNCERTAINTY_BY_QUESTION[question.id] || `the answer to “${question.englishLabel}”`);
  return unresolved;
}

function rationaleFor(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const person = personLanguage(answers.who_needs_care);
  const rationales: Record<string, string> = {
    who_needs_care: "Here’s why I’m asking: knowing who is at the center of this decision lets me speak clearly and interpret every later need in the right family context.",
    preferred_search_area: `Here’s why I’m asking: geography determines which communities are realistic for ${person.object} before we compare care quality or fit.`,
    avoid_search_areas: `Here’s why I’m asking: knowing which parts of the ${ACTIVE_ASSESSMENT_REGION.regionName} to avoid prevents unnecessary options without asking for the city again.`,
    urgency: "Here’s why I’m asking: timing changes whether we should optimize for immediate safety and verified availability or take a broader view of long-term fit.",
    urgent_availability: "Here’s why I’m asking: current availability changes quickly, so I need to know whether a timely opening is a hard constraint that every community must verify.",
    mobility: `Here’s why I’m asking: mobility affects staffing, transfer safety, accessibility, and which communities can safely support ${person.object}.`,
    daily_activities: `Here’s why I’m asking: the specific daily tasks ${person.subject === "you" ? "you need" : `${person.subject} needs`} help with determine the real level of support, not just a broad care label.`,
    cognitive_status: "Here’s why I’m asking: observed memory needs can change the safest care path and the capabilities we must verify.",
    nursing_needs: "Here’s why I’m asking: nursing capabilities require specific evidence, and a general facility label is not enough to prove clinical fit.",
    rehabilitation_needed: "Here’s why I’m asking: rehabilitation changes the care path and which therapy capabilities should influence the recommendation.",
    rehabilitation_focus: "Here’s why I’m asking: different recovery goals require different programs, clinicians, and evidence from a community.",
    rehabilitation_services: "Here’s why I’m asking: physical, occupational, and speech therapy can all be part of the same care plan, so you can select every service that applies.",
    stroke_recovery: "Here’s why I’m asking: a dedicated stroke program is different from general rehabilitation, and that distinction can materially change the safest match.",
    neurological_rehabilitation: "Here’s why I’m asking: neurological rehabilitation requires more specific capability evidence than general therapy availability.",
    payment_method: "Here’s why I’m asking: Medicare, Medicaid, insurance, and private pay follow different care and eligibility paths, so I should not assume they are interchangeable.",
    monthly_budget: "Here’s why I’m asking: a realistic private-pay range helps remove financially unworkable options without treating missing price data as a negative signal.",
    language_needs: "Here’s why I’m asking: daily conversation and clinical communication can require different verified language support.",
    hebrew_support: "Here’s why I’m asking: cultural programming does not prove Hebrew-speaking staff are available where communication matters most.",
    dietary_requirements: "Here’s why I’m asking: dietary preferences and medically necessary preparation require different levels of facility evidence.",
    gluten_free_details: "Here’s why I’m asking: a gluten-free preference is different from medically necessary cross-contamination controls.",
    family_priorities: "Here’s why I’m asking: your priorities tell me which verified differences should matter most when several communities can meet the basic care needs.",
  };
  return rationales[question.id] || `Here’s why I’m asking: this answer can clarify ${UNCERTAINTY_BY_QUESTION[question.id] || "an important part of the recommendation"} for ${person.object}.`;
}

export function buildAdvisorPrompt(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const person = personLanguage(answers.who_needs_care);
  const mobility = Array.isArray(answers.mobility) ? answers.mobility : [answers.mobility].filter(Boolean);
  const prompts: Record<string, string> = {
    who_needs_care: "Who are you helping find care?",
    preferred_search_area: `The current demonstration market is ${ACTIVE_ASSESSMENT_REGION.marketName}. Would you like me to focus on a specific area, or should I search across the entire metropolitan area?`,
    avoid_search_areas: "Are there any areas you'd rather avoid?",
    urgency: `Now that I know where to search for ${person.object}, when might care be needed?`,
    urgent_availability: `You mentioned care may be needed soon. Does a timely opening need to be a firm requirement?`,
    mobility: person.subject === "you" ? "Thinking about your day-to-day needs, how do you usually get around?" : `Thinking about ${person.object}'s day-to-day needs, how does ${person.subject} usually get around?`,
    daily_activities: mobility.includes("DEVICE")
      ? `You mentioned that ${person.object} uses a cane, walker, or wheelchair. Which daily activities would benefit from help right now?`
      : mobility.some((item) => ["SOME_HELP", "SIGNIFICANT_HELP", "FULLY_DEPENDENT"].includes(String(item)))
        ? `You mentioned that ${person.object} needs help getting around. Which daily activities would benefit from support right now?`
        : person.subject === "you" ? "Thinking about your mobility, which daily activities do you need help with?" : `Thinking about ${person.object}'s mobility, which daily activities does ${person.subject} need help with?`,
    medication_support: `Alongside the daily support you described for ${person.object}, how much medication support is needed?`,
    cognitive_status: person.subject === "you" ? "Alongside your daily support needs, is memory or cognitive support relevant?" : `Alongside ${person.object}'s daily support needs, is memory or cognitive support relevant?`,
    nursing_needs: person.subject === "you" ? "With those daily and memory needs in mind, what nursing support do you need?" : `With ${person.object}'s daily and memory needs in mind, what nursing support does ${person.subject} need?`,
    rehabilitation_focus: `You mentioned that rehabilitation is part of ${person.object}'s care plan. What kind of recovery support is the focus?`,
    stroke_recovery: `You mentioned that ${person.object}'s care plan includes stroke recovery. Does the program need to be specifically designed for stroke rehabilitation?`,
    neurological_rehabilitation: `You mentioned that neurological recovery is part of ${person.object}'s care plan. Is a dedicated neurological rehabilitation program required?`,
    rehabilitation_services: `Because rehabilitation is part of ${person.object}'s care plan, which services are needed?`,
    gluten_free_details: `You mentioned gluten-free food support for ${person.object}. How strict must preparation be?`,
    hebrew_support: `You mentioned that Hebrew matters for ${person.object}. Where is that support most important?`,
    monthly_budget: `You mentioned private pay may be part of the plan. What monthly range feels manageable?`,
    cultural_preferences: `You said cultural or religious fit matters for ${person.object}. Which supports would make a meaningful difference?`,
    family_priorities: `Thinking about everything you have shared about ${person.object}, what should matter most when strong options differ?`,
  };
  if (prompts[question.id]) return prompts[question.id];
  if (hasAnswer(answers.who_needs_care)) {
    const label = question.englishLabel.charAt(0).toLowerCase() + question.englishLabel.slice(1);
    return `Keeping ${person.object}'s situation in mind, ${label}`;
  }
  return question.englishLabel;
}

function knowledgeSourcesFor(question: AssessmentQuestion): AdvisorKnowledgeSource[] {
  const sources = new Set<AdvisorKnowledgeSource>([
    "previous answers",
    "canonical parameter definitions",
    "evidence rules",
    "accumulated institutional intelligence",
  ]);
  if (question.rankingRelevant || question.eligibilityRelevant) sources.add("ranking priorities");
  if (parameterRecordsFor(question).length > 0) {
    sources.add("facility knowledge");
    sources.add("facility evidence rules");
    sources.add("verification workflow");
  }
  if (["Daily support", "Memory and thinking", "Clinical care"].includes(question.category)) sources.add("care-path knowledge");
  if (question.category === "Rehabilitation") {
    sources.add("care-path knowledge");
    sources.add("rehabilitation knowledge");
    sources.add("facility knowledge");
    sources.add("facility evidence rules");
  }
  if (question.category === "Budget and coverage") sources.add("payment knowledge");
  if (["Location", "Timing"].includes(question.category)) sources.add("geographic knowledge");
  if (question.decisionArea === "language_needs") sources.add("language support knowledge");
  if (question.decisionArea === "dietary_requirements") sources.add("dietary support knowledge");
  return Array.from(sources);
}

function canonicalParametersFor(question: AssessmentQuestion): AdvisorCanonicalParameter[] {
  return parameterRecordsFor(question).map((record) => ({
    parameterId: record.parameter_id,
    family: record.family,
    displayName: record.display_name,
    consumerDescription: record.consumer_description,
    rankingEligible: record.ranking_eligibility,
    hardFilterEligible: record.hard_filter_eligibility,
    requiresFacilityConfirmation: record.requires_facility_confirmation,
    dynamic: record.dynamic,
    personalizationTags: record.personalization_tags,
    freshnessRule: record.freshness_rule,
    criticality: record.criticality,
    sourceAuthority: record.source_authority,
    currentCoveragePercent: Number(record.current_coverage_percent || 0),
    recommendedActionWhenMissing: record.recommended_action_when_missing,
  }));
}

export function selectAdvisorTurn(answers: AssessmentAnswers): AdvisorTurn | null {
  const candidates = getVisibleQuestions(answers).filter((question) => isAdvisorQuestionRelevant(question) && !hasAnswer(answers[question.id]));
  const selected = candidates
    .map((question, schemaIndex) => ({ question, schemaIndex, score: questionScore(question, answers) }))
    .sort((left, right) => right.score - left.score || left.schemaIndex - right.schemaIndex)[0];
  if (!selected) return null;

  const factors = [
    selected.question.eligibilityRelevant ? "can change eligibility" : "refines the resident profile",
    selected.question.rankingRelevant ? "can change recommendation order" : "improves interpretation",
    contextBonus(selected.question, answers) ? "activated by a previous answer" : "high-value unresolved domain",
    `${selected.question.canonicalMappings.length} canonical mapping${selected.question.canonicalMappings.length === 1 ? "" : "s"}`,
    `${parameterRecordsFor(selected.question).length} governed facility parameter definition${parameterRecordsFor(selected.question).length === 1 ? "" : "s"}`,
  ];

  return {
    question: selected.question,
    prompt: buildAdvisorPrompt(selected.question, answers),
    rationale: rationaleFor(selected.question, answers),
    knownFacts: knownFacts(answers),
    uncertainties: uncertainties(selected.question, answers),
    knowledgeSources: knowledgeSourcesFor(selected.question),
    informationGainScore: Math.min(100, Math.round(selected.score / 160)),
    decisionFactors: factors,
    canonicalParameters: canonicalParametersFor(selected.question),
  };
}

export function isAdvisorReadyForMatch(answers: AssessmentAnswers): boolean {
  return Object.keys(answers).length > 0 && selectAdvisorTurn(answers) === null;
}

export function buildAdvisorCompletionSummary(answers: AssessmentAnswers): AdvisorCompletionSummary {
  const relevantQuestions = getVisibleQuestions(answers).filter(isAdvisorQuestionRelevant);
  const unknownQuestions = relevantQuestions.filter((question) => isUnknown(answers[question.id]));
  const knownCount = relevantQuestions.filter((question) => hasAnswer(answers[question.id]) && !isUnknown(answers[question.id])).length;
  const knownRatio = relevantQuestions.length ? knownCount / relevantQuestions.length : 0;
  const confidence: AdvisorCompletionSummary["confidence"] = unknownQuestions.length === 0 && knownRatio >= 0.9 ? "Strong" : knownRatio >= 0.65 ? "Developing" : "Limited";

  const automaticVerification = relevantQuestions
    .filter((question) => hasAnswer(answers[question.id]))
    .flatMap(canonicalParametersFor)
    .filter((parameter) => parameter.dynamic || parameter.requiresFacilityConfirmation || parameter.currentCoveragePercent < 100)
    .map((parameter) => parameter.displayName);

  return {
    confidence,
    stillNeedsConfirmation: unknownQuestions.map((question) => question.englishLabel.replace(/\?$/, "")),
    automaticVerification: Array.from(new Set(automaticVerification)).slice(0, 5),
  };
}