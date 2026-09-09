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
import {
  CompetitiveIntelligenceSignal,
  MarketIntelligenceReport,
  MarketSupplySignal,
  collectOfficialCmsMarketMetrics,
  fetchCompetitiveIntelligenceSignals,
  fetchMarketIntelligenceReport,
  fetchMarketSupplyIntelligenceSignals,
} from "@/lib/admin-intelligence";

const ADMIN_TOKEN_SESSION_KEY = "optime.admin.token";

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
  const [adminToken, setAdminToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [competitiveSignals, setCompetitiveSignals] = useState<CompetitiveIntelligenceSignal[]>([]);
  const [marketSignals, setMarketSignals] = useState<MarketSupplySignal[]>([]);
  const [marketReport, setMarketReport] = useState<MarketIntelligenceReport | null>(null);
  const [intelligenceError, setIntelligenceError] = useState<string | null>(null);
  const [isLoadingIntelligence, setIsLoadingIntelligence] = useState(false);
  const [isCollectingOfficialMetrics, setIsCollectingOfficialMetrics] = useState(false);

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

  useEffect(() => {
    Promise.resolve().then(() => {
      try {
        const saved = window.sessionStorage.getItem(ADMIN_TOKEN_SESSION_KEY);
        if (saved) {
          setAdminToken(saved);
          setTokenInput(saved);
        }
      } catch {
        // The token can still be entered for this session if storage is unavailable.
      }
    });
  }, []);

  useEffect(() => {
    if (!adminToken) return;
    let active = true;
    setIsLoadingIntelligence(true);
    setIntelligenceError(null);
    Promise.all([
      fetchCompetitiveIntelligenceSignals(adminToken),
      fetchMarketSupplyIntelligenceSignals(adminToken),
      fetchMarketIntelligenceReport(adminToken).catch(() => null),
    ])
      .then(([competitors, market, report]) => {
        if (!active) return;
        setCompetitiveSignals(competitors);
        setMarketSignals(market);
        setMarketReport(report);
      })
      .catch((err) => {
        if (active) setIntelligenceError(err instanceof Error ? err.message : "Failed to load intelligence signals.");
      })
      .finally(() => {
        if (active) setIsLoadingIntelligence(false);
      });
    return () => {
      active = false;
    };
  }, [adminToken]);

  function handleUnlockIntelligence() {
    const trimmed = tokenInput.trim();
    if (!trimmed) return;
    try {
      window.sessionStorage.setItem(ADMIN_TOKEN_SESSION_KEY, trimmed);
    } catch {
      // Use the token in memory if session storage is unavailable.
    }
    setAdminToken(trimmed);
  }

  async function handleCollectOfficialMetrics() {
    if (!adminToken) return;
    setIsCollectingOfficialMetrics(true);
    setIntelligenceError(null);
    try {
      await collectOfficialCmsMarketMetrics(adminToken);
      setMarketReport(await fetchMarketIntelligenceReport(adminToken));
    } catch (err) {
      setIntelligenceError(err instanceof Error ? err.message : "Official market collection failed.");
    } finally {
      setIsCollectingOfficialMetrics(false);
    }
  }

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
  const competitorGroups = competitiveSignals.reduce<Record<string, CompetitiveIntelligenceSignal[]>>((groups, signal) => {
    (groups[signal.competitor_name] ||= []).push(signal);
    return groups;
  }, {});

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
            <Link href="/admin/platform-operations" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">
              Platform Operations
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

            <section className="rounded-3xl border border-cyan-500/25 bg-slate-900/80 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Live Intelligence Agent</p>
                  <h2 className="mt-2 text-2xl font-semibold">Competitors and Market Supply</h2>
                  <p className="mt-2 max-w-3xl text-sm text-slate-300">
                    Direct observations collected by the agent. Competitor signals are public-page observations; market items link to the original source and are not facility availability claims.
                  </p>
                </div>
                <div className="flex gap-3 text-sm">
                  <span className="rounded-full border border-cyan-500/30 px-3 py-1.5 text-cyan-200">{competitiveSignals.length} competitor signals</span>
                  <span className="rounded-full border border-cyan-500/30 px-3 py-1.5 text-cyan-200">{marketSignals.length} market items</span>
                </div>
              </div>

              {!adminToken ? (
                <div className="mt-5 rounded-2xl border border-slate-700 bg-slate-950 p-4">
                  <p className="text-sm text-slate-300">Enter the existing Admin token once to unlock the live agent report in this browser session.</p>
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                    <input
                      type="password"
                      value={tokenInput}
                      onChange={(event) => setTokenInput(event.target.value)}
                      onKeyDown={(event) => event.key === "Enter" && handleUnlockIntelligence()}
                      placeholder="Admin token"
                      className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100"
                    />
                    <button type="button" onClick={handleUnlockIntelligence} className="rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300">
                      Show live report
                    </button>
                  </div>
                </div>
              ) : null}

              {isLoadingIntelligence ? <p className="mt-5 text-sm text-slate-400">Loading live agent output...</p> : null}
              {intelligenceError ? <p className="mt-5 rounded-2xl border border-rose-500/40 bg-rose-950/30 p-4 text-sm text-rose-200">{intelligenceError}</p> : null}

              {adminToken && !isLoadingIntelligence && !intelligenceError ? (
                <>
                  <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-medium">Nevada and U.S. market scorecard</h3>
                        <p className="mt-1 text-sm text-slate-400">Each number keeps its geography, source and scope. Missing means no source-backed observation exists — never zero or estimated.</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <button type="button" onClick={handleCollectOfficialMetrics} disabled={isCollectingOfficialMetrics} className="rounded-xl border border-cyan-400/60 px-3 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-400/10 disabled:cursor-wait disabled:opacity-60">
                          {isCollectingOfficialMetrics ? "Collecting official CMS data…" : "Refresh official CMS data"}
                        </button>
                        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">Not used in recommendation ranking</span>
                      </div>
                    </div>
                    <div className="mt-4 overflow-x-auto">
                      <table className="min-w-full text-left text-sm">
                        <thead className="border-b border-slate-800 text-slate-400">
                          <tr>
                            <th className="px-3 py-2">Metric</th>
                            <th className="px-3 py-2">Status</th>
                            <th className="px-3 py-2">Collected observations</th>
                            <th className="px-3 py-2">Source / scope</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(marketReport?.metrics || []).map((metric) => (
                            <tr key={metric.metric_key} className="border-b border-slate-900 align-top">
                              <td className="px-3 py-3 font-medium text-slate-100"><p>{metric.label}</p><p className="mt-1 text-xs text-slate-500">{metric.scope}</p></td>
                              <td className="px-3 py-3"><span className={metric.status === "AVAILABLE" ? "text-emerald-300" : "text-amber-300"}>{metric.status}</span></td>
                              <td className="px-3 py-3 text-slate-300">
                                {metric.observations.length > 0 ? metric.observations.map((observation) => <p key={`${observation.segment}-${observation.value}`}><span className="text-slate-500">{observation.segment}:</span> {observation.value} {metric.unit} <span className="text-xs text-slate-500">({observation.observed_period})</span></p>) : <span className="text-amber-200">{metric.reason || "No sourced observation collected."}</span>}
                              </td>
                              <td className="px-3 py-3 text-slate-400">
                                {metric.observations.map((observation) => <p key={`${observation.source_name}-${observation.segment}`}><a className="text-cyan-300 underline hover:text-cyan-200" href={observation.source_url} target="_blank" rel="noreferrer">{observation.source_name}</a><span className="ml-1 text-xs">· {observation.evidence_status}</span></p>)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {!marketReport ? <p className="p-4 text-sm text-amber-200">The market-report endpoint has not been deployed yet.</p> : null}
                    </div>
                  </div>

                  <div className="mt-5 grid gap-5 xl:grid-cols-2">
                    <div className="space-y-3">
                      <h3 className="text-lg font-medium">Competitor observations</h3>
                      {Object.entries(competitorGroups).map(([competitor, signals]) => (
                        <article key={competitor} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                          <h4 className="font-medium text-slate-100">{competitor}</h4>
                          <ul className="mt-3 space-y-2 text-sm text-slate-300">
                            {signals.map((signal) => (
                              <li key={`${signal.competitor_key}-${signal.signal_type}`}>
                                <span className="mr-2 text-xs uppercase tracking-wide text-cyan-300">{signal.signal_type.replaceAll("_", " ")}</span>
                                {signal.detail_text}
                              </li>
                            ))}
                          </ul>
                        </article>
                      ))}
                      {competitiveSignals.length === 0 ? <p className="text-sm text-slate-400">No competitor signals have been stored yet.</p> : null}
                    </div>
                    <div>
                      <h3 className="text-lg font-medium">Senior-living supply signals</h3>
                      <div className="mt-3 max-h-[38rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950">
                        <table className="min-w-full text-left text-sm">
                          <thead className="sticky top-0 bg-slate-900 text-slate-400">
                            <tr>
                              <th className="px-3 py-3">Type</th>
                              <th className="px-3 py-3">Place</th>
                              <th className="px-3 py-3">Source</th>
                            </tr>
                          </thead>
                          <tbody>
                            {marketSignals.map((signal) => (
                              <tr key={signal.source_url} className="border-t border-slate-900 align-top">
                                <td className="px-3 py-3 text-xs text-cyan-300">{signal.category.replaceAll("_", " ")}</td>
                                <td className="px-3 py-3">
                                  <p className="font-medium text-slate-100">{signal.headline}</p>
                                  <p className="mt-1 text-slate-400">{signal.city_state || "Location not verified in article"}</p>
                                  <p className="mt-1 text-slate-300">{signal.snippet}</p>
                                </td>
                                <td className="px-3 py-3"><a className="text-cyan-300 underline hover:text-cyan-200" href={signal.source_url} target="_blank" rel="noreferrer">{signal.source_domain}</a></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {marketSignals.length === 0 ? <p className="p-4 text-sm text-slate-400">No market-supply signals have been stored yet.</p> : null}
                      </div>
                    </div>
                  </div>
                </>
              ) : null}
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
