"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Followup = { id: number; event_type: string; facility_id: string; status: string; note?: string; created_at: string; contact_name?: string; email?: string; phone?: string; request: { facility_name?: string; preferred_date?: string; contact_name?: string; email?: string; phone?: string } };

export default function ClientFollowupsPage() {
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Followup[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => { if (active) { try { setToken(window.sessionStorage.getItem("optime.admin.token") || ""); } catch { /* Manual token entry remains available. */ } } });
    return () => { active = false; };
  }, []);
  async function load() {
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/backend/api/admin/client-followups", { headers: { "x-admin-token": token.trim() }, cache: "no-store" });
      if (!response.ok) throw new Error("Unable to load requests. Check your admin token.");
      setRows(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load requests."); }
    finally { setBusy(false); }
  }
  async function update(id: number, status: string) {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/backend/api/admin/client-followups/${id}`, { method: "PATCH", headers: { "x-admin-token": token.trim(), "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
      if (!response.ok) throw new Error("Unable to update this request.");
      setRows(current => current?.flatMap(row => row.id !== id ? [row] : status === "COMPLETED" ? [] : [{ ...row, status }]) || []);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to update request."); }
    finally { setBusy(false); }
  }
  return <main className="min-h-screen bg-[#f7faf8] px-5 py-10 text-[#293e34]"><section className="mx-auto max-w-4xl">
    <Link href="/admin" className="underline">Back to admin</Link>
    <h1 className="mt-5 text-3xl font-semibold">Client visit and pricing requests</h1>
    <p className="mt-3 text-lg leading-8">Follow up with the client and community. A requested date is a preference, not a confirmed appointment. Completing a follow-up does not book a visit or send a message.</p>
    <form onSubmit={e => { e.preventDefault(); void load(); }} className="mt-5 flex flex-wrap gap-3"><label className="flex-1">Admin token<input type="password" value={token} onChange={e => setToken(e.target.value)} autoComplete="off" className="mt-2 block w-full rounded-xl border p-3" /></label><button disabled={busy || !token.trim()} className="self-end rounded-full bg-[#315f53] px-6 py-3 text-white disabled:opacity-40">{busy ? "Working…" : "Load / refresh requests"}</button></form>
    {error ? <p role="alert" className="mt-4 text-[#943b28]">{error}</p> : null}
    {rows?.length === 0 ? <p className="mt-6 text-lg">No open requests.</p> : null}
    <div className="mt-6 space-y-5">{rows?.map(row => <article key={row.id} className="rounded-2xl border bg-white p-6 text-lg leading-8">
      <h2 className="text-2xl font-semibold">{row.event_type === "VISIT_REQUESTED" ? "Visit request" : "Rooms and current prices"} · {row.request.facility_name || row.facility_id}</h2>
      <p>{row.request.contact_name || row.contact_name || "Name not supplied"} · {row.request.email || row.email || "Email not supplied"} · {row.request.phone || row.phone || "Phone not supplied"}</p>
      <p>Status: {row.status === "IN_PROGRESS" ? "In progress" : "Awaiting follow-up"} · Received {new Date(row.created_at).toLocaleString()}</p>
      {row.request.preferred_date ? <p>Preferred visit date: {row.request.preferred_date} — needs confirmation</p> : null}
      {row.note ? <p className="whitespace-pre-wrap">{row.note}</p> : null}
      <div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={busy || row.status === "IN_PROGRESS"} onClick={() => void update(row.id, "IN_PROGRESS")} className="rounded-full border px-5 py-2 disabled:opacity-40">Start follow-up</button><button type="button" disabled={busy} onClick={() => void update(row.id, "COMPLETED")} className="rounded-full bg-[#315f53] px-5 py-2 text-white disabled:opacity-40">Mark follow-up complete</button></div>
    </article>)}</div>
  </section></main>;
}
