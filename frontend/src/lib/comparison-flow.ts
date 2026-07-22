import { DecisionEngineRecommendation, PatientNeedsProfile } from "@/lib/api";

const PARAMETER_LABELS: Record<string, string> = {
  nursing_24_7: "24/7 nursing",
  skilled_nursing_capabilities: "Skilled nursing",
  adl_support: "Bathing / dressing assistance",
  medication_support: "Medication management",
  ot: "Occupational therapy",
  pt: "Physical therapy",
  speech_therapy: "Speech therapy",
  transfer_assistance: "Transfer assistance",
  post_stroke_neuro_evidence: "Stroke / neurological rehabilitation",
  languages: "Language support",
  medicare_attributes: "Medicare acceptance",
  memory_care: "Memory care",
  published_rates: "Transparent pricing",
  transportation: "Transportation support",
  inspection_rating: "Quality & safety",
  quality_measures: "Quality measures",
  rn_hours_per_resident_day: "RN staffing",
  total_nurse_hours_per_resident_day: "Total nursing staffing",
  staffing_turnover: "Staffing stability",
  current_availability: "Current availability",
};

const DEFAULT_RELEVANT_PARAMETER_WINDOW = 12;

function unique(items: string[]): string[] {
  return Array.from(new Set(items.filter(Boolean)));
}

export function displayParameterLabel(parameterId: string): string {
  return PARAMETER_LABELS[parameterId] || parameterId.replace(/_/g, " ");
}

export function buildNeedStatusMap(recommendation: DecisionEngineRecommendation): Map<string, "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"> {
  const statusMap = new Map<string, "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED">();

  for (const item of recommendation.matched_needs || []) {
    if (typeof item?.parameter_id === "string") {
      statusMap.set(item.parameter_id, "MATCH");
    }
  }

  for (const item of recommendation.unmet_verified_needs || []) {
    if (typeof item?.parameter_id === "string") {
      statusMap.set(item.parameter_id, "VERIFIED_GAP");
    }
  }

  for (const item of recommendation.unknown_critical_needs || []) {
    if (typeof item?.parameter_id === "string" && !statusMap.has(item.parameter_id)) {
      statusMap.set(item.parameter_id, "NOT_VERIFIED");
    }
  }

  return statusMap;
}

export function deriveRelevantParameterIds(profile: PatientNeedsProfile | null | undefined, orderedParameterIds: string[], windowSize = DEFAULT_RELEVANT_PARAMETER_WINDOW): string[] {
  const patientNeedIds = (profile?.needs || []).map((need) => need.parameter_id);
  const orderedWindow = orderedParameterIds.slice(0, Math.max(windowSize, patientNeedIds.length));
  return unique([...patientNeedIds, ...orderedWindow]);
}

export function isPatientNeed(profile: PatientNeedsProfile | null | undefined, parameterId: string): boolean {
  return Boolean((profile?.needs || []).find((need) => need.parameter_id === parameterId));
}

export function isCriticalPatientNeed(profile: PatientNeedsProfile | null | undefined, parameterId: string): boolean {
  return Boolean(
    (profile?.needs || []).find(
      (need) => need.parameter_id === parameterId && (need.requirement_level === "REQUIRED" || need.requirement_level === "HIGH")
    )
  );
}

export function sortRelevantParameterIds(profile: PatientNeedsProfile | null | undefined, parameterIds: string[]): string[] {
  const requirementWeight: Record<string, number> = {
    REQUIRED: 0,
    HIGH: 1,
    MEDIUM: 2,
    PREFERENCE: 3,
  };
  const needsById = new Map((profile?.needs || []).map((need) => [need.parameter_id, need] as const));

  return [...parameterIds].sort((left, right) => {
    const leftNeed = needsById.get(left);
    const rightNeed = needsById.get(right);
    const leftWeight = leftNeed ? requirementWeight[leftNeed.requirement_level] ?? 99 : 50;
    const rightWeight = rightNeed ? requirementWeight[rightNeed.requirement_level] ?? 99 : 50;
    if (leftWeight !== rightWeight) return leftWeight - rightWeight;
    return displayParameterLabel(left).localeCompare(displayParameterLabel(right));
  });
}