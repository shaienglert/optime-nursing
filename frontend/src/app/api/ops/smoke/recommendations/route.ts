import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const PERSONAS = {
  son84: {
    questionnaire_state: {
      relationship: "Dad",
      ageGroup: "80-84",
      assistanceLevel: "Needs assistance with bathing and dressing",
      memoryStatus: "No",
      budget: 6500,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing, meals and medication. No dementia.",
    limit: 5,
  },
  self84: {
    questionnaire_state: {
      relationship: "Myself",
      ageGroup: "80-84",
      assistanceLevel: "Needs assistance with bathing and dressing",
      memoryStatus: "No",
      budget: 6500,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "I am 84, recently widowed, live in Las Vegas, am mentally alert and mobile, and need help with bathing, dressing, meals and medication. No dementia.",
    limit: 5,
  },
} as const;

type PersonaKey = keyof typeof PERSONAS;

type Recommendation = {
  canonical_facility_id?: string;
  facility_name?: string;
  city?: string;
  state?: string;
  rank_position?: number;
  rank_display?: string;
  rank_tie_status?: string;
  tied_with?: string[];
  patient_match_score?: number;
  care_setting_fit?: { status?: string };
  tie_break_explanation_vs_next?: { deciding_dimension?: string };
};

type RecommendationPayload = {
  patient_needs_profile?: { location_city?: string | null };
  results?: Recommendation[];
  result_count?: number;
  total_candidates_scored?: number;
  care_setting_policy?: { version?: string };
};

export async function GET(request: NextRequest) {
  const persona = (request.nextUrl.searchParams.get("persona") || "son84") as PersonaKey;
  const compact = request.nextUrl.searchParams.get("compact") === "1";
  if (!(persona in PERSONAS)) {
    return NextResponse.json(
      { error: "Unsupported smoke persona", supported: Object.keys(PERSONAS) },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }

  const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(PERSONAS[persona]),
    cache: "no-store",
  });

  const raw = await response.text();
  let body: RecommendationPayload | { raw: string };
  try {
    body = raw ? JSON.parse(raw) : {};
  } catch {
    body = { raw };
  }

  if (!response.ok) {
    return NextResponse.json(
      { error: "Production decision engine smoke request failed", backend_status: response.status, backend_body: body },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }

  if (compact) {
    const payload = body as RecommendationPayload;
    return NextResponse.json(
      {
        smoke: true,
        persona,
        generated_at: new Date().toISOString(),
        backend: BACKEND_BASE,
        fingerprint: {
          care_setting_policy_version: payload.care_setting_policy?.version ?? null,
          location_city: payload.patient_needs_profile?.location_city ?? null,
          result_count: payload.result_count ?? null,
          total_candidates_scored: payload.total_candidates_scored ?? null,
          top5: (payload.results || []).slice(0, 5).map((row) => ({
            id: row.canonical_facility_id ?? null,
            name: row.facility_name ?? null,
            city: row.city ?? null,
            state: row.state ?? null,
            rank_position: row.rank_position ?? null,
            rank_display: row.rank_display ?? null,
            rank_tie_status: row.rank_tie_status ?? null,
            tied_with_count: row.tied_with?.length ?? 0,
            patient_match_score: row.patient_match_score ?? null,
            care_setting_fit: row.care_setting_fit?.status ?? null,
            next_deciding_dimension: row.tie_break_explanation_vs_next?.deciding_dimension ?? null,
          })),
        },
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  }

  return NextResponse.json(
    {
      smoke: true,
      persona,
      generated_at: new Date().toISOString(),
      result: body,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
