"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useQuestionnaire, type QuestionnaireState } from "@/context/questionnaire-context";
import { getApiBaseUrl, joinApiUrl } from "@/lib/api";
import { QUESTIONNAIRE_SESSION_KEY, saveSessionJson } from "@/lib/search-session";

type Israel = NonNullable<QuestionnaireState["israelMarket"]>;
type Draft = { israel: Israel; notes: string };
type Option = { value: string; label: string; hint?: string };
type Step = {
  id: string;
  prompt: string;
  kind: "single" | "multi" | "text" | "city";
  options?: Option[];
  optionsFor?: (draft: Draft) => Option[];
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
  {
    id: "isCouple",
    prompt: "המקום מיועד לאדם אחד או לזוג?",
    kind: "single",
    options: [
      { value: "false", label: "לאדם אחד" },
      { value: "true", label: "לבני זוג", hint: "נציג רק מוסדות שמקבלים זוגות" },
    ],
    get: (d) => (d.israel.isCouple === true ? "true" : d.israel.isCouple === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, isCouple: v === "true", partnerSameLevel: v === "true" ? d.israel.partnerSameLevel : null, residentGenders: [] } }),
  },
  {
    id: "partnerSameLevel",
    prompt: "שני בני הזוג באותו מצב תפקודי?",
    kind: "single",
    show: (d) => d.israel.isCouple === true,
    options: [
      { value: "true", label: "כן" },
      { value: "false", label: "לא", hint: "למשל אחד עצמאי והשני סיעודי" },
    ],
    get: (d) => (d.israel.partnerSameLevel === true ? "true" : d.israel.partnerSameLevel === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, partnerSameLevel: v === "true" } }),
  },
  {
    id: "residentGenders",
    prompt: "עבור מי המקום?",
    kind: "single",
    optionsFor: (d) =>
      d.israel.isCouple
        ? [
            { value: "FEMALE+MALE", label: "אישה וגבר" },
            { value: "FEMALE", label: "שתי נשים" },
            { value: "MALE", label: "שני גברים" },
          ]
        : [
            { value: "FEMALE", label: "אישה" },
            { value: "MALE", label: "גבר" },
          ],
    get: (d) => (d.israel.residentGenders ?? []).join("+"),
    set: (d, v) => ({ ...d, israel: { ...d.israel, residentGenders: (v ? v.split("+") : []) as Israel["residentGenders"] } }),
  },
  {
    id: "medicalNeeds",
    prompt: "יש צורך רפואי מיוחד?",
    kind: "multi",
    optional: true,
    show: (d) => d.israel.functionalLevel !== "INDEPENDENT",
    options: [
      { value: "VENTILATION", label: "מונשם/ת" },
      { value: "WANDERING", label: "נוטה לשוטט / צריך מחלקה סגורה" },
      { value: "PEG", label: "הזנה דרך PEG" },
      { value: "NG_TUBE", label: "זונדה" },
    ],
    get: (d) => (d.israel.medicalNeeds ?? []).join(","),
    set: (d, v) => ({ ...d, israel: { ...d.israel, medicalNeeds: (v ? v.split(",") : []) as Israel["medicalNeeds"] } }),
  },
  {
    id: "language",
    prompt: "באיזו שפה הכי נוח לדבר?",
    kind: "single",
    options: [
      ["HE", "עברית"], ["RU", "רוסית"], ["AR", "ערבית"], ["EN", "אנגלית"], ["AM", "אמהרית"],
      ["YI", "יידיש"], ["FR", "צרפתית"], ["ES", "ספרדית"], ["RO", "רומנית"],
    ].map(([value, label]) => ({ value, label })),
    ...israelField("language"),
  },
  {
    id: "community",
    prompt: "איזו אווירה מתאימה לכם?",
    kind: "single",
    options: [
      ["", "אין העדפה"], ["SECULAR", "חילונית"], ["TRADITIONAL", "מסורתית"], ["RELIGIOUS", "דתית"], ["HAREDI", "חרדית"],
      ["MUSLIM", "מוסלמית"], ["CHRISTIAN", "נוצרית"], ["DRUZE", "דרוזית"],
    ].map(([value, label]) => ({ value, label, hint: value ? "מוסדות מתאימים יופיעו קודם" : undefined })),
    ...israelField("community"),
    optional: true,
  },
  {
    id: "kashrut",
    prompt: "כשרות",
    kind: "single",
    show: (d) => !["MUSLIM", "CHRISTIAN", "DRUZE"].includes(d.israel.community ?? ""),
    options: [
      { value: "", label: "לא משנה" },
      { value: "KOSHER", label: "כשר" },
      { value: "MEHADRIN", label: "כשר למהדרין" },
    ],
    ...israelField("kashrut"),
    optional: true,
  },
  {
    id: "shabbat",
    prompt: "חשוב שבמוסד שומרים שבת?",
    kind: "single",
    show: (d) => ["TRADITIONAL", "RELIGIOUS", "HAREDI"].includes(d.israel.community ?? ""),
    options: [
      { value: "IMPORTANT", label: "כן, חשוב" },
      { value: "", label: "לא משנה" },
    ],
    ...israelField("shabbat"),
    optional: true,
  },
  {
    id: "shelterNeed",
    prompt: "מיגון: מה הכי רחוק שמקובל עליכם?",
    kind: "single",
    options: [
      { value: "ROOM", label: "ממ״ד בתוך החדר או הדירה", hint: "בלי לצאת מהחדר בזמן אזעקה" },
      { value: "FLOOR", label: "מרחב מוגן באותה קומה", hint: "בלי מדרגות ובלי לצאת מהבניין" },
      { value: "", label: "לא קריטי לנו" },
    ],
    ...israelField("shelterNeed"),
    optional: true,
  },
  {
    id: "shelterIsCondition",
    prompt: "להציג רק מוסדות שעומדים בזה?",
    kind: "single",
    show: (d) => Boolean(d.israel.shelterNeed),
    options: [
      { value: "true", label: "כן, זה תנאי", hint: "מוסד עם מיגון רחוק יותר לא יוצג" },
      { value: "false", label: "לא, רק להעדיף", hint: "מוסדות עם מיגון קרוב יופיעו קודם" },
    ],
    get: (d) => (d.israel.shelterIsCondition === true ? "true" : d.israel.shelterIsCondition === false ? "false" : ""),
    set: (d, v) => ({ ...d, israel: { ...d.israel, shelterIsCondition: v === "true" } }),
  },
  {
    id: "depositCapIls",
    prompt: "בדיור מוגן יש לרוב פיקדון. עד כמה אתם מוכנים להפקיד?",
    kind: "single",
    show: (d) => d.israel.fundingPathway === "PRIVATE" && ["INDEPENDENT", "FRAIL"].includes(d.israel.functionalLevel),
    options: [
      { value: "0", label: "בלי פיקדון", hint: "רק מסלול חודשי" },
      { value: "500000", label: "עד ₪500,000" },
      { value: "1000000", label: "עד ₪1,000,000" },
      { value: "1500000", label: "עד ₪1,500,000" },
      { value: "2500000", label: "עד ₪2,500,000" },
      { value: "", label: "עוד לא יודעים" },
    ],
    ...israelField("depositCapIls", (v) => (v === "" ? null : Number(v))),
    optional: true,
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
    medicalNeeds: [],
    isCouple: null,
    partnerSameLevel: null,
    residentGenders: [],
    community: "",
    kashrut: "",
    shabbat: "",
    language: "",
    shelterInRoom: "",
    shelterNeed: "",
    shelterIsCondition: null,
    depositCapIls: null,
  },
  notes: "",
};

const optionsOf = (step: Step, draft: Draft): Option[] => step.optionsFor?.(draft) ?? step.options ?? [];

const answered = (step: Step, draft: Draft) => step.optional || step.get(draft).trim() !== "";

export function IsraelIntake() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [stepId, setStepId] = useState(STEPS[0].id);
  const [summary, setSummary] = useState(false);
  const [error, setError] = useState(false);
  const [localities, setLocalities] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch(joinApiUrl(getApiBaseUrl(), "/api/il/localities"))
      .then((response) => (response.ok ? response.json() : { names: [] }))
      .then((body: { names?: string[] }) => {
        if (!cancelled) setLocalities(body.names ?? []);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  const cityKnown = (value: string) => localities.length === 0 || localities.includes(value.trim());

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
    // Answers to questions that are no longer shown must not act as filters.
    const visibleIds = new Set(steps.map((s) => s.id));
    const israel: Israel = {
      ...draft.israel,
      medicalNeeds: visibleIds.has("medicalNeeds") ? draft.israel.medicalNeeds : [],
      kashrut: visibleIds.has("kashrut") ? draft.israel.kashrut : "",
      shabbat: visibleIds.has("shabbat") ? draft.israel.shabbat : "",
      partnerSameLevel: visibleIds.has("partnerSameLevel") ? draft.israel.partnerSameLevel : null,
      monthlyBudgetIls: visibleIds.has("monthlyBudgetIls") ? draft.israel.monthlyBudgetIls : null,
      depositCapIls: visibleIds.has("depositCapIls") ? draft.israel.depositCapIls : null,
      shelterIsCondition: draft.israel.shelterNeed ? draft.israel.shelterIsCondition : null,
    };
    const submission: QuestionnaireState = {
      ...state,
      // Free text goes to the shared AI interpreter like any other market.
      notes: draft.notes.trim(),
      budget: israel.monthlyBudgetIls ?? 0,
      israelMarket: israel,
    };
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, submission);
    setState(submission);
    router.push("/results");
  }

  const label = (s: Step) => {
    const value = s.get(draft);
    const options = optionsOf(s, draft);
    if (s.kind === "multi") {
      return value ? value.split(",").map((v) => options.find((o) => o.value === v)?.label ?? v).join(", ") : "אין";
    }
    const found = options.find((o) => o.value === value);
    if (found) return found.label;
    return value || "לא צוין";
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
                {optionsOf(step, draft).map((option) => (
                  <button key={option.value || "any"} type="button" aria-pressed={step.get(draft) === option.value} onClick={() => choose(option.value)} className={choiceClass(step.get(draft) === option.value)}>
                    {option.label}
                    {option.hint ? <span className="mt-1 block text-sm font-normal">{option.hint}</span> : null}
                  </button>
                ))}
              </div>
            ) : step.kind === "multi" ? (
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <p className="text-sm sm:col-span-2">אפשר לבחור כמה. אם אין צורך כזה, פשוט ממשיכים.</p>
                {optionsOf(step, draft).map((option) => {
                  const chosen = step.get(draft).split(",").filter(Boolean);
                  const active = chosen.includes(option.value);
                  const next = active ? chosen.filter((v) => v !== option.value) : [...chosen, option.value];
                  return (
                    <button key={option.value} type="button" aria-pressed={active} onClick={() => setDraft(step.set(draft, next.join(",")))} className={choiceClass(active)}>
                      {option.label}
                    </button>
                  );
                })}
              </div>
            ) : step.kind === "city" ? (
              <>
                <input aria-label={step.prompt} list="il-localities" className="mt-6 w-full rounded-xl border p-3 text-lg" value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חיפה" />
                <datalist id="il-localities">
                  {localities.map((name) => <option key={name} value={name} />)}
                </datalist>
                {step.get(draft).trim() && !cityKnown(step.get(draft)) ? (
                  <p className="mt-2 text-sm">לא מצאנו יישוב בשם הזה, ולכן לא נוכל לחשב מרחק. כדאי לבחור מהרשימה.</p>
                ) : null}
              </>
            ) : (
              <textarea aria-label={step.prompt} className="mt-6 h-40 w-full rounded-xl border p-3 text-lg" value={step.get(draft)} onChange={(e) => setDraft(step.set(draft, e.target.value))} placeholder="למשל: חשוב לנו אוכל כשר ושיהיה צוות שמדבר רוסית" />
            )}
            {error ? <p role="alert" className="mt-3 text-sm text-[#a4501f]">צריך לענות על השאלה כדי להמשיך.</p> : null}
            <div className="mt-8 flex gap-3">
              {index > 0 ? (
                <button type="button" onClick={() => go(index - 1)} className="rounded-xl border px-4 py-2">חזרה</button>
              ) : null}
              {step.kind !== "single" || (step.optional && step.get(draft) !== "") ? (
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
