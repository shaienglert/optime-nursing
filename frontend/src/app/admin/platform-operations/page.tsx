"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AgentKnowledgeReportSummary,
  RuntimeStatus,
  SupervisorIncident,
  SupervisorOverview,
  fetchKnowledgeReports,
  fetchRuntimeStatus,
  fetchSupervisorIncidents,
  fetchSupervisorOverview,
} from "@/lib/api";

function fmt(value: string | null | undefined): string {
  if (!value) return "UNKNOWN";
  return value;
}

type PanelState<T> = {
  loading: boolean;
  error: string | null;
  data: T;
};

function asErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export default function PlatformOperationsAdminPage() {
  const [runtimePanel, setRuntimePanel] = useState<PanelState<RuntimeStatus | null>>({
    loading: true,
    error: null,
    data: null,
  });
  const [overviewPanel, setOverviewPanel] = useState<PanelState<SupervisorOverview | null>>({
    loading: true,
    error: null,
    data: null,
  });
  const [incidentsPanel, setIncidentsPanel] = useState<PanelState<SupervisorIncident[]>>({
    loading: true,
    error: null,
    data: [],
  });
  const [reportsPanel, setReportsPanel] = useState<PanelState<AgentKnowledgeReportSummary[]>>({
    loading: true,
    error: null,
    data: [],
  });

  async function loadRuntimePanel(): Promise<void> {
    setRuntimePanel((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const runtimeStatus = await fetchRuntimeStatus();
      setRuntimePanel({ loading: false, error: null, data: runtimeStatus });
    } catch (err) {
      setRuntimePanel((prev) => ({
        loading: false,
        error: asErrorMessage(err, "Failed to load runtime status."),
        data: prev.data,
      }));
    }
  }

  async function loadOverviewPanel(): Promise<void> {
    setOverviewPanel((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const supervisorOverview = await fetchSupervisorOverview();
      setOverviewPanel({ loading: false, error: null, data: supervisorOverview });
    } catch (err) {
      setOverviewPanel((prev) => ({
        loading: false,
        error: asErrorMessage(err, "Failed to load supervisor overview."),
        data: prev.data,
      }));
    }
  }

  async function loadIncidentsPanel(): Promise<void> {
    setIncidentsPanel((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const incidentRows = await fetchSupervisorIncidents(50);
      setIncidentsPanel({ loading: false, error: null, data: incidentRows.incidents || [] });
    } catch (err) {
      setIncidentsPanel((prev) => ({
        loading: false,
        error: asErrorMessage(err, "Failed to load incidents."),
        data: prev.data,
      }));
    }
  }

  async function loadReportsPanel(): Promise<void> {
    setReportsPanel((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const knowledgeRows = await fetchKnowledgeReports();
      setReportsPanel({ loading: false, error: null, data: knowledgeRows || [] });
    } catch (err) {
      setReportsPanel((prev) => ({
        loading: false,
        error: asErrorMessage(err, "Failed to load knowledge reports."),
        data: prev.data,
      }));
    }
  }

  useEffect(() => {
    let active = true;
    async function run() {
      if (!active) return;
      await Promise.allSettled([
        loadRuntimePanel(),
        loadOverviewPanel(),
        loadIncidentsPanel(),
        loadReportsPanel(),
      ]);
    }
    void run();
    return () => {
      active = false;
    };
  }, []);

  const runtime = runtimePanel.data;
  const overview = overviewPanel.data;
  const incidents = incidentsPanel.data;
  const reports = reportsPanel.data;

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
          </div>
        </div>

        <div className="rounded-3xl border border-amber-500/40 bg-amber-950/20 p-5 text-amber-100">
          <p className="text-sm font-semibold">Read-only mode</p>
          <p className="mt-1 text-sm">
            Refresh mutation is hidden because canonical admin authorization for `/admin`, `/admin/platform-operations`, and POST `/expert-agents/knowledge-reports/refresh` is not enforced in the current application layer.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Runtime Dirty</p>
                {runtimePanel.loading ? <p className="mt-3 text-sm text-slate-400">Loading runtime...</p> : null}
                {runtimePanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: {runtimePanel.error}</p> : null}
                {!runtimePanel.loading && !runtimePanel.error ? <p className="mt-3 text-3xl font-semibold">{runtime?.dirty ? "YES" : "NO"}</p> : null}
                <p className="mt-1 text-xs text-slate-400">Last check: {fmt(runtime?.last_check_at)}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Fresh Agents</p>
                {overviewPanel.loading ? <p className="mt-3 text-sm text-slate-400">Loading supervisor...</p> : null}
                {overviewPanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: {overviewPanel.error}</p> : null}
                {!overviewPanel.loading && !overviewPanel.error ? <p className="mt-3 text-3xl font-semibold">{overview?.fresh_agents ?? "--"}</p> : null}
                <p className="mt-1 text-xs text-slate-400">Stale: {overview?.stale_agents ?? "--"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Failed Refreshes</p>
                {!overviewPanel.loading && !overviewPanel.error ? <p className="mt-3 text-3xl font-semibold">{overview?.failed_refreshes ?? "--"}</p> : null}
                <p className="mt-1 text-xs text-slate-400">Queue: {overview?.refresh_queue ?? "--"}</p>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Knowledge Snapshots</p>
                {reportsPanel.loading ? <p className="mt-3 text-sm text-slate-400">Loading knowledge...</p> : null}
                {reportsPanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: {reportsPanel.error}</p> : null}
                {!reportsPanel.loading && !reportsPanel.error ? <p className="mt-3 text-3xl font-semibold">{reports.length}</p> : null}
                <p className="mt-1 text-xs text-slate-400">Pending reviews: {overview?.pending_reviews ?? "--"}</p>
              </div>
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Supervisor Alerts</p>
              {overviewPanel.loading ? <p className="mt-3 text-sm text-slate-400">Loading alerts...</p> : null}
              {overviewPanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: Supervisor alerts unavailable.</p> : null}
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {(overview?.alerts || []).length > 0
                  ? (overview?.alerts || []).map((alert, idx) => <li key={`${alert}-${idx}`}>- {alert}</li>)
                  : <li>No active alerts.</li>}
              </ul>
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Knowledge Report Visibility</p>
              {reportsPanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: {reportsPanel.error}</p> : null}
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
                    {reportsPanel.loading ? (
                      <tr>
                        <td className="px-3 py-3 text-slate-300" colSpan={6}>Loading knowledge reports...</td>
                      </tr>
                    ) : reports.map((row) => (
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
              {incidentsPanel.error ? <p className="mt-3 text-sm text-rose-300">DEGRADED: {incidentsPanel.error}</p> : null}
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
                    {incidentsPanel.loading ? (
                      <tr>
                        <td className="px-3 py-3 text-slate-300" colSpan={5}>Loading incidents...</td>
                      </tr>
                    ) : incidents.length > 0 ? incidents.map((row) => (
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
      </section>
    </main>
  );
}
