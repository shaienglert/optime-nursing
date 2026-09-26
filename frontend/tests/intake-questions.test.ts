import { describe, expect, it } from "vitest";

import { DEFAULT_STATE } from "../src/context/questionnaire-context";
import {
  QUESTIONS,
  buildSubmission,
  createExtras,
  isAnswered,
  missingQuestions,
  visibleQuestions,
  type IntakeContext,
} from "../src/lib/intake-questions";

function ctx(): IntakeContext {
  const draft = JSON.parse(JSON.stringify(DEFAULT_STATE)) as typeof DEFAULT_STATE;
  return { draft, extras: createExtras(draft) };
}

function answer(context: IntakeContext, id: string, value: string | string[] | number): IntakeContext {
  const question = QUESTIONS.find((item) => item.id === id);
  if (!question) throw new Error(`no question ${id}`);
  return question.set(context, value);
}

/** Walk the interview the way the UI does: always the first unanswered required question. */
function runInterview(context: IntakeContext, answers: Record<string, string | string[] | number>, maxSteps = 100) {
  const asked: string[] = [];
  let current = context;
  for (let step = 0; step < maxSteps; step += 1) {
    const next = visibleQuestions(current).find((question) => question.required && !isAnswered(question, current));
    if (!next) break;
    if (!(next.id in answers)) throw new Error(`interview asked an unanswered question: ${next.id}`);
    asked.push(next.id);
    current = next.set(current, answers[next.id]);
  }
  return { asked, context: current };
}

const FULL_CASE: Record<string, string | string[] | number> = {
  relationship: "Mom",
  ageGroup: "80-84",
  assistance: ["Help with bathing", "Help with dressing"],
  mobilityMethod: "Walker",
  transferAssistance: "One person",
  recentFalls: "One",
  memoryStatus: "No",
  hasOngoingMedicalNeeds: "No",
  recentHospitalization: "No",
  medicaidStatus: "Not sure",
  budget: 6000,
  moveTiming: "1-3 months",
  moveAttitude: "Cautious but open",
  socialFrequency: "Weekly",
  communityStyle: "Medium",
  activities: ["Music"],
  moveLossConcerns: ["Privacy"],
  language: "English",
  religiousCommunity: "No",
  petOwnershipImportance: "No",
  abilityToLeaveIndependently: "Yes",
  biggestFear: "Losing her independence.",
  parkingRequirement: "No",
  continuum: "Preferred",
  locationImportant: "Yes",
  referenceAddress: "Summerlin, Las Vegas, NV",
  maximumDistanceMiles: "20",
};

describe("intake question list", () => {
  it("has unique ids and a prompt for every question", () => {
    const ids = QUESTIONS.map((question) => question.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const question of QUESTIONS) {
      expect(question.prompt.length).toBeGreaterThan(0);
      expect(question.label.length).toBeGreaterThan(0);
      if (question.kind === "single" || question.kind === "multi") {
        expect(question.options && question.options.length).toBeGreaterThan(1);
      }
    }
  });

  it("asks only the questions that apply to the case", () => {
    let context = ctx();
    // Nothing about mobility, memory safety, medical detail or location is asked yet.
    const initial = visibleQuestions(context).map((question) => question.id);
    expect(initial).not.toContain("mobilityMethod");
    expect(initial).not.toContain("memoryWandering");
    expect(initial).not.toContain("medicalNeeds");
    expect(initial).not.toContain("referenceAddress");

    context = answer(context, "assistance", ["Help with bathing"]);
    expect(visibleQuestions(context).map((q) => q.id)).toContain("mobilityMethod");

    context = answer(context, "memoryStatus", "Significant memory issues");
    expect(visibleQuestions(context).map((q) => q.id)).toContain("memoryWandering");

    context = answer(context, "hasOngoingMedicalNeeds", "Yes");
    context = answer(context, "medicalNeeds", ["Dialysis"]);
    const withDialysis = visibleQuestions(context).map((q) => q.id);
    expect(withDialysis).toContain("dialysisFrequency");
    expect(withDialysis).not.toContain("oxygenUse");
  });

  it("stops asking a follow-up when its parent answer changes back", () => {
    let context = ctx();
    context = answer(context, "hasOngoingMedicalNeeds", "Yes");
    context = answer(context, "medicalNeeds", ["Oxygen"]);
    expect(visibleQuestions(context).map((q) => q.id)).toContain("oxygenUse");
    context = answer(context, "hasOngoingMedicalNeeds", "No");
    expect(visibleQuestions(context).map((q) => q.id)).not.toContain("oxygenUse");
  });

  it("keeps 'Fully independent' exclusive of specific support needs", () => {
    let context = ctx();
    context = answer(context, "assistance", ["Help with bathing"]);
    context = answer(context, "assistance", ["Help with bathing", "Fully independent"]);
    expect(context.extras.assistance).toEqual(["Fully independent"]);
    context = answer(context, "assistance", ["Fully independent", "Help with dressing"]);
    expect(context.extras.assistance).toEqual(["Help with dressing"]);
  });
});

describe("one question at a time", () => {
  it("completes the interview asking each question exactly once", () => {
    const { asked, context } = runInterview(ctx(), FULL_CASE);
    expect(new Set(asked).size).toBe(asked.length);
    expect(missingQuestions(context)).toEqual([]);
  });

  it("asks the follow-ups the answers opened, and not the ones they did not", () => {
    const { asked } = runInterview(ctx(), FULL_CASE);
    // Assistance was selected, so mobility follow-ups are asked.
    expect(asked).toContain("mobilityMethod");
    expect(asked).toContain("transferAssistance");
    expect(asked).toContain("recentFalls");
    // No memory concern and no medical needs, so those follow-ups never appear.
    expect(asked).not.toContain("memoryWandering");
    expect(asked).not.toContain("secureMemory");
    expect(asked).not.toContain("medicalNeeds");
    expect(asked).not.toContain("physicianCoordination");
    // No hospital stay, so no Medicare question.
    expect(asked).not.toContain("medicareStatus");
    // Location matters, so the address and radius are asked.
    expect(asked).toContain("referenceAddress");
    expect(asked).toContain("maximumDistanceMiles");
  });

  it("never presents the whole interview at once", () => {
    // The regression this replaces rendered every applicable question on one page.
    // The interview is a list to be stepped through, so each step is exactly one question.
    const { context } = runInterview(ctx(), FULL_CASE);
    const applicable = visibleQuestions(context);
    expect(applicable.length).toBeGreaterThan(20);
    const { asked } = runInterview(ctx(), FULL_CASE);
    for (const id of asked) {
      expect(asked.filter((item) => item === id)).toHaveLength(1);
    }
  });

  it("reports what is missing per question rather than as one lump", () => {
    let context = ctx();
    context = answer(context, "relationship", "Mom");
    const missing = missingQuestions(context);
    expect(missing.length).toBeGreaterThan(0);
    expect(missing.map((question) => question.id)).not.toContain("relationship");
    // Every entry can be navigated to, because it is a question and not a phrase.
    for (const question of missing) expect(QUESTIONS).toContain(question);
  });

  it("does not require optional questions", () => {
    const { context } = runInterview(ctx(), FULL_CASE);
    const optional = visibleQuestions(context).filter((question) => !question.required).map((question) => question.id);
    expect(optional).toContain("dietary");
    expect(optional).toContain("otherInterests");
    expect(optional).toContain("careSearchApproach");
    expect(missingQuestions(context)).toEqual([]);
  });
});

describe("submission", () => {
  it("carries the answers into the questionnaire state the engine receives", () => {
    const { context } = runInterview(ctx(), FULL_CASE);
    const submitted = buildSubmission(context);
    expect(submitted.assistanceLevel).toBe("Help with bathing, Help with dressing");
    expect(submitted.budget).toBe(6000);
    expect(submitted.ageGroup).toBe("80-84");
    expect(submitted.medicalCareProfile.mobilityMethod).toBe("Walker");
    expect(submitted.medicalCareProfile.transferAssistance).toBe("One person");
    expect(submitted.humanIntelligenceV2.socialProfile.socialInteractionFrequency).toBe("Weekly");
    expect(submitted.humanIntelligenceV2.languageProfile.preferredSpokenLanguage).toBe("English");
    expect(submitted.humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference).toBe("Preferred");
    expect(submitted.referenceAddress).toBe("Summerlin, Las Vegas, NV");
    expect(submitted.questionnaireCompletion.mandatoryComplete).toBe(true);
    expect(submitted.questionnaireCompletion.clientSummaryConfirmed).toBe(false);
  });

  it("clears follow-up answers whose parent answer no longer requires them", () => {
    let context = ctx();
    context = answer(context, "hasOngoingMedicalNeeds", "Yes");
    context = answer(context, "medicalNeeds", ["Oxygen"]);
    context = answer(context, "oxygenUse", "At night");
    expect(buildSubmission(context).medicalCareProfile.oxygenUse).toBe("At night");

    context = answer(context, "hasOngoingMedicalNeeds", "No");
    const submitted = buildSubmission(context);
    expect(submitted.medicalCareProfile.oxygenUse).toBe("");
    expect(submitted.medicalCareProfile.physicianCoordination).toBe("");
  });

  it("drops Medicare when there was no recent hospitalization", () => {
    let context = ctx();
    context = answer(context, "recentHospitalization", "Yes");
    context = answer(context, "rehabNeed", "Yes");
    context = answer(context, "medicareStatus", "Original Medicare");
    expect(buildSubmission(context).medicareStatus).toBe("Original Medicare");

    context = answer(context, "rehabNeed", "No");
    expect(buildSubmission(context).medicareStatus).toBe("");
  });

  it("keeps memory-safety answers only while a memory concern stands", () => {
    let context = ctx();
    context = answer(context, "memoryStatus", "Significant memory issues");
    context = answer(context, "memoryWandering", "Yes");
    context = answer(context, "secureMemory", "Yes");
    expect(buildSubmission(context).humanIntelligenceV2.transitionRiskProfile.wanderingConcerns).toBe("Yes");

    context = answer(context, "memoryStatus", "No");
    const submitted = buildSubmission(context);
    expect(submitted.humanIntelligenceV2.transitionRiskProfile.wanderingConcerns).toBe("");
    expect(submitted.humanIntelligenceV2.futureCareProfile.secureMemoryNeighborhoodNeed).toBe("");
  });
});