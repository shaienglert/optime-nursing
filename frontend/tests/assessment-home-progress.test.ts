import { describe, expect, it } from "vitest";

import { getHomeProgress } from "../src/lib/assessment-home-progress";
import { isAdvisorQuestionRelevant } from "../src/lib/assessment-advisor";
import { ASSESSMENT_QUESTIONS, UNKNOWN_FROM_FAMILY, type AssessmentAnswers } from "../src/lib/assessment-schema";

function completeAnswers(): AssessmentAnswers {
  return Object.fromEntries(
    ASSESSMENT_QUESTIONS
      .filter(isAdvisorQuestionRelevant)
      .map((question) => [question.id, question.id === "who_needs_care" ? "Mom" : question.answerType === "multi" || question.answerType === "priority" ? [UNKNOWN_FROM_FAMILY] : UNKNOWN_FROM_FAMILY]),
  );
}

describe("assessment home progress", () => {
  it("reveals layers from completed decision areas rather than raw answer count", () => {
    const first = getHomeProgress({ who_needs_care: "Mom" });
    expect(first.stages.find((stage) => stage.id === "foundation")?.complete).toBe(true);
    expect(first.stages.find((stage) => stage.id === "walls")?.revealed).toBe(false);

    const location = getHomeProgress({ who_needs_care: "Mom", preferred_search_area: ["SUMMERLIN"], avoid_search_areas: ["NONE"], urgency: "EXPLORING" });
    expect(location.stages.find((stage) => stage.id === "roof-frame")?.complete).toBe(true);
    expect(location.currentStageId).toBe("roof-frame");
    expect(location.completedDecisionAreas).toEqual(expect.arrayContaining(["who_needs_care", "preferred_search_area", "avoid_search_areas", "urgency"]));

    const adaptiveContinuation = getHomeProgress({ who_needs_care: "Mom", preferred_search_area: ["SUMMERLIN"], avoid_search_areas: ["NONE"], urgency: "EXPLORING", nursing_needs: ["ROUTINE"] });
    expect(adaptiveContinuation.currentStageId).toBe("windows");
  });

  it("completes only when the existing advisor has no relevant unanswered turn", () => {
    expect(getHomeProgress({ who_needs_care: "Mom" }).ready).toBe(false);
    const progress = getHomeProgress(completeAnswers());
    expect(progress.ready).toBe(true);
    expect(progress.stages.find((stage) => stage.id === "complete")?.complete).toBe(true);
  });
});