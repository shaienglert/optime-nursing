export function hasUnresolvedSemanticConflict(statements: unknown): boolean {
  return Array.isArray(statements) && statements.some((statement) =>
    statement && typeof statement === "object"
    && statement.status === "ASKED"
    && statement.knowledge_state === "AMBIGUOUS"
    && (statement.importance === "MUST" || statement.importance === "UNKNOWN"),
  );
}
