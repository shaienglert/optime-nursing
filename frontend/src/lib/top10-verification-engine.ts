import { RankedRecommendation } from "@/lib/optime-v2-engine";

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

export function buildTop10VerificationBatch(recommendations: RankedRecommendation[]): Top10VerificationBatch {
  const candidates = recommendations.slice(0, 10);
  const requests = candidates.map((recommendation, index): Top10FacilityVerificationRequest => {
    const facility = recommendation.facility;
    const payload = recommendation.report.audit.anonymousVerificationPayload;
    const checklist = recommendation.report.audit.verificationChecklist;
    const items: Top10VerificationItem[] = checklist.map((item) => ({
      label: item.label,
      category: item.category,
      currentState: item.state,
      requestType: requestTypeForState(item.state),
      prompt: promptForItem(item.label, item.state),
    }));
    const knownItems = items.filter((item) => item.currentState !== "UNKNOWN");
    const unknownItems = items.filter((item) => item.currentState === "UNKNOWN");

    const profileLines = [
      `Care level needed: ${payload.careLevel}`,
      payload.functionalLimitations.length ? `Functional needs: ${payload.functionalLimitations.join(", ")}` : "",
      payload.medicalNeeds.length ? `Medical/clinical needs: ${payload.medicalNeeds.join(", ")}` : "",
      payload.dietaryRequirements.length ? `Dietary requirements: ${payload.dietaryRequirements.join(", ")}` : "",
      payload.lifestylePreferences.length ? `Lifestyle preferences: ${payload.lifestylePreferences.join(", ")}` : "",
      `Move-in timeframe: ${payload.moveInTimeframe}`,
      `Geographic preference: ${payload.geographicPreference}`,
    ].filter(Boolean);

    const body = [
      "Dear Admissions Team,",
      "",
      "OPTIME is searching for the best possible match for a prospective resident and your community is among the relevant candidates we are evaluating.",
      "",
      "To make the comparison accurate, we would like you to verify both the information we already have and the information that is still missing for this specific resident profile.",
      "",
      "Resident requirements relevant to this verification:",
      "",
      ...profileLines.map((line) => `- ${line}`),
      "",
      ...section("Please confirm the following information currently recorded by OPTIME:", knownItems),
      ...section("Please provide or clarify the following information that OPTIME does not yet have:", unknownItems),
      "For each item, please indicate whether it is available, not available, available with limitations, or requires further discussion. Please include any relevant conditions, availability, waiting-list information, pricing details, or current promotions where applicable.",
      "",
      "Any commercial offer or promotion will be presented separately to the family and does not purchase or guarantee a higher organic ranking in OPTIME.",
      "",
      "The prospective resident's identity, family contact information, and your community's current ranking have not been shared.",
      "",
      "Thank you,",
      "OPTIME",
    ].join("\n");

    return {
      facilityId: facility.id,
      facilityName: facility.name,
      internalOriginalRank: index + 1,
      subject: "OPTIME prospective resident — information verification request",
      body,
      items,
      knownItems,
      unknownItems,
      privacy: {
        rankingSharedWithFacility: false,
        residentIdentityShared: false,
        familyContactShared: false,
      },
    };
  });

  return {
    createdAt: new Date().toISOString(),
    candidateCount: requests.length,
    requests,
  };
}
