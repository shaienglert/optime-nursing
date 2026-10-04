"use client";

import { updateClientCaseQuestionnaire } from "@/lib/api";
import { budgetChoices } from "@/lib/budget-choices";
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
    <button type="button" aria-pressed={active} onClick={onClick} className={`rounded-xl border min-h-12 px-4 py-3 text-left text-xl font-semibold transition ${active ? "border-forest bg-sand text-forest" : "border-line bg-white text-muted hover:border-forest"}`}>
      {active ? "✓ " : ""}{label}
    </button>
  );
}

type PriceFloor = { minimum_monthly_price: number | null; minimum_budget_is_binding: boolean; funding_pathway: string; status: string; synthetic_pilot?: boolean };

function AnswerControl({ question, value, onAnswer, priceFloor }: { question: IntakeQuestion; value: IntakeAnswer; onAnswer: (value: IntakeAnswer, advance: boolean) => void; priceFloor: PriceFloor | null }) {
  if (question.kind === "single") {
    return (
      <div className="mt-4 flex flex-wrap gap-2">
        {(question.options || []).map((option) => (
          <Choice key={option} label={option} active={value === option} onClick={() => onAnswer(option, true)} />
        ))}
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
  if (question.kind === "number" && question.id === "budget") {
    const knownFloor = priceFloor?.minimum_monthly_price;
    const min = priceFloor?.minimum_budget_is_binding && knownFloor ? knownFloor : 100;
    const max = Math.max(15000, min + 10000);
    const current = Number(value) > 0 ? Number(value) : min;
    const choices = budgetChoices(min, max);
    const selectedIndex = choices.reduce((best, amount, index) => Math.abs(amount - current) < Math.abs(choices[best] - current) ? index : best, 0);
    return <div className="mt-4">
      <input aria-label="Monthly budget slider" aria-valuetext={`$${current.toLocaleString()} per month`} type="range" min={0} max={choices.length - 1} step="1" value={selectedIndex} onChange={(event) => onAnswer(choices[Number(event.target.value)], false)} className="w-full" />
      <div className="mt-2 flex justify-between text-sm text-forest"><span>From ${min.toLocaleString()}</span><strong>${current.toLocaleString()} / month</strong><span>${max.toLocaleString()}+</span></div>
      <label className="mt-3 block text-sm">Monthly budget in dollars<select aria-label="Monthly budget in dollars" value={choices.includes(current) ? current : ""} onChange={event => onAnswer(Number(event.target.value), false)} className="ml-3 rounded-xl border p-2"><option value="" disabled>{Number(value) > 0 ? `$${current.toLocaleString()} (previously entered)` : "Choose a budget"}</option>{choices.map(amount => <option key={amount} value={amount}>${amount.toLocaleString()}</option>)}</select></label>
      {knownFloor ? <p className="mt-3 text-sm">{priceFloor?.synthetic_pilot ? "Synthetic pilot: " : ""}The lowest known starting monthly price in your selected area for the care answers given so far is ${knownFloor.toLocaleString()}.</p> : <p className="mt-3 text-sm">The minimum price for this search has not been verified. Your budget will be kept as stated; affordability still needs evidence.</p>}
      {priceFloor?.funding_pathway === "MEDICAID_COST_REQUIRES_VERIFICATION" ? <p className="mt-2 text-sm">That is a private-pay price, not your Medicaid household cost. Enter what the household can pay; Medicaid coverage and out-of-pocket cost still need verification.</p> : null}
      <p className="mt-2 text-xs text-forest">This is a starting monthly cost, not proof of total affordability. Mandatory fees, one-time entrance fees and any outside care must be checked separately.</p>
    </div>;
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
        className="mt-4 block w-full rounded-xl border border-line bg-white px-4 py-3 text-base outline-none focus:border-forest"
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
      className="mt-4 block w-full rounded-xl border border-line bg-white px-4 py-3 text-base outline-none focus:border-forest"
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
  const [priceFloor, setPriceFloor] = useState<PriceFloor | null>(null);
  const [priceFloorLoading, setPriceFloorLoading] = useState(false);
  const [priceFloorError, setPriceFloorError] = useState(false);
  const [priceFloorRetry, setPriceFloorRetry] = useState(0);

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
  const priceQuery = JSON.stringify({ ...buildSubmission(context), budget: 0 });
  const onBudget = question?.id === "budget";
  useEffect(() => {
    if (!onBudget) return;
    const controller = new AbortController();
    setPriceFloor(null); setPriceFloorLoading(true); setPriceFloorError(false);
    fetch("/api/backend/api/market-price-floor", { method: "POST", headers: { "Content-Type": "application/json" }, body: priceQuery, signal: controller.signal })
      .then(async response => { if (!response.ok) throw new Error("Price lookup unavailable"); return response.json(); })
      .then(value => { if (!controller.signal.aborted) setPriceFloor(value); })
      .catch(() => { if (!controller.signal.aborted) setPriceFloorError(true); })
      .finally(() => { if (!controller.signal.aborted) setPriceFloorLoading(false); });
    return () => controller.abort();
  }, [onBudget, priceQuery, priceFloorRetry]);
  const belowKnownFloor = onBudget && priceFloor?.minimum_budget_is_binding === true && Number(context.draft.budget) > 0 && Number(context.draft.budget) < Number(priceFloor.minimum_monthly_price);
  const relation = context.draft.relationship;
  const subject = relation === "Mom" ? "your mother" : relation === "Dad" ? "your father" : relation === "Grandma" ? "your grandmother" : relation === "Grandpa" ? "your grandfather" : relation === "Spouse" ? "your spouse" : relation === "Myself" ? "you" : relation === "Couple" ? "they" : relation === "Relative" ? "your relative" : relation === "Friend" ? "your friend" : "they";
  const objectPronoun = relation === "Mom" || relation === "Grandma" ? "her" : relation === "Dad" || relation === "Grandpa" ? "him" : relation === "Myself" ? "you" : "them";
  const possessive = relation === "Mom" || relation === "Grandma" ? "her" : relation === "Dad" || relation === "Grandpa" ? "his" : relation === "Myself" ? "your" : "their";
  function personalizePrompt(prompt = "") {
    if (subject === "they") return prompt;
    if (subject === "you") return prompt.replace(/\bthey\b/gi, "you").replace(/\bthem\b/gi, "you").replace(/\btheir\b/gi, "your");
    // The age question starts with "About how old are they?" and needs agreement.
    if (/^About how old are they\?/i.test(prompt)) return `About how old is ${subject}?`;
    return prompt
      .replace(/^Are they\b/i, `Is ${subject}`)
      .replace(/^Do they\b/i, `Does ${subject}`)
      .replace(/^How do they\b/i, `How does ${subject}`)
      .replace(/^What do they\b/i, `What does ${subject}`)
      .replace(/^Can they\b/i, `Can ${subject}`)
      .replace(/^Would they\b/i, `Would ${subject}`)
      .replace(/\bthey\b/gi, subject)
      .replace(/\bthem\b/gi, objectPronoun)
      .replace(/\btheir\b/gi, possessive);
  }
  const displayPrompt = question?.id === "abilityToLeaveIndependently"
    ? (subject === "you" ? "Can you leave the community and go out on your own, without another person assisting you?" : `Can ${subject} leave the community and go out on ${possessive} own, without another person assisting ${objectPronoun}?`)
    : personalizePrompt(question?.prompt);
  const missing = useMemo(() => missingQuestions(context), [context]);

  function finishQuestionnaire(finalContext: IntakeContext) {
    const submission = buildSubmission(finalContext);
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, submission);
    setState(submission);
    const caseToken = typeof window !== "undefined" ? window.localStorage.getItem("oomnik.client.case.token") : null;
    if (caseToken) {
      void updateClientCaseQuestionnaire(caseToken, submission as unknown as Record<string, unknown>, "Client edited and completed the questionnaire").catch(() => undefined);
    }
    router.push("/intake-confirmation?next=%2Fresults");
  }

  function goToIndex(nextIndex: number) {
    if (nextIndex >= questions.length) {
      finishQuestionnaire(context);
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
      finishQuestionnaire(next);
      return;
    }
    setStepId(updated[position + 1].id);
  }

  function next() {
    if (!question) return;
    if (onBudget && (priceFloorLoading || belowKnownFloor)) { setShowError(true); return; }
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
    <main className="min-h-screen bg-canvas px-4 py-8 text-ink sm:px-8">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-forest">Your conversation with Oomnik</p>

        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-xl bg-sand">
          <div className="h-full rounded-xl bg-forest transition-[width] duration-300" style={{ width: `${phase === "summary" ? 100 : progress}%` }} />
        </div>

        {phase === "questions" && question ? (
          <section className="mt-8">
            <p className="text-sm font-semibold uppercase tracking-[0.12em] text-forest">{question.section}</p>
            <div className="mt-5">
              <h1 data-question-id={question?.id} data-question-kind={question?.kind} className="text-4xl font-normal leading-tight tracking-[-0.025em] text-forest sm:text-5xl">{displayPrompt}</h1>
            </div>

            <div className="mt-7">
              {question.note ? <p className="mb-3 text-base leading-7 text-muted">{question.note}</p> : null}
              {question.id === "medicaidStatus" || question.id === "medicaidAmountKnown" ? <div className="mb-4 text-sm leading-6">
                <p>Medicaid may cover approved care at home or in Assisted Living, or care and accommodation in a participating nursing facility. Community-based coverage generally does not pay for room and board. A coverage amount is not necessarily money available to add to your housing budget.</p>
                <p className="mt-2">OOmnik uses the information you provide. We do not process Medicaid applications or determine or guarantee eligibility, coverage or payment. Confirm coverage and your remaining cost with the funding agency and provider before committing.</p>
                <p className="mt-2 flex flex-wrap gap-x-4"><a className="underline" href="https://www.medicaid.gov/medicaid/long-term-services-supports/institutional-long-term-care/nursing-facilities" target="_blank" rel="noopener noreferrer">Official Medicaid guide</a><a className="underline" href="https://adsd.nv.gov/Programs/Seniors/HCBS_%28FE%29/HCBS_%28FE%29/" target="_blank" rel="noopener noreferrer">Nevada home and Assisted Living support</a><a className="underline" href="https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-441/subpart-G/section-441.310" target="_blank" rel="noopener noreferrer">Federal regulation: 42 CFR 441.310</a></p>
                {context.draft.medicaidStatus === "Application pending" ? <p className="mt-2 font-medium">Expected coverage is conditional on approval.</p> : null}
              </div> : null}
              {onBudget && priceFloorLoading ? <p role="status">Checking starting prices in your selected area for the care answers given so far…</p> : <AnswerControl question={question} value={question.get(context)} onAnswer={answer} priceFloor={priceFloor} />}
              {onBudget && priceFloorError ? <p className="mt-3 text-sm">Price lookup is unavailable. <button type="button" onClick={() => setPriceFloorRetry(value => value + 1)} className="underline">Try price lookup again</button></p> : null}
              {belowKnownFloor ? <p role="alert" className="mt-3 text-sm text-[#a4501f]">Your stated budget is below the known private-pay starting price. I have kept your amount. Choose a budget you can fund, or go back to change the area or funding answer before continuing.</p> : null}
              {question.kind === "multi" ? <p className="mt-3 text-sm text-forest">Choose anything that applies, then continue.</p> : null}
              {showError ? <p className="mt-3 text-sm font-semibold text-[#a4501f]">Please answer this before we continue.</p> : null}
            </div>

            <div className="mt-8 flex items-center justify-between gap-3">
              <button type="button" onClick={() => goToIndex(index - 1)} disabled={index === 0} className="rounded-xl border border-line px-5 py-2.5 text-sm font-semibold text-muted disabled:opacity-40">
                ← Back
              </button>
              <p className="text-sm text-forest">Question {index + 1} of {questions.length}</p>
              <button type="button" onClick={next} disabled={onBudget && (priceFloorLoading || belowKnownFloor)} className="inline-flex items-center justify-center gap-3 rounded-xl bg-forest px-6 py-2.5 text-sm font-semibold text-white hover:bg-forest-hover disabled:opacity-40">
                <OomnikMark /> {question.required && !isAnswered(question, context) ? "Next →" : index + 1 === questions.length ? "See the summary →" : "Next →"}
              </button>
            </div>
          </section>
        ) : null}

        {phase === "summary" ? (
          <section className="mt-8">
            <div className="flex items-start gap-3">
              <div className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-xl bg-sand text-sm font-bold text-white">O</div>
              <div className="rounded-[1.6rem] rounded-tl-md bg-sand px-5 py-4">
                <h1 className="text-2xl font-medium leading-8 text-forest">Here’s what I understood</h1>
              </div>
            </div>

            <div className="ml-12 mt-5 grid gap-3 rounded-xl bg-sand p-5 text-sm leading-6 sm:grid-cols-2">
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
              <div className="ml-12 mt-4 rounded-xl border border-amber-300 bg-amber-50 p-5">
                <p className="font-semibold">A few things are still missing:</p>
                <p className="mt-2 text-sm leading-6">{missing.map((item) => item.label).join(", ")}.</p>
                <button type="button" onClick={() => { setPhase("questions"); setStepId(missing[0].id); }} className="mt-3 rounded-xl border border-line bg-white px-5 py-2 text-sm font-semibold">
                  Go to the first one
                </button>
              </div>
            ) : (
              <label className="ml-12 mt-4 flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-white p-4">
                <input type="checkbox" checked={confirmed} onChange={(event) => { setConfirmed(event.target.checked); setShowError(false); }} className="mt-1 size-5 accent-forest" />
                <span><strong>Yes — this reflects what I told Oomnik.</strong><span className="mt-1 block text-sm text-forest">You can still change anything before we continue.</span></span>
              </label>
            )}

            {showError && missing.length === 0 && !confirmed ? <p className="ml-12 mt-3 text-sm font-semibold text-[#a4501f]">Please confirm the summary before we continue.</p> : null}

            <div className="ml-12 mt-6 flex flex-wrap items-center gap-3">
              <button type="button" onClick={() => { setPhase("questions"); setStepId(questions[questions.length - 1].id); }} className="rounded-xl border border-line px-5 py-2.5 text-sm font-semibold text-muted">
                ← Change an answer
              </button>
              <button type="button" onClick={continueToInterview} className="inline-flex items-center justify-center gap-2 rounded-xl bg-forest px-7 py-3 text-base font-semibold text-white hover:bg-forest-hover">
                <OomnikMark /> Continue our conversation
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
