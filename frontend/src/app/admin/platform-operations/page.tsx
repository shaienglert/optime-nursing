"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AgentKnowledgeRefreshResult,
  AgentKnowledgeReportSummary,
  RuntimeStatus,
  SupervisorIncident,
  SupervisorOverview,
  fetchKnowledgeReports,
  fetchRuntimeStatus,
  fetchSupervisorIncidents,
  fetchSupervisorOverview,
  refreshKnowledgeReports,
} from "@/lib/api";

function fmt(value: string | null | undefined): string {
  if (!value) return "UNKNOWN";
  return value;
}

export default function PlatformOperationsAdminPage() {
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [overview, setOverview] = useState<SupervisorOverview | null>(null);
  const [incidents, setIncidents] = useState<SupervisorIncident[]>([]);
  const [reports, setReports] = useState<AgentKnowledgeReportSummary[]>([]);
  const [refreshResult, setRefreshResult] = useState<AgentKnowledgeRefreshResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadAll(): Promise<void> {
    setError(null);
    const [runtimeStatus, supervisorOverview, incidentRows, knowledgeRows] = await Promise.all([
      fetchRuntimeStatus(),
      fetchSupervisorOverview(),
      fetchSupervisorIncidents(50),
      fetchKnowledgeReports(),
    ]);
    setRuntime(runtimeStatus);
    setOverview(supervisorOverview);
    setIncidents(incidentRows.incidents || []);
    setReports(knowledgeRows || []);
  }

  useEffect(() => {
    let active = true;
    async function run() {
      setIsLoading(true);
      try {
        await loadAll();
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load platform operations data.");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void run();
    return () => {
      active = false;
    };
  }, []);

  async function handleRefreshKnowledge(): Promise<void> {
    setIsRefreshing(true);
    setError(null);
    try {
      const result = await refreshKnowledgeReports();
      setRefreshResult(result);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh knowledge reports.");
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-300">Admin</p>
            <h1 className="mt-2 text-3xl font-semibold">Platform Operations</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">
              Existing production surfaces for runtime health, supervisor status, incidents, and knowledge snapshot visibility.
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/admin/executive-intelligence" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">
              Executive Intelligence
            </Link>
            <button
              type="button"
              onClick={() => void handleRefreshKnowledge()}
              disabled={isRefreshing}
              className="rounded-full bg-emerald-400 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-300 disabled:opacity-60"
            >
              {isRefreshing ? "Refreshing..." : "Refresh Knowledge Reports"}
            </button>
          </div>
        </div>

        {isLoading ? <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">Loading platform operations...</div> : null}
        {error ? <div className="rounded-3xl border border-rose-500/40 bg-rose-950/30 p-6 text-rose-200">{error}</div> : null}

        {!isLoading && !error ? (
          <>
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Runtime Dirty</p>
                <p className="mt-3 text-3xl font-semibold">{runtime?.dirty ? "YES" : "NO"}</p>
                <p className="mt-1 text-xs text-slate-400">Last check: {fmt(runtime?.last_check_at)}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Fresh Agents</p>
                <p className="mt-3 text-3xl font-semibold">{overview?.fresh_agents ?? "--"}</p>
                <p className="mt-1 text-xs text-slate-400">Stale: {overview?.stale_agents ?? "--"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Failed Refreshes</p>
                <p className="mt-3 text-3xl font-semibold">{overview?.failed_refreshes ?? "--"}</p>
                <p className="mt-1 text-xs text-slate-400">Queue: {overview?.refresh_queue ?? "--"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Knowledge Snapshots</p>
                <p className="mt-3 text-3xl font-semibold">{reports.length}</p>
                <p className="mt-1 text-xs text-slate-400">Pending reviews: {overview?.pending_reviews ?? "--"}</p>
              </div>
            </section>

            {refreshResult ? (
              <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Latest Refresh Result</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-4 text-sm text-slate-200">
                  <p>Attempted: {refreshResult.attempted}</p>
                  <p>Refreshed: {refreshResult.refreshed}</p>
                  <p>Failures: {refreshResult.failures}</p>
                  <p>Skipped: {refreshResult.skipped}</p>
                </div>
              </section>
            ) : null}

            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Supervisor Alerts</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {(overview?.alerts || []).length > 0
                  ? (overview?.alerts || []).map((alert, idx) => <li key={`${alert}-${idx}`}>- {alert}</li>)
                  : <li>No active alerts.</li>}
              </ul>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Knowledge Report Visibility</p>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="px-3 py-2">Agent</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Freshness</th>
                      <th className="px-3 py-2">Confidence</th>
                      <th className="px-3 py-2">Evidence</th>
                      <th className="px-3 py-2">Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((row) => (
                      <tr key={row.agent_key} className="border-b border-slate-900">
                        <td className="px-3 py-3 text-slate-100">{row.agent_name}</td>
                        <td className="px-3 py-3 text-slate-300">{row.health_status}</td>
                        <td className="px-3 py-3 text-slate-300">{row.freshness_status}</td>
                        <td className="px-3 py-3 text-slate-300">{row.confidence.toFixed(2)}</td>
                        <td className="px-3 py-3 text-slate-300">{row.evidence_count}</td>
                        <td className="px-3 py-3 text-slate-400">{fmt(row.last_update)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Recent Incidents</p>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Severity</th>
                      <th className="px-3 py-2">Agent</th>
                      <th className="px-3 py-2">Summary</th>
                      <th className="px-3 py-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.length > 0 ? incidents.map((row) => (
                      <tr key={row.id} className="border-b border-slate-900">
                        <td className="px-3 py-3 text-slate-200">{row.incident_type}</td>
                        <td className="px-3 py-3 text-slate-200">{row.severity}</td>
                        <td className="px-3 py-3 text-slate-300">{row.agent_key || "-"}</td>
                        <td className="px-3 py-3 text-slate-300">{row.summary}</td>
                        <td className="px-3 py-3 text-slate-400">{fmt(row.created_at)}</td>
                      </tr>
                    )) : (
                      <tr>
                        <td className="px-3 py-3 text-slate-300" colSpan={5}>No incidents found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </section>
    </main>
  );
}
