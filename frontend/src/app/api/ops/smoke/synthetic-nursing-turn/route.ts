import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const maxDuration = 120;

const BACKEND_BASE = (
  process.env.BACKEND_INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "https://optime-nursing.onrender.com"
).replace(/\/+$/, "");

const scenarios = {
  "NURSING-1-WALKER-100M": {
    questionnaire_state: { relationship: "Myself", ageGroup: "80-84", assistanceLevel: "Mostly independent", memoryStatus: "No", budget: 8000, distanceFromFamily: "Balanced location" },
    natural_language_query: "I am 80 and looking for senior living in Las Vegas. I am mentally sharp and otherwise independent, but I use a walker and can walk only about 100 meters at a time. I do not want to use a wheelchair. I want to be able to reach dining, activities and the main services without long internal walks. I also enjoy movies, music and social activities.",
    limit: 5,
  },
  "NURSING-2-GLUTEN-WIDOW": {
    questionnaire_state: { relationship: "Myself", ageGroup: "75-79", assistanceLevel: "Independent", memoryStatus: "No", budget: 10000, distanceFromFamily: "Balanced location" },
    natural_language_query: "I am a 76-year-old widow looking for senior living in Las Vegas. I am independent and do not have dementia. I do not cook, so I need all daily meals provided. I have a medically important gluten allergy and need safe gluten-free food with cross-contact controls. I prefer a high-quality comfortable community, enjoy company, card games, classes and organized activities, and I do not want to feel isolated.",
    limit: 5,
  },
} as const;

type ScenarioId = keyof typeof scenarios;
type AnswerRecord = { questionKey: string; question: string; answer: string; knowledgeState?: "KNOWN" | "UNKNOWN" };
type AnyState = Record<string, any>;

function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)); }
function ensureState(input: Record<string, unknown>): AnyState {
  const state: AnyState = clone(input);
  state.humanIntelligenceV2 ||= {};
  state.humanIntelligenceV2.personalityProfile ||= {};
  state.humanIntelligenceV2.familyProfile ||= {};
  state.humanIntelligenceV2.transitionRiskProfile ||= {};
  state.humanIntelligenceV2.scoringEngine ||= {};
  state.humanIntelligenceV2.scoringEngine.adaptiveSignals ||= [];
  return state;
}

function decodeAnswers(token: string | null): AnswerRecord[] {
  if (!token) return [];
  try {
    const json = Buffer.from(token, "base64url").toString("utf8");
    const value = JSON.parse(json);
    return Array.isArray(value) ? value.filter((row) => row && typeof row.questionKey === "string" && typeof row.answer === "string") : [];
  } catch {
    throw new Error("INVALID_ANSWERS_TOKEN");
  }
}
function encodeAnswers(rows: AnswerRecord[]): string { return Buffer.from(JSON.stringify(rows), "utf8").toString("base64url"); }

function applyAnswers(state: AnyState, answers: AnswerRecord[]): AnyState {
  const next = ensureState(state);
  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = answers.map((row) => ({
    questionKey: row.questionKey,
    question: row.question,
    answer: row.answer,
    knowledgeState: row.knowledgeState || "KNOWN",
    signalType: "decision-interview",
    weights: { informationGain: 1 },
    impactExplanation: "Explicit answer in synthetic governed turn-by-turn E2E.",
    infoGain: 1,
  }));
  const last = answers.at(-1);
  if (last) next.humanIntelligenceV2.scoringEngine.additionalQuestionAsked = last.question;
  return next;
}

function intelligenceOf(payload: any) {
  return payload?.decision_intelligence || payload?.patient_needs_profile?.decision_intelligence || payload?.care_setting_policy?.decision_intelligence || {};
}
function humanOf(payload: any) { return intelligenceOf(payload)?.human_intelligence || {}; }

function summarize(payload: any) {
  const intelligence = intelligenceOf(payload);
  const human = humanOf(payload);
  const questions = human?.adaptive_questions || intelligence?.adaptive_questions || [];
  return {
    decisionReadiness: human?.decision_readiness ?? intelligence?.decision_readiness ?? null,
    adaptiveQuestions: questions.map((q: any) => ({ questionKey: q?.question_key ?? null, question: q?.question ?? q?.prompt ?? null })),
    semanticAI: human?.semantic_ai ?? intelligence?.semantic_ai ?? null,
    decisionFinality: intelligence?.decision_finality ?? intelligence?.agent_evidence_bridge?.decision_finality ?? null,
    recommendationExecutionAllowed: intelligence?.recommendation_execution_allowed ?? null,
    resultCount: payload?.result_count ?? null,
    mustGate: intelligence?.must_gate ?? null,
    top5: (payload?.results || []).slice(0, 5).map((row: any) => ({
      id: row?.canonical_facility_id ?? null,
      name: row?.facility_name ?? null,
      rank: row?.rank_position ?? null,
      hardGate: row?.client_intent_fit?.hard_gate ?? null,
      mustPass: row?.client_intent_fit?.must_pass ?? [],
      mustUnknown: row?.client_intent_fit?.must_unknown ?? [],
      mustFail: row?.client_intent_fit?.must_fail ?? [],
    })),
  };
}

function scriptedAnswer(id: ScenarioId, question: string): string {
  const q = question.toLowerCase();
  if (id === "NURSING-1-WALKER-100M") {
    if (/bathing|dressing|toileting|bed|chair|medication/.test(q)) return "No. I manage bathing, dressing, toileting, transfers, and medications independently. I only use a walker for mobility.";
    if (/budget|8,?000|cost|monthly/.test(q)) return "My total budget is up to $8,000 per month, including housing, meals, and required recurring fees.";
    if (/100 meters|distance|how far|internal walk|route/.test(q)) return "Dining, activities, elevators, and essential services should be within about 100 meters from my unit, preferably with places to sit and rest.";
    if (/wheelchair/.test(q)) return "I strongly prefer to remain mobile with my walker and do not want routine wheelchair use unless medically necessary later.";
    if (/social|activities|movies|music/.test(q)) return "Movies, music, and social activities matter, but independence and safe short walking distances come first.";
    return "My priority is to preserve independence, walker mobility, a roughly 100-meter walking limit, and short internal routes.";
  }
  if (/high-quality|comfortable|which matters|quality/.test(q)) return "A warm welcoming atmosphere and excellent dining and service matter most, followed by a comfortable well-maintained apartment.";
  if (/budget|10,?000|cost|monthly/.test(q)) return "My total budget is up to $10,000 per month, including housing, all daily meals, and required recurring fees.";
  if (/widow|bereavement|loss|husband|spouse/.test(q)) return "My husband died two years ago. I value companionship, but I am not seeking specialized bereavement care.";
  if (/gluten|allergy|cross-contact|food/.test(q)) return "This is a medical requirement. I need all daily meals safely gluten-free with verified cross-contact prevention procedures.";
  if (/social|isolated|company|activities|cards|classes/.test(q)) return "Regular companionship and organized activities are important. I especially want card games, classes, and easy social integration for new residents.";
  return "All daily meals, medically safe gluten-free dining with cross-contact controls, and strong social integration are required.";
}

export async function GET(request: NextRequest) {
  try {
    const id = request.nextUrl.searchParams.get("id") as ScenarioId | null;
    if (!id || !(id in scenarios)) return NextResponse.json({ status: "FAIL", error: "UNKNOWN_SCENARIO", supported: Object.keys(scenarios) }, { status: 400 });
    const answers = decodeAnswers(request.nextUrl.searchParams.get("answers"));
    const scenario = scenarios[id];
    const state = applyAnswers(scenario.questionnaire_state, answers);

    const response = await fetch(`${BACKEND_BASE}/decision-engine/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionnaire_state: state, natural_language_query: scenario.natural_language_query, limit: scenario.limit }),
      cache: "no-store",
    });
    const raw = await response.text();
    if (!response.ok) throw new Error(`Decision engine ${response.status}: ${raw.slice(0, 500)}`);
    const payload = raw ? JSON.parse(raw) : {};
    const output = summarize(payload);
    const nextQuestion = output.adaptiveQuestions[0];
    let continueToken: string | null = null;
    let proposedAnswer: AnswerRecord | null = null;
    if (output.decisionReadiness === "NEEDS_CLARIFICATION" && nextQuestion?.questionKey && nextQuestion?.question) {
      proposedAnswer = { questionKey: nextQuestion.questionKey, question: nextQuestion.question, answer: scriptedAnswer(id, nextQuestion.question), knowledgeState: "KNOWN" };
      continueToken = encodeAnswers([...answers.filter((row) => row.questionKey !== proposedAnswer!.questionKey), proposedAnswer]);
    }

    return NextResponse.json({
      status: "COMPLETED",
      mode: "TURN_BY_TURN",
      id,
      turn: answers.length + 1,
      priorAnswers: answers,
      output,
      proposedAnswer,
      continueToken,
      assertions: {
        noRecommendationBeforeReady: output.decisionReadiness === "READY" || Number(output.resultCount || 0) === 0,
        recommendationExecutionOnlyIfReady: output.recommendationExecutionAllowed !== true || output.decisionReadiness === "READY",
      },
    }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ status: "FAIL", detail: error instanceof Error ? error.message : String(error) }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
