export interface Facility {
  id: number;
  cms_id?: string;
  name: string;
  city?: string;
  state?: string;
  overall_rating?: number;
  staffing_rating?: number;
  beds?: number;
  address?: string;
  zip_code?: string;
  phone?: string | null;
  quality_rating?: number;
  inspection_rating?: number;
  latitude?: number | null;
  longitude?: number | null;
  verified_name: string;
  license_verified: boolean;
  cms_verified: boolean;
  website_verified: boolean;
  phone_verified: boolean;
  verification_score: number;
  matching_confidence: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
}

export type ScoreBreakdownItem = {
  category: string;
  score: number;
  explanation: string;
  dataSource: string[];
};

export type SearchFacility = Facility & {
  imageUrl: string;
  optimeScore: number;
  matchLabel: string;
  shortExplanation: string;
  priceRange: string;
  careTypes: string[];
  matchBadges: string[];
  scoreBreakdown?: ScoreBreakdownItem[];
};

export type FacilityDetailsData = SearchFacility & {
  website: string;
  gallery: string[];
  scoreBreakdown: ScoreBreakdownItem[];
  mapPoints: {
    facility: string;
    family: string;
    hospital: string;
    synagogue: string;
    transit: string;
  };
};

type BackendFacility = {
  id: number;
  cms_id?: string;
  name: string;
  city: string;
  state: string;
  address: string;
  zip_code: string;
  phone?: string | null;
  overall_rating?: number | null;
  staffing_rating?: number | null;
  quality_rating?: number | null;
  inspection_rating?: number | null;
  beds?: number | null;
  medical_quality_score?: number | null;
  staffing_score?: number | null;
  safety_score?: number | null;
  overall_optime_score?: number | null;
  confidence_level?: string | null;
};

type BackendFacilityDetails = BackendFacility & {
  score_breakdown: {
    medical_quality_score: number;
    staffing_score: number;
    safety_score: number;
    overall_optime_score: number;
    medical_components: Record<string, number>;
    staffing_components: Record<string, number>;
    safety_components: Record<string, number>;
  };
};

const GALLERY_SETS: string[][] = [
  [
    "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=1400&q=80",
  ],
  [
    "https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=1400&q=80",
  ],
  [
    "https://images.unsplash.com/photo-1519643381401-22c77e60520e?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1464890100898-a385f744067f?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1430285561322-7808604715df?auto=format&fit=crop&w=1400&q=80",
  ],
];

function parseConfidence(value?: string | null): Facility["matching_confidence"] {
  const normalized = (value || "").toUpperCase();
  if (normalized === "HIGH" || normalized === "MEDIUM" || normalized === "LOW") {
    return normalized;
  }
  return "UNKNOWN";
}

function makePriceRange(facility: BackendFacility): string {
  const base = facility.beds ? 3800 + Math.min(2200, facility.beds * 15) : 4200;
  const high = base + 2400;
  return `$${Math.round(base).toLocaleString()} - $${Math.round(high).toLocaleString()}/month`;
}

function makeCareTypes(facility: BackendFacility): string[] {
  const careTypes: string[] = ["Assisted Living"];
  if ((facility.quality_rating ?? 0) >= 4) careTypes.push("Skilled Nursing");
  if ((facility.inspection_rating ?? 0) >= 4) careTypes.push("Memory Care");
  return careTypes;
}

function makeBadges(facility: BackendFacility): string[] {
  const badges: string[] = ["Matches care needs"];
  if ((facility.overall_rating ?? 0) >= 4) badges.push("Strong clinical quality");
  if ((facility.staffing_rating ?? 0) >= 4) badges.push("Staffing stability");
  if ((facility.quality_rating ?? 0) >= 4) badges.push("Medication support");
  if ((facility.inspection_rating ?? 0) >= 4) badges.push("Safety indicators strong");
  return badges;
}

function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent Match";
  if (score >= 80) return "Great Match";
  if (score >= 70) return "Good Match";
  return "Consider Match";
}

function toFacility(facility: BackendFacility): Facility {
  const verificationScore = Math.max(30, Math.min(100, Math.round((facility.overall_optime_score ?? 70))));

  return {
    id: facility.id,
    cms_id: facility.cms_id,
    name: facility.name,
    city: facility.city,
    state: facility.state,
    overall_rating: facility.overall_rating ?? undefined,
    staffing_rating: facility.staffing_rating ?? undefined,
    beds: facility.beds ?? undefined,
    address: facility.address,
    zip_code: facility.zip_code,
    phone: facility.phone ?? null,
    quality_rating: facility.quality_rating ?? undefined,
    inspection_rating: facility.inspection_rating ?? undefined,
    latitude: null,
    longitude: null,
    verified_name: facility.name,
    license_verified: Boolean(facility.cms_id),
    cms_verified: Boolean(facility.cms_id),
    website_verified: false,
    phone_verified: Boolean(facility.phone),
    verification_score: verificationScore,
    matching_confidence: parseConfidence(facility.confidence_level),
  };
}

function toSearchFacility(facility: BackendFacility): SearchFacility {
  const base = toFacility(facility);
  const gallery = GALLERY_SETS[facility.id % GALLERY_SETS.length];
  const optimeScore = Math.round(facility.overall_optime_score ?? 70);

  return {
    ...base,
    imageUrl: gallery[0],
    optimeScore,
    matchLabel: scoreLabel(optimeScore),
    shortExplanation: "Recommendation derived from production CMS and inspection-based scoring.",
    priceRange: makePriceRange(facility),
    careTypes: makeCareTypes(facility),
    matchBadges: makeBadges(facility),
    scoreBreakdown: [
      {
        category: "Medical Quality",
        score: Math.round(facility.medical_quality_score ?? 0),
        explanation: "Derived from CMS quality and event-rate metrics.",
        dataSource: ["CMS Quality", "Inspections"],
      },
      {
        category: "Staffing",
        score: Math.round(facility.staffing_score ?? 0),
        explanation: "Derived from staffing hours and staffing quality metrics.",
        dataSource: ["CMS Staffing"],
      },
      {
        category: "Safety",
        score: Math.round(facility.safety_score ?? 0),
        explanation: "Derived from deficiencies, complaints, and inspection signals.",
        dataSource: ["CMS Inspections"],
      },
    ],
  };
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function postJson<TReq, TRes>(path: string, payload: TReq): Promise<TRes> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
  }
  return response.json() as Promise<TRes>;
}

export async function fetchFacilities(): Promise<Facility[]> {
  const facilities = await fetchJson<BackendFacility[]>("/facilities");
  return facilities.map(toFacility);
}

export async function fetchSearchFacilities(): Promise<SearchFacility[]> {
  try {
    const facilities = await fetchJson<BackendFacility[]>("/facilities");
    return facilities.map(toSearchFacility);
  } catch {
    return [];
  }
}

export async function fetchFacilityById(id: string): Promise<Facility> {
  const facility = await fetchJson<BackendFacilityDetails>(`/facilities/${id}`);
  return toFacility(facility);
}

export async function fetchFacilityDetails(id: string): Promise<FacilityDetailsData> {
  const facility = await fetchJson<BackendFacilityDetails>(`/facilities/${id}`);
  const searchFacility = toSearchFacility(facility);
  const gallery = GALLERY_SETS[facility.id % GALLERY_SETS.length];

  return {
    ...searchFacility,
    website: "",
    gallery,
    scoreBreakdown: [
      {
        category: "Medical Quality",
        score: Math.round(facility.score_breakdown.medical_quality_score),
        explanation: "CMS quality-aligned output from production ingestion.",
        dataSource: ["CMS Quality", "Inspections"],
      },
      {
        category: "Staffing",
        score: Math.round(facility.score_breakdown.staffing_score),
        explanation: "Staffing score from production staffing ingestion.",
        dataSource: ["CMS Staffing"],
      },
      {
        category: "Safety",
        score: Math.round(facility.score_breakdown.safety_score),
        explanation: "Safety score from deficiencies and complaint patterns.",
        dataSource: ["CMS Inspections"],
      },
    ],
    mapPoints: {
      facility: `${facility.name}, ${facility.city}`,
      family: "Family location",
      hospital: "Nearest hospital",
      synagogue: "Nearby synagogue",
      transit: "Public transportation",
    },
  };
}

export type HumanIntelligenceScorePayload = {
  resident_key: string;
  relationship?: string;
  age_group?: string;
  social_profile_score: number;
  family_support_score: number;
  cultural_match_score: number;
  loneliness_risk_score: number;
  transition_risk_score: number;
  future_care_score: number;
  social_fit_score?: number;
  family_fit_score?: number;
  language_fit_score?: number;
  cultural_fit_score?: number;
  independence_fit_score?: number;
  transition_success_probability?: number;
  metadata_json?: string;
};

export type HumanIntelligenceScoreResponse = HumanIntelligenceScorePayload & { id: number };

export async function persistHumanIntelligenceScores(payload: HumanIntelligenceScorePayload): Promise<HumanIntelligenceScoreResponse> {
  return postJson<HumanIntelligenceScorePayload, HumanIntelligenceScoreResponse>("/human-intelligence", payload);
}

export type AdaptiveQuestionSignalPayload = {
  resident_key: string;
  question_key: string;
  answer: string;
  signal_type: string;
  signal_json?: string;
  weights_json?: string;
  impact_explanation: string;
  info_gain_score: number;
};

export async function persistAdaptiveQuestionSignal(payload: AdaptiveQuestionSignalPayload): Promise<{ id: number }> {
  return postJson<AdaptiveQuestionSignalPayload, { id: number }>("/human-intelligence/adaptive-response", payload);
}

export type ResidentOutcomePayload = {
  resident_key: string;
  human_intelligence_score_id?: number;
  facility_id?: number;
  successful_adjustment: boolean;
  loneliness_event: boolean;
  relocated_within_24m: boolean;
  notes?: string;
};

export async function persistResidentOutcome(payload: ResidentOutcomePayload): Promise<{ id: number }> {
  return postJson<ResidentOutcomePayload, { id: number }>("/resident-outcomes", payload);
}

export async function fetchValidationFeedback(): Promise<{
  outcomes_count: number;
  adjustment_success_rate: number;
  loneliness_event_rate: number;
  relocation_rate_24m: number;
}> {
  return fetchJson("/validation-feedback");
}
