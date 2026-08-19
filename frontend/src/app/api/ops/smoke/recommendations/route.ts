import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const BASE_SON_84 = {
  relationship: "Dad",
  ageGroup: "80-84",
  assistanceLevel: "Needs assistance with bathing and dressing",
  memoryStatus: "No",
  budget: 6500,
  distanceFromFamily: "Balanced location",
};
const BASE_QUERY = "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing, meals and medication. No dementia.";
const answeredState = (communitySizePreference: string) => ({
  ...BASE_SON_84,
  humanIntelligenceV2: {
    personalityProfile: { communitySizePreference },
    familyProfile: { socialInteractionNeed: "Neither" },
    transitionRiskProfile: { attitudeTowardMove: "Cautious but open" },
  },
});

const PERSONAS = {
  son84: { questionnaire_state: BASE_SON_84, natural_language_query: BASE_QUERY, limit: 5 },
  self84: {
    questionnaire_state: { ...BASE_SON_84, relationship: "Myself" },
    natural_language_query: "I am 84, recently widowed, live in Las Vegas, am mentally alert and mobile, and need help with bathing, dressing, meals and medication. No dementia.",
    limit: 5,
  },
  son84_large_neutral: { questionnaire_state: answeredState("Large community"), natural_language_query: BASE_QUERY, limit: 5 },
  son84_small_neutral: { questionnaire_state: answeredState("Small community"), natural_language_query: BASE_QUERY, limit: 5 },
} as const;

type PersonaKey = keyof typeof PERSONAS;
type Recommendation = {
  canonical_facility_id?: string; facility_name?: string; city?: string; state?: string;
  rank_position?: number; rank_display?: string; rank_tie_status?: string; tied_with?: string[];
  patient_match_score?: number; care_setting_fit?: { status?: string };
  success_factor_trace?: { factors?: unknown[] };
  human_person_fit?: { community_size?: { official_bed_count?: number | string; community_size_band?: string; preference?: string; fit_score?: number | string; not_a_quality_factor?: boolean } };
  tie_break_explanation_vs_next?: { deciding_dimension?: string };
};
type DecisionIntelligence = {
  version?: string;
  human_intelligence?: { decision_readiness?: string; adaptive_questions?: Array<{ question_key?: string }> };
  person_fit_rank_effect?: string;
  success_factor_policy?: { factors?: unknown[] };
};
type RecommendationPayload = {
  patient_needs_profile?: { location_city?: string | null; decision_intelligence?: DecisionIntelligence };
  results?: Recommendation[]; result_count?: number; total_candidates_scored?: number;
  care_setting_policy?: { version?: string; decision_intelligence?: DecisionIntelligence };
  decision_intelligence?: DecisionIntelligence;
};

export async function GET(request: NextRequest) {
  const persona = (request.nextUrl.searchParams.get("persona") || "son84") as PersonaKey;
  const compact = request.nextUrl.searchParams.get("compact") === "1";
  if (!(persona in PERSONAS)) {
    return NextResponse.json({ error: "Unsupported smoke persona", supported: Object.keys(PERSONAS) }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(PERSONAS[persona]), cache: "no-store",
  });
  const raw = await response.text();
  let body: RecommendationPayload | { raw: string };
  try { body = raw ? JSON.parse(raw) : {}; } catch { body = { raw }; }
  if (!response.ok) {
    return NextResponse.json({ error: "Production decision engine smoke request failed", backend_status: response.status, backend_body: body }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
  if (compact) {
    const payload = body as RecommendationPayload;
    const intelligence = payload.decision_intelligence || payload.patient_needs_profile?.decision_intelligence || payload.care_setting_policy?.decision_intelligence;
    return NextResponse.json({
      smoke: true, persona, generated_at: new Date().toISOString(), backend: BACKEND_BASE,
      fingerprint: {
        decision_intelligence_version: intelligence?.version ?? null,
        care_setting_policy_version: payload.care_setting_policy?.version ?? null,
        location_city: payload.patient_needs_profile?.location_city ?? null,
        decision_readiness: intelligence?.human_intelligence?.decision_readiness ?? null,
        adaptive_question_keys: (intelligence?.human_intelligence?.adaptive_questions || []).map((q) => q.question_key),
        person_fit_rank_effect: intelligence?.person_fit_rank_effect ?? null,
        success_factor_count: intelligence?.success_factor_policy?.factors?.length ?? null,
        result_count: payload.result_count ?? null,
        total_candidates_scored: payload.total_candidates_scored ?? null,
        top5: (payload.results || []).slice(0, 5).map((row) => ({
          id: row.canonical_facility_id ?? null, name: row.facility_name ?? null, city: row.city ?? null, state: row.state ?? null,
          rank_position: row.rank_position ?? null, rank_display: row.rank_display ?? null, rank_tie_status: row.rank_tie_status ?? null,
          tied_with_count: row.tied_with?.length ?? 0, patient_match_score: row.patient_match_score ?? null,
          care_setting_fit: row.care_setting_fit?.status ?? null, community_size: row.human_person_fit?.community_size ?? null,
          success_factor_count: row.success_factor_trace?.factors?.length ?? null,
          next_deciding_dimension: row.tie_break_explanation_vs_next?.deciding_dimension ?? null,
        })),
      },
    }, { headers: { "Cache-Control": "no-store" } });
  }
  return NextResponse.json({ smoke: true, persona, generated_at: new Date().toISOString(), result: body }, { headers: { "Cache-Control": "no-store" } });
}
