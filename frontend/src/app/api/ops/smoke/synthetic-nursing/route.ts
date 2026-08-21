import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const scenarios = [
  {
    id: "NURSING-1-WALKER-100M",
    questionnaire_state: {
      relationship: "Myself",
      ageGroup: "80-84",
      assistanceLevel: "Mostly independent",
      memoryStatus: "No",
      budget: 8000,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "I am 80 and looking for senior living in Las Vegas. I am mentally sharp and otherwise independent, but I use a walker and can walk only about 100 meters at a time. I do not want to use a wheelchair. I want to be able to reach dining, activities and the main services without long internal walks. I also enjoy movies, music and social activities.",
    limit: 5,
  },
  {
    id: "NURSING-2-GLUTEN-WIDOW",
    questionnaire_state: {
      relationship: "Myself",
      ageGroup: "75-79",
      assistanceLevel: "Independent",
      memoryStatus: "No",
      budget: 10000,
      distanceFromFamily: "Balanced location",
    },
    natural_language_query:
      "I am a 76-year-old widow looking for senior living in Las Vegas. I am independent and do not have dementia. I do not cook, so I need all daily meals provided. I have a medically important gluten allergy and need safe gluten-free food with cross-contact controls. I prefer a high-quality comfortable community, enjoy company, card games, classes and organized activities, and I do not want to feel isolated.",
    limit: 5,
  },
] as const;

async function callDecisionEngine(scenario: (typeof scenarios)[number]) {
  const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      questionnaire_state: scenario.questionnaire_state,
      natural_language_query: scenario.natural_language_query,
      limit: scenario.limit,
    }),
    cache: "no-store",
  });
  const raw = await response.text();
  if (!response.ok) throw new Error(`Decision engine ${response.status}: ${raw.slice(0, 500)}`);
  return raw ? JSON.parse(raw) : {};
}

function summarize(payload: any) {
  const intelligence = payload?.decision_intelligence
    || payload?.patient_needs_profile?.decision_intelligence
    || payload?.care_setting_policy?.decision_intelligence
    || {};
  const human = intelligence?.human_intelligence || {};
  return {
    decisionReadiness: human?.decision_readiness ?? null,
    adaptiveQuestions: (human?.adaptive_questions || []).map((q: any) => ({
      questionKey: q?.question_key ?? null,
      question: q?.question ?? q?.prompt ?? null,
    })),
    semanticAI: human?.semantic_ai ?? intelligence?.semantic_ai ?? null,
    personFitRankEffect: intelligence?.person_fit_rank_effect ?? null,
    decisionFinality: intelligence?.decision_finality ?? intelligence?.agent_evidence_bridge?.decision_finality ?? null,
    mustGate: intelligence?.must_gate ?? null,
    resultCount: payload?.result_count ?? null,
    top5: (payload?.results || []).slice(0, 5).map((row: any) => ({
      id: row?.canonical_facility_id ?? null,
      name: row?.facility_name ?? null,
      rank: row?.rank_position ?? null,
      score: row?.patient_match_score ?? null,
      hardGate: row?.client_intent_fit?.hard_gate ?? null,
      mustPass: row?.client_intent_fit?.must_pass ?? [],
      mustUnknown: row?.client_intent_fit?.must_unknown ?? [],
      mustFail: row?.client_intent_fit?.must_fail ?? [],
      niceMatch: row?.client_intent_fit?.nice_match ?? [],
      niceUnknown: row?.client_intent_fit?.nice_unknown ?? [],
    })),
  };
}

export async function GET() {
  try {
    const rows = [];
    for (const scenario of scenarios) {
      const payload = await callDecisionEngine(scenario);
      rows.push({
        id: scenario.id,
        input: {
          questionnaire_state: scenario.questionnaire_state,
          natural_language_query: scenario.natural_language_query,
        },
        output: summarize(payload),
      });
    }
    return NextResponse.json({
      status: "COMPLETED",
      backend: BACKEND_BASE,
      fixturePolicy: "Two invented resident/family scenarios; read-only; no production data mutation.",
      rows,
    }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({
      status: "FAIL",
      detail: error instanceof Error ? error.message : String(error),
    }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
