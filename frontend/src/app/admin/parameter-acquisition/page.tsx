"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import auditDataJson from "@/data/parameter-acquisition-audit.json";
import { fetchFacilityParameterTable, type FacilityParameterTable, type ParameterTableRow } from "@/lib/api";

type AuditRecord = {
  "Parameter ID": string;
  "Display name": string;
  Category: string;
  "Primary acquisition class": string;
  "Preferred source": string;
  "Source authority": string;
  "Refresh frequency": string;
  "Operational owner": string;
  "Recommended ACTION when missing": string;
  "Current implementation status": string;
  "Current OPTIME coverage": string;
  Criticality: string;
  "Used in ranking": string;
  "Used in eligibility": string;
};

type GoldenFacility = {
  canonical_facility_id: string;
  facility_name: string;
};

type AuditData = {
  generated_at_utc: string;
  parameter_count: number;
  records: AuditRecord[];
  golden_facilities: GoldenFacility[];
};

type FilterKey = "ALL" | "AUTOMATIC" | "FACILITY_REQUEST" | "MANUAL_RESEARCH" | "HUMAN_REVIEW" | "NO_RELIABLE_SOURCE";

const auditData = auditDataJson as AuditData;

function evidenceStatus(row?: ParameterTableRow) {
  if (!row || row.raw_value === "UNKNOWN" || row.raw_value === null || row.raw_value === undefined) return "UNKNOWN";
  return row.evidence_count > 0 ? "EVIDENCED" : "UNVERIFIED";
}

function displayValue(row?: ParameterTableRow) {
  if (!row) return "Not loaded";
  if (row.raw_value === "UNKNOWN" || row.raw_value === null || row.raw_value === undefined) return "UNKNOWN";
  return String(row.status_value);
}

export default function ParameterAcquisitionAdminPage() {
  const [facilityId, setFacilityId] = useState(auditData.golden_facilities[0]?.canonical_facility_id || "");
  const [parameterTable, setParameterTable] = useState<FacilityParameterTable | null>(null);
  const [filter, setFilter] = useState<FilterKey>("ALL");
  const [highPriorityOnly, setHighPriorityOnly] = useState(false);
  const [rankingOnly, setRankingOnly] = useState(false);
  const [eligibilityOnly, setEligibilityOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchFacilityParameterTable(facilityId)
      .then((payload) => {
        if (active) setParameterTable(payload);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setParameterTable(null);
        setError(reason instanceof Error ? reason.message : "Unable to load facility parameter values.");
      });
    return () => {
      active = false;
    };
  }, [facilityId]);

  const valuesById = useMemo(
    () => new Map((parameterTable?.rows || []).map((row) => [row.parameter_id, row])),
    [parameterTable],
  );

  const visibleRecords = useMemo(() => auditData.records.filter((record) => {
    const acquisitionClass = record["Primary acquisition class"];
    if (filter === "AUTOMATIC" && !acquisitionClass.endsWith("_AUTOMATIC")) return false;
    if (filter === "FACILITY_REQUEST" && acquisitionClass !== "DIRECT_FACILITY_REQUEST") return false;
    if (filter === "MANUAL_RESEARCH" && acquisitionClass !== "MANUAL_RESEARCH") return false;
    if (filter === "HUMAN_REVIEW" && acquisitionClass !== "HUMAN_VERIFICATION") return false;
    if (filter === "NO_RELIABLE_SOURCE" && acquisitionClass !== "NOT_RELIABLY_AVAILABLE") return false;
    if (highPriorityOnly && !["CRITICAL", "HIGH"].includes(record.Criticality)) return false;
    if (rankingOnly && record["Used in ranking"] !== "YES") return false;
    if (eligibilityOnly && record["Used in eligibility"] !== "YES") return false;
    return true;
  }), [eligibilityOnly, filter, highPriorityOnly, rankingOnly]);

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-8 text-slate-100 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-[1800px] space-y-5">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Admin / Data Operations</p>
            <h1 className="mt-2 text-3xl font-semibold">Canonical Parameter Acquisition</h1>
            <p className="mt-2 text-sm text-slate-300">
              {auditData.parameter_count} canonical parameters. Acquisition audit generated {auditData.generated_at_utc}.
            </p>
          </div>
          <Link href="/admin/executive-intelligence" className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:border-slate-500">
            Executive intelligence
          </Link>
        </header>

        <section className="border border-slate-800 bg-slate-900 p-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(280px,1fr)_2fr]">
            <label className="text-sm text-slate-300">
              Golden facility values
              <select
                value={facilityId}
                onChange={(event) => {
                  setError(null);
                  setParameterTable(null);
                  setFacilityId(event.target.value);
                }}
                className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
              >
                {auditData.golden_facilities.map((facility) => (
                  <option key={facility.canonical_facility_id} value={facility.canonical_facility_id}>
                    {facility.facility_name} ({facility.canonical_facility_id})
                  </option>
                ))}
              </select>
            </label>

            <div>
              <p className="text-sm text-slate-300">Acquisition filter</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {([
                  ["ALL", "All"], ["AUTOMATIC", "Automatic"], ["FACILITY_REQUEST", "Facility request"],
                  ["MANUAL_RESEARCH", "Manual research"], ["HUMAN_REVIEW", "Human review"],
                  ["NO_RELIABLE_SOURCE", "No reliable source"],
                ] as Array<[FilterKey, string]>).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFilter(key)}
                    className={`rounded-md border px-3 py-2 text-sm ${filter === key ? "border-emerald-300 bg-emerald-300 text-slate-950" : "border-slate-700 bg-slate-950 text-slate-200"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-5 text-sm text-slate-300">
                <label className="flex items-center gap-2"><input type="checkbox" checked={highPriorityOnly} onChange={(event) => setHighPriorityOnly(event.target.checked)} />High priority</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={rankingOnly} onChange={(event) => setRankingOnly(event.target.checked)} />Used in ranking</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={eligibilityOnly} onChange={(event) => setEligibilityOnly(event.target.checked)} />Used in eligibility</label>
              </div>
            </div>
          </div>
          {error ? <p className="mt-3 text-sm text-amber-300">Live values unavailable: {error}. Acquisition metadata remains available.</p> : null}
        </section>

        <section className="overflow-x-auto border border-slate-800 bg-slate-900">
          <table className="min-w-[1900px] text-left text-xs">
            <thead className="sticky top-0 bg-slate-900 text-slate-400">
              <tr className="border-b border-slate-700">
                <th className="px-3 py-3">Parameter</th>
                <th className="px-3 py-3">Current value</th>
                <th className="px-3 py-3">Evidence status</th>
                <th className="px-3 py-3">Primary source</th>
                <th className="px-3 py-3">Acquisition method</th>
                <th className="px-3 py-3">Last updated</th>
                <th className="px-3 py-3">Refresh rule</th>
                <th className="px-3 py-3">Owner</th>
                <th className="px-3 py-3">Action</th>
                <th className="px-3 py-3">Missing-data workflow</th>
              </tr>
            </thead>
            <tbody>
              {visibleRecords.map((record) => {
                const value = valuesById.get(record["Parameter ID"]);
                return (
                  <tr key={record["Parameter ID"]} className="border-b border-slate-800 align-top">
                    <td className="px-3 py-3">
                      <p className="font-semibold text-slate-100">{record["Display name"]}</p>
                      <p className="mt-1 text-slate-500">{record["Parameter ID"]}</p>
                      <p className="mt-1 text-slate-500">{record.Category}</p>
                    </td>
                    <td className="px-3 py-3 text-slate-200">{displayValue(value)}</td>
                    <td className="px-3 py-3 text-slate-300">{evidenceStatus(value)} ({value?.evidence_count || 0})</td>
                    <td className="px-3 py-3 text-slate-300">{value?.source || record["Preferred source"]}<p className="mt-1 text-slate-500">Authority {record["Source authority"]}</p></td>
                    <td className="px-3 py-3 text-slate-300">{record["Primary acquisition class"]}</td>
                    <td className="px-3 py-3 text-slate-300">{value?.last_verified || "Not verified"}</td>
                    <td className="px-3 py-3 text-slate-300">{record["Refresh frequency"]}</td>
                    <td className="px-3 py-3 text-slate-300">{record["Operational owner"]}</td>
                    <td className="px-3 py-3 text-slate-300">{record["Current implementation status"]}<p className="mt-1 text-slate-500">{record["Current OPTIME coverage"]}</p></td>
                    <td className="px-3 py-3 text-slate-300">{record["Recommended ACTION when missing"]}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
        <p className="text-sm text-slate-400">Showing {visibleRecords.length} of {auditData.parameter_count} canonical parameters.</p>
      </section>
    </main>
  );
}