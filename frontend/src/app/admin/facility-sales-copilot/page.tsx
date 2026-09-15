"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  FacilitySalesCopilotAnswer,
  FacilitySalesCopilotBootstrap,
  askFacilitySalesCopilot,
  fetchFacilitySalesCopilotBootstrap,
} from "@/lib/api";

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
      <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
        <section className="mx-auto max-w-md space-y-4 rounded-3xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300">Staff only</p>
          <h1 className="text-2xl font-semibold">Facility Sales Copilot</h1>
          <p className="text-sm text-slate-400">Enter the admin token. This tool contains approved commercial guidance and is not public.</p>
          <input type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && unlock()} placeholder="Admin token" className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3" />
          <button type="button" onClick={unlock} className="w-full rounded-xl bg-emerald-600 px-4 py-3 font-semibold hover:bg-emerald-500">Open Copilot</button>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-8 text-slate-100 sm:px-10">
      <section className="mx-auto max-w-6xl space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300">Live facility call support</p>
            <h1 className="mt-2 text-3xl font-semibold">Oomnik Facility Sales Copilot</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">Type the caller's question exactly. Read only the green “Say this” answer aloud. Escalate when instructed.</p>
          </div>
          <Link href="/admin" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300">Back to Admin</Link>
        </header>

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
