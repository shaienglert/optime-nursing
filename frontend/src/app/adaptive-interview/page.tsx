"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { restoreQuestionnaireState, type QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientNeedsProfile, persistAdaptiveQuestionSignal, type PatientNeedsProfile } from "@/lib/api";
import { applyAdaptiveAnswer, type AdaptiveQuestion } from "@/lib/adaptive-answer";
import { applySemanticQuestionnairePatch } from "@/lib/semantic-questionnaire-patch";
import { canonicalRecoveryQuestion, hasUnresolvedSemanticConflict, semanticConflictQuestion, semanticIntakeFailure } from "@/lib/semantic-conflict";
import { OomnikMark } from "@/components/brand/oomnik-mark";



type NeedsProfileWithDecisionIntelligence = PatientNeedsProfile & {
  decision_intelligence?: {
    human_intelligence?: {
      decision_readiness?: string;
      adaptive_questions?: AdaptiveQuestion[];
      semantic_ai?: { enabled?: boolean; required?: boolean; status?: string; result?: { questionnaire_patch?: Record<string, unknown>; statements?: unknown } };
    };
    adaptive_questions?: AdaptiveQuestion[];
    canonical_decision_state?: {
      authoritative?: boolean;
      client?: string;
      phase?: string;
      system?: string;
      next_action?: string;
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
  const conflictQuestion = semanticConflictQuestion(nested?.semantic_ai?.result?.statements);
  return {
    canonical: top?.canonical_decision_state,
    semanticFailed: semanticIntakeFailure(nested?.semantic_ai),
    hasConflict: hasUnresolvedSemanticConflict(nested?.semantic_ai?.result?.statements),
    adaptive_questions: conflictQuestion ? [conflictQuestion] : top?.adaptive_questions?.length
      ? top.adaptive_questions : nested?.adaptive_questions || [],
    questionnaire_patch: nested?.semantic_ai?.result?.questionnaire_patch || {},
  };
}



function conversationWisdom(question: AdaptiveQuestion): string {
  const text = `${question.target_fact_key || ""} ${question.question} ${(question.decision_dimensions || []).join(" ")}`.toLowerCase();
  if (/memory|cognitive/.test(text)) return "Familiar routines and the right support can help a person keep more of what feels like home.";
  if (/mobility|assist|adl|care/.test(text)) return "The right support should make independence easier, not smaller.";
  if (/social|activity|lifestyle|community/.test(text)) return "A good next chapter should preserve what makes everyday life worth looking forward to.";
  if (/budget|cost|afford/.test(text)) return "A good decision has to work in everyday life — including financially.";
  if (/location|distance|geograph/.test(text)) return "Being close to the people and places that matter can be part of feeling at home.";
  if (/language|culture|relig/.test(text)) return "Feeling understood is about more than care — language, culture and traditions can matter too.";
  return "";
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
  const [question, setQuestion] = useState<AdaptiveQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const nextUrl = useRef("/results");

  async function continueDecision(currentState: QuestionnaireState, destination: string): Promise<void> {

    setBusy(true);
    setError(null);
    try {
      const response = (await withTimeout(fetchPatientNeedsProfile({
        questionnaire_state: currentState as unknown as Record<string, unknown>,
        natural_language_query: currentState.notes || "",
      }))) as NeedsProfileWithDecisionIntelligence;
      const context = getDecisionContext(response);

      if (context.canonical?.authoritative !== true) {
        setError("The decision state could not be verified. Please try again.");
        setBusy(false);
        return;
      }

      if (context.semanticFailed || context.canonical.system === "BLOCKED") {
        const recoveryQuestion = canonicalRecoveryQuestion(response);
        if (recoveryQuestion) {
          setQuestion(recoveryQuestion);
          setAnswer("");
          setBusy(false);
          return;
        }
        setQuestion(null);
        setError("We could not verify our understanding of your answers. Your answers are saved. Please try again.");
        setBusy(false);
        return;
      }

      if (context.canonical.client === "COMPLETE" && !context.hasConflict) {
        const hydratedState = applySemanticQuestionnairePatch(currentState, context.questionnaire_patch);
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

      // The server owns fact resolution. A proposed patch must never answer its
      // own question or trigger another hidden round of interpretation here.
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
    const nextState = applyAdaptiveAnswer(state, question, value);
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
      <section className="mx-auto max-w-3xl p-3 sm:p-6">
        <p className="text-base font-semibold text-[#168fe0]">Oomnik</p>
        <h1 className="mt-3 text-3xl font-medium leading-tight sm:text-4xl">Let’s keep going.</h1>
        <p className="mt-3 text-lg leading-8 text-[#5b6863]">I’ll use everything you’ve already told me, so I won’t make you repeat yourself.</p>

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
              <div className="ml-12 mt-5 flex flex-wrap gap-3">
                {options.map((option) => (
                  <button key={option} type="button" disabled={busy} onClick={() => void submitAnswer(option)} className="rounded-full border border-[#bcd9e7] bg-white px-5 py-3 text-left text-lg font-medium text-[#234f63] shadow-sm hover:border-[#079ff2] hover:bg-[#f2fbff] disabled:opacity-50">{option}</button>
                ))}
              </div>
            ) : (
              <form className="ml-12 mt-5" onSubmit={(event) => { event.preventDefault(); void submitAnswer(answer); }}>
                <label htmlFor="decision-answer" className="sr-only">Your answer</label>
                <textarea id="decision-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} disabled={busy} rows={3} placeholder="Tell me in your own words…" className="w-full rounded-[1.5rem] border border-[#bcd9e7] bg-white px-5 py-4 text-lg leading-8 outline-none focus:border-[#079ff2]" />
                <button type="submit" disabled={busy || !answer.trim()} className="mt-4 inline-flex items-center gap-2 rounded-2xl bg-[#315f53] px-7 py-4 text-xl font-semibold text-white disabled:opacity-50">{!busy && <OomnikMark size={18} />}{busy ? "Using your answer…" : "Continue"}</button>
              </form>
            )}
          </div>
        ) : null}

        {busy ? (
          <div className="mt-8 text-lg leading-8 text-[#5d5548]">Thinking about what you’ve already told me…</div>
        ) : null}
      </section>
    </main>
  );
}
