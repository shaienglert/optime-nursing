"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { type QuestionnaireState, useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientNeedsProfile, persistAdaptiveQuestionSignal, type PatientNeedsProfile } from "@/lib/api";

type AdaptiveQuestion = {
  question_key: string;
  question: string;
  reason?: string;
  decision_dimensions?: string[];
  information_gain?: string;
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

function applyAdaptiveAnswer(
  state: QuestionnaireState,
  questionKey: string,
  answer: string,
): QuestionnaireState {
  const next = JSON.parse(JSON.stringify(state)) as QuestionnaireState;

  if (questionKey === "community_size_preference") {
    next.humanIntelligenceV2.personalityProfile.communitySizePreference = answer;
    return next;
  }

  if (questionKey === "social_interaction_need_after_loss") {
    next.humanIntelligenceV2.familyProfile.socialInteractionNeed = answer;
    return next;
  }

  throw new Error(`Unsupported adaptive question: ${questionKey}`);
}

function optionsFor(questionKey: string): string[] {
  if (questionKey === "community_size_preference") {
    return ["Small community", "Large community", "No preference"];
  }
  if (questionKey === "social_interaction_need_after_loss") {
    return ["High", "Low", "Neither"];
  }
  return [];
}

export default function AdaptiveInterviewPage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [profile, setProfile] = useState<NeedsProfileWithDecisionIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nextUrl, setNextUrl] = useState("/results");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("next");
    if (requested?.startsWith("/results")) setNextUrl(requested);
  }, []);

  const refresh = async (questionnaireState: QuestionnaireState) => {
    setLoading(true);
    setError(null);
    try {
      const response = (await fetchPatientNeedsProfile({
        questionnaire_state: questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: questionnaireState.notes || "",
      })) as NeedsProfileWithDecisionIntelligence;
      setProfile(response);
      const context = getDecisionContext(response);
      if (context.decision_readiness === "READY" || (context.adaptive_questions || []).length === 0) {
        router.replace(nextUrl);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to continue the decision interview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh(state);
    // This intentionally runs once on entry. Subsequent refreshes are driven by explicit answers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const context = useMemo(() => (profile ? getDecisionContext(profile) : {}), [profile]);
  const question = context.adaptive_questions?.[0] || null;
  const options = question ? optionsFor(question.question_key) : [];

  const answerQuestion = async (answer: string) => {
    if (!question) return;
    try {
      const nextState = applyAdaptiveAnswer(state, question.question_key, answer);
      setState(nextState);
      void persistAdaptiveQuestionSignal({
        resident_key: `session-${Date.now()}`,
        question_key: question.question_key,
        answer,
        signal_type: "decision-interview",
        signal_json: JSON.stringify({ decision_dimensions: question.decision_dimensions || [] }),
        weights_json: JSON.stringify({ information_gain: question.information_gain || "UNKNOWN" }),
        impact_explanation: question.reason || "Answer used by governed Human Intelligence runtime.",
        info_gain_score: question.information_gain === "HIGH" ? 1 : 0,
      }).catch(() => undefined);
      await refresh(nextState);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save this answer.");
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e8f4ef_0%,#f8fbfc_42%,#ffffff_78%)] px-6 py-12 sm:px-10">
      <section className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">OPTIME Decision Interview</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">One important question at a time</h1>
        <p className="mt-3 text-base leading-7 text-slate-600">
          We only ask when the answer can materially change the decision. Missing information stays unknown until you answer it.
        </p>

        {loading ? (
          <div className="mt-10 rounded-2xl bg-slate-50 p-6 text-slate-700">Checking what still matters for this decision...</div>
        ) : null}

        {error ? (
          <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800">{error}</div>
        ) : null}

        {!loading && question ? (
          <div className="mt-10">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-6">
              <p className="text-xl font-medium leading-8 text-slate-950">{question.question}</p>
              {question.reason ? <p className="mt-3 text-sm leading-6 text-slate-600">Why we ask: {question.reason}</p> : null}
            </div>
            <div className="mt-6 grid gap-3">
              {options.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => void answerQuestion(option)}
                  className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left font-medium text-slate-900 transition hover:border-emerald-400 hover:bg-emerald-50"
                >
                  {option === "High" ? "More daily social contact would feel helpful" : option === "Low" ? "More daily social contact would feel overwhelming" : option === "Neither" ? "Neither — no strong preference right now" : option}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
