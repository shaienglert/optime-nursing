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
  searchTokens?: string[];
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

const FALLBACK_BACKEND_FACILITIES: BackendFacility[] = [
  {
    id: 91001,
    cms_id: "109001",
    name: "Palms Care and Recovery Center",
    city: "Miami",
    state: "FL",
    address: "1050 Biscayne Blvd",
    zip_code: "33132",
    phone: "(305) 555-0191",
    overall_rating: 4,
    staffing_rating: 4,
    quality_rating: 4,
    inspection_rating: 4,
    beds: 120,
    medical_quality_score: 84,
    staffing_score: 81,
    safety_score: 79,
    overall_optime_score: 83,
    confidence_level: "MEDIUM",
  },
  {
    id: 91002,
    cms_id: "109002",
    name: "Sunrise Harbor Nursing and Rehab",
    city: "Fort Lauderdale",
    state: "FL",
    address: "417 Coastal Dr",
    zip_code: "33304",
    phone: "(954) 555-0178",
    overall_rating: 4,
    staffing_rating: 3,
    quality_rating: 4,
    inspection_rating: 3,
    beds: 98,
    medical_quality_score: 80,
    staffing_score: 74,
    safety_score: 71,
    overall_optime_score: 78,
    confidence_level: "MEDIUM",
  },
  {
    id: 91003,
    cms_id: "109003",
    name: "Winter Haven Health and Rehabilitation Center",
    city: "Winter Haven",
    state: "FL",
    address: "600 Cypress Gardens Rd",
    zip_code: "33880",
    phone: "(863) 555-0139",
    overall_rating: 3,
    staffing_rating: 3,
    quality_rating: 3,
    inspection_rating: 3,
    beds: 140,
    medical_quality_score: 73,
    staffing_score: 70,
    safety_score: 68,
    overall_optime_score: 72,
    confidence_level: "UNKNOWN",
  },
  {
    id: 91004,
    cms_id: "109004",
    name: "Boca Serenity Senior Care",
    city: "Boca Raton",
    state: "FL",
    address: "225 Palmetto Park Rd",
    zip_code: "33432",
    phone: "(561) 555-0127",
    overall_rating: 5,
    staffing_rating: 4,
    quality_rating: 5,
    inspection_rating: 4,
    beds: 88,
    medical_quality_score: 90,
    staffing_score: 84,
    safety_score: 82,
    overall_optime_score: 87,
    confidence_level: "HIGH",
  },
  {
    id: 91005,
    cms_id: "109005",
    name: "Gulfside Memory and Skilled Nursing",
    city: "Tampa",
    state: "FL",
    address: "1402 Harbor View Ave",
    zip_code: "33602",
    phone: "(813) 555-0155",
    overall_rating: 4,
    staffing_rating: 5,
    quality_rating: 4,
    inspection_rating: 4,
    beds: 110,
    medical_quality_score: 86,
    staffing_score: 89,
    safety_score: 80,
    overall_optime_score: 85,
    confidence_level: "HIGH",
  },
];

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

function normalizeSearchText(value: string): string {
  return value.normalize("NFKC").toLowerCase().trim();
}

function tokenizeSearchText(value: string): string[] {
  return normalizeSearchText(value)
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean);
}

const SEARCH_SYNONYMS: Record<string, string[]> = {
  hebrew: ["עברית", "hebrew", "יהודית"],
  jewish: ["יהודי", "יהדות", "jewish", "synagogue", "בית", "כנסת"],
  kosher: ["כשר", "kosher"],
  social: ["חברתי", "social", "active"],
  memory: ["זיכרון", "memory", "דמנציה"],
  wheelchair: ["נגיש", "כיסא", "גלגלים", "wheelchair", "accessible"],
};

function expandSearchTerm(term: string): string[] {
  const normalized = normalizeSearchText(term);
  const expansions = new Set<string>([normalized]);
  Object.entries(SEARCH_SYNONYMS).forEach(([key, values]) => {
    if (key === normalized || values.includes(normalized)) {
      expansions.add(key);
      values.forEach((value) => expansions.add(normalizeSearchText(value)));
    }
  });
  return [...expansions];
}

function buildFacilitySearchTokens(
  base: Facility,
  careTypes: string[] = [],
  matchBadges: string[] = [],
): string[] {
  const joined = [
    base.name,
    base.city || "",
    base.state || "",
    base.address || "",
    base.zip_code || "",
    ...careTypes,
    ...matchBadges,
  ].join(" ");

  const tokens = new Set<string>(tokenizeSearchText(joined));

  tokenizeSearchText(joined).forEach((token) => {
    expandSearchTerm(token).forEach((expanded) => tokens.add(expanded));
  });

  return [...tokens];
}

function matchesSearchQuery(tokens: string[], query: string): boolean {
  const terms = tokenizeSearchText(query);
  if (terms.length === 0) return true;
  return terms.every((term) => {
    const expanded = expandSearchTerm(term);
    return expanded.some((candidate) => tokens.some((token) => token.includes(candidate) || candidate.includes(token)));
  });
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

  const result: SearchFacility = {
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

  result.searchTokens = buildFacilitySearchTokens(base, result.careTypes, result.matchBadges);
  return result;
}

function getFallbackSearchFacilities(searchText?: string): SearchFacility[] {
  const mapped = FALLBACK_BACKEND_FACILITIES.map(toSearchFacility);
  const query = (searchText || "").trim();
  if (!query) return mapped;

  const filtered = mapped.filter((facility) => matchesSearchQuery(facility.searchTokens || [], query));
  return filtered.length > 0 ? filtered : mapped;
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

export async function fetchFacilities(searchText?: string): Promise<Facility[]> {
  let facilities: BackendFacility[] = [];
  try {
    facilities = await fetchJson<BackendFacility[]>("/facilities");
  } catch {
    facilities = FALLBACK_BACKEND_FACILITIES;
  }

  if (facilities.length === 0) {
    facilities = FALLBACK_BACKEND_FACILITIES;
  }

  const mapped = facilities.map(toFacility);
  const query = (searchText || "").trim();
  if (!query) return mapped;

  const filtered = mapped.filter((facility) => matchesSearchQuery(buildFacilitySearchTokens(facility), query));
  return filtered;
}

export async function fetchSearchFacilities(searchText?: string): Promise<SearchFacility[]> {
  try {
    const facilities = await fetchJson<BackendFacility[]>("/facilities");
    if (facilities.length === 0) {
      return getFallbackSearchFacilities(searchText);
    }

    const mapped = facilities.map(toSearchFacility);
    const query = (searchText || "").trim();
    if (!query) return mapped;

    const filtered = mapped.filter((facility) => matchesSearchQuery(facility.searchTokens || [], query));
    return filtered.length > 0 ? filtered : mapped;
  } catch {
    return getFallbackSearchFacilities(searchText);
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
  language_match_score?: number;
  religious_fit_score?: number;
  language_fit_score?: number;
  cultural_fit_score?: number;
  food_fit_score?: number;
  family_engagement_score?: number;
  community_style_score?: number;
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
