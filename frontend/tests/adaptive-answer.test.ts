import { expect, it } from "vitest";
import { applyAdaptiveAnswer } from "../src/lib/adaptive-answer";
import type { QuestionnaireState } from "../src/context/questionnaire-context";

it("preserves the family story and prior answers while recording an explicit follow-up", () => {
  const state = {
    notes: "Dad needs rehabilitation after surgery.",
    questionnaireCompletion: { mandatoryComplete: true, conditionalFollowUpsComplete: true, clientSummaryConfirmed: true, confirmedAt: "earlier" },
    humanIntelligenceV2: { scoringEngine: { adaptiveSignals: [{ questionKey: "other", answer: "prior" }] } },
  } as unknown as QuestionnaireState;
  const next = applyAdaptiveAnswer(state, { question_key: "payment", question: "Which Medicare coverage?", target_fact_key: "medicare_status", information_gain: "HIGH" }, "Original Medicare");
  expect(next.notes).toBe(state.notes);
  expect(next).toHaveProperty("medicareStatus", "Original Medicare");
  expect(next.questionnaireCompletion.clientSummaryConfirmed).toBe(false);
  expect(next.humanIntelligenceV2.scoringEngine.adaptiveSignals).toHaveLength(2);
  expect(next.humanIntelligenceV2.scoringEngine.adaptiveSignals[1]).toMatchObject({ questionKey: "payment", answer: "Original Medicare", impactExplanation: "Question: Which Medicare coverage? | Target fact: medicare_status | explicit client answer" });
  expect(state.questionnaireCompletion.clientSummaryConfirmed).toBe(true);
  const updated = applyAdaptiveAnswer(next, { question_key: "payment", question: "Which Medicare coverage?", target_fact_key: "medicare_status" }, "Medicare Advantage");
  expect(updated.humanIntelligenceV2.scoringEngine.adaptiveSignals).toHaveLength(2);
  expect(updated).toHaveProperty("medicareStatus", "Medicare Advantage");
});
