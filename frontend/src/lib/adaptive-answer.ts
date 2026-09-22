import type { QuestionnaireState } from "@/context/questionnaire-context";
import { canonicalizeAdaptiveFact } from "./decision-fact-canonicalization";

export type AdaptiveQuestion = {
  question_key: string;
  question: string;
  reason?: string;
  decision_dimensions?: string[];
  information_gain?: string;
  answer_options?: string[];
  policy_reference?: string;
  target_fact_key?: string;
};

export function applyAdaptiveAnswer(state: QuestionnaireState, question: AdaptiveQuestion, answer: string): QuestionnaireState {
  let next = JSON.parse(JSON.stringify(state)) as QuestionnaireState;
  next.questionnaireCompletion = {
    ...next.questionnaireCompletion,
    clientSummaryConfirmed: false,
    confirmedAt: "",
  };
  const targetFactKey = String(question.target_fact_key || "").trim();
  const signals = next.humanIntelligenceV2.scoringEngine.adaptiveSignals || [];
  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = [
    ...signals.filter((signal) => signal.questionKey !== question.question_key),
    {
      questionKey: question.question_key,
      answer,
      signalType: "decision-interview",
      weights: { informationGain: question.information_gain === "HIGH" ? 1 : 0 },
      impactExplanation: `Question: ${question.question}${targetFactKey ? ` | Target fact: ${targetFactKey}` : ""} | explicit client answer`,
      infoGain: question.information_gain === "HIGH" ? 1 : 0,
    },
  ];
  if (targetFactKey) next = canonicalizeAdaptiveFact(next, targetFactKey, answer);
  return next;
}
