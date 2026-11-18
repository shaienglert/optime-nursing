"use client";

import { useEffect, useState } from "react";

import type { VisitView } from "@/lib/israel-facility";
import { answerVisitAsFacility, fetchProviderInquiries, respondToInquiry, type ProviderInquiry } from "@/lib/provider-api";

const ils = (n?: number | string | null) => (n == null || n === "" ? null : `₪${Number(n).toLocaleString("he-IL")}`);
const KINDS: [string, string][] = [
  ["ACCEPT", "לאשר שיש התאמה"],
  ["ALTERNATIVE", "להציע מסלול אחר"],
  ["NEED_INFO", "לבקש פרט נוסף"],
  ["DECLINE", "לא נוכל לקבל כרגע"],
];
const MESSAGE: Record<string, string> = {
  REQUEST: "הבקשה התקבלה",
  REPLY: "תשובת המשפחה",
  ACCEPT: "אישרתם התאמה",
  ALTERNATIVE: "הצעתם מסלול אחר",
  NEED_INFO: "ביקשתם פרט נוסף",
  DECLINE: "השבתם שלא תוכלו לקבל",
};

/** Requests families sent to this facility, and the facility's answers. */
export function IsraelInquiries({ facilityId, enabled }: { facilityId: number; enabled: boolean }) {
  const [inquiries, setInquiries] = useState<ProviderInquiry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    fetchProviderInquiries(facilityId)
      .then((rows) => {
        if (!cancelled) setInquiries(rows);
      })
      .catch(() => {
        if (!cancelled) setError("לא ניתן לטעון את הבקשות כרגע.");
      });
    return () => {
      cancelled = true;
    };
  }, [facilityId, enabled]);

  if (!enabled) return null;
  const replace = (updated: ProviderInquiry) =>
    setInquiries((rows) => (rows ?? []).map((row) => (row.inquiry_id === updated.inquiry_id ? updated : row)));

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold">בקשות ממשפחות</h2>
      {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
      {inquiries && !inquiries.length ? <p className="mt-2 text-sm">עוד לא התקבלו בקשות.</p> : null}
      <ul className="mt-3 space-y-4">
        {(inquiries ?? []).map((inquiry) => (
          <InquiryCard key={inquiry.inquiry_id} facilityId={facilityId} inquiry={inquiry} onUpdated={replace} />
        ))}
      </ul>
    </section>
  );
}

function InquiryCard({ facilityId, inquiry, onUpdated }: { facilityId: number; inquiry: ProviderInquiry; onUpdated: (row: ProviderInquiry) => void }) {
  const [kind, setKind] = useState("ACCEPT");
  const [text, setText] = useState("");
  const [monthly, setMonthly] = useState("");
  const [deposit, setDeposit] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const r = inquiry.request;
  const field = "mt-1 w-full rounded-xl border p-2";

  async function send() {
    setSending(true);
    setError(null);
    try {
      onUpdated(
        await respondToInquiry(facilityId, inquiry.inquiry_id, {
          kind,
          text: text || undefined,
          monthly_ils: monthly ? Number(monthly) : null,
          deposit_ils: deposit ? Number(deposit) : null,
        }),
      );
      setText("");
      setMonthly("");
      setDeposit("");
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "השליחה נכשלה.");
    } finally {
      setSending(false);
    }
  }

  return (
    <li className="rounded-xl border p-4">
      <p className="font-semibold">{r.contact_name} · <span dir="ltr">{r.contact_phone}</span></p>
      <p className="mt-1 text-sm">
        {r.room_type} · {r.level} · כניסה: {r.move_in}
        {r.monthly_cap_ils ? ` · עד ${ils(r.monthly_cap_ils)} לחודש` : ""}
        {r.deposit_cap_ils ? ` · פיקדון עד ${ils(r.deposit_cap_ils)}` : ""}
      </p>
      {r.note ? <p className="mt-1 text-sm whitespace-pre-wrap">{r.note}</p> : null}
      <p className="mt-2 text-sm font-semibold">{inquiry.status_label}</p>
      <ol className="mt-2 space-y-1 text-sm">
        {inquiry.messages.slice(1).map((m, i) => (
          <li key={i}>
            <span className="font-semibold">{MESSAGE[m.kind] ?? m.kind}:</span> {m.text}
            {m.monthly_ils ? ` (${ils(m.monthly_ils)} לחודש)` : ""}
            {m.deposit_ils ? ` (פיקדון ${ils(m.deposit_ils)})` : ""}
          </li>
        ))}
      </ol>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <label className="text-sm">
          התשובה שלכם
          <select className={field} value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        {kind === "ALTERNATIVE" || kind === "ACCEPT" ? (
          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm">
              תשלום חודשי (₪)
              <input dir="ltr" type="number" min={0} className={field} value={monthly} onChange={(e) => setMonthly(e.target.value)} />
            </label>
            <label className="text-sm">
              פיקדון (₪)
              <input dir="ltr" type="number" min={0} className={field} value={deposit} onChange={(e) => setDeposit(e.target.value)} />
            </label>
          </div>
        ) : null}
      </div>
      <label className="mt-2 block text-sm">
        {kind === "NEED_INFO" ? "איזה פרט חסר?" : kind === "ALTERNATIVE" ? "מה המסלול שאתם מציעים?" : "הודעה למשפחה (לא חובה)"}
        <textarea className={`${field} min-h-16`} maxLength={1000} value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
      <button type="button" disabled={sending} onClick={() => void send()} className="mt-2 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
        {sending ? "שולח…" : "שליחה למשפחה"}
      </button>
      {inquiry.visit ? (
        <VisitBlock
          facilityId={facilityId}
          inquiryId={inquiry.inquiry_id}
          visit={inquiry.visit}
          onUpdated={(visit) => onUpdated({ ...inquiry, visit })}
        />
      ) : null}
    </li>
  );
}


/** The facility answers a family's visit request: confirm one of its dates with a time, propose another, or cancel. */
function VisitBlock({
  facilityId,
  inquiryId,
  visit,
  onUpdated,
}: {
  facilityId: number;
  inquiryId: number;
  visit: VisitView;
  onUpdated: (visit: VisitView) => void;
}) {
  const [slot, setSlot] = useState(0);
  const [time, setTime] = useState("10:00");
  const [otherDate, setOtherDate] = useState("");
  const [otherTime, setOtherTime] = useState("10:00");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const field = "mt-1 rounded-xl border p-2";

  async function act(body: Parameters<typeof answerVisitAsFacility>[2]) {
    setBusy(true);
    setError(null);
    try {
      onUpdated(await answerVisitAsFacility(facilityId, inquiryId, { ...body, note: note || undefined }));
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "הפעולה נכשלה.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 rounded-xl bg-sand p-3">
      <p className="font-semibold">
        ביקור ({visit.mode_label}, {visit.visitors} מבקרים): {visit.status_label}
      </p>
      {visit.confirmed ? <p className="mt-1 text-sm">{visit.status === "CONFIRMED" ? "נקבע" : "הצעתם"}: {visit.confirmed.label}</p> : null}
      {visit.note ? <p className="mt-1 text-sm whitespace-pre-wrap">הערת המשפחה: {visit.note}</p> : null}

      {visit.status === "REQUESTED" ? (
        <fieldset className="mt-2">
          <legend className="text-sm font-medium">המועדים שהמשפחה הציעה</legend>
          {visit.slots.map((s, index) => (
            <label key={s.date + s.part} className="mt-1 flex items-center gap-2 text-sm">
              <input type="radio" name={`slot-${inquiryId}`} checked={slot === index} onChange={() => setSlot(index)} />
              {s.label}
            </label>
          ))}
          <label className="mt-2 block text-sm">
            שעה מדויקת
            <input type="time" dir="ltr" className={`${field} ms-2`} value={time} onChange={(e) => setTime(e.target.value)} />
          </label>
          <button type="button" disabled={busy} onClick={() => void act({ action: "CONFIRM", slot_index: slot, time })} className="mt-2 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
            אישור המועד
          </button>
        </fieldset>
      ) : null}

      {visit.status !== "CANCELLED" ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm underline">להציע מועד אחר</summary>
          <div className="mt-2 flex flex-wrap gap-2">
            <label className="text-sm">
              תאריך
              <input type="date" dir="ltr" className={`${field} ms-2`} value={otherDate} onChange={(e) => setOtherDate(e.target.value)} />
            </label>
            <label className="text-sm">
              שעה
              <input type="time" dir="ltr" className={`${field} ms-2`} value={otherTime} onChange={(e) => setOtherTime(e.target.value)} />
            </label>
          </div>
          <button type="button" disabled={busy || !otherDate} onClick={() => void act({ action: "PROPOSE", date: otherDate, time: otherTime })} className="mt-2 rounded-xl border px-4 py-2 disabled:opacity-50">
            שליחת ההצעה למשפחה
          </button>
        </details>
      ) : null}

      <label className="mt-3 block text-sm">
        הערה למשפחה (למשל: לאן להגיע, את מי לשאול)
        <textarea className={`${field} min-h-12 w-full`} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
      {visit.status !== "CANCELLED" ? (
        <button type="button" disabled={busy} onClick={() => void act({ action: "CANCEL" })} className="mt-2 text-sm underline">
          ביטול הביקור
        </button>
      ) : null}
    </div>
  );
}
