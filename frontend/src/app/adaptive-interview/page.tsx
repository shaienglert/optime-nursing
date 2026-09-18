"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { restoreQuestionnaireState, type QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientNeedsProfile, persistAdaptiveQuestionSignal, type PatientNeedsProfile } from "@/lib/api";
import { canonicalizeAdaptiveFact } from "@/lib/decision-fact-canonicalization";

type AdaptiveQuestion = {
  question_key: string;
  question: string;
  reason?: string;
  decision_dimensions?: string[];
  information_gain?: string;
  answer_options?: string[];
  policy_reference?: string;
  target_fact_key?: string;
};

type NeedsProfileWithDecisionIntelligence = PatientNeedsProfile & {
  decision_intelligence?: {
    human_intelligence?: {
      decision_readiness?: string;
      adaptive_questions?: AdaptiveQuestion[];
      semantic_ai?: { result?: { questionnaire_patch?: Record<string, unknown> } };
    };
    adaptive_questions?: AdaptiveQuestion[];
    canonical_decision_state?: {
      authoritative?: boolean;
      client?: string;
      phase?: string;
    };
  };
};

const UI_REQUEST_TIMEOUT_MS = 320000;

function cloneState(state: QuestionnaireState): QuestionnaireState {
  return JSON.parse(JSON.stringify(state)) as QuestionnaireState;
}

function getDecisionContext(profile: NeedsProfileWithDecisionIntelligence) {
  const top = profile.decision_intelligence;
  const nested = top?.human_intelligence;
  return {
    canonical: top?.canonical_decision_state,
    adaptive_questions: top?.adaptive_questions || nested?.adaptive_questions || [],
    questionnaire_patch: nested?.semantic_ai?.result?.questionnaire_patch || {},
  };
}

function applySemanticQuestionnairePatch(state: QuestionnaireState, patch: Record<string, unknown>): QuestionnaireState {
  const next = cloneState(state);
  const stringKeys: Array<keyof QuestionnaireState> = [
    "relationship", "ageGroup", "assistanceLevel", "memoryStatus",
    "medicaidStatus", "referenceLocationValue",
  ];
  for (const key of stringKeys) {
    const value = patch[key];
    if (typeof value === "string" && value.trim()) {
      (next as unknown as Record<string, unknown>)[key] = value.trim();
    }
  }
  if (typeof patch.budget === "number" && Number.isFinite(patch.budget) && patch.budget > 0) {
    next.budget = Math.round(patch.budget);
  }

  const medical = patch.medicalCareProfile;
  if (medical && typeof medical === "object" && !Array.isArray(medical)) {
    const source = medical as Record<string, unknown>;
    const medicalStringKeys: Array<keyof QuestionnaireState["medicalCareProfile"]> = [
      "hasOngoingMedicalNeeds", "mobilityMethod", "transferAssistance", "recentFalls",
      "dialysisFrequency", "dialysisCenter", "dialysisTransportation", "oxygenUse",
      "woundCareFrequency", "complexConditionDetails", "physicianCoordination",
    ];
    for (const key of medicalStringKeys) {
      const value = source[key];
      if (typeof value === "string" && value.trim()) {
        (next.medicalCareProfile as unknown as Record<string, unknown>)[key] = value.trim();
      }
    }
    if (Array.isArray(source.needs)) {
      next.medicalCareProfile.needs = source.needs.map(String).map((value) => value.trim()).filter(Boolean);
    }
  }

  const human = patch.humanIntelligenceV2;
  if (human && typeof human === "object" && !Array.isArray(human)) {
    const source = human as Record<string, unknown>;
    const mergeStrings = (target: Record<string, unknown>, candidate: unknown) => {
      if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return;
      for (const [key, value] of Object.entries(candidate as Record<string, unknown>)) {
        if (typeof value === "string" && value.trim() && key in target) target[key] = value.trim();
        if (Array.isArray(value) && key in target) target[key] = value.map(String).map((item) => item.trim()).filter(Boolean);
      }
    };
    mergeStrings(next.humanIntelligenceV2.transitionRiskProfile as unknown as Record<string, unknown>, source.transitionRiskProfile);
    mergeStrings(next.humanIntelligenceV2.languageProfile as unknown as Record<string, unknown>, source.languageProfile);
    mergeStrings(next.humanIntelligenceV2.foodProfile as unknown as Record<string, unknown>, source.foodProfile);
    mergeStrings(next.humanIntelligenceV2.futureCareProfile as unknown as Record<string, unknown>, source.futureCareProfile);
  }

  next.questionnaireCompletion = {
    ...next.questionnaireCompletion,
    clientSummaryConfirmed: false,
    confirmedAt: "",
  };
  return next;
}

function existingAnswerFor(question: AdaptiveQuestion, state: QuestionnaireState): string | null {
  const key = String(question.target_fact_key || "").toLowerCase();
  const text = `${question.question} ${(question.decision_dimensions || []).join(" ")}`.toLowerCase();
  const hi = state.humanIntelligenceV2;

  if (/market|location|city|area|geograph/.test(key + " " + text)) {
    return state.referenceLocationValue?.trim() || state.referenceAddress?.trim() || null;
  }
  if (/budget|afford|monthly/.test(key + " " + text)) {
    return state.budget > 0 ? `$${state.budget.toLocaleString("en-US")} per month` : null;
  }
  if (key.includes("community_size")) return hi.personalityProfile.communitySizePreference || null;
  if (key.includes("social_interaction")) return hi.familyProfile.socialInteractionNeed || hi.socialProfile.preferredSocialIntensity || null;
  if (key.includes("move") || key.includes("transition")) return hi.transitionRiskProfile.attitudeTowardMove || null;
  if (key.includes("language")) return hi.languageProfile.preferredSpokenLanguage || hi.languageProfile.nativeLanguage || null;
  if (key.includes("relig")) return hi.culturalProfile.religionImportance || null;
  if (key.includes("grief")) return hi.familyProfile.griefSupportInterest || null;
  if (key.includes("widow") || key.includes("bereavement")) return hi.familyProfile.widowStatus || hi.transitionRiskProfile.bereavementStatus || null;
  if (key.includes("memory")) return state.memoryStatus || null;
  if (key.includes("care") || key.includes("adl") || key.includes("assistance")) return state.assistanceLevel || null;
  return null;
}

function applyAnswer(state: QuestionnaireState, question: AdaptiveQuestion, answer: string): QuestionnaireState {
  let next = cloneState(state);
  next.questionnaireCompletion = {
    ...next.questionnaireCompletion,
    clientSummaryConfirmed: false,
    confirmedAt: "",
  };
  const targetFactKey = String(question.target_fact_key || "").trim();
  const signals = next.humanIntelligenceV2.scoringEngine.adaptiveSignals || [];
  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = [
    ...signals.filter((signal) => signal.questionKey !== question.question_key),
    {
      questionKey: question.question_key,
      answer,
      signalType: "decision-interview",
      weights: { informationGain: question.information_gain === "HIGH" ? 1 : 0 },
      impactExplanation: `Question: ${question.question}${targetFactKey ? ` | Target fact: ${targetFactKey}` : ""} | explicit client answer`,
      infoGain: question.information_gain === "HIGH" ? 1 : 0,
    },
  ];
  if (targetFactKey) next = canonicalizeAdaptiveFact(next, targetFactKey, answer);
  return next;
}

async function withTimeout<T>(promise: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error("This is taking longer than expected. Please try again.")), UI_REQUEST_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export default function AdaptiveInterviewPage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const autoResolved = useRef<Set<string>>(new Set());
  const [question, setQuestion] = useState<AdaptiveQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nextUrl = useRef("/results");

  async function continueDecision(currentState: QuestionnaireState, destination: string, depth = 0): Promise<void> {
    if (depth > 8) {
      setError("We could not resolve the interview state cleanly. Please try again.");
      setBusy(false);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = (await withTimeout(fetchPatientNeedsProfile({
        questionnaire_state: currentState as unknown as Record<string, unknown>,
        natural_language_query: currentState.notes || "",
      }))) as NeedsProfileWithDecisionIntelligence;
      const context = getDecisionContext(response);
      const hydratedState = applySemanticQuestionnairePatch(currentState, context.questionnaire_patch);
      if (JSON.stringify(hydratedState) !== JSON.stringify(currentState)) setState(hydratedState);

      if (context.canonical?.authoritative !== true) {
        setError("The decision state could not be verified. Please try again.");
        setBusy(false);
        return;
      }

      if (context.canonical.client === "COMPLETE") {
        setQuestion(null);
        setState(hydratedState);
        router.replace(`/intake-confirmation?next=${encodeURIComponent(destination)}`);
        return;
      }

      const nextQuestion = (context.adaptive_questions || [])[0];
      if (!nextQuestion) {
        setError("We still need information, but no useful next question was returned.");
        setBusy(false);
        return;
      }

      const existing = existingAnswerFor(nextQuestion, hydratedState);
      if (existing && !autoResolved.current.has(nextQuestion.question_key)) {
        autoResolved.current.add(nextQuestion.question_key);
        const resolvedState = applyAnswer(hydratedState, nextQuestion, existing);
        setState(resolvedState);
        await continueDecision(resolvedState, destination, depth + 1);
        return;
      }

      setQuestion(nextQuestion);
      setAnswer("");
      setBusy(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to continue the decision right now.");
      setBusy(false);
    }
  }

  useEffect(() => {
    // A navigation can mount this page before React commits the provider update.
    // The home page persists the complete snapshot first, so use that snapshot as
    // the authority for this initial gate instead of redirecting on stale context.
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("next");
    const destination = requested?.startsWith("/results") ? requested : "/results";
    const storyFromDestination = requested?.startsWith("/results")
      ? new URL(requested, window.location.origin).searchParams.get("notes")?.trim() || ""
      : "";
    const restoredState = restoreQuestionnaireState();
    const restoredOrCurrent = restoredState.notes?.trim() ? restoredState : state;
    const initialState = !restoredOrCurrent.notes?.trim() && storyFromDestination
      ? { ...restoredOrCurrent, notes: storyFromDestination }
      : restoredOrCurrent;
    const structuredQuestionnaireComplete =
      initialState.questionnaireCompletion?.mandatoryComplete &&
      initialState.questionnaireCompletion?.conditionalFollowUpsComplete;
    const hasOpeningStory = Boolean(initialState.notes?.trim());

    // The story path is a real AI intake, not a shortcut into the manual form.
    // Semantic AI reads the narrative, accounts for every statement, and asks only
    // for material missing facts. A visitor with neither a completed form nor a
    // story still belongs in the structured questionnaire.
    if (!structuredQuestionnaireComplete && !hasOpeningStory) {
      router.replace("/intake");
      return;
    }
    if (initialState !== state) setState(initialState);
    nextUrl.current = destination;
    void continueDecision(cloneState(initialState), destination);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitAnswer(raw: string) {
    if (!question || busy) return;
    const value = raw.trim();
    if (!value) return;
    setBusy(true);
    const nextState = applyAnswer(state, question, value);
    setState(nextState);
    void persistAdaptiveQuestionSignal({
      resident_key: "decision-interview-session",
      question_key: question.question_key,
      answer: value,
      signal_type: "decision-interview",
      signal_json: JSON.stringify({
        question: question.question,
        target_fact_key: question.target_fact_key || null,
        explicit_answer: true,
      }),
      weights_json: JSON.stringify({ information_gain: question.information_gain || "UNKNOWN" }),
      impact_explanation: `Question: ${question.question} | explicit client answer`,
      info_gain_score: question.information_gain === "HIGH" ? 1 : 0,
    }).catch(() => undefined);
    await continueDecision(nextState, nextUrl.current);
  }

  const options = question?.answer_options || [];

  return (
    <main className="min-h-screen bg-[#f8f5ef] px-5 py-10 text-[#22332d] sm:px-8">
      <section className="mx-auto max-w-4xl rounded-[2rem] border border-[#ded6c9] bg-white p-7 shadow-sm sm:p-10">
        <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">OPTIME</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight sm:text-5xl">One thing that could improve the decision</h1>
        <p className="mt-4 text-xl leading-8 text-[#5b6863]">We use everything you already told us. We only ask when an important answer is genuinely missing.</p>

        {error ? (
          <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-xl leading-8 text-rose-800">
            <p>{error}</p>
            <button type="button" onClick={() => void continueDecision(cloneState(state), nextUrl.current)} className="mt-5 rounded-2xl bg-[#315f53] px-6 py-4 text-xl font-semibold text-white">Try again</button>
          </div>
        ) : null}

        {question ? (
          <div className="mt-8">
            <div className="rounded-2xl bg-[#eef7f2] p-6">
              <p className="text-2xl font-semibold leading-9 sm:text-3xl">{question.question}</p>
            </div>

            {options.length > 0 ? (
              <div className="mt-6 grid gap-3">
                {options.map((option) => (
                  <button key={option} type="button" disabled={busy} onClick={() => void submitAnswer(option)} className="rounded-2xl border-2 border-[#d7ddd8] bg-white px-6 py-5 text-left text-xl font-semibold hover:border-[#5c8b7d] hover:bg-[#f2f8f5] disabled:opacity-50">{option}</button>
                ))}
              </div>
            ) : (
              <form className="mt-6" onSubmit={(event) => { event.preventDefault(); void submitAnswer(answer); }}>
                <label htmlFor="decision-answer" className="text-xl font-semibold">Your answer</label>
                <textarea id="decision-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} disabled={busy} rows={3} className="mt-3 w-full rounded-2xl border-2 border-[#d7ddd8] px-5 py-4 text-xl leading-8 outline-none focus:border-[#5c8b7d]" />
                <button type="submit" disabled={busy || !answer.trim()} className="mt-4 rounded-2xl bg-[#315f53] px-7 py-4 text-xl font-semibold text-white disabled:opacity-50">{busy ? "Using your answer…" : "Continue"}</button>
              </form>
            )}
          </div>
        ) : null}

        {busy ? (
          <div className="mt-8 rounded-2xl bg-[#f4f1ea] p-6 text-xl leading-8 text-[#5d5548]">Using the information you already provided…</div>
        ) : null}
      </section>
    </main>
  );
}
