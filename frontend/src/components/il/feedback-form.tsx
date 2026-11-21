"use client";

import { useEffect, useState } from "react";

import { fetchFeedback, sendFeedback, type FeedbackAnswer, type FeedbackState } from "@/lib/israel-facility";

/** A family that wrote to a facility rates it after visiting or moving in. */
export function FeedbackForm({ token, facilityName }: { token: string; facilityName: string }) {
  const [state, setState] = useState<FeedbackState | null>(null);
  const [answer, setAnswer] = useState<Partial<FeedbackAnswer>>({ ratings: {} });
  const [status, setStatus] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchFeedback(token)
      .then((loaded) => {
        if (cancelled) return;
        setState(loaded);
        if (loaded.mine) setAnswer(loaded.mine);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!state) return null;

  async function submit() {
    setSending(true);
    setStatus(null);
    try {
      const saved = await sendFeedback(token, answer as FeedbackAnswer);
      setState(saved);
      setStatus("תודה. המשוב נשמר, ואפשר לעדכן אותו בכל עת.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "השמירה נכשלה.");
    } finally {
      setSending(false);
    }
  }

  const ratings = answer.ratings ?? {};
  const setRating = (key: string, value: number | null) => {
    const next = { ...ratings };
    if (value === null) delete next[key];
    else next[key] = value;
    setAnswer({ ...answer, ratings: next });
  };

  return (
    <section className="mt-10 rounded-2xl border p-5" aria-labelledby="feedback-title">
      <h2 id="feedback-title" className="text-xl font-semibold">איך היה ב{facilityName}?</h2>
      <p className="mt-1 text-sm">
        המשוב עוזר למשפחות אחרות. הוא מוצג רק כממוצע, ורק אחרי ש־{state.form.min_to_show} משפחות ענו. ההערה החופשית לא מתפרסמת.
      </p>

      <fieldset className="mt-4">
        <legend className="font-medium">מה הקשר שלכם למקום?</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {state.form.relations.map((relation) => (
            <button
              key={relation.value}
              type="button"
              aria-pressed={answer.relation === relation.value}
              onClick={() => setAnswer({ ...answer, relation: relation.value as FeedbackAnswer["relation"] })}
              className={`rounded-full border px-4 py-2 ${answer.relation === relation.value ? "bg-black text-white" : ""}`}
            >
              {relation.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="mt-5 space-y-3">
        {state.form.aspects.map((aspect) => (
          <fieldset key={aspect.key} className="flex flex-wrap items-center gap-2">
            <legend className="w-36 shrink-0 text-sm font-medium">{aspect.label}</legend>
            {state.form.scale.map((score) => (
              <button
                key={score}
                type="button"
                aria-label={`${aspect.label}: ${score} מתוך 5`}
                aria-pressed={ratings[aspect.key] === score}
                onClick={() => setRating(aspect.key, score)}
                className={`h-9 w-9 rounded-full border ${ratings[aspect.key] === score ? "bg-black text-white" : ""}`}
              >
                {score}
              </button>
            ))}
            <button type="button" aria-pressed={ratings[aspect.key] === undefined} onClick={() => setRating(aspect.key, null)} className="text-sm underline">
              לא רלוונטי
            </button>
          </fieldset>
        ))}
      </div>

      <fieldset className="mt-5">
        <legend className="font-medium">הייתם ממליצים על המקום למשפחה אחרת?</legend>
        <div className="mt-2 flex gap-2">
          {(["YES", "NO"] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={answer.recommend === value}
              onClick={() => setAnswer({ ...answer, recommend: value })}
              className={`rounded-full border px-4 py-2 ${answer.recommend === value ? "bg-black text-white" : ""}`}
            >
              {value === "YES" ? "כן" : "לא"}
            </button>
          ))}
        </div>
      </fieldset>

      <label className="mt-5 block font-medium" htmlFor="feedback-comment">הערה (לא מתפרסמת)</label>
      <textarea
        id="feedback-comment"
        maxLength={1000}
        className="mt-1 min-h-20 w-full rounded-xl border p-2"
        value={answer.comment ?? ""}
        onChange={(e) => setAnswer({ ...answer, comment: e.target.value })}
      />

      {status ? <p role="status" className="mt-2 text-sm">{status}</p> : null}
      <button type="button" onClick={() => void submit()} disabled={sending} className="mt-3 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
        {sending ? "שומר…" : state.mine ? "עדכון המשוב" : "שמירת המשוב"}
      </button>
    </section>
  );
}
