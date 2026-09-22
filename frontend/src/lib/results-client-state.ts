import type { AdaptiveQuestion } from "./adaptive-answer";

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : {};
}

// Canonical state controls the UI; legacy questions only supply display content.
export function resultsClientState(value: unknown) {
  const response = record(value);
  const decision = record(response.decision_intelligence);
  const canonical = record(decision.canonical_decision_state);
  const authoritative = canonical.authoritative === true;
  const blocked = !authoritative || canonical.system === "BLOCKED";
  const needsAnswer = !blocked && canonical.client === "INCOMPLETE";
  const human = record(decision.human_intelligence);
  const audit = record(response.recommendation_audit_trace);
  const questions = [decision.adaptive_questions, human.adaptive_questions, audit.adaptive_questions]
    .flatMap((items) => Array.isArray(items) ? items : []);
  const question = questions.find((item): item is AdaptiveQuestion => {
    const q = record(item);
    return typeof q.question === "string" && !!q.question.trim()
      && typeof q.question_key === "string" && !!q.question_key.trim();
  });
  return { blocked, needsAnswer, question: needsAnswer ? question : undefined };
}
