"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { FeedbackForm } from "@/components/il/feedback-form";
import { fetchInquiry, MESSAGE_LABELS, replyToInquiry, type InquiryView } from "@/lib/israel-facility";

const ils = (n?: number | null) => (n == null ? null : `₪${n.toLocaleString("he-IL")}`);

/** The family's private view of one request and the facility's answers. */
export default function InquiryPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [view, setView] = useState<InquiryView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchInquiry(token)
      .then((loaded) => {
        if (!cancelled) setView(loaded);
      })
      .catch(() => {
        if (!cancelled) setError("הבקשה לא נמצאה. בדקו שהקישור הועתק במלואו.");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function sendReply() {
    if (!reply.trim()) return;
    setSending(true);
    try {
      setView(await replyToInquiry(token, reply));
      setReply("");
    } catch (replyError) {
      setError(replyError instanceof Error ? replyError.message : "השליחה נכשלה.");
    } finally {
      setSending(false);
    }
  }

  if (error && !view) return <main dir="rtl" lang="he" className="mx-auto max-w-2xl p-6"><p role="alert">{error}</p></main>;
  if (!view) return <main dir="rtl" lang="he" className="mx-auto max-w-2xl p-6"><p role="status">טוען…</p></main>;

  const request = view.request;
  return (
    <main dir="rtl" lang="he" className="mx-auto max-w-2xl p-6">
      <p className="text-sm">הבקשה שלכם ל־</p>
      <h1 className="text-2xl font-semibold">
        <Link className="underline" href={`/he/facility/${encodeURIComponent(view.facility.canonical_id)}`}>{view.facility.name}</Link>
      </h1>
      <p className="mt-3 rounded-xl border p-3 font-semibold" role="status">{view.status_label}</p>
      <p className="mt-2 text-sm">שמרו את הקישור לדף הזה כדי לחזור אליו. רק מי שמחזיק בקישור רואה את הבקשה.</p>

      <dl className="mt-6 space-y-1 text-sm">
        <div className="flex gap-2"><dt className="w-36 font-semibold">סוג חדר</dt><dd>{request.room_type}</dd></div>
        <div className="flex gap-2"><dt className="w-36 font-semibold">מצב תפקודי</dt><dd>{request.level}</dd></div>
        <div className="flex gap-2"><dt className="w-36 font-semibold">מועד כניסה</dt><dd>{request.move_in}</dd></div>
        <div className="flex gap-2"><dt className="w-36 font-semibold">תשלום חודשי עד</dt><dd>{ils(request.monthly_cap_ils as number | null) ?? "לא שותף"}</dd></div>
        <div className="flex gap-2"><dt className="w-36 font-semibold">פיקדון עד</dt><dd>{ils(request.deposit_cap_ils as number | null) ?? "לא שותף"}</dd></div>
      </dl>

      <h2 className="mt-8 text-xl font-semibold">ההתכתבות</h2>
      <ol className="mt-3 space-y-3">
        {view.messages.map((message, index) => (
          <li key={index} className={`rounded-xl border p-3 ${message.from === "FACILITY" ? "bg-sand" : ""}`}>
            <p className="font-semibold">{MESSAGE_LABELS[message.kind]}</p>
            {message.text ? <p className="mt-1 whitespace-pre-wrap">{message.text}</p> : null}
            {message.monthly_ils || message.deposit_ils ? (
              <p className="mt-1 text-sm">
                {message.monthly_ils ? `תשלום חודשי: ${ils(message.monthly_ils)}` : ""}
                {message.monthly_ils && message.deposit_ils ? " · " : ""}
                {message.deposit_ils ? `פיקדון: ${ils(message.deposit_ils)}` : ""}
              </p>
            ) : null}
            <p className="mt-1 text-xs" dir="ltr">{new Date(message.at).toLocaleString("he-IL")}</p>
          </li>
        ))}
      </ol>

      {view.status === "NEED_INFO" || view.status === "ALTERNATIVE" ? (
        <div className="mt-6">
          <label className="block font-medium" htmlFor="reply">התשובה שלכם למוסד</label>
          <textarea id="reply" className="mt-1 min-h-24 w-full rounded-xl border p-2" maxLength={1000} value={reply} onChange={(e) => setReply(e.target.value)} />
          {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}
          <button type="button" onClick={() => void sendReply()} disabled={sending || !reply.trim()} className="mt-2 rounded-xl bg-black px-4 py-2 text-white disabled:opacity-50">
            {sending ? "שולח…" : "שליחת תשובה"}
          </button>
        </div>
      ) : null}

      <FeedbackForm token={token} facilityName={view.facility.name} />
    </main>
  );
}
