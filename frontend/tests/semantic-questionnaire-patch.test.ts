import { describe, expect, it } from "vitest";
import type { QuestionnaireState } from "../src/context/questionnaire-context";
import { applySemanticQuestionnairePatch } from "../src/lib/semantic-questionnaire-patch";

function blankState(): QuestionnaireState {
  return {
    relationship: "", gender: "", budget: 0, medicareStatus: "", moveTiming: "",
    referenceAddress: "", maximumDistanceMiles: "", locationImportant: "", coupleAssistance: "",
    medicalCareProfile: { needs: [] }, questionnaireCompletion: { clientSummaryConfirmed: true },
    humanIntelligenceV2: {
      transitionRiskProfile: { attitudeTowardMove: "" }, languageProfile: {}, foodProfile: {},
      futureCareProfile: {}, culturalProfile: { religionImportance: "" },
      familyProfile: { socialInteractionNeed: "" }, personalityProfile: { communitySizePreference: "" }, socialProfile: {},
    },
  } as unknown as QuestionnaireState;
}

describe("explicit narrative facts reach confirmation", () => {
  it("retains coverage, timing, exact address and a non-preset radius", () => {
    const initial = blankState();
    const result = applySemanticQuestionnairePatch(initial, {
      medicareStatus: "Original Medicare", moveTiming: "Within 30 days", budget: 2500,
      referenceAddress: "333 S Valley View Blvd, Las Vegas NV 89107", maximumDistanceMiles: "15", locationImportant: "Yes",
      humanIntelligenceV2: { transitionRiskProfile: { attitudeTowardMove: "Cautious but open" }, culturalProfile: { religionImportance: "No" } },
    });
    expect(result.medicareStatus).toBe("Original Medicare");
    expect(result.moveTiming).toBe("Within 30 days");
    expect(result.budget).toBe(2500);
    expect(result.maximumDistanceMiles).toBe("15");
    expect(result.referenceAddress).toContain("333 S Valley View");
    expect(result.humanIntelligenceV2.culturalProfile.religionImportance).toBe("No");
    expect(result.questionnaireCompletion.clientSummaryConfirmed).toBe(false);
    expect(initial.budget).toBe(0);
  });
  it("keeps partner attribution and does not create omitted clinical facts", () => {
    const result = applySemanticQuestionnairePatch(blankState(), {
      relationship: "Couple", coupleAssistance: "Husband needs bathing help; wife is independent",
      humanIntelligenceV2: { familyProfile: { socialInteractionNeed: "Weekly" } },
    });
    expect(result.coupleAssistance).toContain("wife is independent");
    expect(result.humanIntelligenceV2.familyProfile.socialInteractionNeed).toBe("Weekly");
    expect(result.medicaidStatus).toBeUndefined();
    expect(result.medicalCareProfile.needs).toEqual([]);
  });
});
