"use client";

import { useMemo, useState } from "react";

import type { VisitCalendar, VisitCalendarDay } from "@/lib/israel-facility";

const WEEK = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"];

/** Month-style grid of the facility's next 30 days; days with open slots are selectable. */
export function VisitCalendarGrid({
  calendar,
  selectedDate,
  selectedTime,
  onPick,
}: {
  calendar: VisitCalendar;
  selectedDate: string | null;
  selectedTime: string | null;
  onPick: (date: string, time: string | null) => void;
}) {
  const weeks = useMemo(() => {
    const days = calendar.days;
    if (!days.length) return [] as (VisitCalendarDay | null)[][];
    const first = new Date(`${days[0].date}T12:00:00`);
    const cells: (VisitCalendarDay | null)[] = Array(first.getDay()).fill(null).concat(days);
    while (cells.length % 7) cells.push(null);
    const rows: (VisitCalendarDay | null)[][] = [];
    for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
    return rows;
  }, [calendar.days]);
  const [focus, setFocus] = useState<string | null>(selectedDate);
  const day = calendar.days.find((d) => d.date === (focus ?? selectedDate));

  return (
    <div>
      <table className="w-full table-fixed border-separate border-spacing-1 text-center" aria-label="ימים פנויים לביקור">
        <thead>
          <tr>
            {WEEK.map((w) => (
              <th key={w} scope="col" className="text-xs font-medium text-muted">
                {w}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => {
                if (!cell) return <td key={c} />;
                const open = cell.slots.length > 0;
                const active = cell.date === (focus ?? selectedDate);
                const d = new Date(`${cell.date}T12:00:00`);
                return (
                  <td key={c}>
                    <button
                      type="button"
                      disabled={!open}
                      aria-pressed={active}
                      aria-label={`${cell.label}${open ? `, ${cell.slots.length} מועדים פנויים` : ", אין מועדים פנויים"}`}
                      onClick={() => {
                        setFocus(cell.date);
                        onPick(cell.date, null);
                      }}
                      className={`h-11 w-full rounded-xl text-sm ${active ? "bg-black text-white" : open ? "border bg-white font-semibold" : "text-muted opacity-40"}`}
                    >
                      {d.getDate()}
                      {d.getDate() === 1 || cell === calendar.days[0] ? <span className="block text-[10px] font-normal">{d.toLocaleDateString("he-IL", { month: "short" })}</span> : null}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {day ? (
        <div className="mt-3">
          <p className="text-sm font-medium">{day.label}</p>
          <div role="radiogroup" aria-label="שעה" className="mt-2 flex flex-wrap gap-2">
            {day.slots.map((slot) => (
              <button
                key={slot.time}
                type="button"
                role="radio"
                aria-checked={selectedTime === slot.time && selectedDate === day.date}
                onClick={() => onPick(day.date, slot.time)}
                className={`rounded-full border px-4 py-2 text-sm ${selectedTime === slot.time && selectedDate === day.date ? "bg-black text-white" : "bg-white"}`}
                dir="ltr"
              >
                {slot.time}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted">בחרו יום מודגש כדי לראות את השעות הפנויות.</p>
      )}
    </div>
  );
}
