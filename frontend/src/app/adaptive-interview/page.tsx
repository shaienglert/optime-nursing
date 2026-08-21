"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { type QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientNeedsProfile, persistAdaptiveQuestionSignal, type PatientNeedsProfile } from "@/lib/api";

type AdaptiveQuestion = {
  question_key: string;
  question: string;
  reason?: string;
  decision_dimensions?: string[];
  information_gain?: string;
  answer_options?: string[];
  policy_reference?: string;
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

function getDecisionContext(profile: NeedsProfileWithDecisionIntelligence): HumanDecisionContext {
  const top = profile.decision_intelligence;
  const nested = top?.human_intelligence;
  return {
    decision_readiness: top?.decision_readiness || nested?.decision_readiness,
    adaptive_questions: top?.adaptive_questions || nested?.adaptive_questions || [],
  };
}

function applyAdaptiveAnswer(state: QuestionnaireState, question: AdaptiveQuestion, answer: string): QuestionnaireState {
  const next = JSON.parse(JSON.stringify(state)) as QuestionnaireState;
  const questionKey = question.question_key;

  // Preserve the canonical typed fields that deterministic guards already understand.
  if (questionKey === "community_size_preference") {
    next.humanIntelligenceV2.personalityProfile.communitySizePreference = answer;
  } else if (questionKey === "social_interaction_need_after_loss" || questionKey === "social_interaction_preference") {
    next.humanIntelligenceV2.familyProfile.socialInteractionNeed = answer;
  } else if (questionKey === "move_participation") {
    next.humanIntelligenceV2.transitionRiskProfile.attitudeTowardMove = answer;
  }

  // Every governed AI question, including future question types, is also captured generically.
  // The complete questionnaire state is sent back to Semantic AI on the next turn, so the
  // reasoning layer can consume this answer without a frontend whitelist.
  const signals = next.humanIntelligenceV2.scoringEngine.adaptiveSignals || [];
  next.humanIntelligenceV2.scoringEngine.adaptiveSignals = [
    ...signals.filter((signal) => signal.questionKey !== questionKey),
    {
      questionKey,
      answer,
      signalType: "decision-interview",
      weights: { informationGain: question.information_gain === "HIGH" ? 1 : 0 },
      impactExplanation: question.reason || "Explicit answer to a governed adaptive AI question.",
      infoGain: question.information_gain === "HIGH" ? 1 : 0,
    },
  ];
  next.humanIntelligenceV2.scoringEngine.additionalQuestionAsked = question.question;
  return next;
}

function fallbackOptions(questionKey: string): string[] {
  if (questionKey === "community_size_preference") return ["Small community", "Medium community", "Large community", "No preference"];
  if (questionKey === "social_interaction_need_after_loss") return ["Helpful", "Overwhelming", "Neither", "Not sure"];
  if (questionKey === "social_interaction_preference") return ["Very important", "Somewhat important", "Not important", "No preference", "Not sure"];
  if (questionKey === "move_participation") return ["Positive and involved", "Cautious but open", "Reluctant or feels pushed", "Not sure"];
  return [];
}

export default function AdaptiveInterviewPage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [question, setQuestion] = useState<AdaptiveQuestion | null>(null);
  const [freeTextAnswer, setFreeTextAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextUrl, setNextUrl] = useState("/results");
  const answeredQuestionKeys = useRef<Set<string>>(new Set());

  const refresh = async (questionnaireState: QuestionnaireState, destination = nextUrl) => {
    setLoading(true);
    setError(null);
    try {
      const response = (await fetchPatientNeedsProfile({
        questionnaire_state: questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: questionnaireState.notes || "",
      })) as NeedsProfileWithDecisionIntelligence;
      const context = getDecisionContext(response);
      const unansweredQuestions = (context.adaptive_questions || []).filter(
        (candidate) => !answeredQuestionKeys.current.has(candidate.question_key),
      );

      if (context.decision_readiness === "READY" || unansweredQuestions.length === 0) {
        setQuestion(null);
        router.replace(destination);
        return;
      }

      setFreeTextAnswer("");
      setQuestion(unansweredQuestions[0]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to continue the decision interview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("next");
    const destination = requested?.startsWith("/results") ? requested : "/results";
    setNextUrl(destination);
    void refresh(state, destination);
    // Entry evaluation is intentionally one-shot. Later evaluations follow explicit answers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const options = question ? (question.answer_options?.length ? question.answer_options : fallbackOptions(question.question_key)) : [];

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
      const nextState = applyAdaptiveAnswer(state, question, answer);
      answeredQuestionKeys.current.add(answeredKey);
      setState(nextState);
      void persistAdaptiveQuestionSignal({
        resident_key: "decision-interview-session",
        question_key: answeredKey,
        answer,
        signal_type: "decision-interview",
        signal_json: JSON.stringify({
          question: question.question,
          decision_dimensions: question.decision_dimensions || [],
          policy_reference: question.policy_reference || null,
          explicit_answer: true,
          knowledge_state: answer.toLowerCase() === "not sure" ? "UNKNOWN" : "KNOWN",
        }),
        weights_json: JSON.stringify({ information_gain: question.information_gain || "UNKNOWN" }),
        impact_explanation: question.reason || "Explicit answer used by governed Human Intelligence runtime.",
        info_gain_score: question.information_gain === "HIGH" ? 1 : 0,
      }).catch(() => undefined);
      await refresh(nextState);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save this answer.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e8f4ef_0%,#f8fbfc_42%,#ffffff_78%)] px-6 py-12 sm:px-10">
      <section className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">OPTIME Decision Interview</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">One important question at a time</h1>
        <p className="mt-3 text-base leading-7 text-slate-600">We only ask when the answer can materially change eligibility, ordering, an important trade-off, or the transition plan. Missing information stays unknown until you answer it.</p>

        {loading ? <div className="mt-10 rounded-2xl bg-slate-50 p-6 text-slate-700">Checking what still matters for this decision...</div> : null}
        {error ? <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800">{error}</div> : null}

        {!loading && question ? (
          <div className="mt-10">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-6">
              <p className="text-xl font-medium leading-8 text-slate-950">{question.question}</p>
              {question.reason ? <p className="mt-3 text-sm leading-6 text-slate-600">Why we ask: {question.reason}</p> : null}
            </div>

            {options.length > 0 ? (
              <div className="mt-6 grid gap-3">
                {options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    disabled={submitting}
                    onClick={() => void answerQuestion(option)}
                    className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left font-medium text-slate-900 transition hover:border-emerald-400 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <form
                className="mt-6"
                onSubmit={(event) => {
                  event.preventDefault();
                  void answerQuestion(freeTextAnswer);
                }}
              >
                <label htmlFor="adaptive-answer" className="text-sm font-medium text-slate-700">Your answer</label>
                <textarea
                  id="adaptive-answer"
                  value={freeTextAnswer}
                  onChange={(event) => setFreeTextAnswer(event.target.value)}
                  disabled={submitting}
                  rows={4}
                  className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-400 disabled:opacity-60"
                  placeholder="Answer in your own words"
                />
                <button
                  type="submit"
                  disabled={submitting || !freeTextAnswer.trim()}
                  className="mt-4 rounded-2xl bg-emerald-700 px-5 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {submitting ? "Understanding your answer..." : "Continue"}
                </button>
              </form>
            )}
          </div>
        ) : null}
      </section>
    </main>
  );
}
