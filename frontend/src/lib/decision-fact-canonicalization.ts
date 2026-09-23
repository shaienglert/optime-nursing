import type { QuestionnaireState } from "@/context/questionnaire-context";

type ExtendedQuestionnaireState = QuestionnaireState & {
  medicareStatus?: string;
  moveTiming?: string;
  entranceFeeTolerance?: string;
};

export type MonthlyBudgetAnswer = {
  /** Upper bound in dollars per month, or undefined when the client stated no usable ceiling. */
  budget?: number;
  /** The client stated a floor ("Above $12,000"), so no upper bound may be inferred. */
  noUpperLimit: boolean;
  /** The client answered but supplied no amount ("Not sure"). Unknown, never a default. */
  acknowledgedUnknown: boolean;
};

/**
 * Interpret an answer to the `monthly_budget` question.
 *
 * `current_price.desired_value` is consumed downstream strictly as an inclusive upper
 * bound (`price <= budget`), so a range must yield its TOP value, and a floor-style
 * answer must yield no bound at all. Concatenating the digits of a range — the previous
 * behaviour — turned "$5,000-$8,000" into a $50,008,000 ceiling, which silently disabled
 * every budget comparison in the pipeline.
 *
 * An answer carrying no amount is an acknowledged unknown: it is never converted into a
 * default value, per the material-unknown policy.
 */
export function parseMonthlyBudgetAnswer(answer: string): MonthlyBudgetAnswer {
  const normalized = String(answer ?? "").trim().toLowerCase();
  const amounts = (normalized.match(/\d[\d,]*(?:\.\d+)?/g) ?? [])
    .map((token) => Number(token.replace(/,/g, "")))
    .filter((value) => Number.isFinite(value) && value > 0);

  if (amounts.length === 0) return { noUpperLimit: false, acknowledgedUnknown: true };

  // "Above $12,000" / "over $12,000" / "$12,000+" state a floor, not a ceiling.
  if (/\b(above|over|more than|at least|greater than)\b/.test(normalized) || /\d\s*\+/.test(normalized)) {
    return { noUpperLimit: true, acknowledgedUnknown: false };
  }

  return { budget: Math.max(...amounts), noUpperLimit: false, acknowledgedUnknown: false };
}

export function canonicalizeAdaptiveFact(state: QuestionnaireState, targetFactKey: string, answer: string): QuestionnaireState {
  const next = state as ExtendedQuestionnaireState;
  const normalized = answer.trim().toLowerCase();

  switch (targetFactKey) {
    case "market_location":
    case "location":
    case "city_or_metro_area":
      next.referenceLocationValue = answer;
      next.referenceLocationType = "City or metro area";
      break;
    case "monthly_budget": {
      const parsed = parseMonthlyBudgetAnswer(answer);
      if (parsed.budget !== undefined) next.budget = parsed.budget;
      break;
    }
    case "community_size_preference":
      next.humanIntelligenceV2.personalityProfile.communitySizePreference = answer;
      break;
    case "social_interaction_need_after_loss":
      next.humanIntelligenceV2.familyProfile.socialInteractionNeed = answer;
      break;
    case "move_participation":
      next.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove = answer;
      break;
    case "rehab_level_needed":
      if (normalized.includes("only personal") || normalized === "no") {
        next.humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed = "No";
      } else if (normalized.includes("skilled") || normalized.includes("physical") || normalized.includes("occupational") || normalized === "yes" || normalized === "both") {
        next.humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed = "Required";
      } else {
        next.humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed = answer;
      }
      break;
    case "medicare_status":
      next.medicareStatus = answer;
      break;
    case "move_timing_vs_rehab":
      next.moveTiming = answer;
      break;
    case "ccrc_entrance_fee_tolerance":
      next.entranceFeeTolerance = answer;
      break;
    default:
      break;
  }
  return next;
}
