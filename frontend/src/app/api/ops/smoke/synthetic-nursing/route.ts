import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const maxDuration = 300;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const scenarios = [
  {
    id: "NURSING-1-WALKER-100M",
    questionnaire_state: { relationship: "Myself", ageGroup: "80-84", assistanceLevel: "Mostly independent", memoryStatus: "No", budget: 8000, distanceFromFamily: "Balanced location" },
    natural_language_query: "I am 80 and looking for senior living in Las Vegas. I am mentally sharp and otherwise independent, but I use a walker and can walk only about 100 meters at a time. I do not want to use a wheelchair. I want to be able to reach dining, activities and the main services without long internal walks. I also enjoy movies, music and social activities.",
    limit: 5,
  },
  {
    id: "NURSING-2-GLUTEN-WIDOW",
    questionnaire_state: { relationship: "Myself", ageGroup: "75-79", assistanceLevel: "Independent", memoryStatus: "No", budget: 10000, distanceFromFamily: "Balanced location" },
    natural_language_query: "I am a 76-year-old widow looking for senior living in Las Vegas. I am independent and do not have dementia. I do not cook, so I need all daily meals provided. I have a medically important gluten allergy and need safe gluten-free food with cross-contact controls. I prefer a high-quality comfortable community, enjoy company, card games, classes and organized activities, and I do not want to feel isolated.",
    limit: 5,
  },
] as const;

type Scenario = (typeof scenarios)[number];
type AnyState = Record<string, any>;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function ensureAdaptiveState(input: Record<string, unknown>): AnyState {
  const state: AnyState = clone(input);
  state.humanIntelligenceV2 ||= {};
  state.humanIntelligenceV2.personalityProfile ||= {};
  state.humanIntelligenceV2.familyProfile ||= {};
  state.humanIntelligenceV2.transitionRiskProfile ||= {};
  state.humanIntelligenceV2.scoringEngine ||= {};
  state.humanIntelligenceV2.scoringEngine.adaptiveSignals ||= [];
  return state;
}

async function callDecisionEngine(scenario: Scenario, questionnaireState: AnyState) {
  const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ questionnaire_state: questionnaireState, natural_language_query: scenario.natural_language_query, limit: scenario.limit }),
    cache: "no-store",
  });
  const raw = await response.text();
  if (!response.ok) throw new Error(`Decision engine ${response.status}: ${raw.slice(0, 500)}`);
  return raw ? JSON.parse(raw) : {};
}

function intelligenceOf(payload: any) {
  return payload?.decision_intelligence || payload?.patient_needs_profile?.decision_intelligence || payload?.care_setting_policy?.decision_intelligence || {};
}

function humanOf(payload: any) {
  const intelligence = intelligenceOf(payload);
  return intelligence?.human_intelligence || {};
}

function scriptedAnswer(scenarioId: string, question: string, turn: number): string {
  const q = question.toLowerCase();
  if (scenarioId === "NURSING-1-WALKER-100M") {
    if (/bathing|dressing|toileting|bed|chair|medication/.test(q)) return "No. I manage bathing, dressing, toileting, transfers, and medications independently. I only use a walker for mobility.";
    if (/budget|8,?000|cost|monthly/.test(q)) return "My total budget is up to $8,000 per month, including housing, meals, and required recurring fees.";
    if (/100 meters|distance|how far|internal walk|route/.test(q)) return "I want dining, activities, elevators, and essential services reachable within about 100 meters from my unit, preferably with places to sit and rest.";
    if (/wheelchair/.test(q)) return "I strongly prefer to remain mobile with my walker and do not want routine wheelchair use unless medically necessary in the future.";
    if (/social|activities|movies|music/.test(q)) return "Social activities matter, especially movies and music, but safe short walking distances and independence come first.";
    return `For this test, my answer is explicit and known: preserve my independence, walker mobility, 100-meter walking limit, and short internal routes. Turn ${turn}.`;
  }
  if (/high-quality|comfortable|which matters|quality/.test(q)) return "A warm welcoming atmosphere and excellent dining and service matter most, followed by a comfortable well-maintained apartment.";
  if (/budget|10,?000|cost|monthly/.test(q)) return "My total budget is up to $10,000 per month, including housing, all daily meals, and required recurring fees.";
  if (/widow|bereavement|loss|husband|spouse/.test(q)) return "My husband died two years ago. I value companionship, but I am not seeking specialized bereavement care.";
  if (/gluten|allergy|cross-contact|food/.test(q)) return "This is a medical requirement. I need all daily meals to be safely gluten-free with verified cross-contact prevention procedures.";
  if (/social|isolated|company|activities|cards|classes/.test(q)) return "Regular companionship and organized activities are important to me. I especially want card games, classes, and an easy way for new residents to join social life.";
  return `For this test, my answer is explicit and known: all daily meals, medically safe gluten-free dining with cross-contact controls, and strong social integration are required. Turn ${turn}.`;
}

function applyAnswer(state: AnyState, question: any, answer: string): AnyState {
  const next = ensureAdaptiveState(state);
  const key = String(question?.question_key || "");
  const signals = next.humanIntelligenceV2.scoringEngine.adaptiveSignals || [];
  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = [
    ...signals.filter((signal: any) => signal?.questionKey !== key),
    {
      questionKey: key,
      question: String(question?.question || ""),
      answer,
      knowledgeState: answer.toLowerCase().includes("not sure") ? "UNKNOWN" : "KNOWN",
      signalType: "decision-interview",
      weights: { informationGain: question?.information_gain === "HIGH" ? 1 : 0 },
      impactExplanation: question?.reason || "Explicit answer in synthetic governed multi-turn E2E.",
      infoGain: question?.information_gain === "HIGH" ? 1 : 0,
    },
  ];
  next.humanIntelligenceV2.scoringEngine.additionalQuestionAsked = String(question?.question || "");
  return next;
}

function summarize(payload: any) {
  const intelligence = intelligenceOf(payload);
  const human = humanOf(payload);
  return {
    decisionReadiness: human?.decision_readiness ?? intelligence?.decision_readiness ?? null,
    adaptiveQuestions: (human?.adaptive_questions || intelligence?.adaptive_questions || []).map((q: any) => ({ questionKey: q?.question_key ?? null, question: q?.question ?? q?.prompt ?? null })),
    semanticAI: human?.semantic_ai ?? intelligence?.semantic_ai ?? null,
    decisionFinality: intelligence?.decision_finality ?? intelligence?.agent_evidence_bridge?.decision_finality ?? null,
    recommendationExecutionAllowed: intelligence?.recommendation_execution_allowed ?? null,
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

async function runMultiTurn(scenario: Scenario) {
  let state = ensureAdaptiveState(scenario.questionnaire_state);
  const turns: any[] = [];
  const answeredKeys = new Set<string>();
  const maxTurns = 6;
  let finalPayload: any = null;

  for (let turn = 0; turn < maxTurns; turn += 1) {
    const payload = await callDecisionEngine(scenario, state);
    finalPayload = payload;
    const summary = summarize(payload);
    turns.push({ turn: turn + 1, inputAdaptiveSignals: state.humanIntelligenceV2.scoringEngine.adaptiveSignals, output: summary });

    if (summary.decisionReadiness === "READY" || summary.decisionReadiness === "NEEDS_RESEARCH") break;
    const questions = humanOf(payload)?.adaptive_questions || intelligenceOf(payload)?.adaptive_questions || [];
    const nextQuestion = questions.find((q: any) => q?.question_key && !answeredKeys.has(String(q.question_key)));
    if (!nextQuestion) break;
    const key = String(nextQuestion.question_key);
    const answer = scriptedAnswer(scenario.id, String(nextQuestion.question || ""), turn + 1);
    answeredKeys.add(key);
    state = applyAnswer(state, nextQuestion, answer);
    turns[turn].syntheticAnswer = { questionKey: key, question: nextQuestion.question, answer };
  }

  const final = summarize(finalPayload || {});
  return {
    id: scenario.id,
    input: { questionnaire_state: scenario.questionnaire_state, natural_language_query: scenario.natural_language_query },
    turns,
    final,
    assertions: {
      noRecommendationsBeforeReady: turns.every((row) => row.output.decisionReadiness === "READY" || Number(row.output.resultCount || 0) === 0),
      reachedReady: final.decisionReadiness === "READY",
      stoppedForResearch: final.decisionReadiness === "NEEDS_RESEARCH",
      recommendationsOnlyIfReady: Number(final.resultCount || 0) === 0 || final.decisionReadiness === "READY",
      recommendationExecutionAllowedOnlyIfReady: final.recommendationExecutionAllowed !== true || final.decisionReadiness === "READY",
    },
  };
}

export async function GET(request: NextRequest) {
  try {
    const requestedId = request.nextUrl.searchParams.get("id");
    const mode = request.nextUrl.searchParams.get("mode") || "single";
    const selected = requestedId ? scenarios.filter((scenario) => scenario.id === requestedId) : scenarios;
    if (requestedId && selected.length === 0) {
      return NextResponse.json({ status: "FAIL", error: "UNKNOWN_SCENARIO", supported: scenarios.map((scenario) => scenario.id) }, { status: 400 });
    }

    if (mode === "multi") {
      const rows = [];
      for (const scenario of selected) rows.push(await runMultiTurn(scenario));
      return NextResponse.json({ status: "COMPLETED", mode: "MULTI_TURN", backend: BACKEND_BASE, fixturePolicy: "Invented resident/family scenarios; read-only; answers follow the same generic adaptiveSignals contract as the production UI.", rows }, { headers: { "Cache-Control": "no-store" } });
    }

    const rows = [];
    for (const scenario of selected) {
      const payload = await callDecisionEngine(scenario, ensureAdaptiveState(scenario.questionnaire_state));
      rows.push({ id: scenario.id, input: { questionnaire_state: scenario.questionnaire_state, natural_language_query: scenario.natural_language_query }, output: summarize(payload) });
    }
    return NextResponse.json({ status: "COMPLETED", mode: "SINGLE_TURN", backend: BACKEND_BASE, fixturePolicy: "Two invented resident/family scenarios; read-only; no production data mutation.", rows }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ status: "FAIL", detail: error instanceof Error ? error.message : String(error) }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
