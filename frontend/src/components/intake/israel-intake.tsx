"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useQuestionnaire, type QuestionnaireState } from "@/context/questionnaire-context";
import { QUESTIONNAIRE_SESSION_KEY, saveSessionJson } from "@/lib/search-session";

type Israel = NonNullable<QuestionnaireState["israelMarket"]>;
type Draft = { israel: Israel; notes: string };
type Option = { value: string; label: string; hint?: string };
type Step = {
  id: string;
  prompt: string;
  kind: "single" | "text" | "city";
  options?: Option[];
  show?: (draft: Draft) => boolean;
  get: (draft: Draft) => string;
  set: (draft: Draft, value: string) => Draft;
  optional?: boolean;
};

const israelField = <K extends keyof Israel>(key: K, parse: (value: string) => Israel[K] = (v) => v as Israel[K]) => ({
  get: (d: Draft) => (d.israel[key] === null || d.israel[key] === undefined ? "" : String(d.israel[key])),
  set: (d: Draft, value: string): Draft => ({ ...d, israel: { ...d.israel, [key]: parse(value) } }),
});

const toNumber = (value: string) => (value ? Number(value) : null);

const STEPS: Step[] = [
  {
    id: "relationship",
    prompt: "עבור מי אתם מחפשים מסגרת?",
    kind: "single",
    options: ["אמא", "אבא", "סבתא", "סבא", "בן/בת זוג", "עבורי", "קרוב/ה אחר/ת"].map((v) => ({ value: v, label: v })),
    ...israelField("relationship"),
  },
  {
    id: "ageGroup",
    prompt: "מה הגיל בערך?",
    kind: "single",
    options: ["מתחת ל-70", "70–79", "80–89", "90 ומעלה"].map((v) => ({ value: v, label: v })),
    ...israelField("ageGroup"),
  },
  {
    id: "functionalLevel",
    prompt: "מה המצב התפקודי היום?",
    kind: "single",
    options: [
      { value: "INDEPENDENT", label: "עצמאי/ת", hint: "מתלבש/ת, מתרחץ/ת ואוכל/ת בלי עזרה" },
      { value: "FRAIL", label: "תשוש/ה", hint: "צריך/ה עזרה חלקית, אבל מתנייד/ת בעצמו/ה" },
      { value: "NURSING", label: "סיעודי/ת", hint: "תלוי/ה בעזרה ברוב פעולות היום-יום" },
      { value: "COGNITIVE_FRAIL", label: "תשוש/ת נפש", hint: "ירידה קוגניטיבית או דמנציה שמחייבת השגחה" },
      { value: "UNCLEAR", label: "לא בטוחים", hint: "לא נציג מסגרת כמתאימה עד שזה יתברר" },
    ],
    ...israelField("functionalLevel"),
  },
  {
    id: "fundingPathway",
    prompt: "איך מתכננים לממן את המסגרת?",
    kind: "single",
    options: [
      { value: "MOH_CODE", label: "קוד של משרד הבריאות", hint: "השתתפות המדינה באשפוז סיעודי או תשו״ן" },
      { value: "WELFARE_ASSISTANCE", label: "סיוע של משרד הרווחה", hint: "דרך המחלקה לשירותים חברתיים" },
      { value: "PRIVATE", label: "באופן פרטי" },
      { value: "UNCLEAR", label: "עוד לא יודעים" },
    ],
    ...israelField("fundingPathway"),
  },
  {
    id: "monthlyBudgetIls",
    prompt: "מה התקציב החודשי?",
    kind: "single",
    show: (d) => d.israel.fundingPathway === "PRIVATE",
    options: [6000, 9000, 12000, 15000, 20000, 25000, 30000].map((n) => ({ value: String(n), label: `עד ₪${n.toLocaleString("he-IL")}` })),
    ...israelField("monthlyBudgetIls", toNumber),
  },
  { id: "city", prompt: "באיזה יישוב או אזור?", kind: "city", ...israelField("city") },
  {
    id: "maxDistanceKm",
    prompt: "עד כמה רחוק מהיישוב הזה אפשר?",
    kind: "single",
    options: [
      { value: "5", label: "עד 5 ק״מ" },
      { value: "10", label: "עד 10 ק״מ" },
      { value: "20", label: "עד 20 ק״מ" },
      { value: "40", label: "עד 40 ק״מ" },
      { value: "", label: "בכל הארץ" },
    ],
    ...israelField("maxDistanceKm", toNumber),
    optional: true,
  },
  {
    id: "notes",
    prompt: "ספרו לנו במילים שלכם מה חשוב לכם",
    kind: "text",
    optional: true,
    get: (d) => d.notes,
    set: (d, value) => ({ ...d, notes: value }),
  },
];

const EMPTY: Draft = {
  israel: {
    relationship: "",
    ageGroup: "",
    functionalLevel: "" as Israel["functionalLevel"],
    fundingPathway: "" as Israel["fundingPathway"],
    city: "",
    maxDistanceKm: null,
    monthlyBudgetIls: null,
  },
  notes: "",
};

const answered = (step: Step, draft: Draft) => step.optional || step.get(draft).trim() !== "";

export function IsraelIntake() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [stepId, setStepId] = useState(STEPS[0].id);
  const [summary, setSummary] = useState(false);
  const [error, setError] = useState(false);

  const steps = useMemo(() => STEPS.filter((s) => !s.show || s.show(draft)), [draft]);
  const index = Math.max(0, steps.findIndex((s) => s.id === stepId));
  const step = steps[index];
  const progress = summary ? 100 : Math.round((index / steps.length) * 100);

  function go(nextIndex: number, current: Draft = draft) {
    const visible = STEPS.filter((s) => !s.show || s.show(current));
    if (nextIndex >= visible.length) setSummary(true);
    else setStepId(visible[Math.max(0, nextIndex)].id);
    setError(false);
  }

  function choose(value: string) {
    const next = step.set(draft, value);
    setDraft(next);
    const visible = STEPS.filter((s) => !s.show || s.show(next));
    go(visible.findIndex((s) => s.id === step.id) + 1, next);
  }

  function submit() {
    const submission: QuestionnaireState = {
      ...state,
      // Free text goes to the shared AI interpreter like any other market.
      notes: draft.notes.trim(),
      budget: draft.israel.monthlyBudgetIls ?? 0,
      israelMarket: draft.israel,
    };
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, submission);
    setState(submission);
    router.push("/results");
  }

  const label = (s: Step) => {
    const value = s.get(draft);
    if (!value) return "לא צוין";
    return s.options?.find((o) => o.value === value)?.label ?? value;
  };

  const choiceClass = (active: boolean) =>
    `rounded-xl border min-h-12 px-4 py-3 text-right text-lg font-semibold transition ${active ? "border-forest bg-forest text-white" : "border-line bg-white text-muted hover:border-forest"}`;

  return (
    <main dir="rtl" lang="he" className="min-h-screen bg-canvas px-4 py-8 text-ink sm:px-8">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-semibold text-forest">השיחה שלכם עם OOMNIK</p>
        <div className="mt-4 h-1.5 w-full overflow-hidden rounded-xl bg-sand">
          <div className="h-full rounded-xl bg-forest transition-[width] duration-300" style={{ width: `${progress}%` }} />
        </div>

        {!summary && step ? (
          <section className="mt-8">
            <h1 className="text-3xl font-semibold">{step.prompt}</h1>
            {step.kind === "single" ? (
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {step.options?.map((option) => (
                  <button key={option.value || "any"} type="button" aria-pressed={step.get(draft) === option.value} onClick={() => choose(option.value)} className={choiceClass(step.get(draft) === option.value)}>
                    {option.label}
                    {option.hint ? <span className="mt-1 block text-sm font-normal">{option.hint}</span> : null}
                  </button>
                ))}
              </div>
            ) : step.kind === "city" ? (
              <input aria-label={step.prompt} className="mt-6 w-full rounded-xl border p-3 text-lg" value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חיפה" />
            ) : (
              <textarea aria-label={step.prompt} className="mt-6 h-40 w-full rounded-xl border p-3 text-lg" value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חשוב לנו אוכל כשר ושיהיה צוות שמדבר רוסית" />
            )}
            {error ? <p role="alert" className="mt-3 text-sm text-[#a4501f]">צריך לענות על השאלה כדי להמשיך.</p> : null}
            <div className="mt-8 flex gap-3">
              {index > 0 ? (
                <button type="button" onClick={() => go(index - 1)} className="rounded-xl border px-4 py-2">חזרה</button>
              ) : null}
              {step.kind !== "single" || step.optional ? (
                <button type="button" onClick={() => (answered(step, draft) ? go(index + 1) : setError(true))} className="rounded-xl bg-forest px-4 py-2 font-semibold text-white">המשך</button>
              ) : null}
            </div>
          </section>
        ) : (
          <section className="mt-8">
            <h1 className="text-3xl font-semibold">זה מה שהבנו</h1>
            <dl className="mt-6 space-y-2 text-lg">
              {steps.map((s) => (
                <div key={s.id} className="flex gap-2">
                  <dt className="font-semibold">{s.prompt}</dt>
                  <dd>{label(s)}</dd>
                </div>
              ))}
            </dl>
            {draft.israel.functionalLevel === "UNCLEAR" ? (
              <p className="mt-4 text-sm">המצב התפקודי עוד לא ברור. עד שיתברר, אף מסגרת לא תוצג כמתאימה.</p>
            ) : null}
            <div className="mt-8 flex gap-3">
              <button type="button" onClick={() => { setSummary(false); setStepId(steps[0].id); }} className="rounded-xl border px-4 py-2">לתקן</button>
              <button type="button" onClick={submit} className="rounded-xl bg-forest px-4 py-2 font-semibold text-white">נכון, להמשיך</button>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
