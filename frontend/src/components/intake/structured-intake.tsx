"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { OomnikMark } from "@/components/brand/oomnik-mark";
import { QUESTIONNAIRE_SESSION_KEY, saveSessionJson } from "@/lib/search-session";
import {
  buildSubmission,
  createExtras,
  isAnswered,
  missingQuestions,
  visibleQuestions,
  type IntakeAnswer,
  type IntakeContext,
  type IntakeQuestion,
} from "@/lib/intake-questions";

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function Choice({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" aria-pressed={active} onClick={onClick} className={`rounded-full border px-4 py-2 text-left text-sm font-semibold transition ${active ? "border-[#397a69] bg-[#e8f4ef] text-[#245b4d]" : "border-[#ddd4c7] bg-white text-[#5e554b] hover:border-[#8eaa9f]"}`}>
      {active ? "✓ " : ""}{label}
    </button>
  );
}

function AnswerControl({ question, value, onAnswer, availableStates }: { question: IntakeQuestion; value: IntakeAnswer; onAnswer: (value: IntakeAnswer, advance: boolean) => void; availableStates: Set<string> }) {
  if (question.kind === "single") {
    return (
      <div className="mt-4 flex flex-wrap gap-2">
        {(question.options || []).map((option) => {
          const stateUnavailable = question.id === "searchState" && !availableStates.has(option);
          return stateUnavailable ? (
            <button key={option} type="button" disabled title="Coming soon — no active facilities in the current database" className="rounded-full border border-[#ddd4c7] bg-[#f4f4f1] px-4 py-2 text-sm font-medium text-[#9a9a92] opacity-70">
              {option} · Coming soon
            </button>
          ) : (
            <Choice key={option} label={option} active={value === option} onClick={() => onAnswer(option, true)} />
          );
        })}
      </div>
    );
  }
  if (question.kind === "multi") {
    const values = Array.isArray(value) ? value : [];
    return (
      <div className="mt-4 flex flex-wrap gap-2">
        {(question.options || []).map((option) => (
          <Choice key={option} label={option} active={values.includes(option)} onClick={() => onAnswer(toggle(values, option), false)} />
        ))}
      </div>
    );
  }
  if (question.kind === "number") {
    return (
      <input
        type="number"
        min="1"
        step="1"
        autoFocus
        placeholder={question.placeholder}
        value={Number(value) > 0 ? String(value) : ""}
        onChange={(event) => onAnswer(Number(event.target.value), false)}
        className="mt-4 block w-full rounded-xl border border-[#ddd4c7] bg-white px-4 py-3 text-base outline-none focus:border-[#5a8c7d]"
      />
    );
  }
  return (
    <input
      type="text"
      autoFocus
      placeholder={question.placeholder}
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onAnswer(event.target.value, false)}
      className="mt-4 block w-full rounded-xl border border-[#ddd4c7] bg-white px-4 py-3 text-base outline-none focus:border-[#5a8c7d]"
    />
  );
}

export function StructuredIntake() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [context, setContext] = useState<IntakeContext>(() => {
    const draft = JSON.parse(JSON.stringify(state)) as typeof state;
    return { draft, extras: createExtras(state) };
  });
  const [phase, setPhase] = useState<"questions" | "summary">("questions");
  const [confirmed, setConfirmed] = useState(false);
  const [showError, setShowError] = useState(false);
  const [availableStates, setAvailableStates] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    fetch("/api/backend/public/search-states")
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("state inventory unavailable")))
      .then((payload) => {
        if (!cancelled) setAvailableStates(new Set(Array.isArray(payload?.available_states) ? payload.available_states : []));
      })
      .catch(() => {
        // Fail closed: a state is never made selectable without inventory evidence.
        if (!cancelled) setAvailableStates(new Set());
      });
    return () => { cancelled = true; };
  }, []);

  const questions = useMemo(() => visibleQuestions(context), [context]);

  // The step is tracked by question id, not by index: answering a question can add or
  // remove follow-ups, and an index would silently point at a different question.
  const [stepId, setStepId] = useState<string>(() => {
    const initial = visibleQuestions(context);
    const firstUnanswered = initial.find((question) => question.required && !isAnswered(question, context));
    // Questions already answered on the home page are not asked again.
    return (firstUnanswered || initial[initial.length - 1] || initial[0]).id;
  });

  const index = Math.max(0, questions.findIndex((question) => question.id === stepId));
  const question = questions[index];
  const missing = useMemo(() => missingQuestions(context), [context]);

  function goToIndex(nextIndex: number) {
    if (nextIndex >= questions.length) {
      setPhase("summary");
      return;
    }
    setShowError(false);
    setStepId(questions[Math.max(0, nextIndex)].id);
  }

  function answer(value: IntakeAnswer, advance: boolean) {
    if (!question) return;
    const next = question.set(context, value);
    setContext(next);
    // Any change after confirming means the confirmation no longer reflects the answers.
    setConfirmed(false);
    setShowError(false);
    if (!advance) return;
    // A single-select answer is complete the moment it is chosen, so it moves on by
    // itself. The next question is computed from the updated context, because this
    // answer may have just opened or closed a follow-up.
    const updated = visibleQuestions(next);
    const position = updated.findIndex((item) => item.id === question.id);
    if (position === -1 || position + 1 >= updated.length) {
      setPhase("summary");
      return;
    }
    setStepId(updated[position + 1].id);
  }

  function next() {
    if (!question) return;
    if (question.required && !isAnswered(question, context)) {
      setShowError(true);
      return;
    }
    goToIndex(index + 1);
  }

  function continueToInterview() {
    if (missing.length > 0 || !confirmed) {
      setShowError(true);
      if (missing.length > 0) {
        setPhase("questions");
        setStepId(missing[0].id);
      }
      return;
    }
    const submission = buildSubmission(context);
    // The adaptive interview restores its initial gate from session storage. Persist this
    // completed snapshot before navigation so the route cannot mount between the React
    // state update and the provider's asynchronous persistence effect.
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, submission);
    setState(submission);
    router.push("/adaptive-interview?next=%2Fresults");
  }

  const { draft, extras } = context;
  const answeredCount = questions.filter((item) => isAnswered(item, context)).length;
  const progress = Math.round((answeredCount / Math.max(1, questions.length)) * 100);

  return (
    <main className="min-h-screen bg-[#f7fbfd] px-4 py-8 text-[#26352f] sm:px-8">
      <div className="mx-auto max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-[#397a69]">Your conversation with Oomnik</p>

        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-[#e3ece8]">
          <div className="h-full rounded-full bg-[#397a69] transition-[width] duration-300" style={{ width: `${phase === "summary" ? 100 : progress}%` }} />
        </div>

        {phase === "questions" && question ? (
          <section className="mt-8">
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#7d8b84]">{question.section}</p>
            <div className="mt-4 flex items-start gap-3">
              <div className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-full bg-[#079ff2] text-sm font-bold text-white">O</div>
              <div className="rounded-[1.6rem] rounded-tl-md bg-[#eaf6fd] px-5 py-4">
                <h1 className="text-2xl font-medium leading-8 text-[#183f55]">{question.prompt}</h1>
              </div>
            </div>

            <div className="ml-12 mt-5 rounded-[1.4rem] bg-white px-5 py-5 shadow-sm">
              {question.note ? <p className="mb-3 text-base leading-7 text-[#527083]">{question.note}</p> : null}
              <AnswerControl question={question} value={question.get(context)} onAnswer={answer} availableStates={availableStates} />
              {question.kind === "multi" ? <p className="mt-3 text-sm text-[#7d8b84]">Choose anything that applies, then continue.</p> : null}
              {showError ? <p className="mt-3 text-sm font-semibold text-[#a4501f]">Please answer this before we continue.</p> : null}
            </div>

            <div className="ml-12 mt-6 flex items-center justify-between gap-3">
              <button type="button" onClick={() => goToIndex(index - 1)} disabled={index === 0} className="rounded-full border border-[#ddd4c7] px-5 py-2.5 text-sm font-semibold text-[#5e554b] disabled:opacity-40">
                ← Back
              </button>
              <p className="text-sm text-[#7d8b84]">Question {index + 1} of {questions.length}</p>
              <button type="button" onClick={next} className="rounded-full bg-[#397a69] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#2f6759]">
                {question.required && !isAnswered(question, context) ? "Next →" : index + 1 === questions.length ? "See the summary →" : "Next →"}
              </button>
            </div>
          </section>
        ) : null}

        {phase === "summary" ? (
          <section className="mt-8">
            <div className="flex items-start gap-3">
              <div className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-full bg-[#079ff2] text-sm font-bold text-white">O</div>
              <div className="rounded-[1.6rem] rounded-tl-md bg-[#eaf6fd] px-5 py-4">
                <h1 className="text-2xl font-medium leading-8 text-[#183f55]">Here’s what I understood</h1>
              </div>
            </div>

            <div className="ml-12 mt-5 grid gap-3 rounded-2xl bg-[#eef5f2] p-5 text-sm leading-6 sm:grid-cols-2">
              <p><strong>Person:</strong> {draft.relationship || "Missing"}, {draft.ageGroup || "age missing"}</p>
              <p><strong>Daily support:</strong> {extras.assistance.join(", ") || "Missing"}</p>
              <p><strong>Memory:</strong> {draft.memoryStatus || "Missing"}</p>
              <p><strong>Medical needs:</strong> {draft.medicalCareProfile.hasOngoingMedicalNeeds === "No" ? "None reported" : draft.medicalCareProfile.needs.join(", ") || "Missing"}</p>
              <p><strong>Budget:</strong> {draft.budget > 0 ? `$${draft.budget.toLocaleString()} monthly` : "Not provided"}</p>
              <p><strong>Move timing:</strong> {draft.moveTiming || "Missing"}</p>
              <p><strong>Priorities:</strong> {draft.moveLossConcerns.join(", ") || "Missing"}</p>
              <p><strong>Parking:</strong> {draft.parkingRequirement || "Missing"}</p>
              <p><strong>Language:</strong> {extras.language || "Missing"}</p>
              <p><strong>Future care:</strong> {extras.continuum || "Missing"}</p>
            </div>

            {missing.length > 0 ? (
              <div className="ml-12 mt-4 rounded-2xl border border-amber-300 bg-amber-50 p-5">
                <p className="font-semibold">A few things are still missing:</p>
                <p className="mt-2 text-sm leading-6">{missing.map((item) => item.label).join(", ")}.</p>
                <button type="button" onClick={() => { setPhase("questions"); setStepId(missing[0].id); }} className="mt-3 rounded-full border border-[#ddd4c7] bg-white px-5 py-2 text-sm font-semibold">
                  Go to the first one
                </button>
              </div>
            ) : (
              <label className="ml-12 mt-4 flex cursor-pointer items-start gap-3 rounded-2xl border border-[#cddbd5] bg-white p-4">
                <input type="checkbox" checked={confirmed} onChange={(event) => { setConfirmed(event.target.checked); setShowError(false); }} className="mt-1 size-5 accent-[#397a69]" />
                <span><strong>Yes — this reflects what I told Oomnik.</strong><span className="mt-1 block text-sm text-[#606a64]">You can still change anything before we continue.</span></span>
              </label>
            )}

            {showError && missing.length === 0 && !confirmed ? <p className="ml-12 mt-3 text-sm font-semibold text-[#a4501f]">Please confirm the summary before we continue.</p> : null}

            <div className="ml-12 mt-6 flex flex-wrap items-center gap-3">
              <button type="button" onClick={() => { setPhase("questions"); setStepId(questions[questions.length - 1].id); }} className="rounded-full border border-[#ddd4c7] px-5 py-2.5 text-sm font-semibold text-[#5e554b]">
                ← Change an answer
              </button>
              <button type="button" onClick={continueToInterview} className="inline-flex items-center justify-center gap-2 rounded-full bg-[#397a69] px-7 py-3 text-base font-semibold text-white hover:bg-[#2f6759]">
                <OomnikMark size={18} /> Continue our conversation
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
