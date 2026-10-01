import { DecisionEngineRecommendation } from "@/lib/api";

type VerificationState = "YES" | "NO" | "UNKNOWN" | "LIMITED";

type VerificationInboxQuestion = {
  capability_key: string;
  question: string;
  current_state: VerificationState;
  rationale: string;
};

export type ProviderVerificationInboxItem = {
  canonical_facility_id: string;
  facility_name: string;
  created_at: string;
  status: "OPEN" | "RESOLVED";
  question_count: number;
  questions: VerificationInboxQuestion[];
  privacy: { resident_info_shared: false; notes: string };
};

function keyOf(item: Record<string, unknown>): string {
  return String(item.parameter_id || item.need_key || item.need_text || "unknown_requirement");
}

export function createVerificationInbox(recommendations: DecisionEngineRecommendation[]): ProviderVerificationInboxItem[] {
  const now = new Date().toISOString();
  return recommendations.flatMap((recommendation) => {
    const unknown = recommendation.unknown_critical_needs || [];
    if (!unknown.length) return [];
    return [{
      canonical_facility_id: recommendation.canonical_facility_id,
      facility_name: recommendation.facility_name,
      created_at: now,
      status: "OPEN" as const,
      question_count: unknown.length,
      questions: unknown.map((item) => ({
        capability_key: keyOf(item),
        question: `Please verify the current facility fact: ${keyOf(item).replace(/_/g, " ")}.`,
        current_state: "UNKNOWN" as const,
        rationale: "Required facility evidence is currently unknown in the backend decision snapshot.",
      })),
      privacy: {
        resident_info_shared: false as const,
        notes: "Capability-only verification. No resident identity, family contact, budget, or clinical narrative is shared.",
      },
    }];
  });
}

/*
Provider answers must be written through the backend Facility Evidence Profile API.
This frontend module deliberately does not mutate recommendation state or maintain a
second facility-memory/decision engine.
*/
