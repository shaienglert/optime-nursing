import {
  ASSESSMENT_QUESTIONS,
  UNKNOWN_FROM_FAMILY,
  getVisibleQuestions,
  type AssessmentAnswer,
  type AssessmentAnswers,
  type AssessmentQuestion,
} from "@/lib/assessment-schema";
import { ACTIVE_ASSESSMENT_REGION } from "@/lib/assessment-region";

export const ASSESSMENT_SECTIONS = [
  { id: "about", label: "About your loved one", categories: ["About your family"] },
  { id: "situation", label: "Current situation", categories: ["Daily life"] },
  { id: "support", label: "Daily support", categories: ["Daily support", "Memory and thinking"] },
  { id: "health", label: "Health and rehabilitation", categories: ["Clinical care", "Rehabilitation"] },
  { id: "location", label: "Location and timing", categories: ["Location", "Timing"] },
  { id: "budget", label: "Budget and payment", categories: ["Budget and coverage", "Living space"] },
  { id: "culture", label: "Language, culture, and lifestyle", categories: ["Language and culture", "Food and diet"] },
  { id: "priorities", label: "Priorities and deal-breakers", categories: ["Priorities", "Save and continue"] },
  { id: "summary", label: "What OPTIME understood", categories: [] },
] as const;

export type AssessmentSection = (typeof ASSESSMENT_SECTIONS)[number];

const QUESTION_SECTION_OVERRIDES: Record<string, AssessmentSection["id"]> = {
  current_living_situation: "situation",
  social_activity_preferences: "culture",
  preferred_search_area: "location",
  avoid_search_areas: "location",
  urgency: "location",
  urgent_availability: "location",
  distance_from_family: "location",
  room_preference: "budget",
};

export function hasAssessmentAnswer(answer: AssessmentAnswer | undefined): boolean {
  if (Array.isArray(answer)) return answer.length > 0;
  if (typeof answer === "number") return Number.isFinite(answer);
  return typeof answer === "string" && answer.trim().length > 0;
}

export function isUnknownAnswer(answer: AssessmentAnswer | undefined): boolean {
  return answer === UNKNOWN_FROM_FAMILY || (Array.isArray(answer) && answer.includes(UNKNOWN_FROM_FAMILY));
}

export function getAssessmentSection(question: AssessmentQuestion): AssessmentSection {
  const override = QUESTION_SECTION_OVERRIDES[question.id];
  if (override) return ASSESSMENT_SECTIONS.find((section) => section.id === override) || ASSESSMENT_SECTIONS[0];
  return ASSESSMENT_SECTIONS.find((section) => (section.categories as readonly string[]).includes(question.category)) || ASSESSMENT_SECTIONS[0];
}

export function getConversationQuestions(answers: AssessmentAnswers): AssessmentQuestion[] {
  const sectionOrder = new Map(ASSESSMENT_SECTIONS.map((section, index) => [section.id, index]));
  return getVisibleQuestions(answers)
    .map((question, sourceIndex) => ({ question, sourceIndex }))
    .sort((left, right) => {
      const sectionDifference = (sectionOrder.get(getAssessmentSection(left.question).id) || 0) - (sectionOrder.get(getAssessmentSection(right.question).id) || 0);
      return sectionDifference || left.sourceIndex - right.sourceIndex;
    })
    .map(({ question }) => question);
}

export function getProgressiveQuestions(answers: AssessmentAnswers): AssessmentQuestion[] {
  const visible = getConversationQuestions(answers);
  const firstUnanswered = visible.findIndex((question) => !hasAssessmentAnswer(answers[question.id]));
  return firstUnanswered === -1 ? visible : visible.slice(0, firstUnanswered + 1);
}

export function pruneHiddenAssessmentAnswers(answers: AssessmentAnswers): { answers: AssessmentAnswers; clearedQuestionIds: string[] } {
  const next = { ...answers };
  const clearedQuestionIds: string[] = [];
  let changed = true;

  while (changed) {
    changed = false;
    const visibleIds = new Set(getVisibleQuestions(next).map((question) => question.id));
    for (const question of ASSESSMENT_QUESTIONS) {
      if (!visibleIds.has(question.id) && question.id in next) {
        delete next[question.id];
        clearedQuestionIds.push(question.id);
        changed = true;
      }
    }
  }

  return { answers: next, clearedQuestionIds };
}

function relationshipLanguage(value: AssessmentAnswer | undefined): { object: string; subject: string; possessive: string } {
  const relationship = typeof value === "string" ? value : "";
  if (relationship === "Mom") return { object: "your mom", subject: "she", possessive: "her" };
  if (relationship === "Dad") return { object: "your dad", subject: "he", possessive: "his" };
  if (relationship === "Spouse") return { object: "your partner", subject: "they", possessive: "their" };
  if (relationship === "Myself") return { object: "you", subject: "you", possessive: "your" };
  if (relationship === "Grandparent") return { object: "your grandparent", subject: "they", possessive: "their" };
  return { object: "your relative", subject: "they", possessive: "their" };
}

function answerValues(answer: AssessmentAnswer | undefined): string[] {
  return Array.isArray(answer) ? answer : [answer].filter((value): value is string => typeof value === "string");
}

function previousAnsweredQuestion(question: AssessmentQuestion, answers: AssessmentAnswers): AssessmentQuestion | undefined {
  const index = ASSESSMENT_QUESTIONS.findIndex((item) => item.id === question.id);
  return ASSESSMENT_QUESTIONS.slice(0, index).reverse().find((item) => hasAssessmentAnswer(answers[item.id]));
}

export function advisorResponseFor(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const person = relationshipLanguage(answers.who_needs_care);
  const previous = previousAnsweredQuestion(question, answers);
  if (previous && isUnknownAnswer(answers[previous.id])) {
    return "No problem. This stays unknown rather than assuming no; we’ll verify it later if needed.";
  }
  if (question.id === "who_needs_care") return "Let’s start with the person at the center of this decision.";
  if (question.id === "preferred_search_area") return `I’ll focus on ${ACTIVE_ASSESSMENT_REGION.city} unless you want to include nearby communities.`;
  if (question.id === "avoid_search_areas") return "I’ll keep the areas you selected in mind while I search the valley.";
  if (question.id === "current_living_situation" && ["IMMEDIATE", "WITHIN_30_DAYS"].includes(String(answers.urgency))) {
    return "Let’s focus first on what is needed for a safe move soon.";
  }
  if (question.id === "current_living_situation" && ["ONE_TO_THREE_MONTHS", "EXPLORING"].includes(String(answers.urgency))) {
    return "We can take a broader look at preferences and long-term fit.";
  }
  if (question.id === "daily_activities" && answerValues(answers.mobility).some((item) => item !== "INDEPENDENT")) {
    return `We’ll prioritize communities that can safely support ${person.possessive} mobility.`;
  }
  if (question.id === "cognitive_status" && ["ADMINISTRATION", "COMPLEX"].includes(String(answers.medication_support))) {
    return "We’ll make medication management a required part of the care profile.";
  }
  if (["rehabilitation_services", "stroke_recovery"].includes(question.id) && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) {
    return "I understand. Stroke recovery makes rehabilitation and transfer support especially important.";
  }
  if (question.id === "hebrew_support") {
    return "We’ll verify that Hebrew-speaking support is actually available.";
  }
  if (question.id === "gluten_free_details") {
    return "We’ll verify the preparation and safety level your family needs.";
  }
  return "That helps. We’ll use that.";
}

function answerLabels(questionId: string, answers: AssessmentAnswers): string[] {
  const question = ASSESSMENT_QUESTIONS.find((item) => item.id === questionId);
  const answer = answers[questionId];
  const values = Array.isArray(answer) ? answer : answer === undefined ? [] : [answer];
  return values
    .filter((value) => value !== UNKNOWN_FROM_FAMILY && value !== "NONE")
    .map((value) => question?.options?.find((option) => option.value === value)?.label || String(value));
}

function naturalList(items: string[]): string {
  if (items.length < 2) return items[0] || "";
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items.at(-1)}`;
}

export function buildAssessmentSummary(answers: AssessmentAnswers): string {
  const person = relationshipLanguage(answers.who_needs_care);
  const location = answerLabels("preferred_search_area", answers).join(", ");
  const details: string[] = [];
  if (Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) details.push("is recovering from a stroke");
  const mobility = answerValues(answers.mobility);
  if (mobility.includes("DEVICE")) details.push("uses a cane, walker, or wheelchair");
  if (mobility.includes("SOME_HELP")) details.push("needs some help getting around");
  const dailySupport = answerLabels("daily_activities", answers).map((label) => label.toLowerCase());
  if (dailySupport.length) details.push(`needs help with ${dailySupport.join(", ")}`);
  if (["ADMINISTRATION", "COMPLEX"].includes(String(answers.medication_support))) details.push("needs medication support");

  const priorities = [
    ...answerLabels("family_priorities", answers),
    ...answerLabels("language_needs", answers).filter((label) => label !== "English").map((label) => `${label} support`),
    ...answerLabels("dietary_requirements", answers).map((label) => `${label.toLowerCase()} meals`),
  ].slice(0, 6).map((label, index) => index === 0 || label.startsWith("Hebrew") ? label : label.toLowerCase());
  const opening = `We’re looking for care for ${person.object}${location ? ` near ${location}` : ""}.`;
  const needs = details.length ? ` ${person.subject === "you" ? "You" : `${person.subject.charAt(0).toUpperCase()}${person.subject.slice(1)}`} ${naturalList(details)}.` : "";
  const important = priorities.length ? ` ${naturalList(priorities)} ${priorities.length === 1 ? "is" : "are"} important.` : "";
  return `${opening}${needs}${important}`;
}

export function getUnknownClarifications(answers: AssessmentAnswers): AssessmentQuestion[] {
  return getConversationQuestions(answers).filter((question) => isUnknownAnswer(answers[question.id]) || (question.required && !hasAssessmentAnswer(answers[question.id])));
}

export function assessmentAnswerLabel(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const answer = answers[question.id];
  const values = Array.isArray(answer) ? answer : answer === undefined ? [] : [answer];
  if (!values.length) return "Not answered yet";
  return values
    .map((value) => value === UNKNOWN_FROM_FAMILY ? "Not sure yet" : question.options?.find((option) => option.value === value)?.label || String(value))
    .join(", ");
}

export function completedAnswerSentence(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const person = relationshipLanguage(answers.who_needs_care);
  const subject = person.subject === "you" ? "You" : `${person.subject.charAt(0).toUpperCase()}${person.subject.slice(1)}`;
  const label = assessmentAnswerLabel(question, answers);
  if (isUnknownAnswer(answers[question.id])) return `${question.englishLabel.replace(/\?$/, "")} is still unknown and will stay open for verification.`;

  const details: Record<string, string> = {
    who_needs_care: `We’re looking for the right care for ${person.object}.`,
    preferred_search_area: `I’ll focus the search around ${label}.`,
    avoid_search_areas: label === "No areas to avoid" ? `There are no ${ACTIVE_ASSESSMENT_REGION.regionName} areas to exclude.` : `Areas to avoid: ${label}.`,
    current_living_situation: `${subject} currently ${label.toLowerCase()}.`,
    urgency: `Care may be needed ${label.toLowerCase()}.`,
    urgent_availability: label === "Yes" ? "A timely opening is a deal-breaker." : "A timely opening is not a deal-breaker.",
    mobility: `${subject} ${person.subject === "you" ? "get" : "gets"} around with this level of support: ${label.toLowerCase()}.`,
    daily_activities: `Daily support is needed for ${label.toLowerCase()}.`,
    transfer_assistance: `Safe transfers require ${label.toLowerCase()}.`,
    medication_support: `Medication support: ${label}.`,
    cognitive_status: `Memory and cognitive support: ${label}.`,
    nursing_needs: `Known nursing needs: ${label}.`,
    rehabilitation_needed: label === "Yes" ? "Rehabilitation is part of the care path." : "Rehabilitation is not currently part of the care path.",
    rehabilitation_focus: `The rehabilitation focus is ${label.toLowerCase()}.`,
    rehabilitation_services: `Rehabilitation services: ${label}.`,
    stroke_recovery: `Dedicated stroke program: ${label}.`,
    neurological_rehabilitation: `Neurological rehabilitation program: ${label}.`,
    dietary_requirements: `Important dietary requirements: ${label}.`,
    gluten_free_details: `Gluten-free preparation must support ${label.toLowerCase()}.`,
    language_needs: `Daily communication should support ${label}.`,
    hebrew_support: `Hebrew support matters for ${label.toLowerCase()}.`,
    culture_importance: `Religious or cultural fit is ${label.toLowerCase()}.`,
    cultural_preferences: `Important cultural support includes ${label.toLowerCase()}.`,
    social_activity_preferences: `A worthwhile daily life includes ${label.toLowerCase()}.`,
    room_preference: `Room preference: ${label}.`,
    payment_method: `The likely payment path includes ${label.toLowerCase()}.`,
    monthly_budget: `The manageable private-pay range is ${label.toLowerCase()}.`,
    distance_from_family: `Family proximity preference: ${label}.`,
    family_priorities: `Your family’s leading priorities are ${label.toLowerCase()}.`,
    deal_breakers: `Deal-breakers: ${label}.`,
  };
  return details[question.id] ?? `${question.englishLabel.replace(/\?$/, "")}: ${label}.`;
}

export function buildConversationCheckpoint(questions: AssessmentQuestion[], answers: AssessmentAnswers): string {
  const summary = buildAssessmentSummary(answers);
  const recentDetails = questions.slice(-4).map((question) => completedAnswerSentence(question, answers)).filter(Boolean);
  return recentDetails.length ? `${summary} ${recentDetails.join(" ")}` : summary;
}