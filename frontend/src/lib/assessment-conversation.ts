import {
  ASSESSMENT_QUESTIONS,
  UNKNOWN_FROM_FAMILY,
  getVisibleQuestions,
  type AssessmentAnswer,
  type AssessmentAnswers,
  type AssessmentQuestion,
} from "@/lib/assessment-schema";

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
  current_location: "situation",
  current_living_situation: "situation",
  social_activity_preferences: "culture",
  preferred_search_area: "location",
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

function previousAnsweredQuestion(question: AssessmentQuestion, answers: AssessmentAnswers): AssessmentQuestion | undefined {
  const index = ASSESSMENT_QUESTIONS.findIndex((item) => item.id === question.id);
  return ASSESSMENT_QUESTIONS.slice(0, index).reverse().find((item) => hasAssessmentAnswer(answers[item.id]));
}

export function advisorResponseFor(question: AssessmentQuestion, answers: AssessmentAnswers): string {
  const person = relationshipLanguage(answers.who_needs_care);
  const previous = previousAnsweredQuestion(question, answers);
  if (previous && isUnknownAnswer(answers[previous.id])) {
    return "That’s completely fine. We’ll keep this as unknown rather than assuming no, and help verify it later.";
  }
  if (question.id === "who_needs_care") return "Let’s start with the person at the center of this decision.";
  if (question.id === "current_location") return `Got it — we’re looking for the right care for ${person.object}.`;
  if (question.id === "current_living_situation" && ["IMMEDIATE", "WITHIN_30_DAYS"].includes(String(answers.urgency))) {
    return "Let’s focus first on what is needed for a safe move soon.";
  }
  if (question.id === "current_living_situation" && ["ONE_TO_THREE_MONTHS", "EXPLORING"].includes(String(answers.urgency))) {
    return "We can take a broader look at preferences and long-term fit.";
  }
  if (question.id === "daily_activities" && answers.mobility && answers.mobility !== "INDEPENDENT") {
    return `We’ll prioritize communities that can safely support ${person.possessive} mobility.`;
  }
  if (question.id === "cognitive_status" && ["ADMINISTRATION", "COMPLEX"].includes(String(answers.medication_support))) {
    return "We’ll make medication management a required part of the care profile.";
  }
  if (["physical_therapy", "occupational_therapy", "speech_therapy", "stroke_recovery"].includes(question.id) && Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) {
    return "Stroke recovery can make therapy availability and transfer support especially important.";
  }
  if (question.id === "hebrew_support") {
    return "We’ll check whether Hebrew-speaking staff are actually available, not just listed.";
  }
  if (question.id === "gluten_free_details") {
    return "We’ll verify whether the community can support the level of gluten-free preparation your family needs.";
  }
  return `Each answer helps us understand what would make care feel safe and workable for ${person.object}.`;
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
  const location = typeof answers.preferred_search_area === "string" ? answers.preferred_search_area.trim() : "";
  const details: string[] = [];
  if (Array.isArray(answers.rehabilitation_focus) && answers.rehabilitation_focus.includes("STROKE")) details.push("is recovering from a stroke");
  if (answers.mobility === "DEVICE") details.push("uses a cane, walker, or wheelchair");
  if (answers.mobility === "SOME_HELP") details.push("needs some help getting around");
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