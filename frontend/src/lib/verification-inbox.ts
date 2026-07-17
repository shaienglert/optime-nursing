import { QuestionnaireState } from "@/context/questionnaire-context";
import { SearchFacility } from "@/lib/api";
import {
  applyVerificationResponses,
  EngineOutput,
  getFacilityKnowledgeMemory,
} from "@/lib/optime-v2-engine";

type VerificationState = "YES" | "NO" | "UNKNOWN" | "LIMITED";

type VerificationChecklistItem = {
  label: string;
  state: VerificationState;
  category: string;
  rationale: string;
};

type VerificationInboxQuestion = {
  capability_key: string;
  question: string;
  current_state: VerificationState;
  rationale: string;
};

export type ProviderVerificationInboxItem = {
  facility_id: number;
  facility_name: string;
  created_at: string;
  status: "OPEN" | "RESOLVED";
  question_count: number;
  questions: VerificationInboxQuestion[];
  privacy: {
    resident_info_shared: false;
    notes: string;
  };
};

export type ProviderVerificationAnswerPayload = {
  facility: SearchFacility;
  state: QuestionnaireState;
  checklist: VerificationChecklistItem[];
  answers: Record<string, "YES" | "NO" | "LIMITED">;
  verifiedAt?: string;
  expiresInDays?: number;
};

function toQuestionKey(label: string): string {
  return label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function createVerificationInbox(engineOutput: EngineOutput): ProviderVerificationInboxItem[] {
  const now = new Date().toISOString();
  const items: ProviderVerificationInboxItem[] = [];

  engineOutput.accepted.forEach((recommendation) => {
    const checklist = recommendation.report.audit.verificationChecklist as VerificationChecklistItem[];
    const unknownItems = checklist.filter((item) => item.state === "UNKNOWN");
    if (unknownItems.length === 0) {
      return;
    }

    items.push({
      facility_id: recommendation.facility.id,
      facility_name: recommendation.facility.name,
      created_at: now,
      status: "OPEN",
      question_count: unknownItems.length,
      questions: unknownItems.map((item) => ({
        capability_key: toQuestionKey(item.label),
        question: item.label,
        current_state: item.state,
        rationale: item.rationale,
      })),
      privacy: {
        resident_info_shared: false,
        notes: "Inbox contains capability-only questions. No resident demographic, contact, budget, or clinical history data is shared.",
      },
    });
  });

  return items;
}

export function applyProviderVerificationAnswers(payload: ProviderVerificationAnswerPayload): {
  updatedChecklist: VerificationChecklistItem[];
  updatedRequest: {
    unknownCount: number;
    confidenceScore: number;
    visitReadinessScore: number;
    nextStepMessage: string;
  };
  memorySnapshot: ReturnType<typeof getFacilityKnowledgeMemory>;
} {
  const result = applyVerificationResponses(
    payload.facility,
    payload.state,
    payload.checklist,
    payload.answers,
    {
      source: "PROVIDER_PORTAL",
      verifiedAt: payload.verifiedAt,
      expiresInDays: payload.expiresInDays,
    },
  );

  return {
    updatedChecklist: result.checklist,
    updatedRequest: {
      unknownCount: result.request.unknownCount,
      confidenceScore: result.request.confidenceScore,
      visitReadinessScore: result.request.visitReadinessScore,
      nextStepMessage: result.request.nextStepMessage,
    },
    memorySnapshot: getFacilityKnowledgeMemory(payload.facility.id),
  };
}
