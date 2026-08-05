"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ExecutiveReportPayload,
  ExecutiveReportRecord,
  fetchExecutiveReportById,
  fetchExecutiveReportHistory,
  fetchExecutiveReportLatestFull,
} from "@/lib/api";

type AgentRow = {
  agent_id: string;
  name: string;
  current_status: string;
  worked: string;
  what_it_did: string;
  new_value_created: string;
  evidence: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asRows(value: unknown): AgentRow[] {
  return Array.isArray(value) ? (value as AgentRow[]) : [];
}

export default function ExecutiveIntelligenceAdminPage() {
  const [history, setHistory] = useState<ExecutiveReportRecord[]>([]);
  const [payload, setPayload] = useState<ExecutiveReportPayload | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [latest, historyResponse] = await Promise.all([
          fetchExecutiveReportLatestFull(),
          fetchExecutiveReportHistory(30),
        ]);
        if (!active) return;
        setPayload(latest);
        setHistory(historyResponse.reports || []);
        setSelectedReportId(latest.record.report_id);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load executive intelligence.");
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  async function handleSelect(reportId: string) {
    setSelectedReportId(reportId);
    setIsLoadingReport(true);
    setError(null);
    try {
      const next = await fetchExecutiveReportById(reportId);
      setPayload(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load selected report.");
    } finally {
      setIsLoadingReport(false);
    }
  }

  const report = asRecord(payload?.report);
  const controlTower = asRecord(report.agent_control_tower);
  const summary = asRecord(controlTower.summary);
  const achievements = asRecord(controlTower.achievements);
  const authority = asRecord(report.authority_status);
  const authorityStages = asRecord(authority.stages);
  const organic = asRecord(report.organic_ai_authority);
  const attention = Array.isArray(controlTower.attention) ? (controlTower.attention as Array<Record<string, unknown>>) : [];
  const agents = asRows(controlTower.rows);
  const summaryCards: Array<{ label: string; value: string | number }> = [
    { label: "Total Known Agents", value: String(summary.total_known_agents ?? "UNKNOWN") },
    { label: "Automatic Agents", value: String(summary.automatic_agents ?? "UNKNOWN") },
    { label: "Actually Worked", value: String(summary.actually_worked_last_24h ?? "UNKNOWN") },
    { label: "Ran, No New Value", value: String(summary.ran_no_new_value_last_24h ?? "UNKNOWN") },
    { label: "Failed", value: String(summary.failed_last_24h ?? "UNKNOWN") },
    { label: "Unknown", value: String(summary.unknown_status ?? "UNKNOWN") },
  ];
  const topPriorities = Array.isArray(asRecord(report.tomorrow).top_five_priorities)
    ? (asRecord(report.tomorrow).top_five_priorities as string[])
    : [];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-300">Admin</p>
            <h1 className="mt-2 text-3xl font-semibold">OPTIME Daily Executive Intelligence</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">
              One control-tower view for agent activity, authority progress, daily deltas, and issues requiring attention.
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/admin/parameter-acquisition" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">
              Parameter acquisition
            </Link>
            <Link href="/" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">
              Home
            </Link>
            <Link href="/facilities" className="rounded-full bg-emerald-400 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-300">
              Facilities
            </Link>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-400">System Status</p>
            <h2 className="mt-3 text-2xl font-semibold">{String(authority.overall_status || "UNKNOWN")}</h2>
            <p className="mt-3 text-sm text-slate-300">{String(authority.answer || "No executive authority assessment available.")}</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Date</p>
                <p className="mt-2 text-lg font-medium">{payload?.record.report_date || "UNKNOWN"}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Generated</p>
                <p className="mt-2 text-lg font-medium">{payload?.record.generated_at_utc || "UNKNOWN"}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Organic / AI</p>
                <p className="mt-2 text-lg font-medium">{String(organic.current_status || "UNKNOWN")}</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
            <label htmlFor="report-history" className="text-xs uppercase tracking-[0.25em] text-slate-400">
              Daily Report History
            </label>
            <select
              id="report-history"
              value={selectedReportId}
              onChange={(event) => void handleSelect(event.target.value)}
              className="mt-3 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100"
            >
              {history.map((row) => (
                <option key={row.report_id} value={row.report_id}>
                  {row.report_date} | {row.report_id}
                </option>
              ))}
            </select>
            <div className="mt-4 space-y-2 text-sm text-slate-300">
              <p>Canonical latest report: {payload?.record.json_path || "UNKNOWN"}</p>
              <p>Email sent: {String(payload?.record.sent ?? "UNKNOWN")}</p>
              <p>Loading selected report: {isLoadingReport ? "YES" : "NO"}</p>
            </div>
          </div>
        </div>

        {isLoading ? <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">Loading executive intelligence...</div> : null}
        {error ? <div className="rounded-3xl border border-rose-500/40 bg-rose-950/30 p-6 text-rose-200">{error}</div> : null}

        {!isLoading && !error ? (
          <>
            <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
              {summaryCards.map((card) => (
                <div key={card.label} className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{card.label}</p>
                  <p className="mt-3 text-3xl font-semibold">{card.value}</p>
                </div>
              ))}
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">What OPTIME Achieved In Last 24 Hours</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Object.entries(achievements).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{key.replaceAll("_", " ")}</p>
                    <p className="mt-2 text-lg font-medium">{String(value)}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Agent Activity</p>
                  <h2 className="mt-2 text-2xl font-semibold">Last 24 Hours</h2>
                </div>
                <p className="text-sm text-slate-400">Every known agent appears, including manual-only and unknown surfaces.</p>
              </div>
              <div className="mt-5 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="px-3 py-2">Agent</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Worked?</th>
                      <th className="px-3 py-2">What it did</th>
                      <th className="px-3 py-2">New achievement</th>
                      <th className="px-3 py-2">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((row) => (
                      <tr key={row.agent_id} className="border-b border-slate-900 align-top">
                        <td className="px-3 py-3 font-medium text-slate-100">{row.name}</td>
                        <td className="px-3 py-3 text-slate-300">{row.current_status}</td>
                        <td className="px-3 py-3 text-slate-300">{row.worked}</td>
                        <td className="px-3 py-3 text-slate-300">{row.what_it_did}</td>
                        <td className="px-3 py-3 text-slate-300">{row.new_value_created}</td>
                        <td className="px-3 py-3 text-slate-400">{row.evidence.join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Authority Progress</p>
                <div className="mt-4 space-y-3">
                  {Object.entries(authorityStages).map(([stage, raw]) => {
                    const value = asRecord(raw);
                    return (
                      <div key={stage} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="text-lg font-medium">{stage}</h3>
                          <span className="text-sm text-emerald-300">{String(value.status || "UNKNOWN")}</span>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">Last verified: {String(value.last_verified_utc || "UNKNOWN")}</p>
                        <p className="mt-3 text-sm text-slate-300">Next action: {String(value.next_action || "UNKNOWN")}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Agents Requiring Attention</p>
                <div className="mt-4 space-y-3">
                  {attention.length > 0 ? attention.map((item, index) => (
                    <div key={`${String(item.agent)}-${index}`} className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
                      <p className="font-medium text-amber-100">{String(item.agent)}</p>
                      <p className="mt-1 text-sm text-amber-200">Why: {String(item.why)}</p>
                      <p className="mt-1 text-sm text-amber-200">Impact: {String(item.impact)}</p>
                      <p className="mt-1 text-sm text-amber-200">Next action: {String(item.next_action)}</p>
                    </div>
                  )) : <p className="text-sm text-slate-300">No attention items recorded.</p>}
                </div>

                <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Top 5 Priorities Today</p>
                  <ol className="mt-3 space-y-2 text-sm text-slate-200">
                    {topPriorities.map((item, index) => (
                      <li key={`${item}-${index}`}>{index + 1}. {item}</li>
                    ))}
                  </ol>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}