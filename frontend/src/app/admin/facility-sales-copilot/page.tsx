"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  FacilitySalesCopilotAnswer,
  FacilitySalesCopilotBootstrap,
  askFacilitySalesCopilot,
  fetchFacilitySalesCopilotBootstrap,
} from "@/lib/api";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

const TOKEN_KEY = "optime.admin.token";

export default function FacilitySalesCopilotPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [question, setQuestion] = useState("");
  const [facilityName, setFacilityName] = useState("");
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
        // Staff may still enter the token for this session.
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
        facility_name: facilityName.trim() || undefined,
        call_stage: callStage,
      }, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The copilot could not answer.");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !bootstrap) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#dff7ed_0,#f7fbf9_38%,#e7eef8_100%)] px-6 py-14 text-[#0b2850]">
        <section className="mx-auto max-w-md space-y-5 rounded-[2rem] border border-white/80 bg-white/85 p-8 shadow-[0_30px_90px_rgba(11,40,80,.18)] backdrop-blur-xl">
          <div className="scale-[1.55] origin-left"><OptimeStaticLogo href="/admin/facility-sales-copilot" /></div>
          <p className="pt-4 text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">Partner desk · Staff only</p>
          <h1 className="text-3xl font-black tracking-tight">Your live facility sales command center.</h1>
          <p className="text-sm leading-6 text-slate-600">Approved answers, commercial terms, market evidence, and objection handling—built for the team introducing the next generation of senior-living matching.</p>
          <input type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && unlock()} placeholder="Admin token" className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3" />
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
              <div className="inline-block rounded-2xl bg-white px-5 py-3 shadow-xl"><div className="scale-[1.45] origin-left pr-24"><OptimeStaticLogo href="/admin/facility-sales-copilot" /></div></div>
              <p className="mt-8 text-xs font-bold uppercase tracking-[0.25em] text-emerald-300">Oomnik Partner Desk · Las Vegas</p>
              <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight tracking-[-0.04em] sm:text-6xl">Build the matching platform every community will want to join.</h1>
              <p className="mt-4 max-w-3xl text-lg text-slate-300">Finding You the Right Way. Give every facility conversation the confidence, evidence, and polish of a category-defining company.</p>
            </div>
            <Link href="/admin" className="rounded-full border border-white/20 bg-white/10 px-5 py-2 text-sm text-white hover:bg-white/20">Back to Admin</Link>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-3xl border border-emerald-400/30 bg-emerald-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-300">Founding offer</p><p className="mt-3 text-3xl font-black">$0 Oomnik fee</p><p className="mt-2 text-sm text-slate-300">First placement for qualifying communities onboarding in the 90-day launch window. Facility funds the $500 Welcome Package.</p></article>
          <article className="rounded-3xl border border-sky-400/30 bg-sky-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-sky-300">Standard placement</p><p className="mt-3 text-3xl font-black">$1,999 after 60 days</p><p className="mt-2 text-sm text-slate-300">Outcome-aligned fee. From placement two onward, the Welcome Package is split $250 facility / $250 Oomnik.</p></article>
          <article className="rounded-3xl border border-violet-400/30 bg-violet-400/10 p-6"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-300">Resident benefit</p><p className="mt-3 text-3xl font-black">$500 Welcome Package</p><p className="mt-2 text-sm text-slate-300">A defined part of the Oomnik placement offer, supporting approved transition needs—not an unrelated promotion.</p></article>
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

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,.65fr)]">
          <div className="space-y-5">
            <form onSubmit={submit} className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm text-slate-300">Facility name
                  <input value={facilityName} onChange={(e) => setFacilityName(e.target.value)} placeholder="Optional" className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white" />
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
