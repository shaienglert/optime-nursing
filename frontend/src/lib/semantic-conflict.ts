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
