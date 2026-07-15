export interface Facility {
  id: number;
  name: string;
  city?: string;
  state?: string;
  overall_rating?: number;
  staffing_rating?: number;
  beds?: number;
  cms_id?: string;
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

const firstWords = [
  "Sunrise",
  "Harbor",
  "Cypress",
  "Silver",
  "Palm",
  "Bayside",
  "Legacy",
  "Grandview",
  "Willow",
  "Ocean",
];

const secondWords = [
  "Gardens",
  "Manor",
  "Heights",
  "Village",
  "Haven",
  "Springs",
  "Commons",
  "Residence",
  "Pointe",
  "Retreat",
];

const cities = [
  "Miami",
  "Boca Raton",
  "Coral Gables",
  "Fort Lauderdale",
  "Aventura",
  "Hollywood",
  "Delray Beach",
  "Weston",
  "Pembroke Pines",
  "Naples",
];

const gallerySets = [
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

const explanationPool = [
  "Excellent staffing and strong social activities. Great fit for active seniors requiring light assistance.",
  "Reliable clinical coverage and calm daily routines. A strong option for memory support and family visibility.",
  "Balanced care quality, social engagement, and value. Works well for seniors who want both support and independence.",
];

const badgesPool = [
  ["Matches care needs", "Matches budget", "Strong social program", "Close to family", "Memory support available"],
  ["Matches care needs", "Matches budget", "Medication support", "Close to family", "Hebrew speaking staff"],
  ["Matches care needs", "Matches budget", "Active community", "Close to family", "Skilled nursing available"],
];

const careTypePool = [
  ["Assisted Living", "Memory Care", "Skilled Nursing"],
  ["Independent Living", "Assisted Living"],
  ["Assisted Living", "Skilled Nursing"],
];

function buildVerificationFields(seed: number, name: string, city: string, website: string | null | undefined, phone: string | null | undefined, cmsId: string): {
  verified_name: string;
  license_verified: boolean;
  cms_verified: boolean;
  website_verified: boolean;
  phone_verified: boolean;
  verification_score: number;
  matching_confidence: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
} {
  const pattern = seed % 12;

  if (pattern === 7) {
    return {
      verified_name: `${city} Senior Community`,
      license_verified: Boolean(cmsId),
      cms_verified: Boolean(cmsId),
      website_verified: Boolean(website),
      phone_verified: Boolean(phone),
      verification_score: 40,
      matching_confidence: "LOW",
    };
  }

  if (pattern === 4) {
    return {
      verified_name: name.replace("Senior Living", "Senior Lving"),
      license_verified: Boolean(cmsId),
      cms_verified: Boolean(cmsId),
      website_verified: Boolean(website),
      phone_verified: Boolean(phone),
      verification_score: 70,
      matching_confidence: "MEDIUM",
    };
  }

  return {
    verified_name: name,
    license_verified: Boolean(cmsId),
    cms_verified: Boolean(cmsId),
    website_verified: Boolean(website),
    phone_verified: Boolean(phone),
    verification_score: 100,
    matching_confidence: "HIGH",
  };
}

function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent Match";
  if (score >= 80) return "Great Match";
  if (score >= 70) return "Good Match";
  return "Consider Match";
}

function buildScoreBreakdown(seed: number): ScoreBreakdownItem[] {
  const categories = [
    "Medical Quality",
    "Staffing",
    "Activities",
    "Independence Support",
    "Value for Money",
    "Food Quality",
    "Living Environment",
    "Memory Support",
  ];

  return categories.map((category, index) => {
    const score = Math.max(68, Math.min(97, 78 + ((seed + index * 7) % 20)));
    return {
      category,
      score,
      explanation: `${category} assessment combines recent performance trends and consistency indicators.`,
      dataSource:
        category === "Medical Quality"
          ? ["CMS Quality Rating", "Hospitalization rate", "Fall statistics", "Inspection reports"]
          : ["CMS data", "Facility profile", "Family feedback"],
    };
  });
}

function buildMockFacilities(): FacilityDetailsData[] {
  const facilities: FacilityDetailsData[] = [];

  for (let i = 1; i <= 30; i += 1) {
    const variant = i % 3;
    const city = cities[i % cities.length];
    const score = 68 + ((i * 9) % 31);
    const name = `${firstWords[i % firstWords.length]} ${secondWords[i % secondWords.length]} Senior Living`;
    const website = i % 4 === 0 ? null : `https://www.optime-nursing.example/facilities/fl-${100000 + i}`;
    const phone = `305-555-${String(1000 + i).slice(-4)}`;
    const cmsId = `FL-${100000 + i}`;
    const verification = buildVerificationFields(i, name, city, website, phone, cmsId);

    facilities.push({
      id: i,
      cms_id: cmsId,
      name,
      city,
      state: "FL",
      address: `${300 + i} Wellness Avenue`,
      zip_code: `${33000 + i}`,
      phone,
      beds: 90 + ((i * 7) % 70),
      overall_rating: Math.max(3, Math.min(5, Math.round(score / 20))),
      staffing_rating: Math.max(3, Math.min(5, Math.round((score - 5) / 20))),
      quality_rating: Math.max(3, Math.min(5, Math.round((score + 3) / 20))),
      inspection_rating: Math.max(3, Math.min(5, Math.round((score + 1) / 20))),
      latitude: 25.7 + i * 0.01,
      longitude: -80.2 - i * 0.01,
      imageUrl: gallerySets[variant][0],
      gallery: gallerySets[variant],
      website: website || `https://www.optime-nursing.example/facilities/fl-${100000 + i}`,
      optimeScore: score,
      matchLabel: scoreLabel(score),
      shortExplanation: explanationPool[variant],
      priceRange: `$${(4200 + i * 90).toLocaleString()} - $${(6800 + i * 115).toLocaleString()}/month`,
      careTypes: careTypePool[variant],
      matchBadges: badgesPool[variant],
      ...verification,
      scoreBreakdown: buildScoreBreakdown(i),
      mapPoints: {
        facility: `${name}, ${city}`,
        family: "Family location - 22 minutes away",
        hospital: "Nearest hospital - 8 minutes away",
        synagogue: "Nearby synagogue - 12 minutes away",
        transit: "Public transportation - 6 minutes away",
      },
    });
  }

  return facilities;
}

const MOCK_FACILITIES = buildMockFacilities();

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export async function fetchFacilities(): Promise<Facility[]> {
  return MOCK_FACILITIES;
}

export async function fetchSearchFacilities(): Promise<SearchFacility[]> {
  return MOCK_FACILITIES;
}

export async function fetchFacilityById(id: string): Promise<Facility> {
  const facility = MOCK_FACILITIES.find((item) => item.id === Number(id));
  if (!facility) {
    throw new Error("Failed to load facility (404)");
  }
  return facility;
}

export async function fetchFacilityDetails(id: string): Promise<FacilityDetailsData> {
  const facility = MOCK_FACILITIES.find((item) => item.id === Number(id));
  if (!facility) {
    throw new Error("Failed to load facility details (404)");
  }
  return facility;
}
