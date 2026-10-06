/** Read the existing decision strategy; do not infer a clinical care plan. */
export function hasSeparateRecoveryEpisode(decision?: Record<string, unknown>): boolean {
  const strategy = decision?.living_strategy;
  if (!strategy || typeof strategy !== "object") return false;
  const candidates = (strategy as { strategy_candidates?: unknown }).strategy_candidates;
  return Array.isArray(candidates) && candidates.some(candidate => candidate && typeof candidate === "object" &&
    (candidate as { strategy_id?: string }).strategy_id === "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING");
}
