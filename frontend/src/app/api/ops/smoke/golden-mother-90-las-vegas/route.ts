import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const maxDuration = 300;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const CLIENT_TEXT =
  "My mother is 90. Her husband died two months ago and she does not want to remain alone at home. She is mentally alert, has no dementia, is mobile, and otherwise functions independently, but she needs daily help with bathing, dressing and medication management. She enjoys classical music and being around other people. We are looking across the Las Vegas Valley with a total monthly housing-and-care budget up to $8,000. We want the least restrictive safe setting and a socially supportive community.";

const QUESTIONNAIRE_STATE = {
  relationship: "Mom",
  ageGroup: "90+",
  assistanceLevel: "Needs assistance with bathing and dressing",
  memoryStatus: "No",
  budget: 8000,
  locationCity: "Las Vegas",
  state: "NV",
  humanIntelligenceV2: {
    personalityProfile: { communitySizePreference: "No preference" },
    familyProfile: { socialInteractionNeed: "Important" },
    transitionRiskProfile: { attitudeTowardMove: "Cautious but open" },
    scoringEngine: { adaptiveSignals: [] },
  },
};

export async function GET() {
  try {
    const started = Date.now();
    const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionnaire_state: QUESTIONNAIRE_STATE, natural_language_query: CLIENT_TEXT, limit: 5 }),
      cache: "no-store",
    });
    const raw = await response.text();
    const elapsedMs = Date.now() - started;
    if (!response.ok) {
      console.error("MOTHER90_SMOKE_BACKEND_FAIL", JSON.stringify({ backendStatus: response.status, elapsedMs, detail: raw.slice(0, 1200) }));
      return NextResponse.json({ status: "FAIL", error: `Decision engine ${response.status}`, elapsedMs, detail: raw.slice(0, 1200) }, { status: 502, headers: { "Cache-Control": "no-store" } });
    }
    const payload = raw ? JSON.parse(raw) : {};
    const intelligence = payload?.decision_intelligence || payload?.patient_needs_profile?.decision_intelligence || {};
    const human = intelligence?.human_intelligence || {};
    const rows = payload?.results || [];
    const top5 = rows.slice(0, 5).map((row: any) => ({
      rank: row?.rank_position ?? null,
      name: row?.facility_name ?? null,
      city: row?.city ?? null,
      canonicalType: row?.canonical_type ?? null,
      hardGate: row?.client_intent_fit?.hard_gate ?? null,
      mustPass: row?.client_intent_fit?.must_pass ?? [],
      mustUnknown: row?.client_intent_fit?.must_unknown ?? [],
      niceCoverage: row?.semantic_preference_coverage ?? row?.nice_to_have_coverage ?? null,
      aiRanking: row?.ai_ranking ?? null,
    }));
    const readiness = human?.decision_readiness ?? intelligence?.decision_readiness ?? null;
    const bereavement = human?.signals?.recent_bereavement?.value ?? null;
    const assertions = {
      clientInterviewComplete: readiness === "READY",
      recentBereavementPreserved: String(bereavement || "").toUpperCase() === "YES",
      producedFiveVisibleCandidates: top5.length === 5,
      noHardMustFailuresVisible: top5.every((row: any) => row.hardGate !== "FAIL"),
      assistedLivingCareSetting: top5.every((row: any) => ["ASSISTED_LIVING_RFG", "ASSISTED_LIVING"].includes(String(row.canonicalType || "").toUpperCase())),
      ranksAreStableOneToFive: top5.every((row: any, index: number) => row.rank === index + 1),
      completesInsideVercelBudget: elapsedMs < 240000,
    };
    const passed = Object.values(assertions).every(Boolean);
    const diagnostic = {
      elapsedMs,
      decisionReadiness: readiness,
      decisionFinality: intelligence?.decision_finality ?? null,
      recommendationExecutionAllowed: intelligence?.recommendation_execution_allowed ?? null,
      facilityResearchState: intelligence?.facility_research_state ?? null,
      recentBereavement: bereavement,
      resultCount: payload?.result_count ?? rows.length,
      assertions,
      top5,
    };
    console.log("MOTHER90_SMOKE_DIAGNOSTIC", JSON.stringify(diagnostic));
    return NextResponse.json({ status: passed ? "PASS" : "FAIL", caseId: "GOLDEN-MOTHER-90-WIDOW-LAS-VEGAS-8K", ...diagnostic, processOwner: intelligence?.process_owner ?? null }, { status: passed ? 200 : 409, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    console.error("MOTHER90_SMOKE_EXCEPTION", error);
    return NextResponse.json({ status: "FAIL", error: error instanceof Error ? error.message : String(error) }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
