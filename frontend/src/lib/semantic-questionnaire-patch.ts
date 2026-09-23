import type { QuestionnaireState } from "@/context/questionnaire-context";
import { applyCanonicalIdentity } from "./canonical-intake-state";

export function applySemanticQuestionnairePatch(state: QuestionnaireState, patch: Record<string, unknown>): QuestionnaireState {
  let next = JSON.parse(JSON.stringify(state)) as QuestionnaireState;
  const stringKeys: Array<keyof QuestionnaireState> = [
    "ageGroup", "assistanceLevel", "memoryStatus",
    "medicaidStatus", "medicareStatus", "moveTiming", "referenceLocationValue",
    "referenceAddress", "locationImportant", "maximumDistanceMiles", "coupleAssistance",
    "parkingRequirement", "parkingVehicleCount",
  ];
  for (const key of stringKeys) {
    const value = patch[key];
    const current = next[key];
    if (typeof value === "string" && value.trim() && value.trim() !== "Not sure" && !String(current || "").trim()) {
      (next as unknown as Record<string, unknown>)[key] = value.trim();
    }
  }
  if (typeof patch.relationship === "string" && patch.relationship.trim() && !next.relationship.trim()) {
    next.relationship = patch.relationship.trim();
  }
  if (next.relationship) {
    next = applyCanonicalIdentity(next, next.relationship, typeof patch.gender === "string" ? patch.gender : "");
  }
  const budgetAnswered = next.humanIntelligenceV2?.scoringEngine?.adaptiveSignals?.some((signal) => {
    const fact = (signal as unknown as Record<string, unknown>).targetFactKey
      || (signal as unknown as Record<string, unknown>).target_fact_key
      || /Target fact:\s*([A-Za-z0-9_]+)/i.exec(signal.impactExplanation || "")?.[1];
    return ["monthly_budget", "monthly_affordability", "budget"].includes(String(fact)) && Boolean(signal.answer?.trim());
  });
  if (!budgetAnswered && next.budget <= 0 && typeof patch.budget === "number" && Number.isFinite(patch.budget) && patch.budget > 0) {
    next.budget = Math.round(patch.budget);
  }

  const medical = patch.medicalCareProfile;
  if (medical && typeof medical === "object" && !Array.isArray(medical)) {
    const source = medical as Record<string, unknown>;
    const medicalStringKeys: Array<keyof QuestionnaireState["medicalCareProfile"]> = [
      "hasOngoingMedicalNeeds", "mobilityMethod", "transferAssistance", "recentFalls",
      "dialysisFrequency", "dialysisCenter", "dialysisTransportation", "oxygenUse",
      "woundCareFrequency", "complexConditionDetails", "physicianCoordination",
    ];
    for (const key of medicalStringKeys) {
      const value = source[key];
      const current = next.medicalCareProfile[key];
      if (typeof value === "string" && value.trim() && value.trim() !== "Not sure" && !String(current || "").trim()) {
        (next.medicalCareProfile as unknown as Record<string, unknown>)[key] = value.trim();
      }
    }
    if (Array.isArray(source.needs)) {
      next.medicalCareProfile.needs = Array.from(new Set([
        ...next.medicalCareProfile.needs,
        ...source.needs.map(String).map((value) => value.trim()).filter(Boolean),
      ]));
    }
  }

  const human = patch.humanIntelligenceV2;
  if (human && typeof human === "object" && !Array.isArray(human)) {
    const source = human as Record<string, unknown>;
    const mergeStrings = (target: Record<string, unknown>, candidate: unknown) => {
      if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return;
      for (const [key, value] of Object.entries(candidate as Record<string, unknown>)) {
        if (typeof value === "string" && value.trim() && value.trim() !== "Not sure" && key in target && !String(target[key] || "").trim()) {
          target[key] = value.trim();
        }
        if (Array.isArray(value) && key in target && Array.isArray(target[key]) && (target[key] as unknown[]).length === 0) {
          target[key] = value.map(String).map((item) => item.trim()).filter(Boolean);
        }
      }
    };
    mergeStrings(next.humanIntelligenceV2.transitionRiskProfile as unknown as Record<string, unknown>, source.transitionRiskProfile);
    mergeStrings(next.humanIntelligenceV2.languageProfile as unknown as Record<string, unknown>, source.languageProfile);
    mergeStrings(next.humanIntelligenceV2.foodProfile as unknown as Record<string, unknown>, source.foodProfile);
    mergeStrings(next.humanIntelligenceV2.futureCareProfile as unknown as Record<string, unknown>, source.futureCareProfile);
    mergeStrings(next.humanIntelligenceV2.culturalProfile as unknown as Record<string, unknown>, source.culturalProfile);
    mergeStrings(next.humanIntelligenceV2.familyProfile as unknown as Record<string, unknown>, source.familyProfile);
    mergeStrings(next.humanIntelligenceV2.personalityProfile as unknown as Record<string, unknown>, source.personalityProfile);
    mergeStrings(next.humanIntelligenceV2.socialProfile as unknown as Record<string, unknown>, source.socialProfile);
  }

  next.questionnaireCompletion = {
    ...next.questionnaireCompletion,
    clientSummaryConfirmed: false,
    confirmedAt: "",
  };
  return next;
}
