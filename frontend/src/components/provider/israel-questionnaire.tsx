"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchIsraelQuestionnaireSchema,
  fetchIsraelRegistration,
  saveIsraelRegistration,
  type IsraelRegistration,
  type PriceOffer,
  type Question,
  type QuestionnaireSchema,
} from "@/lib/provider-api";

type Answers = Record<string, unknown>;

const LEVEL_LABELS: Record<string, string> = {
  INDEPENDENT: "עצמאיים",
  FRAIL: "תשושים",
  NURSING: "סיעודיים",
  COGNITIVE_FRAIL: "תשושי נפש",
};

function isEmpty(value: unknown): boolean {
  if (value === undefined || value === null || value === "") return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.values(value as object).every(isEmpty);
  return false;
}

function toPayload(schema: QuestionnaireSchema, answers: Answers): IsraelRegistration {
  const questionnaire: Answers = {};
  const core: Answers = {};
  for (const section of schema.sections) {
    for (const question of section.questions) {
      const value = answers[question.key];
      if (isEmpty(value)) continue;
      const numeric = ["int", "money", "number"].includes(question.type);
      const cleaned = numeric ? Number(value) : value;
      if (question.core) core[question.key] = cleaned;
      else questionnaire[question.key] = cleaned;
    }
  }
  return {
    ...(core as Omit<IsraelRegistration, "questionnaire">),
    monthly_price_ils: (core.monthly_price_ils as number | undefined) ?? null,
    deposit_ils: (core.deposit_ils as number | undefined) ?? null,
    questionnaire,
  };
}

function fromSaved(saved: IsraelRegistration): Answers {
  const { questionnaire, ...core } = saved;
  const answers: Answers = { ...(questionnaire ?? {}) };
  for (const [key, value] of Object.entries(core)) {
    if (value !== null && value !== undefined) answers[key] = value;
  }
  return answers;
}

/**
 * The full facility questionnaire, one section per step. The schema comes from the
 * backend, which validates with the same definition.
 */
export function IsraelQuestionnaire({ facilityId, userId }: { facilityId: number; userId: number | null }) {
  const [schema, setSchema] = useState<QuestionnaireSchema | null>(null);
  const [answers, setAnswers] = useState<Answers>({});
  const [step, setStep] = useState(0);
  const [hasSaved, setHasSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchIsraelQuestionnaireSchema()
      .then((loaded) => {
        if (!cancelled) setSchema(loaded);
      })
      .catch(() => {
        if (!cancelled) setLoadError("לא ניתן לטעון את השאלון כרגע. נסו לרענן את הדף.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    fetchIsraelRegistration(facilityId)
      .then(({ registration }) => {
        if (cancelled || !registration) return;
        setAnswers(fromSaved(registration));
        setHasSaved(true);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [facilityId, userId]);

  const sections = useMemo(() => schema?.sections ?? [], [schema]);
  const missingBySection = useMemo(
    () =>
      sections.map((section) =>
        section.questions.filter((q) => q.required && isEmpty(answers[q.key])).map((q) => q.label),
      ),
    [sections, answers],
  );

  if (loadError) return <p role="alert" className="mt-6 rounded-xl border p-3">{loadError}</p>;
  if (!schema) return <p role="status" className="mt-6">טוען את השאלון…</p>;

  const section = sections[step];
  const last = step === sections.length - 1;
  const allMissing = missingBySection.flat();
  const set = (key: string, value: unknown) => setAnswers((current) => ({ ...current, [key]: value }));

  async function save() {
    if (!userId || !schema) return;
    if (allMissing.length) {
      const firstIncomplete = missingBySection.findIndex((list) => list.length);
      setStep(firstIncomplete);
      setStatus({ kind: "error", text: `חסרות תשובות חובה: ${allMissing.join(", ")}` });
      return;
    }
    setSaving(true);
    setStatus(null);
    try {
      const result = await saveIsraelRegistration(facilityId, userId, toPayload(schema, answers));
      setHasSaved(true);
      setStatus({
        kind: "ok",
        text: result.changed ? "הפרטים נשמרו. מעכשיו OOMNIK יתאים את המוסד למשפחות לפיהם." : "הפרטים אושרו ללא שינוי.",
      });
    } catch (error) {
      setStatus({ kind: "error", text: error instanceof Error ? error.message : "השמירה נכשלה." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-6">
      {hasSaved ? (
        <p className="mb-4 rounded-xl border p-3 text-sm">
          אלה הפרטים ששמרתם. עברו על השלבים, תקנו מה שהשתנה, ובסוף לחצו על &quot;אישור ושמירה&quot;.
        </p>
      ) : null}

      <nav aria-label="שלבי השאלון" className="flex flex-wrap gap-2">
        {sections.map((s, index) => (
          <button
            key={s.key}
            type="button"
            onClick={() => setStep(index)}
            aria-current={index === step ? "step" : undefined}
            className={`rounded-full border px-3 py-1 text-sm ${index === step ? "bg-black text-white" : ""}`}
          >
            {index + 1}. {s.title}
            {missingBySection[index]?.length ? " •" : ""}
          </button>
        ))}
      </nav>

      <section className="mt-6" aria-labelledby={`section-${section.key}`}>
        <h2 id={`section-${section.key}`} className="text-xl font-semibold">{section.title}</h2>
        {section.intro ? <p className="mt-1 text-sm">{section.intro}</p> : null}
        <div className="mt-4 space-y-6">
          {section.questions
            .filter((question) => !(question.type === "price_offers" && answers.price_publication === "WITHHOLD"))
            .map((question) =>
              question.type === "price_offers" ? (
                <PriceOffersField
                  key={question.key}
                  label={question.label}
                  options={schema.price_offer_options}
                  value={(answers[question.key] as PriceOffer[] | undefined) ?? []}
                  onChange={(v) => set(question.key, v)}
                />
              ) : (
                <QuestionField key={question.key} question={question} value={answers[question.key]} onChange={(v) => set(question.key, v)} />
              ),
            )}
        </div>
      </section>

      {status ? (
        <p role={status.kind === "error" ? "alert" : "status"} className="mt-6 rounded-xl border p-3 text-sm">{status.text}</p>
      ) : null}

      <div className="mt-6 flex gap-3">
        {step > 0 ? (
          <button type="button" onClick={() => setStep(step - 1)} className="rounded-xl border px-4 py-2">הקודם</button>
        ) : null}
        {!last ? (
          <button type="button" onClick={() => setStep(step + 1)} className="rounded-xl bg-black px-4 py-2 text-white">הבא</button>
        ) : (
          <button
            type="button"
            onClick={() => void save()}
            disabled={!userId || saving}
            className="rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50"
          >
            {saving ? "שומר…" : hasSaved ? "אישור ושמירה" : "שמירה"}
          </button>
        )}
      </div>
    </div>
  );
}

function QuestionField({ question, value, onChange }: { question: Question; value: unknown; onChange: (value: unknown) => void }) {
  const id = `q-${question.key}`;
  const label = (
    <>
      {question.label}
      {question.required ? <span aria-hidden="true"> *</span> : null}
    </>
  );
  const input = "mt-1 w-full rounded-xl border p-2";

  if (question.type === "multi") {
    const chosen = Array.isArray(value) ? (value as string[]) : [];
    return (
      <fieldset>
        <legend className="font-medium">{label}</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {question.options?.map((option) => (
            <label key={option.value} className="flex items-center gap-2 rounded-xl border px-3 py-2">
              <input
                type="checkbox"
                checked={chosen.includes(option.value)}
                onChange={() =>
                  onChange(chosen.includes(option.value) ? chosen.filter((v) => v !== option.value) : [...chosen, option.value])
                }
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
    );
  }

  if (question.type === "single") {
    return (
      <fieldset>
        <legend className="font-medium">{label}</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {question.options?.map((option) => (
            <label key={option.value} className="flex items-center gap-2 rounded-xl border px-3 py-2">
              <input type="radio" name={id} checked={value === option.value} onChange={() => onChange(option.value)} />
              {option.label}
            </label>
          ))}
          {!question.required && value ? (
            <button type="button" className="text-sm underline" onClick={() => onChange("")}>ניקוי</button>
          ) : null}
        </div>
      </fieldset>
    );
  }

  if (question.type === "per_level") {
    const current = (value && typeof value === "object" ? value : {}) as Record<string, string>;
    return (
      <fieldset>
        <legend className="font-medium">{label}</legend>
        <div className="mt-2 space-y-2">
          {Object.entries(LEVEL_LABELS).map(([level, levelLabel]) => (
            <label key={level} className="flex items-center gap-3">
              <span className="w-24">{levelLabel}</span>
              <select
                className="flex-1 rounded-xl border p-2"
                value={current[level] ?? ""}
                onChange={(event) => onChange({ ...current, [level]: event.target.value })}
              >
                <option value="">לא רלוונטי / לא ידוע</option>
                {question.options?.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </fieldset>
    );
  }

  const text = value === undefined || value === null ? "" : String(value);
  if (question.type === "textarea") {
    return (
      <label className="block font-medium" htmlFor={id}>
        {label}
        <textarea id={id} className={`${input} min-h-28`} maxLength={question.max_length} value={text} onChange={(e) => onChange(e.target.value)} />
      </label>
    );
  }

  const numeric = ["int", "money", "number"].includes(question.type);
  const ltr = numeric || ["phone", "email", "url", "date"].includes(question.type);
  const type = question.type === "date" ? "date" : question.type === "email" ? "email" : question.type === "phone" ? "tel" : numeric ? "number" : "text";
  return (
    <label className="block font-medium" htmlFor={id}>
      {label}
      <input
        id={id}
        type={type}
        dir={ltr ? "ltr" : undefined}
        inputMode={numeric ? "decimal" : undefined}
        min={numeric ? question.min : undefined}
        max={numeric ? question.max : undefined}
        maxLength={question.max_length}
        className={input}
        value={text}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

const EMPTY_OFFER: PriceOffer = { track: "MONTHLY", room_type: "", level: "", monthly_from_ils: null, deposit_from_ils: null };

function PriceOffersField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: QuestionnaireSchema["price_offer_options"];
  value: PriceOffer[];
  onChange: (value: PriceOffer[]) => void;
}) {
  const update = (index: number, patch: Partial<PriceOffer>) =>
    onChange(value.map((offer, i) => (i === index ? { ...offer, ...patch } : offer)));
  const money = (text: string) => (text === "" ? null : Number(text));
  const select = "mt-1 w-full rounded-xl border p-2";

  return (
    <fieldset>
      <legend className="font-medium">{label}</legend>
      <p className="mt-1 text-sm">
        מחיר &quot;החל מ-&quot; לכל מסלול, ועל מה הוא חל. בדיור מוגן במסלול פיקדון: הפיקדון ודמי האחזקה צריכים להיות של אותה דירה. אם אחד מהם לא ידוע, השאירו ריק ונציג &quot;דורש בירור&quot;.
      </p>
      <div className="mt-3 space-y-4">
        {value.map((offer, index) => (
          <div key={index} className="rounded-xl border p-3">
            <div className="grid gap-2 sm:grid-cols-3">
              <label className="text-sm">
                מסלול
                <select className={select} value={offer.track} onChange={(e) => update(index, { track: e.target.value })}>
                  {options.tracks.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </label>
              <label className="text-sm">
                סוג חדר / דירה
                <select className={select} value={offer.room_type} onChange={(e) => update(index, { room_type: e.target.value })}>
                  <option value="">בחרו</option>
                  {options.rooms.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </label>
              <label className="text-sm">
                רמת טיפול
                <select className={select} value={offer.level} onChange={(e) => update(index, { level: e.target.value })}>
                  <option value="">בחרו</option>
                  {options.levels.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </label>
              <label className="text-sm">
                {offer.track === "DEPOSIT" ? "דמי אחזקה החל מ- (₪ לחודש)" : "מחיר חודשי החל מ- (₪)"}
                <input dir="ltr" inputMode="numeric" type="number" min={0} className={select} value={offer.monthly_from_ils ?? ""} onChange={(e) => update(index, { monthly_from_ils: money(e.target.value) })} />
              </label>
              <label className="text-sm">
                {offer.track === "DEPOSIT" ? "פיקדון החל מ- (₪)" : "פיקדון נלווה, אם יש (₪)"}
                <input dir="ltr" inputMode="numeric" type="number" min={0} className={select} value={offer.deposit_from_ils ?? ""} onChange={(e) => update(index, { deposit_from_ils: money(e.target.value) })} />
              </label>
              <div className="flex items-end">
                <button type="button" className="text-sm underline" onClick={() => onChange(value.filter((_, i) => i !== index))}>הסרת המחיר</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {value.length < options.max ? (
        <button type="button" className="mt-3 rounded-xl border px-3 py-2 text-sm" onClick={() => onChange([...value, { ...EMPTY_OFFER }])}>
          + הוספת מחיר
        </button>
      ) : null}
    </fieldset>
  );
}
