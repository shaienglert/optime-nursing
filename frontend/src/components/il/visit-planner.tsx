"use client";

import { useEffect, useMemo, useState } from "react";

import { VisitCalendarGrid } from "@/components/il/visit-calendar";
import {
  answerVisit,
  bookVisit,
  fetchVisitSlots,
  requestVisit,
  visitCalendarHref,
  type VisitCalendar,
  type VisitSlot,
  type VisitView,
} from "@/lib/israel-facility";

const PARTS: [VisitSlot["part"], string][] = [
  ["MORNING", "בוקר"],
  ["NOON", "צהריים"],
  ["AFTERNOON", "אחה״צ"],
];

function israelDate(offset: number) {
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Jerusalem" }));
  now.setDate(now.getDate() + offset);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** The family proposes up to three dates; the facility confirms one with an exact time. */
export function VisitPlanner({ token, initial }: { token: string; initial: VisitView | null }) {
  const [visit, setVisit] = useState<VisitView | null>(initial);
  const [slots, setSlots] = useState<VisitSlot[]>([{ date: "", part: "MORNING" }]);
  const [mode, setMode] = useState<"IN_PERSON" | "VIDEO">("IN_PERSON");
  const [visitors, setVisitors] = useState(1);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [calendar, setCalendar] = useState<VisitCalendar | null>(null);
  const [pick, setPick] = useState<{ date: string | null; time: string | null }>({ date: null, time: null });
  const min = useMemo(() => israelDate(1), []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const loaded = await fetchVisitSlots(token);
        if (!cancelled) setCalendar(loaded);
      } catch {
        if (!cancelled) setCalendar({ configured: false, days: [] });
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [token, visit?.status]);
  const max = useMemo(() => israelDate(60), []);

  async function run(action: () => Promise<VisitView>) {
    setBusy(true);
    setError(null);
    try {
      setVisit(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : "הפעולה נכשלה.");
    } finally {
      setBusy(false);
    }
  }

  const open = !visit || visit.status !== "CONFIRMED";
  const useCalendar = Boolean(calendar?.configured);
  const canPropose = calendar !== null && !useCalendar && (!visit || visit.status === "CANCELLED" || visit.status === "REQUESTED" || visit.status === "FACILITY_PROPOSED");
  const openDays = calendar?.days.filter((d) => d.slots.length).length ?? 0;
  const chosen = slots.filter((s) => s.date);

  return (
    <section className="mt-10 rounded-2xl border p-5" aria-labelledby="visit-title">
      <h2 id="visit-title" className="text-xl font-semibold">תיאום ביקור</h2>

      {visit ? (
        <div className="mt-3 rounded-xl bg-sand p-3" role="status">
          <p className="font-semibold">{visit.status_label}</p>
          {visit.status === "CONFIRMED" && visit.confirmed ? (
            <>
              <p className="mt-1">
                {visit.mode_label}: {visit.confirmed.label}
              </p>
              {visit.confirmed.note ? <p className="mt-1 text-sm">הערת המוסד: {visit.confirmed.note}</p> : null}
              <a href={visitCalendarHref(token)} className="mt-2 inline-block underline">
                הוספה ליומן
              </a>
            </>
          ) : null}
          {visit.status === "FACILITY_PROPOSED" && visit.confirmed ? (
            <>
              <p className="mt-1">המוסד מציע: {visit.confirmed.label}</p>
              {visit.confirmed.note ? <p className="mt-1 text-sm">{visit.confirmed.note}</p> : null}
              <button type="button" disabled={busy} onClick={() => void run(() => answerVisit(token, "ACCEPT"))} className="mt-2 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
                מאשרים את המועד
              </button>
            </>
          ) : null}
          {visit.status === "REQUESTED" ? (
            <ul className="mt-1 list-disc pe-5 text-sm">
              {visit.slots.map((s) => (
                <li key={s.date + s.part}>{s.label}</li>
              ))}
            </ul>
          ) : null}
          {visit.status !== "CANCELLED" ? (
            <button type="button" disabled={busy} onClick={() => void run(() => answerVisit(token, "CANCEL"))} className="mt-2 block text-sm underline">
              ביטול הביקור
            </button>
          ) : null}
        </div>
      ) : useCalendar ? (
        <p className="mt-1 text-sm">בחרו יום ושעה מתוך שעות הביקור של המוסד. הביקור נקבע מיד, ותוכלו להוסיף אותו ליומן.</p>
      ) : calendar ? (
        <p className="mt-1 text-sm">המוסד עוד לא פרסם שעות ביקור. הציעו עד שלושה מועדים שנוחים לכם, והמוסד יבחר אחד ויקבע שעה, או יציע מועד אחר.</p>
      ) : null}

      {useCalendar && calendar && open ? (
        <div className="mt-4">
          {openDays ? (
            <VisitCalendarGrid calendar={calendar} selectedDate={pick.date} selectedTime={pick.time} onPick={(date, time) => setPick({ date, time })} />
          ) : (
            <p className="text-sm">אין כרגע מועדים פנויים ב־30 הימים הקרובים. אפשר לכתוב למוסד בהתכתבות למעלה.</p>
          )}
          <div className="mt-4 flex flex-wrap gap-4">
            {calendar.modes && calendar.modes.length > 1 ? (
              <fieldset>
                <legend className="text-sm font-medium">סוג הביקור</legend>
                <div className="mt-1 flex gap-1">
                  {calendar.modes.map((m) => (
                    <button key={m.value} type="button" aria-pressed={mode === m.value} onClick={() => setMode(m.value)} className={`rounded-full border px-3 py-1 text-sm ${mode === m.value ? "bg-black text-white" : ""}`}>
                      {m.label}
                    </button>
                  ))}
                </div>
              </fieldset>
            ) : null}
            <label className="text-sm font-medium">
              כמה תגיעו
              <input type="number" min={1} max={8} value={visitors} onChange={(e) => setVisitors(Number(e.target.value) || 1)} className="ms-2 w-16 rounded-xl border p-1" />
            </label>
          </div>
          <label className="mt-3 block text-sm font-medium" htmlFor="book-note">הערה למוסד (לא חובה)</label>
          <textarea id="book-note" maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 min-h-16 w-full rounded-xl border p-2" />
          {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
          <button
            type="button"
            disabled={busy || !pick.date || !pick.time}
            onClick={() =>
              void run(async () => {
                try {
                  return await bookVisit(token, { date: pick.date!, time: pick.time!, mode, visitors, note: note || undefined });
                } catch (e) {
                  setCalendar(await fetchVisitSlots(token));
                  setPick({ date: null, time: null });
                  throw e;
                }
              })
            }
            className="mt-3 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "קובע…" : pick.date && pick.time ? `קביעת ביקור, ${pick.time}` : "בחרו יום ושעה"}
          </button>
        </div>
      ) : null}

      {canPropose ? (
        <div className="mt-4">
          {visit && visit.status !== "CANCELLED" ? <p className="mb-2 text-sm font-medium">רוצים להציע מועדים אחרים?</p> : null}
          {slots.map((slot, index) => (
            <div key={index} className="mt-2 flex flex-wrap items-center gap-2">
              <label className="sr-only" htmlFor={`slot-date-${index}`}>{`תאריך ${index + 1}`}</label>
              <input
                id={`slot-date-${index}`}
                type="date"
                min={min}
                max={max}
                value={slot.date}
                onChange={(e) => setSlots(slots.map((s, i) => (i === index ? { ...s, date: e.target.value } : s)))}
                className="rounded-xl border p-2"
              />
              <div role="radiogroup" aria-label={`חלק ביום, מועד ${index + 1}`} className="flex gap-1">
                {PARTS.map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={slot.part === value}
                    onClick={() => setSlots(slots.map((s, i) => (i === index ? { ...s, part: value } : s)))}
                    className={`rounded-full border px-3 py-1 text-sm ${slot.part === value ? "bg-black text-white" : ""}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {slots.length < 3 ? (
            <button type="button" onClick={() => setSlots([...slots, { date: "", part: "MORNING" }])} className="mt-2 text-sm underline">
              מועד נוסף
            </button>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-4">
            <fieldset>
              <legend className="text-sm font-medium">סוג הביקור</legend>
              <div className="mt-1 flex gap-1">
                {(["IN_PERSON", "VIDEO"] as const).map((value) => (
                  <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} className={`rounded-full border px-3 py-1 text-sm ${mode === value ? "bg-black text-white" : ""}`}>
                    {value === "IN_PERSON" ? "ביקור במקום" : "שיחת וידאו"}
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="text-sm font-medium">
              כמה תגיעו
              <input type="number" min={1} max={8} value={visitors} onChange={(e) => setVisitors(Number(e.target.value) || 1)} className="ms-2 w-16 rounded-xl border p-1" />
            </label>
          </div>
          <label className="mt-3 block text-sm font-medium" htmlFor="visit-note">הערה למוסד (לא חובה)</label>
          <textarea id="visit-note" maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 min-h-16 w-full rounded-xl border p-2" />
          {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
          <button
            type="button"
            disabled={busy || !chosen.length}
            onClick={() => void run(() => requestVisit(token, { slots: chosen, mode, visitors, note: note || undefined }))}
            className="mt-3 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50"
          >
            {busy ? "שולח…" : "שליחת המועדים למוסד"}
          </button>
        </div>
      ) : error ? (
        <p role="alert" className="mt-2 text-sm">{error}</p>
      ) : null}
    </section>
  );
}
