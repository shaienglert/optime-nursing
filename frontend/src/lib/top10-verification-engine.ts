import { DecisionEngineRecommendation } from "@/lib/api";

export type Top10VerificationItem = {
  label: string;
  category: string;
  currentState: "YES" | "NO" | "UNKNOWN" | "LIMITED";
  requestType: "CONFIRM_KNOWN" | "RESOLVE_UNKNOWN" | "CLARIFY_LIMITATION" | "CONFIRM_NEGATIVE";
  prompt: string;
};

export type Top10FacilityVerificationRequest = {
  facilityId: number;
  facilityName: string;
  internalOriginalRank: number;
  subject: string;
  body: string;
  items: Top10VerificationItem[];
  knownItems: Top10VerificationItem[];
  unknownItems: Top10VerificationItem[];
  privacy: {
    rankingSharedWithFacility: false;
    residentIdentityShared: false;
    familyContactShared: false;
  };
};

export type Top10VerificationBatch = {
  createdAt: string;
  candidateCount: number;
  requests: Top10FacilityVerificationRequest[];
};

function promptForItem(label: string, state: Top10VerificationItem["currentState"]): string {
  if (state === "UNKNOWN") return `Please confirm whether you can provide: ${label}.`;
  if (state === "LIMITED") return `Our current information indicates ${label} may be available with limitations. Please confirm the exact limitations and conditions.`;
  if (state === "NO") return `Our current information indicates ${label} is not available. Please confirm whether this remains accurate.`;
  return `Our current information indicates that you provide ${label}. Please confirm that this remains accurate and available for this prospective resident profile.`;
}

function requestTypeForState(state: Top10VerificationItem["currentState"]): Top10VerificationItem["requestType"] {
  if (state === "UNKNOWN") return "RESOLVE_UNKNOWN";
  if (state === "LIMITED") return "CLARIFY_LIMITATION";
  if (state === "NO") return "CONFIRM_NEGATIVE";
  return "CONFIRM_KNOWN";
}

function section(title: string, items: Top10VerificationItem[]): string[] {
  if (items.length === 0) return [];
  return [title, "", ...items.map((item) => `- ${item.prompt}`), ""];
}

export function buildTop10VerificationBatch(recommendations: DecisionEngineRecommendation[]): Top10VerificationBatch {
  const candidates = recommendations.slice(0, 10);
  const requests = candidates.map((recommendation, index): Top10FacilityVerificationRequest => {
    const checklist: Top10VerificationItem[] = [
      ...(recommendation.matched_needs || []).map((item) => ({ label: String(item.parameter_id || item.need_text || "Verified requirement"), category: "MATCH", currentState: "YES" as const, requestType: "CONFIRM_KNOWN" as const, prompt: promptForItem(String(item.parameter_id || item.need_text || "Verified requirement"), "YES") })),
      ...(recommendation.unknown_critical_needs || []).map((item) => ({ label: String(item.parameter_id || item.need_text || "Requirement"), category: "MUST", currentState: "UNKNOWN" as const, requestType: "RESOLVE_UNKNOWN" as const, prompt: promptForItem(String(item.parameter_id || item.need_text || "Requirement"), "UNKNOWN") })),
      ...(recommendation.unmet_verified_needs || []).map((item) => ({ label: String(item.parameter_id || item.need_text || "Requirement"), category: "MUST", currentState: "NO" as const, requestType: "CONFIRM_NEGATIVE" as const, prompt: promptForItem(String(item.parameter_id || item.need_text || "Requirement"), "NO") })),
    ];
    const knownItems=checklist.filter((item)=>item.currentState!=="UNKNOWN");
    const unknownItems=checklist.filter((item)=>item.currentState==="UNKNOWN");
    const body=["Dear Admissions Team","","OOmnik is verifying current information for a prospective resident. No resident identity or family contact information is shared.","",...checklist.map((item)=>"- "+item.prompt),"","Availability in either direction always requires current direct confirmation."].join("\n");
    return {facilityId:Number(recommendation.facility_profile_id || 0),facilityName:recommendation.facility_name,internalOriginalRank:recommendation.rank_position || index+1,subject:`OOmnik verification request — ${recommendation.facility_name}`,body,items:checklist,knownItems,unknownItems,privacy:{rankingSharedWithFacility:false,residentIdentityShared:false,familyContactShared:false}};
  });
  return {createdAt:new Date().toISOString(),candidateCount:candidates.length,requests};
}
