type Primitive = string | number | boolean;

type ConditionValue = Primitive | Primitive[];

export type ConditionMap = Record<string, ConditionValue>;

export type QuestionNode = {
  question_id: string;
  writes_to: string;
  show_if?: ConditionMap;
  hide_if?: ConditionMap;
  depends_on?: string[];
  next_questions: string[];
  source_of_truth: boolean;
};

export type VisibilityAuditRow = {
  question_id: string;
  visible: boolean;
  hidden_reason: string;
  writes_to: string;
  source_of_truth: boolean;
};

export const QUESTION_GRAPH: QuestionNode[] = [
  { question_id: "Q_RELATIONSHIP", writes_to: "relationship", next_questions: ["Q_COUPLE_ASSISTANCE", "Q_COUPLE_SAME_CARE", "Q_COUPLE_STAY_TOGETHER", "Q_COUPLE_TEMP_SEPARATION", "Q_CONTINUUM_OF_CARE", "Q_FUTURE_CARE_PREFERENCE", "Q_LOSS_STATUS", "Q_LOSS_TIMING", "Q_SOCIAL_CHANGE_SINCE_LOSS", "Q_LONELINESS_CONCERN", "Q_GRIEF_SUPPORT", "Q_RELIGION_IMPORTANCE", "Q_FAITH_TRADITION", "Q_COMMUNITY_IMPORTANCE", "Q_DIETARY_REQUIREMENTS", "Q_WORSHIP_ACCESS", "Q_KOSHER_MEALS", "Q_SYNAGOGUE_ACCESS", "Q_JEWISH_PROGRAMMING", "Q_CHURCH_ACCESS", "Q_CHRISTIAN_SERVICES", "Q_HALAL_MEALS", "Q_PRAYER_FACILITIES", "Q_PRIMARY_LANGUAGE", "Q_SOCIAL_LANGUAGE", "Q_MEDICAL_LANGUAGE", "Q_BILINGUAL_STAFF", "Q_VISIT_FREQUENCY", "Q_MIN_TRAVEL_TIME", "Q_EMERGENCY_ACCESS_IMPORTANCE"], source_of_truth: true },
  { question_id: "Q_COUPLE_ASSISTANCE", writes_to: "couple_assistance", show_if: { relationship: "Couple" }, next_questions: ["Q_COUPLE_SAME_CARE", "Q_COUPLE_STAY_TOGETHER", "Q_COUPLE_TEMP_SEPARATION", "Q_CONTINUUM_OF_CARE"], source_of_truth: true },
  { question_id: "Q_COUPLE_SAME_CARE", writes_to: "couple_same_care_level", show_if: { relationship: "Couple" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_COUPLE_STAY_TOGETHER", writes_to: "couple_stay_together_preference", show_if: { relationship: "Couple" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_COUPLE_TEMP_SEPARATION", writes_to: "temporary_separation_acceptance", show_if: { relationship: "Couple" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_FUTURE_CARE_PREFERENCE", writes_to: "future_care_preference", show_if: { assistance_level: "Fully independent" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_LOSS_STATUS", writes_to: "widow_status", hide_if: { relationship: "Couple" }, depends_on: ["Q_RELATIONSHIP"], next_questions: ["Q_LOSS_TIMING", "Q_SOCIAL_CHANGE_SINCE_LOSS", "Q_LONELINESS_CONCERN", "Q_GRIEF_SUPPORT"], source_of_truth: true },
  { question_id: "Q_LOSS_TIMING", writes_to: "loss_timing", show_if: { widow_status: "Yes" }, hide_if: { relationship: "Couple" }, depends_on: ["Q_LOSS_STATUS"], next_questions: [], source_of_truth: true },
  { question_id: "Q_SOCIAL_CHANGE_SINCE_LOSS", writes_to: "social_activity_change_since_loss", show_if: { widow_status: "Yes" }, hide_if: { relationship: "Couple" }, depends_on: ["Q_LOSS_STATUS"], next_questions: [], source_of_truth: true },
  { question_id: "Q_LONELINESS_CONCERN", writes_to: "loneliness_risk", show_if: { widow_status: "Yes" }, hide_if: { relationship: "Couple" }, depends_on: ["Q_LOSS_STATUS"], next_questions: [], source_of_truth: true },
  { question_id: "Q_GRIEF_SUPPORT", writes_to: "grief_support_interest", show_if: { widow_status: "Yes" }, hide_if: { relationship: "Couple" }, depends_on: ["Q_LOSS_STATUS"], next_questions: [], source_of_truth: true },
  { question_id: "Q_RELIGION_IMPORTANCE", writes_to: "religion_importance", next_questions: ["Q_FAITH_TRADITION", "Q_COMMUNITY_IMPORTANCE", "Q_DIETARY_REQUIREMENTS", "Q_WORSHIP_ACCESS", "Q_KOSHER_MEALS", "Q_SYNAPGOGUE_ACCESS", "Q_JEWISH_PROGRAMMING", "Q_CHURCH_ACCESS", "Q_CHRISTIAN_SERVICES", "Q_HALAL_MEALS", "Q_PRAYER_FACILITIES"], source_of_truth: true },
  { question_id: "Q_FAITH_TRADITION", writes_to: "faith_traditions", show_if: { religion_importance_min: "Medium" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_COMMUNITY_IMPORTANCE", writes_to: "religious_community_importance", show_if: { religion_importance_min: "Medium" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_DIETARY_REQUIREMENTS", writes_to: "religious_dietary_requirements", show_if: { religion_importance_min: "Medium" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_WORSHIP_ACCESS", writes_to: "worship_access_requirement", show_if: { religion_importance_min: "Medium" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_KOSHER_MEALS", writes_to: "kosher_requirements", show_if: { faith_traditions_has: "Jewish" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_SYNAGOGUE_ACCESS", writes_to: "synagogue_access", show_if: { faith_traditions_has: "Jewish" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_JEWISH_PROGRAMMING", writes_to: "jewish_programming_importance", show_if: { faith_traditions_has: "Jewish" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_CHURCH_ACCESS", writes_to: "church_access_requirement", show_if: { faith_traditions_has_any: ["Catholic", "Protestant", "Orthodox Christian"] }, next_questions: [], source_of_truth: true },
  { question_id: "Q_CHRISTIAN_SERVICES", writes_to: "christian_service_requirement", show_if: { faith_traditions_has_any: ["Catholic", "Protestant", "Orthodox Christian"] }, next_questions: [], source_of_truth: true },
  { question_id: "Q_HALAL_MEALS", writes_to: "halal_meals_requirement", show_if: { faith_traditions_has: "Muslim" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_PRAYER_FACILITIES", writes_to: "prayer_facility_requirement", show_if: { faith_traditions_has: "Muslim" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_PRIMARY_LANGUAGE", writes_to: "preferred_spoken_language", next_questions: ["Q_SOCIAL_LANGUAGE", "Q_MEDICAL_LANGUAGE", "Q_BILINGUAL_STAFF"], source_of_truth: true },
  { question_id: "Q_SOCIAL_LANGUAGE", writes_to: "social_interaction_language", show_if: { preferred_spoken_language_not: "English" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_MEDICAL_LANGUAGE", writes_to: "medical_discussion_language", show_if: { preferred_spoken_language_not: "English" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_BILINGUAL_STAFF", writes_to: "bilingual_staff_required", show_if: { preferred_spoken_language_not: "English" }, next_questions: [], source_of_truth: true },
  { question_id: "Q_VISIT_FREQUENCY", writes_to: "family_visit_expectation", next_questions: [], source_of_truth: true },
  { question_id: "Q_MIN_TRAVEL_TIME", writes_to: "minimum_acceptable_travel_time", next_questions: [], source_of_truth: true },
  { question_id: "Q_EMERGENCY_ACCESS_IMPORTANCE", writes_to: "emergency_access_importance", next_questions: [], source_of_truth: true },
];

const IMPORTANCE_RANK: Record<string, number> = {
  "Not important": 0,
  Low: 1,
  "Somewhat important": 1,
  Medium: 2,
  Important: 3,
  High: 3,
  "Very important": 4,
  "Very high": 4,
};

function matchesConditionValue(actual: unknown, expected: ConditionValue): boolean {
  if (Array.isArray(expected)) {
    return expected.includes(actual as Primitive);
  }
  return actual === expected;
}

function isVisible(node: QuestionNode, answers: Record<string, unknown>): { visible: boolean; hiddenReason: string } {
  if (node.hide_if) {
    for (const [key, expected] of Object.entries(node.hide_if)) {
      if (matchesConditionValue(answers[key], expected)) {
        return { visible: false, hiddenReason: `hide_if matched ${key}` };
      }
    }
  }

  if (!node.show_if) {
    return { visible: true, hiddenReason: "" };
  }

  for (const [key, expected] of Object.entries(node.show_if)) {
    if (key === "religion_importance_min") {
      const actual = String(answers["religion_importance"] || "");
      const min = IMPORTANCE_RANK[String(expected)] ?? 0;
      const rank = IMPORTANCE_RANK[actual] ?? -1;
      if (rank < min) return { visible: false, hiddenReason: "show_if religion_importance_min not met" };
      continue;
    }

    if (key === "faith_traditions_has") {
      const actual = Array.isArray(answers["faith_traditions"]) ? (answers["faith_traditions"] as unknown[]) : [];
      if (!actual.includes(expected)) return { visible: false, hiddenReason: "show_if faith_traditions_has not met" };
      continue;
    }

    if (key === "faith_traditions_has_any") {
      const actual = Array.isArray(answers["faith_traditions"]) ? (answers["faith_traditions"] as unknown[]) : [];
      const required = Array.isArray(expected) ? expected : [expected];
      if (!required.some((item) => actual.includes(item))) return { visible: false, hiddenReason: "show_if faith_traditions_has_any not met" };
      continue;
    }

    if (key === "preferred_spoken_language_not") {
      const actual = String(answers["preferred_spoken_language"] || "");
      if (!actual || actual === String(expected)) return { visible: false, hiddenReason: "show_if preferred_spoken_language_not not met" };
      continue;
    }

    if (!matchesConditionValue(answers[key], expected)) {
      return { visible: false, hiddenReason: `show_if ${key} not met` };
    }
  }

  return { visible: true, hiddenReason: "" };
}

function findDuplicateWrites(graph: QuestionNode[]): string[] {
  const counts: Record<string, number> = {};
  for (const node of graph) {
    counts[node.writes_to] = (counts[node.writes_to] || 0) + 1;
  }
  return Object.entries(counts)
    .filter(([, count]) => count > 1)
    .map(([key]) => key);
}

function findCycles(graph: QuestionNode[]): string[] {
  const byId = new Map(graph.map((node) => [node.question_id, node]));
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const cycles: string[] = [];

  const dfs = (id: string) => {
    if (visiting.has(id)) {
      cycles.push(id);
      return;
    }
    if (visited.has(id)) return;
    visiting.add(id);
    const node = byId.get(id);
    if (node) {
      for (const next of node.next_questions) dfs(next);
    }
    visiting.delete(id);
    visited.add(id);
  };

  for (const node of graph) dfs(node.question_id);
  return Array.from(new Set(cycles));
}

function findUnreachable(graph: QuestionNode[]): string[] {
  const root = graph.find((node) => node.question_id === "Q_RELATIONSHIP");
  if (!root) return graph.map((node) => node.question_id);

  const byId = new Map(graph.map((node) => [node.question_id, node]));
  const reached = new Set<string>();
  const queue = [root.question_id];

  while (queue.length > 0) {
    const id = queue.shift() as string;
    if (reached.has(id)) continue;
    reached.add(id);
    const node = byId.get(id);
    if (!node) continue;
    for (const dep of node.next_questions) queue.push(dep);
  }

  return graph.filter((node) => !reached.has(node.question_id)).map((node) => node.question_id);
}

function findContradictions(graph: QuestionNode[]): string[] {
  const contradictions: string[] = [];
  for (const node of graph) {
    if (!node.show_if || !node.hide_if) continue;
    for (const [showKey, showExpected] of Object.entries(node.show_if)) {
      if (showKey in node.hide_if && matchesConditionValue(showExpected, node.hide_if[showKey])) {
        contradictions.push(node.question_id);
      }
    }
  }
  return contradictions;
}

export function validateQuestionGraph(graph: QuestionNode[]): void {
  const duplicateWrites = findDuplicateWrites(graph);
  const cycles = findCycles(graph);
  const unreachable = findUnreachable(graph);
  const contradictions = findContradictions(graph);

  const failures: string[] = [];
  if (duplicateWrites.length > 0) failures.push(`duplicate writes_to: ${duplicateWrites.join(", ")}`);
  if (cycles.length > 0) failures.push(`circular dependencies: ${cycles.join(", ")}`);
  if (unreachable.length > 0) failures.push(`unreachable questions: ${unreachable.join(", ")}`);
  if (contradictions.length > 0) failures.push(`contradictory branches: ${contradictions.join(", ")}`);

  if (failures.length > 0) {
    throw new Error(`Question graph validation failed: ${failures.join(" | ")}`);
  }
}

export function buildVisibilityAudit(
  graph: QuestionNode[],
  answers: Record<string, unknown>,
): VisibilityAuditRow[] {
  return graph.map((node) => {
    const result = isVisible(node, answers);
    return {
      question_id: node.question_id,
      visible: result.visible,
      hidden_reason: result.hiddenReason,
      writes_to: node.writes_to,
      source_of_truth: node.source_of_truth,
    };
  });
}
