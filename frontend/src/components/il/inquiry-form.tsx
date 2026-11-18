"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { LEVEL_LABELS, MOVE_IN_LABELS, ROOM_LABELS, sendInquiry } from "@/lib/israel-facility";

/**
 * A short, focused request to one facility. The family chooses what to share:
 * the monthly and deposit ceilings are optional.
 */
export function InquiryForm({ canonicalId, facilityName }: { canonicalId: string; facilityName: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    room_type: "",
    level: "",
    move_in: "",
    monthly_cap_ils: "",
    deposit_cap_ils: "",
    contact_name: "",
    contact_phone: "",
    note: "",
  });
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));
  const field = "mt-1 w-full rounded-xl border p-2";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const { token } = await sendInquiry(canonicalId, {
        ...form,
        monthly_cap_ils: form.monthly_cap_ils ? Number(form.monthly_cap_ils) : null,
        deposit_cap_ils: form.deposit_cap_ils ? Number(form.deposit_cap_ils) : null,
      });
      router.push(`/he/inquiry/${token}`);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "השליחה נכשלה.");
      setSending(false);
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="mt-4 rounded-xl bg-black px-4 py-3 font-semibold text-white">
        פנייה ל{facilityName} ותיאום ביקור
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="mt-4 space-y-3 rounded-xl border p-4">
      <h2 className="text-xl font-semibold">בקשה ממוקדת למוסד</h2>
      <p className="text-sm">המוסד יוכל לאשר, להציע מסלול אחר או לבקש פרט נוסף. את התשובה תראו בקישור אישי שיופיע אחרי השליחה, ושם גם תוכלו להציע מועדים לביקור.</p>
      <label className="block text-sm">
        סוג חדר או דירה
        <select className={field} value={form.room_type} onChange={set("room_type")}>
          <option value="">לא משנה / לא יודעים</option>
          {Object.entries(ROOM_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className="block text-sm">
        המצב התפקודי
        <select className={field} value={form.level} onChange={set("level")}>
          <option value="">לא בטוחים</option>
          {Object.entries(LEVEL_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className="block text-sm">
        מתי מתכננים להיכנס? *
        <select className={field} value={form.move_in} onChange={set("move_in")} required>
          <option value="">בחרו</option>
          {Object.entries(MOVE_IN_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          תשלום חודשי עד (₪, לא חובה)
          <input dir="ltr" type="number" min={0} className={field} value={form.monthly_cap_ils} onChange={set("monthly_cap_ils")} />
        </label>
        <label className="block text-sm">
          פיקדון עד (₪, לא חובה)
          <input dir="ltr" type="number" min={0} className={field} value={form.deposit_cap_ils} onChange={set("deposit_cap_ils")} />
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          שם *
          <input className={field} value={form.contact_name} onChange={set("contact_name")} required maxLength={80} />
        </label>
        <label className="block text-sm">
          טלפון *
          <input dir="ltr" type="tel" className={field} value={form.contact_phone} onChange={set("contact_phone")} required />
        </label>
      </div>
      <label className="block text-sm">
        משהו נוסף שחשוב שהמוסד יידע
        <textarea className={`${field} min-h-20`} maxLength={1000} value={form.note} onChange={set("note")} />
      </label>
      <p className="text-xs">השם והטלפון יועברו רק למוסד הזה.</p>
      {error ? <p role="alert" className="text-sm">{error}</p> : null}
      <button type="submit" disabled={sending} className="rounded-xl bg-black px-4 py-2 font-semibold text-white disabled:opacity-50">
        {sending ? "שולח…" : "שליחה"}
      </button>
    </form>
  );
}
