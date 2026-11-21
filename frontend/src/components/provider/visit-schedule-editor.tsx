"use client";

import { useEffect, useState } from "react";

import { fetchVisitSchedule, saveVisitSchedule, type VisitSchedule } from "@/lib/provider-api";

type Day = "SUN" | "MON" | "TUE" | "WED" | "THU" | "FRI" | "SAT";
const DAYS: [Day, string][] = [
  ["SUN", "ראשון"],
  ["MON", "שני"],
  ["TUE", "שלישי"],
  ["WED", "רביעי"],
  ["THU", "חמישי"],
  ["FRI", "שישי"],
  ["SAT", "שבת"],
];
const EMPTY: VisitSchedule = { weekly: {}, slot_minutes: 45, capacity: 1, lead_hours: 24, blocked_dates: [], modes: ["IN_PERSON"] };

/** Visiting hours the facility publishes. Families book open slots from these hours directly. */
export function VisitScheduleEditor({ facilityId, enabled }: { facilityId: number; enabled: boolean }) {
  const [schedule, setSchedule] = useState<VisitSchedule>(EMPTY);
  const [openSlots, setOpenSlots] = useState<number | null>(null);
  const [blocked, setBlocked] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchVisitSchedule(facilityId);
        if (cancelled) return;
        if (res.schedule) setSchedule(res.schedule);
        setOpenSlots(res.calendar.days.reduce((n, d) => n + d.slots.length, 0));
      } catch {
        if (!cancelled) setStatus("לא הצלחנו לטעון את שעות הביקור.");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [facilityId, enabled]);

  if (!enabled) return null;

  const setRanges = (day: Day, ranges: [string, string][]) =>
    setSchedule((s) => {
      const weekly = { ...s.weekly };
      if (ranges.length) weekly[day] = ranges;
      else delete weekly[day];
      return { ...s, weekly };
    });

  async function save() {
    setBusy(true);
    setStatus(null);
    try {
      const res = await saveVisitSchedule(facilityId, schedule);
      if (res.schedule) setSchedule(res.schedule);
      const n = res.calendar.days.reduce((k, d) => k + d.slots.length, 0);
      setOpenSlots(n);
      setStatus(`נשמר. משפחות יכולות לקבוע עכשיו ${n} מועדים ב־30 הימים הקרובים.`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "השמירה נכשלה.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8 rounded-2xl border p-4" aria-labelledby="visit-hours">
      <h2 id="visit-hours" className="text-lg font-semibold">שעות ביקור לקביעה עצמית</h2>
      <p className="mt-1 text-sm">
        משפחות שפנו אליכם יראו לוח שנה עם המועדים הפנויים לפי השעות כאן, ויקבעו ביקור בעצמן. כל ביקור שנקבע מופיע בפניות למעלה.
        {openSlots !== null ? ` כרגע פתוחים ${openSlots} מועדים.` : null}
      </p>

      <div className="mt-4 space-y-2">
        {DAYS.map(([day, label]) => {
          const ranges = schedule.weekly[day] ?? [];
          return (
            <div key={day} className="flex flex-wrap items-center gap-2">
              <label className="flex w-24 items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={ranges.length > 0} onChange={(e) => setRanges(day, e.target.checked ? [["10:00", "13:00"]] : [])} />
                {label}
              </label>
              {ranges.map(([start, end], i) => (
                <span key={i} className="flex items-center gap-1 text-sm">
                  <input aria-label={`${label} התחלה`} type="time" step={900} value={start} onChange={(e) => setRanges(day, ranges.map((r, j) => (j === i ? [e.target.value, r[1]] : r)))} className="rounded border p-1" />
                  –
                  <input aria-label={`${label} סיום`} type="time" step={900} value={end} onChange={(e) => setRanges(day, ranges.map((r, j) => (j === i ? [r[0], e.target.value] : r)))} className="rounded border p-1" />
                  <button type="button" aria-label={`הסרת טווח ב${label}`} onClick={() => setRanges(day, ranges.filter((_, j) => j !== i))} className="px-1">✕</button>
                </span>
              ))}
              {ranges.length > 0 && ranges.length < 3 ? (
                <button type="button" onClick={() => setRanges(day, [...ranges, ["16:00", "18:00"]])} className="text-sm underline">טווח נוסף</button>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <label className="text-sm font-medium">
          משך ביקור
          <select value={schedule.slot_minutes} onChange={(e) => setSchedule((s) => ({ ...s, slot_minutes: Number(e.target.value) }))} className="mt-1 block w-full rounded border p-1">
            {[30, 45, 60, 90].map((m) => <option key={m} value={m}>{m} דקות</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">
          משפחות בכל מועד
          <input type="number" min={1} max={10} value={schedule.capacity} onChange={(e) => setSchedule((s) => ({ ...s, capacity: Number(e.target.value) || 1 }))} className="mt-1 block w-full rounded border p-1" />
        </label>
        <label className="text-sm font-medium">
          התראה מינימלית (שעות)
          <input type="number" min={0} max={168} value={schedule.lead_hours} onChange={(e) => setSchedule((s) => ({ ...s, lead_hours: Number(e.target.value) || 0 }))} className="mt-1 block w-full rounded border p-1" />
        </label>
      </div>

      <fieldset className="mt-4">
        <legend className="text-sm font-medium">סוגי ביקור</legend>
        {([["IN_PERSON", "ביקור במקום"], ["VIDEO", "שיחת וידאו"]] as const).map(([value, label]) => (
          <label key={value} className="me-4 text-sm">
            <input
              type="checkbox"
              className="me-1"
              checked={schedule.modes.includes(value)}
              onChange={(e) => setSchedule((s) => ({ ...s, modes: e.target.checked ? [...s.modes, value] : s.modes.filter((m) => m !== value) }))}
            />
            {label}
          </label>
        ))}
      </fieldset>

      <div className="mt-4">
        <p className="text-sm font-medium">ימים סגורים (חגים, אירועים)</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          {schedule.blocked_dates.map((d) => (
            <span key={d} className="rounded-full border px-2 py-0.5 text-sm">
              {d.split("-").reverse().join("/")}
              <button type="button" aria-label={`הסרת ${d}`} className="ms-1" onClick={() => setSchedule((s) => ({ ...s, blocked_dates: s.blocked_dates.filter((x) => x !== d) }))}>✕</button>
            </span>
          ))}
          <input aria-label="תאריך סגור" type="date" value={blocked} onChange={(e) => setBlocked(e.target.value)} className="rounded border p-1 text-sm" />
          <button type="button" disabled={!blocked} onClick={() => { setSchedule((s) => ({ ...s, blocked_dates: [...new Set([...s.blocked_dates, blocked])].sort() })); setBlocked(""); }} className="text-sm underline disabled:opacity-50">הוספה</button>
        </div>
      </div>

      {status ? <p role="status" className="mt-3 text-sm">{status}</p> : null}
      <button type="button" disabled={busy} onClick={() => void save()} className="mt-4 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
        {busy ? "שומר…" : "שמירת שעות הביקור"}
      </button>
    </section>
  );
}
