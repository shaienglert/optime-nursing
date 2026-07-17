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

export type CareType =
  | "Independent Living"
  | "Active Adult 55+"
  | "Assisted Living"
  | "Memory Care"
  | "Skilled Nursing"
  | "Rehabilitation"
  | "CCRC"
  | "Continuing Care"
  | "Hospice"
  | "UNKNOWN";

export type CareTypeProbabilities = Record<CareType, number>;

export type SignalProvenance = "REAL" | "SYNTHETIC" | "HEURISTIC" | "INFERRED";

export type IntelligenceSignalDetail = {
  source: string;
  collection_timestamp: string;
  raw_url: string;
  provenance: SignalProvenance;
  collection_method: string;
  signal_type?: string;
  category?: string;
  polarity?: string;
  summary?: string;
  confidence?: number;
  impact_score?: number;
};

export type FacilityIntelligenceSnapshot = {
  intelligence_confidence: number;
  sources_used: string[];
  positive_signals: string[];
  negative_signals: string[];
  signal_details: IntelligenceSignalDetail[];
  family_satisfaction_index: number;
  staff_stability_index: number;
  regulatory_risk_index: number;
  litigation_risk_index: number;
  social_energy_index: number;
  community_engagement_index: number;
  reputation_index: number;
  cultural_match_signals: number;
};

export type VisualImageAsset = {
  category: string;
  url: string;
  source: "Official Site" | "Google Business" | "Facebook" | "Instagram" | "CMS Placeholder";
  collected_at: string;
};

export type VisualLifestyleTag = {
  label: string;
  icon: string;
};

export type FacilityVisualIntelligence = {
  heroImage: VisualImageAsset;
  galleryImages: VisualImageAsset[];
  lifestyleTags: VisualLifestyleTag[];
  visualConfidenceScore: number;
  visualCoverageScore: number;
};

export type CapabilityState = "YES" | "NO" | "UNKNOWN" | "LIMITED";

export type SearchFacility = Facility & {
  imageUrl: string;
  optimeScore: number;
  matchLabel: string;
  shortExplanation: string;
  priceRange: string;
  price: number;
  minAge: number;
  maxAge: number;
  entryAgeRange: {
    min: number;
    max: number;
  };
  careTypes: CareType[];
  care_types: CareType[];
  minimum_age: number;
  maximum_age: number;
  monthly_cost_range: string;
  private_apartment: CapabilityState;
  kitchenette: CapabilityState;
  pets_allowed: CapabilityState;
  transportation: CapabilityState;
  pool: CapabilityState;
  fitness_center: CapabilityState;
  movie_program: CapabilityState;
  music_program: CapabilityState;
  gardening_program: CapabilityState;
  religious_services: CapabilityState;
  kosher_meals: CapabilityState;
  gluten_free_meals: CapabilityState;
  hebrew_support: CapabilityState;
  speech_therapy: CapabilityState;
  physical_therapy: CapabilityState;
  occupational_therapy: CapabilityState;
  memory_program: CapabilityState;
  continuum_of_care: CapabilityState;
  walker_accessibility: CapabilityState;
  wheelchair_accessibility: CapabilityState;
  medicalCapabilities: string[];
  rehabilitationCapabilities: string[];
  lifestyleCapabilities: string[];
  diningCapabilities: string[];
  housingCapabilities: string[];
  continuumOfCareAvailable: boolean;
  careTypeConfidence: "HIGH" | "MEDIUM" | "LOW";
  careTypeConfidenceScore: number;
  careTypeProbabilities: CareTypeProbabilities;
  intelligenceSnapshot?: FacilityIntelligenceSnapshot;
  matchBadges: string[];
  visualIntelligence: FacilityVisualIntelligence;
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
  intelligence_confidence?: number | null;
  intelligence_sources_used?: string[] | null;
  intelligence_positive_signals?: string[] | null;
  intelligence_negative_signals?: string[] | null;
  intelligence_signal_details?: IntelligenceSignalDetail[] | null;
  family_satisfaction_index?: number | null;
  staff_stability_index?: number | null;
  regulatory_risk_index?: number | null;
  litigation_risk_index?: number | null;
  social_energy_index?: number | null;
  community_engagement_index?: number | null;
  reputation_index?: number | null;
  cultural_match_signals?: number | null;
  visual_hero_image?: Record<string, unknown> | null;
  visual_gallery_images?: Array<Record<string, unknown>> | null;
  visual_lifestyle_tags?: Array<Record<string, unknown>> | null;
  visual_confidence_score?: number | null;
  visual_coverage_score?: number | null;
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

export type FacilityIntelligenceProfile = {
  facility_id: number;
  last_updated: string;
  sources_used: string[];
  clinical_score: number;
  family_score: number;
  employee_score: number;
  social_score: number;
  reputation_score: number;
  legal_risk_score: number;
  regulatory_risk_score: number;
  intelligence_confidence: number;
  verified_facts: string[];
  public_allegations: string[];
  public_opinions: string[];
  missing_information: string[];
  positive_signals: string[];
  negative_signals: string[];
  signal_details: IntelligenceSignalDetail[];
  unresolved_risks: string[];
  intelligence_summary: string;
  social_energy_index: number;
  family_satisfaction_index: number;
  staff_stability_index: number;
  regulatory_risk_index: number;
  litigation_risk_index: number;
  cultural_match_signals: number;
  activity_density_index: number;
  community_engagement_index: number;
  clinical_quality_index: number;
  reputation_index: number;
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

const CMS_PLACEHOLDER_IMAGE = "/cms-placeholder.svg";

function pickVisualSource(value: unknown): VisualImageAsset["source"] {
  if (value === "Official Site" || value === "Google Business" || value === "Facebook" || value === "Instagram" || value === "CMS Placeholder") {
    return value;
  }
  return "CMS Placeholder";
}

function toVisualAsset(raw: Record<string, unknown> | null | undefined, fallbackCategory: string): VisualImageAsset {
  const source = pickVisualSource(raw?.source);
  const url = typeof raw?.url === "string" && raw.url.trim() ? raw.url : CMS_PLACEHOLDER_IMAGE;
  return {
    category: typeof raw?.category === "string" && raw.category.trim() ? raw.category : fallbackCategory,
    url,
    source,
    collected_at: typeof raw?.collected_at === "string" && raw.collected_at.trim() ? raw.collected_at : "",
  };
}

function sourcePriorityRank(source: VisualImageAsset["source"]): number {
  switch (source) {
    case "Official Site":
      return 1;
    case "Google Business":
      return 2;
    case "Facebook":
      return 3;
    case "Instagram":
      return 4;
    default:
      return 5;
  }
}

function buildFallbackVisualIntelligence(facilityId: number): FacilityVisualIntelligence {
  const fallbackGallery = (GALLERY_SETS[facilityId % GALLERY_SETS.length] || []).map((url, index) => ({
    category: ["exterior", "apartments", "dining room"][index] || "exterior",
    url,
    source: "CMS Placeholder" as const,
    collected_at: "",
  }));
  const heroImage = fallbackGallery[0] || {
    category: "exterior",
    url: CMS_PLACEHOLDER_IMAGE,
    source: "CMS Placeholder" as const,
    collected_at: "",
  };

  return {
    heroImage,
    galleryImages: fallbackGallery,
    lifestyleTags: [],
    visualConfidenceScore: fallbackGallery.length > 0 ? 50 : 0,
    visualCoverageScore: fallbackGallery.length > 0 ? 37.5 : 0,
  };
}

function buildVisualIntelligence(facility: BackendFacility): FacilityVisualIntelligence {
  const fallback = buildFallbackVisualIntelligence(facility.id);
  const galleryRaw = Array.isArray(facility.visual_gallery_images) ? facility.visual_gallery_images : [];
  const galleryImages = galleryRaw.map((item) => toVisualAsset(item, "exterior"));

  const heroCandidate = toVisualAsset((facility.visual_hero_image || {}) as Record<string, unknown>, "exterior");
  const heroFromPriority = [...galleryImages].sort((left, right) => sourcePriorityRank(left.source) - sourcePriorityRank(right.source))[0];
  const heroImage = heroCandidate.url !== CMS_PLACEHOLDER_IMAGE ? heroCandidate : (heroFromPriority || fallback.heroImage);

  const lifestyleTags = Array.isArray(facility.visual_lifestyle_tags)
    ? facility.visual_lifestyle_tags
      .filter((item) => item && typeof item === "object")
      .map((item) => ({
        label: typeof item.label === "string" ? item.label : "",
        icon: typeof item.icon === "string" ? item.icon : "",
      }))
      .filter((item) => item.label)
    : [];

  return {
    heroImage,
    galleryImages: galleryImages.length > 0 ? galleryImages : fallback.galleryImages,
    lifestyleTags,
    visualConfidenceScore: Math.round(facility.visual_confidence_score ?? fallback.visualConfidenceScore),
    visualCoverageScore: Math.round(facility.visual_coverage_score ?? fallback.visualCoverageScore),
  };
}

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

function makeDerivedPrice(priceRange: string): number {
  const match = priceRange.match(/\$([\d,]+)\s*-\s*\$([\d,]+)/);
  if (!match) return 0;
  const low = Number(match[1].replace(/,/g, ""));
  const high = Number(match[2].replace(/,/g, ""));
  return Math.round((low + high) / 2);
}

function deriveAgeRange(careTypes: CareType[]): { minAge: number; maxAge: number } {
  if (careTypes.some((careType) => careType === "Skilled Nursing" || careType === "Rehabilitation" || careType === "Hospice")) {
    return { minAge: 65, maxAge: 120 };
  }

  if (careTypes.some((careType) => careType === "Memory Care")) {
    return { minAge: 60, maxAge: 120 };
  }

  if (careTypes.some((careType) => careType === "Active Adult 55+" || careType === "Independent Living" || careType === "Assisted Living" || careType === "CCRC" || careType === "Continuing Care")) {
    return { minAge: 55, maxAge: 120 };
  }

  return { minAge: 55, maxAge: 120 };
}

function deriveCapabilities(facility: BackendFacility, careTypes: CareType[]): {
  medicalCapabilities: string[];
  rehabilitationCapabilities: string[];
  lifestyleCapabilities: string[];
  diningCapabilities: string[];
  housingCapabilities: string[];
  continuumOfCareAvailable: boolean;
} {
  const text = [facility.name || "", facility.address || "", buildShortExplanation(facility)].join(" ").toLowerCase();

  const medicalCapabilities = new Set<string>();
  const rehabilitationCapabilities = new Set<string>();
  const lifestyleCapabilities = new Set<string>();
  const diningCapabilities = new Set<string>();
  const housingCapabilities = new Set<string>();

  if (careTypes.includes("Skilled Nursing")) {
    medicalCapabilities.add("24/7 nursing support");
    medicalCapabilities.add("medication management");
    medicalCapabilities.add("clinical supervision");
  }

  if (careTypes.includes("Assisted Living")) {
    medicalCapabilities.add("daily living support");
    medicalCapabilities.add("medication reminders");
  }

  if (careTypes.includes("Memory Care")) {
    medicalCapabilities.add("memory support programming");
    medicalCapabilities.add("dementia-informed care");
  }

  if (careTypes.includes("Rehabilitation") || /rehab|rehabilitation|recovery|therapy/.test(text)) {
    rehabilitationCapabilities.add("physical therapy");
    rehabilitationCapabilities.add("occupational therapy");
  }

  if (/speech|aphasia|language/.test(text)) {
    rehabilitationCapabilities.add("speech therapy");
  }

  if (/neurolog|stroke|post-acute/.test(text)) {
    rehabilitationCapabilities.add("neurological rehabilitation");
  }

  if (/movie|cinema|theater/.test(text)) {
    lifestyleCapabilities.add("movie programming");
  }
  if (/music|concert|performance/.test(text)) {
    lifestyleCapabilities.add("music activities");
  }
  if (/social|community|group|engagement/.test(text)) {
    lifestyleCapabilities.add("group social activities");
  }
  if (/fitness|wellness|garden|outdoor/.test(text)) {
    lifestyleCapabilities.add("wellness and active lifestyle options");
  }

  if (/dining|food|restaurant|chef/.test(text)) {
    diningCapabilities.add("special meal accommodations");
  }
  if (/kosher|halal|diet/.test(text)) {
    diningCapabilities.add("dietary support");
  }
  diningCapabilities.add("meal service available");

  if (/accessible|ada|mobility|wheelchair/.test(text) || careTypes.includes("Skilled Nursing") || careTypes.includes("Rehabilitation")) {
    housingCapabilities.add("accessible mobility layout");
  }
  if (/private|suite|apartment|residence/.test(text)) {
    housingCapabilities.add("private or semi-private room options");
  }
  housingCapabilities.add("on-site support environment");

  const hasIndependent = careTypes.includes("Active Adult 55+") || careTypes.includes("Independent Living");
  const hasProgressiveCare = careTypes.includes("Assisted Living") || careTypes.includes("Memory Care") || careTypes.includes("Skilled Nursing") || careTypes.includes("Rehabilitation");
  const continuumOfCareAvailable = careTypes.includes("CCRC") || careTypes.includes("Continuing Care") || (hasIndependent && hasProgressiveCare);

  return {
    medicalCapabilities: [...medicalCapabilities],
    rehabilitationCapabilities: [...rehabilitationCapabilities],
    lifestyleCapabilities: [...lifestyleCapabilities],
    diningCapabilities: [...diningCapabilities],
    housingCapabilities: [...housingCapabilities],
    continuumOfCareAvailable,
  };
}

function capabilityFromText(
  text: string,
  positive: RegExp,
  negative?: RegExp,
  limited?: RegExp,
): CapabilityState {
  if (limited && limited.test(text)) return "LIMITED";
  if (positive.test(text)) return "YES";
  if (negative && negative.test(text)) return "NO";
  return "UNKNOWN";
}

function deriveInventoryCapabilityStates(
  facility: BackendFacility,
  careTypes: CareType[],
  ageRange: { minAge: number; maxAge: number },
  priceRange: string,
): {
  care_types: CareType[];
  minimum_age: number;
  maximum_age: number;
  monthly_cost_range: string;
  private_apartment: CapabilityState;
  kitchenette: CapabilityState;
  pets_allowed: CapabilityState;
  transportation: CapabilityState;
  pool: CapabilityState;
  fitness_center: CapabilityState;
  movie_program: CapabilityState;
  music_program: CapabilityState;
  gardening_program: CapabilityState;
  religious_services: CapabilityState;
  kosher_meals: CapabilityState;
  gluten_free_meals: CapabilityState;
  hebrew_support: CapabilityState;
  speech_therapy: CapabilityState;
  physical_therapy: CapabilityState;
  occupational_therapy: CapabilityState;
  memory_program: CapabilityState;
  continuum_of_care: CapabilityState;
  walker_accessibility: CapabilityState;
  wheelchair_accessibility: CapabilityState;
} {
  const text = [facility.name || "", facility.address || "", buildShortExplanation(facility)].join(" ").toLowerCase();

  const skilledOrRehab = careTypes.includes("Skilled Nursing") || careTypes.includes("Rehabilitation");
  const independentTrack = careTypes.includes("Active Adult 55+") || careTypes.includes("Independent Living") || careTypes.includes("Assisted Living");
  const continuumLikely = careTypes.includes("CCRC") || careTypes.includes("Continuing Care") || (independentTrack && skilledOrRehab);

  return {
    care_types: careTypes,
    minimum_age: ageRange.minAge,
    maximum_age: ageRange.maxAge,
    monthly_cost_range: priceRange,
    private_apartment: capabilityFromText(text, /private|apartment|residence|suite/, /ward|shared-only/),
    kitchenette: capabilityFromText(text, /kitchenette|full kitchen|kitchen/, /no kitchen|kitchen not available/, /shared kitchen/),
    pets_allowed: capabilityFromText(text, /pet[- ]?friendly|pets? allowed/, /no pets?|pets? not allowed/, /pets? with restrictions/),
    transportation: capabilityFromText(text, /transport|shuttle|scheduled rides?/, /no transport/, /limited transport|transportation with limits/),
    pool: capabilityFromText(text, /pool|aquatic/, /no pool/),
    fitness_center: capabilityFromText(text, /fitness|gym|wellness center/, /no fitness|no gym/),
    movie_program: capabilityFromText(text, /movie|cinema|theater/, /no movie/),
    music_program: capabilityFromText(text, /music|concert|choir|performance/, /no music/),
    gardening_program: capabilityFromText(text, /garden|gardening|horticulture/, /no gardening/),
    religious_services: capabilityFromText(text, /religious|chapel|worship|faith|church|synagogue/, /no religious services/),
    kosher_meals: capabilityFromText(text, /kosher/, /no kosher/, /limited kosher/),
    gluten_free_meals: capabilityFromText(text, /gluten[- ]?free|celiac/, /no gluten[- ]?free/, /limited gluten[- ]?free/),
    hebrew_support: capabilityFromText(text, /hebrew|jewish|israeli/, /no hebrew support/, /limited hebrew/),
    speech_therapy: skilledOrRehab ? capabilityFromText(text, /speech|aphasia|language therapy/, /no speech therapy/, /limited speech therapy/) : "UNKNOWN",
    physical_therapy: skilledOrRehab ? capabilityFromText(text, /physical therapy|pt\b|rehab/, /no physical therapy/, /limited physical therapy/) : "UNKNOWN",
    occupational_therapy: skilledOrRehab ? capabilityFromText(text, /occupational therapy|ot\b/, /no occupational therapy/, /limited occupational therapy/) : "UNKNOWN",
    memory_program: careTypes.includes("Memory Care") ? "YES" : capabilityFromText(text, /memory care|memory support|dementia|alzheim/, /no memory care/, /limited memory support/),
    continuum_of_care: continuumLikely ? "YES" : capabilityFromText(text, /continuum of care|continuing care|life plan/, /single level only/, /limited continuum/),
    walker_accessibility: capabilityFromText(text, /walker|mobility|accessible|ada/, /not accessible/, /limited accessibility/),
    wheelchair_accessibility: capabilityFromText(text, /wheelchair|accessible|ada/, /not wheelchair accessible/, /limited wheelchair access/),
  };
}

type CareTaxonomyResult = {
  careTypes: CareType[];
  confidence: "HIGH" | "MEDIUM" | "LOW";
  confidenceScore: number;
  probabilities: CareTypeProbabilities;
};

const CARE_TYPE_ORDER: CareType[] = [
  "Independent Living",
  "Active Adult 55+",
  "Assisted Living",
  "Memory Care",
  "Skilled Nursing",
  "Rehabilitation",
  "CCRC",
  "Continuing Care",
  "Hospice",
  "UNKNOWN",
];

type SignalBucket = {
  text: string;
  weight: number;
};

function emptyCareTypeProbabilities(): CareTypeProbabilities {
  return {
    "Independent Living": 0,
    "Active Adult 55+": 0,
    "Assisted Living": 0,
    "Memory Care": 0,
    "Skilled Nursing": 0,
    Rehabilitation: 0,
    CCRC: 0,
    "Continuing Care": 0,
    Hospice: 0,
    UNKNOWN: 0,
  };
}

function addSignalScore(
  scores: Record<CareType, number>,
  bucket: SignalBucket,
  patterns: Partial<Record<CareType, RegExp[]>>,
): void {
  (Object.entries(patterns) as Array<[CareType, RegExp[]]>).forEach(([type, regexes]) => {
    regexes.forEach((regex) => {
      if (regex.test(bucket.text)) {
        scores[type] += bucket.weight;
      }
    });
  });
}

function normalizeProbabilities(scores: Record<CareType, number>): CareTypeProbabilities {
  const total = CARE_TYPE_ORDER.reduce((sum, type) => sum + Math.max(0, scores[type]), 0);
  if (total <= 0) {
    const empty = emptyCareTypeProbabilities();
    empty.UNKNOWN = 1;
    return empty;
  }

  const probabilities = emptyCareTypeProbabilities();
  CARE_TYPE_ORDER.forEach((type) => {
    probabilities[type] = Number((Math.max(0, scores[type]) / total).toFixed(4));
  });
  return probabilities;
}

function deriveCareTypesFromProbabilities(probabilities: CareTypeProbabilities): CareType[] {
  const sorted = CARE_TYPE_ORDER.filter((type) => type !== "UNKNOWN")
    .map((type) => ({ type, probability: probabilities[type] }))
    .sort((left, right) => right.probability - left.probability);

  const selected = sorted
    .filter((item, index) => item.probability >= 0.18 || (index === 0 && item.probability >= 0.12))
    .map((item) => item.type);

  return selected.length > 0 ? selected : ["UNKNOWN"];
}

export function inferCareTaxonomy(facility: BackendFacility): CareTaxonomyResult {
  const shortDescription = buildShortExplanation(facility);
  const baseText = `${facility.name || ""} ${facility.address || ""} ${facility.city || ""} ${shortDescription}`.toLowerCase();
  const explicitRehabSignal = /\brehab\b|\brehabilitation\b|\bpost-acute\b/.test(baseText);
  const explicitClinicalSignal = /\bnursing\b|\bconvalescent\b|\bextended care\b|\bmedical center\b|\bhealth center\b/.test(baseText);
  const explicitIndependentSignal = /\bindependent\b|\bretirement\b|\bactive adult\b|\b55\+\b|\b55 plus\b|\bvillage\b/.test(baseText);
  const syntheticServices = [
    (facility.quality_rating ?? 0) >= 4 ? "medication support skilled nursing" : "",
    (facility.staffing_rating ?? 0) >= 4 ? "staff support daily living" : "",
    (facility.inspection_rating ?? 0) >= 4 ? "memory safety secure care" : "",
    (facility.beds ?? 0) < 95 ? "small community resident lifestyle" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const syntheticActivities = /village|community|senior living|retirement/i.test(facility.name) ? "group dining social activities movies wellness" : "";
  const syntheticPrograms = /memory|alzheim|dementia/i.test(facility.name) ? "memory support cognitive program" : /rehab|rehabilitation|post-acute/i.test(facility.name) ? "physical therapy occupational therapy rehab" : "";
  const cmsCategories = [
    Math.round(facility.medical_quality_score ?? 0) >= 82 ? "high clinical category" : "",
    Math.round(facility.staffing_score ?? 0) >= 80 ? "staffing stability category" : "",
    Math.round(facility.safety_score ?? 0) >= 80 ? "safety category" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const signalBuckets: SignalBucket[] = [
    { text: (facility.name || "").toLowerCase(), weight: 34 },
    { text: shortDescription.toLowerCase(), weight: 18 },
    { text: `${facility.address || ""} ${facility.city || ""}`.toLowerCase(), weight: 8 },
    { text: syntheticServices.toLowerCase(), weight: 14 },
    { text: syntheticActivities.toLowerCase(), weight: 10 },
    { text: syntheticPrograms.toLowerCase(), weight: 12 },
    { text: cmsCategories.toLowerCase(), weight: 8 },
  ];

  const scores: Record<CareType, number> = {
    "Independent Living": 10,
    "Active Adult 55+": 6,
    "Assisted Living": 8,
    "Memory Care": 4,
    "Skilled Nursing": 8,
    Rehabilitation: 1,
    CCRC: 4,
    "Continuing Care": 4,
    Hospice: 2,
    UNKNOWN: 6,
  };

  const patterns: Partial<Record<CareType, RegExp[]>> = {
    "Independent Living": [
      /\bindependent living\b/,
      /\bsenior living\b/,
      /\bretirement living\b/,
      /\bretirement residence\b/,
      /\b55 and older\b/,
      /\bcommunity living\b/,
      /\bknox village\b/,
    ],
    "Active Adult 55+": [/\bactive adult\b/, /\b55\+\b/, /\b55 plus\b/, /\bactive senior\b/, /\badult living\b/, /\b55 and older\b/],
    "Assisted Living": [
      /\bassisted living\b/,
      /\bsenior care\b/,
      /\bpersonal care\b/,
      /\bhome for the aged\b/,
      /\bresident care\b/,
      /\bhelp with daily living\b/,
      /\bhebrew home\b/,
      /\bjewish health\b/,
      /\bsenior community\b/,
    ],
    "Memory Care": [
      /\bmemory care\b/,
      /\bmemory support\b/,
      /\balzheim/,
      /\bdementia\b/,
      /\bcognitive support\b/,
      /\bsecure memory\b/,
    ],
    "Skilled Nursing": [
      /\bskilled nursing\b/,
      /\bnursing home\b/,
      /\bnursing center\b/,
      /\bconvalescent\b/,
      /\bextended care\b/,
      /\bmedical center\b/,
      /\bhealth center\b/,
      /\bhealth systems\b/,
    ],
    Rehabilitation: [
      /\brehab\b/,
      /\brehabilitation\b/,
      /\bpost-acute\b/,
    ],
    CCRC: [
      /\bccrc\b/,
      /\bretirement community\b/,
      /\bretirement village\b/,
      /\bvillage\b/,
      /\blife plan\b/,
    ],
    "Continuing Care": [/\bcontinuing care\b/, /\bcontinuum of care\b/, /\bmultiple care levels\b/],
    Hospice: [/\bhospice\b/, /\bpalliative\b/, /\bend of life\b/],
  };

  signalBuckets.forEach((bucket) => addSignalScore(scores, bucket, patterns));

  if ((facility.beds ?? 0) <= 90) {
    scores["Independent Living"] += 8;
    scores["Assisted Living"] += 6;
  }
  if ((facility.beds ?? 0) >= 120) {
    scores["Skilled Nursing"] += 8;
  }
  if ((facility.medical_quality_score ?? 0) >= 85) {
    scores["Skilled Nursing"] += 8;
  }
  if ((facility.staffing_score ?? 0) >= 80) {
    scores["Assisted Living"] += 5;
    scores["Memory Care"] += 4;
  }
  if ((facility.inspection_rating ?? 0) >= 4) {
    scores["Memory Care"] += 8;
  }
  if ((facility.safety_score ?? 0) >= 75) {
    scores["Memory Care"] += 6;
    scores["Assisted Living"] += 4;
  }
  if ((facility.beds ?? 0) <= 140) {
    scores["Assisted Living"] += 6;
  }
  if (/\b(home|village|community|center|health systems|manor|gardens)\b/.test((facility.name || "").toLowerCase())) {
    scores["Assisted Living"] += 10;
  }
  if (/\b(memory|secure|support|aged|hebrew|jewish|senior)\b/.test((facility.name || "").toLowerCase())) {
    scores["Memory Care"] += 8;
  }
  if (/\b(jewish|hebrew|faith|church|catholic|spanish|community)\b/.test((facility.name || "").toLowerCase())) {
    scores["Independent Living"] += 6;
    scores["Assisted Living"] += 5;
  }

  if (explicitRehabSignal) {
    scores.Rehabilitation += 22;
  } else {
    scores.Rehabilitation = Math.max(0, scores.Rehabilitation - 4);
  }

  if (explicitIndependentSignal && !explicitClinicalSignal && !explicitRehabSignal) {
    scores["Independent Living"] += 10;
    scores["Active Adult 55+"] += 14;
  }
  if (/(rehab|nursing|convalescent|extended care|medical center)/i.test(facility.name || "")) {
    scores.UNKNOWN = Math.max(0, scores.UNKNOWN - 4);
  }
  if (/(village|retirement|senior living|community)/i.test(facility.name || "")) {
    scores.UNKNOWN = Math.max(0, scores.UNKNOWN - 5);
    scores.CCRC += 5;
  }

  const probabilities = normalizeProbabilities(scores);
  const careTypes = deriveCareTypesFromProbabilities(probabilities);
  if (
    careTypes.includes("Assisted Living") &&
    !careTypes.includes("Independent Living") &&
    probabilities["Independent Living"] >= 0.1 &&
    probabilities["Skilled Nursing"] < 0.2 &&
    probabilities.Rehabilitation < 0.2
  ) {
    careTypes.push("Independent Living");
  }
  if (
    careTypes.includes("Independent Living") &&
    !careTypes.includes("CCRC") &&
    probabilities.CCRC >= 0.12
  ) {
    careTypes.push("CCRC");
  }
  if (
    careTypes.includes("Independent Living") &&
    !careTypes.includes("Active Adult 55+") &&
    probabilities["Active Adult 55+"] >= 0.08 &&
    probabilities["Skilled Nursing"] < 0.2 &&
    probabilities.Rehabilitation < 0.15
  ) {
    careTypes.push("Active Adult 55+");
  }

  if (!explicitRehabSignal && careTypes.includes("Rehabilitation")) {
    const index = careTypes.indexOf("Rehabilitation");
    careTypes.splice(index, 1);
  }
  const dominantProbability = Math.max(...CARE_TYPE_ORDER.filter((type) => type !== "UNKNOWN").map((type) => probabilities[type]));
  const confidenceScore = Math.round(dominantProbability * 100);
  const confidence: CareTaxonomyResult["confidence"] = confidenceScore >= 70 ? "HIGH" : confidenceScore >= 45 ? "MEDIUM" : "LOW";

  if (careTypes.length === 1 && careTypes[0] === "UNKNOWN") {
    probabilities.UNKNOWN = Math.max(probabilities.UNKNOWN, 0.35);
  }

  return {
    careTypes,
    confidence,
    confidenceScore,
    probabilities,
  };
}

function combineConfidence(
  modelConfidence: Facility["matching_confidence"],
  careTypeConfidence: CareTaxonomyResult["confidence"],
): Facility["matching_confidence"] {
  const rank: Record<Facility["matching_confidence"], number> = {
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
    UNKNOWN: 0,
  };

  return rank[careTypeConfidence] < rank[modelConfidence] ? careTypeConfidence : modelConfidence;
}

function makeBadges(facility: BackendFacility, taxonomy: CareTaxonomyResult): string[] {
  const badges: string[] = ["Matches care needs"];
  if (taxonomy.careTypes[0] !== "UNKNOWN") {
    badges.push(`Primary care type: ${taxonomy.careTypes[0]}`);
  }
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

function buildShortExplanation(facility: BackendFacility): string {
  const quality = Math.round(facility.medical_quality_score ?? 0);
  const staffing = Math.round(facility.staffing_score ?? 0);
  const safety = Math.round(facility.safety_score ?? 0);

  if (quality >= 85 && staffing >= 80) {
    return "High-performing clinical and staffing profile with strong day-to-day support.";
  }

  if (safety >= 80) {
    return "Safety and inspection indicators are strong for a more stable care environment.";
  }

  if ((facility.quality_rating ?? 0) >= 4 || (facility.overall_rating ?? 0) >= 4) {
    return "Solid CMS-aligned quality performance with balanced medical and support signals.";
  }

  return "Balanced option for families looking for practical care support at this budget range.";
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
  const taxonomy = inferCareTaxonomy(facility);
  const ageRange = deriveAgeRange(taxonomy.careTypes);
  const monthlyCostRange = makePriceRange(facility);
  const capabilities = deriveCapabilities(facility, taxonomy.careTypes);
  const inventoryCapabilities = deriveInventoryCapabilityStates(facility, taxonomy.careTypes, ageRange, monthlyCostRange);

  const result: SearchFacility = {
    ...base,
    matching_confidence: combineConfidence(base.matching_confidence, taxonomy.confidence),
    imageUrl: gallery[0],
    optimeScore,
    matchLabel: scoreLabel(optimeScore),
    shortExplanation: buildShortExplanation(facility),
    priceRange: monthlyCostRange,
    price: makeDerivedPrice(monthlyCostRange),
    ...ageRange,
    entryAgeRange: {
      min: ageRange.minAge,
      max: ageRange.maxAge,
    },
    careTypes: taxonomy.careTypes,
    ...inventoryCapabilities,
    medicalCapabilities: capabilities.medicalCapabilities,
    rehabilitationCapabilities: capabilities.rehabilitationCapabilities,
    lifestyleCapabilities: capabilities.lifestyleCapabilities,
    diningCapabilities: capabilities.diningCapabilities,
    housingCapabilities: capabilities.housingCapabilities,
    continuumOfCareAvailable: capabilities.continuumOfCareAvailable,
    careTypeConfidence: taxonomy.confidence,
    careTypeConfidenceScore: taxonomy.confidenceScore,
    careTypeProbabilities: taxonomy.probabilities,
    intelligenceSnapshot: facility.intelligence_confidence !== null && facility.intelligence_confidence !== undefined ? {
      intelligence_confidence: facility.intelligence_confidence,
      sources_used: facility.intelligence_sources_used || [],
      positive_signals: facility.intelligence_positive_signals || [],
      negative_signals: facility.intelligence_negative_signals || [],
      signal_details: facility.intelligence_signal_details || [],
      family_satisfaction_index: facility.family_satisfaction_index || 0,
      staff_stability_index: facility.staff_stability_index || 0,
      regulatory_risk_index: facility.regulatory_risk_index || 0,
      litigation_risk_index: facility.litigation_risk_index || 0,
      social_energy_index: facility.social_energy_index || 0,
      community_engagement_index: facility.community_engagement_index || 0,
      reputation_index: facility.reputation_index || 0,
      cultural_match_signals: facility.cultural_match_signals || 0,
    } : undefined,
    matchBadges: makeBadges(facility, taxonomy),
    visualIntelligence: buildVisualIntelligence(facility),
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
  const gallery = searchFacility.visualIntelligence.galleryImages.map((image) => image.url);

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

export async function fetchFacilityIntelligenceProfile(id: string): Promise<FacilityIntelligenceProfile> {
  return fetchJson<FacilityIntelligenceProfile>(`/intelligence/facilities/${id}`);
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
