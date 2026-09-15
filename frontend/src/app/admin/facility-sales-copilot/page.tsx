"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  FacilitySalesCopilotAnswer,
  FacilitySalesCopilotBootstrap,
  FacilityRecord,
  FacilityRecordSearchResult,
  addFacilityRecordDocument,
  addFacilityRecordEvent,
  askFacilitySalesCopilot,
  fetchFacilityRecord,
  fetchFacilitySalesCopilotBootstrap,
  searchFacilityRecords,
} from "@/lib/api";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

const TOKEN_KEY = "oomnik.sales-desk.token";

export default function FacilitySalesCopilotPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [question, setQuestion] = useState("");
  const [facilityName, setFacilityName] = useState("");
  const [facilityResults, setFacilityResults] = useState<FacilityRecordSearchResult[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState("");
  const [facilityRecord, setFacilityRecord] = useState<FacilityRecord | null>(null);
  const [eventSummary, setEventSummary] = useState("");
  const [eventType, setEventType] = useState("CALL");
  const [contactName, setContactName] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentType, setDocumentType] = useState("CONTRACT");
  const [documentUrl, setDocumentUrl] = useState("");
  const [callStage, setCallStage] = useState("FOLLOW_UP_AFTER_EMAIL");
  const [bootstrap, setBootstrap] = useState<FacilitySalesCopilotBootstrap | null>(null);
  const [answer, setAnswer] = useState<FacilitySalesCopilotAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.resolve().then(() => {
      try {
        const saved = window.sessionStorage.getItem(TOKEN_KEY) || "";
        setToken(saved);
        setTokenInput(saved);
      } catch {
        // The representative may enter the dedicated Sales Desk code.
      }
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    let active = true;
    fetchFacilitySalesCopilotBootstrap(token)
      .then((value) => {
        if (active) {
          setBootstrap(value);
          setError(null);
        }
      })
      .catch((err) => active && setError(err instanceof Error ? err.message : "Unable to unlock the copilot."));
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token || facilityName.trim().length < 2 || selectedFacilityId) return;
    const timer = window.setTimeout(() => {
      searchFacilityRecords(facilityName.trim(), token).then(setFacilityResults).catch(() => setFacilityResults([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [facilityName, selectedFacilityId, token]);

  useEffect(() => {
    if (!token || !selectedFacilityId) return;
    fetchFacilityRecord(selectedFacilityId, token).then(setFacilityRecord).catch((err) => setError(err instanceof Error ? err.message : "Unable to load facility record."));
  }, [selectedFacilityId, token]);

  function unlock() {
    const value = tokenInput.trim();
    if (!value) return;
    try { window.sessionStorage.setItem(TOKEN_KEY, value); } catch {}
    setToken(value);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setAnswer(await askFacilitySalesCopilot({
        question: question.trim(),
        canonical_facility_id: selectedFacilityId || undefined,
        facility_name: facilityName.trim() || undefined,
        call_stage: callStage,
      }, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The copilot could not answer.");
    } finally {
      setLoading(false);
    }
  }

  function selectFacility(facility: FacilityRecordSearchResult) {
    setSelectedFacilityId(facility.canonical_facility_id);
    setFacilityName(facility.facility_name);
    setFacilityResults([]);
  }

  async function saveEvent() {
    if (!selectedFacilityId || !eventSummary.trim()) return;
    setLoading(true); setError(null);
    try {
      setFacilityRecord(await addFacilityRecordEvent(selectedFacilityId, {
        event_type: eventType, channel: eventType === "EMAIL" ? "EMAIL" : eventType === "WEBSITE" ? "WEBSITE" : "PHONE",
        direction: eventType === "NOTE" ? "INTERNAL" : "OUTBOUND", summary: eventSummary.trim(), contact_name: contactName.trim() || undefined,
      }, token));
      setEventSummary("");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save activity."); }
    finally { setLoading(false); }
  }

  async function saveDocument() {
    if (!selectedFacilityId || !documentTitle.trim() || !documentUrl.trim()) return;
    setLoading(true); setError(null);
    try {
      setFacilityRecord(await addFacilityRecordDocument(selectedFacilityId, {
        title: documentTitle.trim(), document_type: documentType, document_url: documentUrl.trim(),
      }, token));
      setDocumentTitle(""); setDocumentUrl("");
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save document."); }
    finally { setLoading(false); }
  }

  if (!token || !bootstrap) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#dff7ed_0,#f7fbf9_38%,#e7eef8_100%)] px-6 py-14 text-[#0b2850]">
        <section className="mx-auto max-w-md space-y-5 rounded-[2rem] border border-white/80 bg-white/85 p-8 shadow-[0_30px_90px_rgba(11,40,80,.18)] backdrop-blur-xl">
          <div className="scale-[1.55] origin-left"><OptimeStaticLogo href="/partner-desk" /></div>
          <p className="pt-4 text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">Partner desk · Staff only</p>
          <h1 className="text-3xl font-black tracking-tight">Your live facility sales command center.</h1>
          <p className="text-sm leading-6 text-slate-600">Approved answers, commercial terms, market evidence, and objection handling—built for the team introducing the next generation of senior-living matching.</p>
          <label className="block text-sm font-semibold text-slate-700">Sales Desk access code
            <input type="password" autoComplete="current-password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && unlock()} placeholder="Sales access code" className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white" />
          </label>
          <button type="button" onClick={unlock} className="w-full rounded-xl bg-[#0b2850] px-4 py-3 font-semibold text-white shadow-lg hover:bg-[#123b70]">Enter Partner Desk</button>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_10%_0%,#173f70_0,#071a33_34%,#030b17_100%)] px-5 py-8 text-slate-100 sm:px-10">
      <section className="mx-auto max-w-6xl space-y-6">
        <header className="overflow-hidden rounded-[2rem] border border-white/15 bg-white/[.07] p-7 shadow-[0_25px_80px_rgba(0,0,0,.35)] backdrop-blur-xl sm:p-10">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <div className="inline-block rounded-2xl bg-white px-5 py-3 shadow-xl"><div className="scale-[1.45] origin-left pr-24"><OptimeStaticLogo href="/partner-desk" /></div></div>
              <p className="mt-8 text-xs font-bold uppercase tracking-[0.25em] text-emerald-300">Oomnik Partner Desk · Las Vegas</p>
              <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight tracking-[-0.04em] sm:text-6xl">Build the matching platform every community will want to join.</h1>
              <p className="mt-4 max-w-3xl text-lg text-slate-300">Finding You the Right Way. Give every facility conversation the confidence, evidence, and polish of a category-defining company.</p>
            </div>
            <Link href="/" className="rounded-full border border-white/20 bg-white/10 px-5 py-2 text-sm text-white hover:bg-white/20">Oomnik Home</Link>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-3xl border border-emerald-400/30 bg-emerald-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-300">Founding offer</p><p className="mt-3 text-3xl font-black">$0 Oomnik fee</p><p className="mt-2 text-sm text-slate-300">First placement for qualifying communities onboarding in the 90-day launch window. Facility funds the $500 Welcome Package.</p></article>
          <article className="rounded-3xl border border-sky-400/30 bg-sky-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-sky-300">Standard placement</p><p className="mt-3 text-3xl font-black">$1,999 after 60 days</p><p className="mt-2 text-sm text-slate-300">Outcome-aligned fee. From placement two onward, the Welcome Package is split $250 facility / $250 Oomnik.</p></article>
          <article className="rounded-3xl border border-violet-400/30 bg-violet-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-300">Participating · Private pay only</p><p className="mt-3 text-3xl font-black">$500 Welcome Package</p><p className="mt-2 text-sm text-slate-300">Requires a registered participating facility and an eligible private-pay placement. Not available for Medicare, Medicaid, VA, or other government-funded placements.</p></article>
        </section>

        <section className="rounded-3xl border border-sky-700/70 bg-sky-950/30 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">How to ask Oomnik during a call</p>
          <h2 className="mt-2 text-xl font-semibold">Write the caller's question exactly as it was asked</h2>
          <ol className="mt-4 grid gap-2 text-sm text-slate-200 sm:grid-cols-2">
            {bootstrap.how_to_use.map((step, index) => <li key={step} className="rounded-xl bg-slate-950/50 p-3"><span className="mr-2 font-semibold text-sky-300">{index + 1}.</span>{step}</li>)}
          </ol>
          <p className="mt-4 rounded-xl border border-amber-700/50 bg-amber-950/30 p-3 text-sm text-amber-100">
            Example: “The facility says it has no employee available to maintain its profile. What should I offer?”
          </p>
        </section>

        {facilityRecord ? <section className="rounded-3xl border border-emerald-500/30 bg-white/[.06] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">Facility Record</p><h2 className="mt-2 text-3xl font-black">{facilityRecord.facility.name}</h2><p className="mt-1 text-sm text-slate-300">{[facilityRecord.facility.address, facilityRecord.facility.city, facilityRecord.facility.state].filter(Boolean).join(", ")}</p></div>
            <div className="flex gap-2 text-sm"><span className="rounded-full bg-sky-950 px-4 py-2">{facilityRecord.counts.timeline_events} activities</span><span className="rounded-full bg-violet-950 px-4 py-2">{facilityRecord.counts.documents} documents</span></div>
          </div>
          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-700 bg-slate-950/50 p-5">
              <h3 className="font-semibold">Record a call, email or note</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2"><select value={eventType} onChange={(e) => setEventType(e.target.value)} className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2"><option>CALL</option><option>EMAIL</option><option>WEBSITE</option><option>MEETING</option><option>NOTE</option></select><input value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="Facility contact" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" /></div>
              <textarea value={eventSummary} onChange={(e) => setEventSummary(e.target.value)} rows={3} placeholder="What happened, what was agreed, and the next step" className="mt-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" />
              <button type="button" onClick={saveEvent} disabled={loading || !eventSummary.trim()} className="mt-3 rounded-full bg-emerald-600 px-5 py-2 font-semibold disabled:opacity-50">Save activity</button>
            </div>
            <div className="rounded-2xl border border-slate-700 bg-slate-950/50 p-5">
              <h3 className="font-semibold">Attach a document</h3><p className="mt-1 text-xs text-slate-400">Add a secure Drive, Dropbox or document-system link. File upload will follow encrypted storage.</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2"><select value={documentType} onChange={(e) => setDocumentType(e.target.value)} className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2"><option>CONTRACT</option><option>ADDENDUM</option><option>LICENSE</option><option>CORRESPONDENCE</option><option>PRICING</option><option>INSURANCE</option><option>OTHER</option></select><input value={documentTitle} onChange={(e) => setDocumentTitle(e.target.value)} placeholder="Document title" className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" /></div>
              <input value={documentUrl} onChange={(e) => setDocumentUrl(e.target.value)} placeholder="https:// secure document link" className="mt-3 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" />
              <button type="button" onClick={saveDocument} disabled={loading || !documentTitle.trim() || !documentUrl.trim()} className="mt-3 rounded-full bg-violet-600 px-5 py-2 font-semibold disabled:opacity-50">Attach to record</button>
            </div>
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div><h3 className="font-semibold">Complete history</h3><div className="mt-3 max-h-80 space-y-3 overflow-y-auto">{facilityRecord.timeline.length ? facilityRecord.timeline.map((item) => <article key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><div className="flex justify-between gap-3 text-xs text-slate-400"><span>{item.event_type} · {item.direction}</span><time>{new Date(item.occurred_at).toLocaleString()}</time></div>{item.subject ? <p className="mt-2 font-semibold">{item.subject}</p> : null}<p className="mt-1 whitespace-pre-wrap text-sm text-slate-200">{item.summary}</p>{item.contact_name ? <p className="mt-2 text-xs text-sky-300">Contact: {item.contact_name}</p> : null}</article>) : <p className="text-sm text-slate-400">No activity recorded yet.</p>}</div></div>
            <div><h3 className="font-semibold">Documents</h3><div className="mt-3 max-h-80 space-y-3 overflow-y-auto">{facilityRecord.documents.length ? facilityRecord.documents.map((item) => <a key={item.id} href={item.document_url} target="_blank" rel="noreferrer" className="block rounded-xl border border-slate-800 bg-slate-950/50 p-4 hover:border-violet-500"><span className="text-xs text-violet-300">{item.document_type} · {item.status}</span><span className="mt-1 block font-semibold">{item.title}</span><span className="mt-1 block text-xs text-slate-400">Added {new Date(item.created_at).toLocaleString()}</span></a>) : <p className="text-sm text-slate-400">No documents attached yet.</p>}</div></div>
          </div>
        </section> : null}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,.65fr)]">
          <div className="space-y-5">
            <form onSubmit={submit} className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="relative text-sm text-slate-300">Facility record
                  <input value={facilityName} onChange={(e) => { setFacilityName(e.target.value); setSelectedFacilityId(""); setFacilityRecord(null); }} placeholder="Search a Las Vegas facility" className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white" />
                  {facilityResults.length ? <div className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 shadow-2xl">
                    {facilityResults.map((facility) => <button key={facility.canonical_facility_id} type="button" onClick={() => selectFacility(facility)} className="block w-full border-b border-slate-800 px-4 py-3 text-left hover:bg-slate-800">
                      <span className="block font-semibold text-white">{facility.facility_name}</span><span className="text-xs text-slate-400">{facility.city}, {facility.state} · {facility.canonical_type || "Type unknown"}</span>
                    </button>)}
                  </div> : null}
                </label>
                <label className="text-sm text-slate-300">Call stage
                  <select value={callStage} onChange={(e) => setCallStage(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white">
                    <option value="FOLLOW_UP_AFTER_EMAIL">Follow-up after email</option>
                    <option value="INTRODUCTION">Introduction</option>
                    <option value="COMMERCIAL_REVIEW">Commercial review</option>
                    <option value="ONBOARDING">Onboarding</option>
                    <option value="OBJECTION_HANDLING">Objection handling</option>
                  </select>
                </label>
              </div>
              <label className="block text-sm text-slate-300">What did the facility ask?
                <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={5} placeholder='Example: “Does paying Oomnik improve our ranking?”' className="mt-1 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white" />
              </label>
              <button disabled={loading || !question.trim()} className="rounded-full bg-emerald-600 px-6 py-3 font-semibold hover:bg-emerald-500 disabled:opacity-50">{loading ? "Preparing answer…" : "Get approved answer"}</button>
            </form>

            {error ? <p className="rounded-2xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-200">{error}</p> : null}
            {answer ? (
              <article className="space-y-4 rounded-3xl border border-emerald-700 bg-emerald-950/25 p-6">
                <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em]">
                  <span className="rounded-full bg-emerald-800 px-3 py-1 text-emerald-100">{answer.confidence} confidence</span>
                  {answer.escalation ? <span className="rounded-full bg-amber-800 px-3 py-1 text-amber-100">Escalate: {answer.escalation.replaceAll("_", " ")}</span> : null}
                </div>
                <section>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Say this</p>
                  <p className="mt-2 text-xl leading-relaxed text-white">“{answer.say_this}”</p>
                </section>
                {answer.bridge_phrase ? <section className="rounded-2xl border border-amber-700/60 bg-amber-950/30 p-4"><p className="text-xs uppercase tracking-[0.18em] text-amber-300">If you need time</p><p className="mt-2 text-amber-50">“{answer.bridge_phrase}”</p></section> : null}
                {answer.evidence ? <section className={`rounded-2xl border p-4 ${answer.evidence.verification_status === "VERIFIED" ? "border-emerald-700/60 bg-emerald-950/30" : "border-amber-700/60 bg-amber-950/30"}`}>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">Agent evidence · {answer.evidence.verification_status.replaceAll("_", " ")}</p>
                  <p className="mt-2 text-sm">{answer.evidence.value_display} — {answer.evidence.metric_definition}</p>
                  <p className="mt-1 text-xs text-slate-300">Data period: {answer.evidence.data_period} · Geography: {answer.evidence.geography} · Checked: {answer.evidence.checked_at}</p>
                  <a href={answer.evidence.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm underline">{answer.evidence.source_title} — {answer.evidence.source_publisher}</a>
                </section> : null}
                {answer.objection_guidance?.supporting.length ? <section className="rounded-2xl border border-sky-800/60 bg-sky-950/25 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">Use only if needed</p>
                  <div className="mt-2 space-y-2">{answer.objection_guidance.supporting.map((item) => <p key={item.id} className="text-sm text-slate-200">“{item.line}”</p>)}</div>
                </section> : null}
                <section><p className="text-xs uppercase tracking-[0.18em] text-slate-400">Next step</p><p className="mt-1 text-slate-200">{answer.next_step}</p></section>
              </article>
            ) : null}
          </div>

          <aside className="space-y-5">
            <section className="rounded-3xl border border-emerald-800/70 bg-emerald-950/25 p-5">
              <h2 className="font-semibold">Sales lines</h2>
              <p className="mt-1 text-xs text-slate-400">Use the idea naturally. Do not recite every line in one call.</p>
              <div className="mt-3 space-y-3">{bootstrap.sales_lines.map((item) => <button key={item.id} type="button" onClick={() => navigator.clipboard?.writeText(item.line)} className="w-full rounded-xl border border-emerald-800/60 p-3 text-left hover:border-emerald-500"><span className="block text-xs font-semibold uppercase tracking-[0.12em] text-emerald-300">{item.title}</span><span className="mt-1 block text-sm text-slate-200">“{item.line}”</span></button>)}</div>
            </section>
            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
              <h2 className="font-semibold">Call rules</h2>
              <ol className="mt-3 space-y-2 text-sm text-slate-300">{bootstrap.rules.map((rule, index) => <li key={rule}>{index + 1}. {rule}</li>)}</ol>
            </section>
            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
              <h2 className="font-semibold">Professional bridge phrases</h2>
              <div className="mt-3 space-y-3">{bootstrap.bridge_phrases.map((phrase) => <button key={phrase} type="button" onClick={() => navigator.clipboard?.writeText(phrase)} className="w-full rounded-xl border border-slate-700 p-3 text-left text-sm text-slate-300 hover:border-emerald-600">“{phrase}”</button>)}</div>
            </section>
          </aside>
        </div>
      </section>
    </main>
  );
}
