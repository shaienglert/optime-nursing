import type { AdaptiveQuestion } from "./adaptive-answer";

// A failed model packet cannot authorize recommendations. It also must not hide
// a question already selected by the canonical missing-fact policy.
export function canonicalRecoveryQuestion(profile: unknown): AdaptiveQuestion | undefined {
  const record = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
  const decision = record(record(profile).decision_intelligence);
  const canonical = record(decision.canonical_decision_state);
  if (canonical.authoritative !== true || canonical.client !== "INCOMPLETE") return undefined;
  const human = record(decision.human_intelligence);
  const guardian = record(human.readiness_guardian);
  if (guardian.fallback_reason !== "SEMANTIC_AI_UNAVAILABLE" || typeof guardian.selected_fact_key !== "string") return undefined;
  const questions = Array.isArray(human.adaptive_questions) ? human.adaptive_questions : [];
  return questions.find((value): value is AdaptiveQuestion => {
    const q = record(value);
    return q.question_owner === "DETERMINISTIC_CANONICAL_FALLBACK"
      && q.target_fact_key === guardian.selected_fact_key
      && typeof q.question_key === "string" && !!q.question_key.trim()
      && typeof q.question === "string" && !!q.question.trim()
      && Array.isArray(q.answer_options) && q.answer_options.length > 0;
  });
}

export function semanticIntakeFailure(packet: { enabled?: boolean; required?: boolean; status?: string } | undefined): boolean {
  if (!packet) return false;
  if (packet.status === "FAILED" || packet.status === "REQUIRED_BUT_DISABLED") return true;
  return Boolean(packet.enabled || packet.required)
    && packet.status !== "CONSULTED_AND_VALIDATED"
    && packet.status !== "GUARDIAN_BLOCKED_READY";
}

export function hasUnresolvedSemanticConflict(statements: unknown): boolean {
  return Array.isArray(statements) && statements.some((statement) =>
    statement && typeof statement === "object"
    && statement.status === "ASKED"
    && statement.knowledge_state === "AMBIGUOUS"
    && (statement.importance === "MUST" || statement.importance === "UNKNOWN"),
  );
}

export function semanticConflictQuestion(statements: unknown) {
  if (!Array.isArray(statements)) return null;
  const index = statements.findIndex((statement) =>
    hasUnresolvedSemanticConflict([statement])
    && typeof statement.clarification_question === "string"
    && statement.clarification_question.trim(),
  );
  if (index < 0) return null;
  const statement = statements[index];
  const gapKey = typeof statement.gap_key === "string" ? statement.gap_key : "";
  return {
    question_key: `semantic-conflict-${gapKey || index}`,
    question: statement.clarification_question.trim() as string,
    decision_dimensions: Array.isArray(statement.mapped_parameters)
      ? statement.mapped_parameters.filter((value: unknown): value is string => typeof value === "string") : [],
    information_gain: "HIGH",
  };
}
