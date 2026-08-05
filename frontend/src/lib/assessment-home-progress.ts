import { isAdvisorQuestionRelevant, isAdvisorReadyForMatch } from "@/lib/assessment-advisor";
import { hasAssessmentAnswer } from "@/lib/assessment-conversation";
import { getVisibleQuestions, type AssessmentAnswers, type DecisionArea } from "@/lib/assessment-schema";

export type HomeProgressStage = {
  id: string;
  label: string;
  description: string;
  decisionAreas: DecisionArea[];
};

export type HomeProgressStageState = HomeProgressStage & {
  completedAreas: number;
  availableAreas: number;
  revealed: boolean;
  complete: boolean;
};

export const HOME_PROGRESS_STAGES: HomeProgressStage[] = [
  { id: "foundation", label: "Foundation", description: "Who needs care and the family situation", decisionAreas: ["who_needs_care", "current_living_situation"] },
  { id: "walls", label: "Support walls", description: "Mobility and daily living support", decisionAreas: ["mobility", "daily_activities"] },
  { id: "windows", label: "Care windows", description: "Medical, nursing, memory, and rehabilitation needs", decisionAreas: ["medication_support", "cognitive_status", "nursing_needs", "rehabilitation_needs", "rehabilitation_services", "stroke_recovery", "neurological_rehabilitation"] },
  { id: "roof-frame", label: "Roof structure", description: "Location, timing, and availability", decisionAreas: ["preferred_search_area", "avoid_search_areas", "urgency"] },
  { id: "roof", label: "Shelter", description: "Budget, payment, and room preferences", decisionAreas: ["budget", "payment_method", "room_preference"] },
  { id: "access", label: "Door and path", description: "Transfers and family access", decisionAreas: ["transfer_assistance", "distance_from_family"] },
  { id: "garden", label: "Garden", description: "Activities and everyday preferences", decisionAreas: ["social_activity_preferences"] },
  { id: "lights", label: "Warm lights", description: "Language, culture, and dietary needs", decisionAreas: ["language_needs", "religious_cultural_preferences", "dietary_requirements"] },
  { id: "complete", label: "Ready home", description: "Priorities and deal-breakers resolved", decisionAreas: ["family_priorities", "deal_breakers"] },
];

export function getHomeProgress(answers: AssessmentAnswers): { stages: HomeProgressStageState[]; completedDecisionAreas: DecisionArea[]; currentStageId: string; ready: boolean } {
  const relevantVisibleQuestions = getVisibleQuestions(answers).filter(isAdvisorQuestionRelevant);
  const availableAreas = new Set(relevantVisibleQuestions.map((question) => question.decisionArea));
  const completedAreas = new Set(
    relevantVisibleQuestions
      .filter((question) => hasAssessmentAnswer(answers[question.id]))
      .map((question) => question.decisionArea),
  );
  const ready = isAdvisorReadyForMatch(answers);

  const stages = HOME_PROGRESS_STAGES.map((stage) => {
    const stageAreas = stage.decisionAreas.filter((area) => availableAreas.has(area));
    const completedStageAreas = stageAreas.filter((area) => completedAreas.has(area));
    const complete = stage.id === "complete"
      ? ready
      : stageAreas.length > 0 && completedStageAreas.length === stageAreas.length;
    return {
      ...stage,
      completedAreas: completedStageAreas.length,
      availableAreas: stageAreas.length,
      revealed: complete || completedStageAreas.length > 0,
      complete,
    };
  });

  const questionById = new Map(relevantVisibleQuestions.map((question) => [question.id, question]));
  const latestArea = Object.keys(answers).reverse().map((questionId) => questionById.get(questionId)?.decisionArea).find((area): area is DecisionArea => Boolean(area));
  const currentStageId = ready ? "complete" : HOME_PROGRESS_STAGES.find((stage) => latestArea && stage.decisionAreas.includes(latestArea))?.id || "foundation";

  return { stages, completedDecisionAreas: Array.from(completedAreas), currentStageId, ready };
}