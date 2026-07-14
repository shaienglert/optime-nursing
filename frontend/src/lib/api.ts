export type Facility = {
  id: number;
  cms_id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  phone: string | null;
  overall_rating: number | null;
  staffing_rating: number | null;
  quality_rating: number | null;
  inspection_rating: number | null;
  beds: number | null;
  latitude: number | null;
  longitude: number | null;
};

export type ScoreBreakdownItem = {
  category: string;
  score: number;
  explanation: string;
  dataSource: string[];
};

export type ReviewGroup = {
  type: string;
  rating: number;
  quote: string;
};

export type SearchFacility = Facility & {
  feedId: string;
  imageUrl: string;
  optimeScore: number;
  aiSummary: string[];
  priceRange: string;
  careTypes: string[];
  matchBadges: string[];
};

export type FacilityDetailsData = SearchFacility & {
  website: string;
  gallery: string[];
  scoreBreakdown: ScoreBreakdownItem[];
  matchScore: number;
  matchReasons: string[];
  mapPoints: {
    family: string;
    hospital: string;
    synagogue: string;
    transit: string;
  };
  reviews: ReviewGroup[];
};

const imageSets = [
  [
    "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1200&q=80",
  ],
  [
    "https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
  ],
  [
    "https://images.unsplash.com/photo-1519643381401-22c77e60520e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1464890100898-a385f744067f?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1430285561322-7808604715df?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
  ],
];

const careTypeSets = [
  ["Assisted Living", "Memory Care", "Skilled Nursing"],
  ["Independent Living", "Assisted Living"],
  ["Skilled Nursing", "Memory Care"],
];

const matchBadgeSets = [
  ["Matches budget", "Matches social preferences", "Within requested distance"],
  ["Matches budget", "Hebrew speaking staff", "Memory care available"],
  ["Within requested distance", "Matches social preferences", "Memory care available"],
];

const summarySets = [
  [
    "Excellent staffing levels and medical care.",
    "Strong social activity program.",
    "Ideal for seniors needing mild assistance.",
  ],
  [
    "Consistent care team with strong family communication.",
    "Calmer environment for seniors who value routine.",
    "Good fit for residents balancing independence and support.",
  ],
  [
    "High-touch nursing coverage and dementia support.",
    "Well-suited for families prioritizing safety oversight.",
    "Balanced value for more advanced care needs.",
  ],
];

const reviewSets: ReviewGroup[][] = [
  [
    { type: "Families", rating: 5, quote: "The staff keeps us informed and treats my mother with real warmth." },
    { type: "Residents", rating: 4, quote: "There is always something to do, and the movie nights are a highlight." },
    { type: "Employees", rating: 4, quote: "Clinical leadership is organized and shifts are well supported." },
    { type: "OPTIME review", rating: 5, quote: "Strong all-around match for seniors needing mild to moderate daily support." },
  ],
  [
    { type: "Families", rating: 4, quote: "We liked the steady communication and flexible care planning." },
    { type: "Residents", rating: 4, quote: "Quiet apartments and a friendly social calendar make it easy to settle in." },
    { type: "Employees", rating: 4, quote: "The team culture is collaborative, especially between nursing and activities." },
    { type: "OPTIME review", rating: 4, quote: "Good value for families prioritizing routine, social fit, and moderate assistance." },
  ],
  [
    { type: "Families", rating: 5, quote: "The memory care team feels experienced and responsive during stressful moments." },
    { type: "Residents", rating: 4, quote: "Meals are good and the staff checks in often without feeling intrusive." },
    { type: "Employees", rating: 4, quote: "Strong nursing oversight and reliable processes for high-acuity residents." },
    { type: "OPTIME review", rating: 5, quote: "Best for families emphasizing clinical support, dementia care, and medical readiness." },
  ],
];

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function getVariantIndex(facilityId: number, offset = 0): number {
  return (facilityId + offset) % 3;
}

function toScore(value: number | null | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }

  return Math.max(70, Math.min(99, value * 18 + 10));
}

function buildSearchFacility(facility: Facility, offset = 0): SearchFacility {
  const variant = getVariantIndex(facility.id, offset);

  return {
    ...facility,
    feedId: `${facility.id}-${offset}`,
    imageUrl: imageSets[variant][0],
    optimeScore: toScore(facility.overall_rating, 88) + (offset % 3),
    aiSummary: summarySets[variant],
    priceRange: `$${(facility.beds ? Math.max(3200, facility.beds * 35) : 5200).toLocaleString()} - $${(facility.beds ? Math.max(5400, facility.beds * 52) : 7800).toLocaleString()}/mo`,
    careTypes: careTypeSets[variant],
    matchBadges: matchBadgeSets[variant],
  };
}

function buildScoreBreakdown(facility: Facility): ScoreBreakdownItem[] {
  return [
    {
      category: "Medical Quality",
      score: toScore(facility.quality_rating, 90),
      explanation: "Combines clinical quality signals and health outcome reliability.",
      dataSource: ["CMS Quality Rating", "Hospitalization rate", "Fall statistics", "Inspection reports"],
    },
    {
      category: "Staffing Levels",
      score: toScore(facility.staffing_rating, 86),
      explanation: "Measures staffing stability, nurse coverage, and support responsiveness.",
      dataSource: ["CMS Staffing Rating", "RN coverage", "Care team consistency"],
    },
    {
      category: "Social Activities",
      score: 88,
      explanation: "Assesses lifestyle programming and the likelihood of meaningful engagement.",
      dataSource: ["Activities calendar", "Family interviews", "Resident feedback"],
    },
    {
      category: "Independence Support",
      score: 84,
      explanation: "Evaluates how well the community balances support with resident autonomy.",
      dataSource: ["Care plan flexibility", "Mobility support", "Resident routines"],
    },
    {
      category: "Value for Money",
      score: 81,
      explanation: "Compares expected monthly cost against support intensity and quality signals.",
      dataSource: ["Local market pricing", "Care level offerings", "Facility amenities"],
    },
    {
      category: "Food Quality",
      score: 79,
      explanation: "Reflects nutrition quality, menu range, and dining satisfaction.",
      dataSource: ["Menu audits", "Resident reviews", "Family observations"],
    },
    {
      category: "Living Environment",
      score: 87,
      explanation: "Captures cleanliness, design, quietness, and overall comfort.",
      dataSource: ["Facility profile", "Review themes", "Inspection context"],
    },
    {
      category: "Dementia Support",
      score: 85,
      explanation: "Evaluates specialized memory care readiness and cognitive support structures.",
      dataSource: ["Memory care availability", "Staff specialization", "Safety procedures"],
    },
  ];
}

export async function fetchFacilities(): Promise<Facility[]> {
  const response = await fetch(`${getApiBaseUrl()}/facilities`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facilities (${response.status})`);
  }

  return (await response.json()) as Facility[];
}

export async function fetchFacilityById(id: string): Promise<Facility> {
  const response = await fetch(`${getApiBaseUrl()}/facilities/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facility (${response.status})`);
  }

  return (await response.json()) as Facility;
}

export async function fetchSearchFacilities(): Promise<SearchFacility[]> {
  const facilities = await fetchFacilities();

  return Array.from({ length: 18 }, (_, index) => {
    const facility = facilities[index % facilities.length];
    return buildSearchFacility(facility, index);
  });
}

export async function fetchFacilityDetails(id: string): Promise<FacilityDetailsData> {
  const facility = await fetchFacilityById(id);
  const variant = getVariantIndex(facility.id);
  const searchFacility = buildSearchFacility(facility, variant);

  return {
    ...searchFacility,
    website: `https://www.optime-nursing.example/facilities/${facility.cms_id.toLowerCase()}`,
    gallery: imageSets[variant],
    scoreBreakdown: buildScoreBreakdown(facility),
    matchScore: Math.min(97, searchFacility.optimeScore + 3),
    matchReasons: [
      "Matches required care level",
      "Supports active lifestyle",
      "Fits budget",
      "Close to family",
    ],
    mapPoints: {
      family: "Family location - 18 minutes away",
      hospital: "Baptist Health hospital - 7 minutes away",
      synagogue: "Nearby synagogue - 11 minutes away",
      transit: "Public transit access - 6 minutes away",
    },
    reviews: reviewSets[variant],
  };
}

  export type ScoreBreakdownItem = {
    category: string;
    score: number;
    explanation: string;
    dataSource: string[];
  };

  export type ReviewGroup = {
    type: string;
    rating: number;
    quote: string;
  };

  export type SearchFacility = Facility & {
    feedId: string;
    imageUrl: string;
    optimeScore: number;
    aiSummary: string[];
    priceRange: string;
    careTypes: string[];
    matchBadges: string[];
  };

  export type FacilityDetailsData = SearchFacility & {
    website: string;
    gallery: string[];
    scoreBreakdown: ScoreBreakdownItem[];
    matchScore: number;
    matchReasons: string[];
    mapPoints: {
      family: string;
      hospital: string;
      synagogue: string;
      transit: string;
    };
    reviews: ReviewGroup[];
  };

  const imageSets = [
    [
      "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1200&q=80",
    ],
    [
      "https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80",
    ],
    [
      "https://images.unsplash.com/photo-1519643381401-22c77e60520e?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1464890100898-a385f744067f?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1430285561322-7808604715df?auto=format&fit=crop&w=1200&q=80",
      "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=80",
    ],
  ];

  const careTypeSets = [
    ["Assisted Living", "Memory Care", "Skilled Nursing"],
    ["Independent Living", "Assisted Living"],
    ["Skilled Nursing", "Memory Care"],
  ];

  const matchBadgeSets = [
    ["Matches budget", "Matches social preferences", "Within requested distance"],
    ["Matches budget", "Hebrew speaking staff", "Memory care available"],
    ["Within requested distance", "Matches social preferences", "Memory care available"],
  ];

  const summarySets = [
    [
      "Excellent staffing levels and medical care.",
      "Strong social activity program.",
      "Ideal for seniors needing mild assistance.",
    ],
    [
      "Consistent care team with strong family communication.",
      "Calmer environment for seniors who value routine.",
      "Good fit for residents balancing independence and support.",
    ],
    [
      "High-touch nursing coverage and dementia support.",
      "Well-suited for families prioritizing safety oversight.",
      "Balanced value for more advanced care needs.",
    ],
  ];

  const reviewSets: ReviewGroup[][] = [
    [
      { type: "Families", rating: 5, quote: "The staff keeps us informed and treats my mother with real warmth." },
      { type: "Residents", rating: 4, quote: "There is always something to do, and the movie nights are a highlight." },
      { type: "Employees", rating: 4, quote: "Clinical leadership is organized and shifts are well supported." },
      { type: "OPTIME review", rating: 5, quote: "Strong all-around match for seniors needing mild to moderate daily support." },
    ],
    [
      { type: "Families", rating: 4, quote: "We liked the steady communication and flexible care planning." },
      { type: "Residents", rating: 4, quote: "Quiet apartments and a friendly social calendar make it easy to settle in." },
      { type: "Employees", rating: 4, quote: "The team culture is collaborative, especially between nursing and activities." },
      { type: "OPTIME review", rating: 4, quote: "Good value for families prioritizing routine, social fit, and moderate assistance." },
    ],
    [
      { type: "Families", rating: 5, quote: "The memory care team feels experienced and responsive during stressful moments." },
      { type: "Residents", rating: 4, quote: "Meals are good and the staff checks in often without feeling intrusive." },
      { type: "Employees", rating: 4, quote: "Strong nursing oversight and reliable processes for high-acuity residents." },
      { type: "OPTIME review", rating: 5, quote: "Best for families emphasizing clinical support, dementia care, and medical readiness." },
    ],
  ];

  function getApiBaseUrl(): string {
    return (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  }

export async function fetchFacilities(): Promise<Facility[]> {
  const response = await fetch(`${getApiBaseUrl()}/facilities`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facilities (${response.status})`);
  }
  return (await response.json()) as Facility[];
}

export async function fetchFacilityById(id: string): Promise<Facility> {
  const response = await fetch(`${getApiBaseUrl()}/facilities/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load facility (${response.status})`);
  }
  return (await response.json()) as Facility;
}

export async function fetchSearchFacilities(): Promise<SearchFacility[]> {
  const facilities = await fetchFacilities();
  return Array.from({ length: 18 }, (_, index) => {
    const facility = facilities[index % facilities.length];
    return buildSearchFacility(facility, index);
  });
}

export async function fetchFacilityDetails(id: string): Promise<FacilityDetailsData> {
  const facility = await fetchFacilityById(id);
  const variant = getVariantIndex(facility.id);
  const searchFacility = buildSearchFacility(facility, variant);

  return {
    ...searchFacility,
    website: `https://www.optime-nursing.example/facilities/${facility.cms_id.toLowerCase()}`,
    gallery: imageSets[variant],
    scoreBreakdown: buildScoreBreakdown(facility),
    matchScore: Math.min(97, searchFacility.optimeScore + 3),
    matchReasons: [
      "Matches required care level",
      "Supports active lifestyle",
      "Fits budget",
      "Close to family",
    ],
    mapPoints: {
      family: "Family location - 18 minutes away",
      hospital: "Baptist Health hospital - 7 minutes away",
      synagogue: "Nearby synagogue - 11 minutes away",
      transit: "Public transit access - 6 minutes away",
    },
    reviews: reviewSets[variant],
  };
}
