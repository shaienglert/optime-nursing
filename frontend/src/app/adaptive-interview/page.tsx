"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { type QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
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

type HumanDecisionContext = {
  decision_readiness?: string;
  adaptive_questions?: AdaptiveQuestion[];
};

type NeedsProfileWithDecisionIntelligence = PatientNeedsProfile & {
  decision_intelligence?: {
    human_intelligence?: HumanDecisionContext;
    decision_readiness?: string;
    adaptive_questions?: AdaptiveQuestion[];
  };
};

type AnswerHistoryEntry = {
  question: AdaptiveQuestion;
  answer: string;
  stateBefore: QuestionnaireState;
};

const HISTORY_STORAGE_KEY = "optime-nursing-decision-interview-history-v1";
const UI_REQUEST_TIMEOUT_MS = process.env.NODE_ENV === "production" ? 90000 : 30000;

function cloneState(state: QuestionnaireState): QuestionnaireState {
  return JSON.parse(JSON.stringify(state)) as QuestionnaireState;
}

function parseMonthlyBudget(text: string): number | null {
  if (!/(budget|monthly|per month|month|afford|cost)/i.test(text)) return null;
  const candidates = [...text.matchAll(/\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{4,6})/g)]
    .map((match) => Number(match[1].replace(/,/g, "")))
    .filter((value) => Number.isFinite(value) && value >= 500 && value <= 100000);
  return candidates.length ? Math.max(...candidates) : null;
}

function normalizeInterviewState(state: QuestionnaireState): QuestionnaireState {
  const next = cloneState(state);
  const budgetFromNotes = parseMonthlyBudget(next.notes || "");
  if (budgetFromNotes !== null) {
    next.budget = budgetFromNotes;
  } else if (next.budget === 7000) {
    next.budget = 0;
  }
  return next;
}

function loadHistory(): AnswerHistoryEntry[] {
  try {
    const raw = window.sessionStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: AnswerHistoryEntry[]) {
  try {
    if (entries.length) window.sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries));
    else window.sessionStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch {
    // Editing convenience only; decision safety never depends on browser storage.
  }
}

function getDecisionContext(profile: NeedsProfileWithDecisionIntelligence): HumanDecisionContext {
  const top = profile.decision_intelligence;
  const nested = top?.human_intelligence;
  return {
    decision_readiness: top?.decision_readiness || nested?.decision_readiness,
    adaptive_questions: top?.adaptive_questions || nested?.adaptive_questions || [],
  };
}

async function withUiTimeout<T>(promise: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error("The decision interview is taking too long to respond. Please retry.")), UI_REQUEST_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function applyAdaptiveAnswer(state: QuestionnaireState, question: AdaptiveQuestion, answer: string): QuestionnaireState {
  let next = normalizeInterviewState(state);
  const questionKey = question.question_key;
  const questionText = question.question.trim();
  const targetFactKey = String(question.target_fact_key || "").trim();
  const questionAndDimensions = `${questionText} ${(question.decision_dimensions || []).join(" ")}`;
  const signals = next.humanIntelligenceV2.scoringEngine.adaptiveSignals || [];
  const targetFactTrace = targetFactKey ? ` | Target fact: ${targetFactKey}` : "";

  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = [
    ...signals.filter((signal) => signal.questionKey !== questionKey),
    {
      questionKey,
      answer,
      signalType: "decision-interview",
      weights: { informationGain: question.information_gain === "HIGH" ? 1 : 0 },
      impactExplanation: `Question: ${questionText}${targetFactTrace} | ${question.reason || "Explicit answer to a governed adaptive AI question."}`,
      infoGain: question.information_gain === "HIGH" ? 1 : 0,
    },
  ];

  if (targetFactKey) next = canonicalizeAdaptiveFact(next, targetFactKey, answer);

  if (/(where|location|city|area|market|geograph)/i.test(questionAndDimensions) && answer.toLowerCase() !== "not sure") {
    next.referenceLocationValue = answer;
    next.referenceLocationType = next.referenceLocationType || "preferred search area";
    next.locationImportant = next.locationImportant || "Yes";
  }
  const budget = parseMonthlyBudget(`${questionText} ${answer}`);
  if (/(budget|monthly|afford|cost)/i.test(questionAndDimensions) && budget !== null) {
    next.budget = budget;
  }

  next.humanIntelligenceV2.scoringEngine.additionalQuestionAsked = questionText;
  return next;
}

export default function AdaptiveInterviewPage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const initialStateRef = useRef<QuestionnaireState | null>(null);
  const answeredQuestionKeys = useRef<Set<string>>(new Set());
  const lastRequestedStateRef = useRef<QuestionnaireState | null>(null);
  const [history, setHistory] = useState<AnswerHistoryEntry[]>([]);
  const [question, setQuestion] = useState<AdaptiveQuestion | null>(null);
  const [freeTextAnswer, setFreeTextAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextUrl, setNextUrl] = useState("/results");

  const syncHistory = (entries: AnswerHistoryEntry[]) => {
    setHistory(entries);
    answeredQuestionKeys.current = new Set(entries.map((entry) => entry.question.question_key));
    saveHistory(entries);
  };

  const refresh = async (rawQuestionnaireState: QuestionnaireState, destination = nextUrl) => {
    const questionnaireState = normalizeInterviewState(rawQuestionnaireState);
    lastRequestedStateRef.current = cloneState(questionnaireState);
    setLoading(true);
    setReviewing(false);
    setError(null);
    try {
      const response = (await withUiTimeout(fetchPatientNeedsProfile({
        questionnaire_state: questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: questionnaireState.notes || "",
      }))) as NeedsProfileWithDecisionIntelligence;
      const context = getDecisionContext(response);
      const unansweredQuestions = (context.adaptive_questions || []).filter(
        (candidate) => !answeredQuestionKeys.current.has(candidate.question_key),
      );

      if (context.decision_readiness === "READY") {
        setQuestion(null);
        router.push(destination);
        return;
      }

      if (unansweredQuestions.length === 0) {
        setQuestion(null);
        setError("The decision interview still needs information but did not return a usable next question. Please retry.");
        return;
      }

      setFreeTextAnswer("");
      setQuestion(unansweredQuestions[0]);
    } catch (cause) {
      setQuestion(null);
      setError(cause instanceof Error ? cause.message : "Unable to continue the decision interview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("next");
    const destination = requested?.startsWith("/results") ? requested : "/results";
    const reviewMode = params.get("review") === "1";
    setNextUrl(destination);

    const normalizedState = normalizeInterviewState(state);
    if (normalizedState.budget !== state.budget) setState(normalizedState);

    const savedHistory = loadHistory();
    if (savedHistory.length) {
      syncHistory(savedHistory);
      initialStateRef.current = normalizeInterviewState(savedHistory[0].stateBefore);
    } else if (!initialStateRef.current) {
      initialStateRef.current = cloneState(normalizedState);
    }

    if (reviewMode && savedHistory.length) {
      setReviewing(true);
      setQuestion(null);
      setLoading(false);
      return;
    }

    void refresh(normalizedState, destination);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const options = question?.answer_options || [];

  const answerQuestion = async (rawAnswer: string) => {
    if (!question || submitting) return;
    const answer = rawAnswer.trim();
    if (!answer) {
      setError("Please answer the question before continuing.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const answeredKey = question.question_key;
      const stateBefore = cloneState(state);
      const nextState = applyAdaptiveAnswer(state, question, answer);
      const nextHistory = [...history, { question, answer, stateBefore }];
      syncHistory(nextHistory);
      setState(nextState);
      void persistAdaptiveQuestionSignal({
        resident_key: "decision-interview-session",
        question_key: answeredKey,
        answer,
        signal_type: "decision-interview",
        signal_json: JSON.stringify({
          question: question.question,
          target_fact_key: question.target_fact_key || null,
          decision_dimensions: question.decision_dimensions || [],
          policy_reference: question.policy_reference || null,
          explicit_answer: true,
          knowledge_state: answer.toLowerCase() === "not sure" ? "UNKNOWN" : "KNOWN",
        }),
        weights_json: JSON.stringify({ information_gain: question.information_gain || "UNKNOWN" }),
        impact_explanation: `Question: ${question.question}${question.target_fact_key ? ` | Target fact: ${question.target_fact_key}` : ""} | ${question.reason || "Explicit answer used by governed Human Intelligence runtime."}`,
        info_gain_score: question.information_gain === "HIGH" ? 1 : 0,
      }).catch(() => undefined);
      await refresh(nextState);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save this answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const restoreForEdit = (index: number) => {
    if (submitting || loading) return;
    const entry = history[index];
    if (!entry) return;
    const priorHistory = history.slice(0, index);
    syncHistory(priorHistory);
    const restored = normalizeInterviewState(entry.stateBefore);
    setState(restored);
    setQuestion(entry.question);
    setFreeTextAnswer(entry.answer);
    setReviewing(false);
    setError(null);
  };

  const goBack = () => {
    if (submitting || loading) return;
    if (history.length > 0) {
      restoreForEdit(history.length - 1);
      return;
    }
    router.back();
  };

  const startOver = () => {
    if (submitting || loading) return;
    const initial = initialStateRef.current;
    if (initial) setState(cloneState(initial));
    syncHistory([]);
    setQuestion(null);
    setFreeTextAnswer("");
    setReviewing(false);
    setError(null);
    if (initial) void refresh(cloneState(initial));
  };

  const retry = () => {
    if (loading || submitting) return;
    void refresh(lastRequestedStateRef.current ? cloneState(lastRequestedStateRef.current) : cloneState(state));
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e8f4ef_0%,#f8fbfc_42%,#ffffff_78%)] px-6 py-12 sm:px-10">
      <section className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">OPTIME Decision Interview</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">One important question at a time</h1>
        <p className="mt-3 text-base leading-7 text-slate-600">We only ask when the answer can materially change eligibility, ordering, an important trade-off, or the transition plan. Missing information stays unknown until you answer it.</p>

        {history.length > 0 ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <h2 className="font-semibold text-slate-900">Your answers</h2>
            <div className="mt-3 grid gap-3">
              {history.map((entry, index) => (
                <div key={`${entry.question.question_key}-${index}`} className="rounded-xl bg-white p-4">
                  <p className="text-sm text-slate-600">{entry.question.question}</p>
                  <p className="mt-1 font-medium text-slate-950">{entry.answer}</p>
                  <button type="button" disabled={submitting || loading} onClick={() => restoreForEdit(index)} className="mt-2 text-sm font-semibold text-emerald-700 disabled:opacity-50">Edit</button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {loading ? <div className="mt-10 rounded-2xl bg-slate-50 p-6 text-slate-700">Checking what still matters for this decision...</div> : null}
        {!loading && error ? (
          <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800">
            <p>{error}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={retry} className="rounded-2xl bg-emerald-700 px-5 py-3 font-semibold text-white">Retry</button>
              <button type="button" onClick={() => router.push("/")} className="rounded-2xl border border-slate-300 px-5 py-3 font-semibold text-slate-700">Back to start</button>
            </div>
          </div>
        ) : null}

        {!loading && reviewing && !question ? (
          <div className="mt-8 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-6">
            <p className="font-medium text-slate-950">Choose Edit beside any answer above to change it. OPTIME will re-run the governed AI interview and recalculate the decision from that point.</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" onClick={() => router.push(nextUrl)} className="rounded-2xl bg-emerald-700 px-5 py-3 font-semibold text-white">Return to results</button>
              <button type="button" onClick={startOver} className="rounded-2xl border border-slate-300 px-5 py-3 font-semibold text-slate-700">Start over</button>
            </div>
          </div>
        ) : null}

        {!loading && !error && question ? (
          <div className="mt-10">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-6">
              <p className="text-xl font-medium leading-8 text-slate-950">{question.question}</p>
              {question.reason ? <p className="mt-3 text-sm leading-6 text-slate-600">Why we ask: {question.reason}</p> : null}
            </div>

            {options.length > 0 ? (
              <div className="mt-6 grid gap-3">
                {options.map((option) => (
                  <button key={option} type="button" disabled={submitting} onClick={() => void answerQuestion(option)} className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left font-medium text-slate-900 transition hover:border-emerald-400 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60">{option}</button>
                ))}
              </div>
            ) : (
              <form className="mt-6" onSubmit={(event) => { event.preventDefault(); void answerQuestion(freeTextAnswer); }}>
                <label htmlFor="adaptive-answer" className="text-sm font-medium text-slate-700">Your answer</label>
                <textarea id="adaptive-answer" value={freeTextAnswer} onChange={(event) => setFreeTextAnswer(event.target.value)} disabled={submitting} rows={4} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-400 disabled:opacity-60" placeholder="Answer in your own words" />
                <button type="submit" disabled={submitting || !freeTextAnswer.trim()} className="mt-4 rounded-2xl bg-emerald-700 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? "Understanding your answer..." : "Continue"}</button>
              </form>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" disabled={submitting || loading} onClick={goBack} className="rounded-2xl border border-slate-300 px-5 py-3 font-semibold text-slate-700 disabled:opacity-50">Back</button>
              <button type="button" disabled={submitting || loading} onClick={startOver} className="rounded-2xl border border-slate-300 px-5 py-3 font-semibold text-slate-700 disabled:opacity-50">Start over</button>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
