import type { QuestionnaireState } from "@/context/questionnaire-context";

type ExtendedQuestionnaireState = QuestionnaireState & {
  medicareStatus?: string;
  moveTiming?: string;
  entranceFeeTolerance?: string;
};

export function canonicalizeAdaptiveFact(state: QuestionnaireState, targetFactKey: string, answer: string): QuestionnaireState {
  const next = state as ExtendedQuestionnaireState;
  const normalized = answer.trim().toLowerCase();

  switch (targetFactKey) {
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
