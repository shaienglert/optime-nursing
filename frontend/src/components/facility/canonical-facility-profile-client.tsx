"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { FacilityParameterTable, fetchFacilityParameterTable } from "@/lib/api";

type CanonicalFacilityProfileClientProps = {
  canonicalFacilityId: string;
  backHref: string;
  backLabel: string;
};

type RegulatoryHistory = {
  inspection_count?: number | null;
  known_grade_count?: number | null;
  grade_counts?: Record<string, number> | null;
  latest_known_grade?: string | null;
  latest_known_grade_date?: string | null;
  disciplinary_action?: string | null;
  [key: string]: unknown;
};

type RegulatoryResponse = {
  canonical_facility_id: string;
  facility_name?: string | null;
  source?: string | null;
  regulatory_history?: RegulatoryHistory | null;
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "" || value === "UNKNOWN") return "UNKNOWN";
  if (value === true || value === "YES") return "Yes";
  if (value === false || value === "NO") return "No";
  return String(value);
}

function prettyLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isImportantParameter(parameterId: string): boolean {
  return [
    "license_status",
    "licensed_beds_capacity",
    "adl_support",
    "medication_support",
    "transfer_assistance",
    "memory_care",
    "dementia_alz_programs",
    "skilled_nursing_capabilities",
    "nursing_24_7",
    "inspection_rating",
    "penalties_fines",
    "deficiency_count",
    "deficiency_severity",
  ].includes(parameterId);
}

export function CanonicalFacilityProfileClient({ canonicalFacilityId, backHref, backLabel }: CanonicalFacilityProfileClientProps) {
  const [table, setTable] = useState<FacilityParameterTable | null>(null);
  const [regulatory, setRegulatory] = useState<RegulatoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const parameterTable = await fetchFacilityParameterTable(canonicalFacilityId);
        let regulatoryPayload: RegulatoryResponse | null = null;
        try {
          const response = await fetch(`/api/backend/canonical-facilities/${encodeURIComponent(canonicalFacilityId)}/regulatory-history`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
            cache: "no-store",
          });
          if (response.ok) {
            regulatoryPayload = await response.json() as RegulatoryResponse;
          }
        } catch {
          regulatoryPayload = null;
        }

        if (!mounted) return;
        setTable(parameterTable);
        setRegulatory(regulatoryPayload);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Unable to load canonical facility profile.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    if (canonicalFacilityId) void load();
    return () => { mounted = false; };
  }, [canonicalFacilityId]);

  const importantRows = useMemo(
    () => (table?.rows || []).filter((row) => isImportantParameter(row.parameter_id)),
    [table],
  );

  if (isLoading) {
    return <main className="min-h-screen bg-[#fffdf8] px-6 py-12 text-[#5d5548]">Loading verified facility profile...</main>;
  }

  if (error || !table) {
    return (
      <main className="min-h-screen bg-[#fffdf8] px-6 py-12">
        <p className="text-[#8b3d2e]">{error || "Canonical facility not found."}</p>
        <Link href={backHref} className="mt-4 inline-flex rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245]">{backLabel}</Link>
      </main>
    );
  }

  const history = regulatory?.regulatory_history || null;
  const gradeCounts = history?.grade_counts || {};

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_24%,#ffffff_48%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#5f7f6b]">Canonical Facility Intelligence Profile</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#2f2a24]">{table.facility_name}</h1>
              <p className="mt-1 text-[#6d655b]">{[table.city, table.state, table.zip].filter(Boolean).join(", ")}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-full border border-[#cfe2d8] bg-[#f4fbf7] px-3 py-1 text-[#315f53]">{table.canonical_type || "Type UNKNOWN"}</span>
                <span className="rounded-full border border-[#d9cfbf] bg-[#faf7f1] px-3 py-1 text-[#6d655b]">Canonical ID: {table.canonical_facility_id}</span>
              </div>
            </div>
            <Link href={backHref} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">{backLabel}</Link>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border border-[#e8ddcc] bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Verified care & licensing evidence</p>
            <div className="mt-4 divide-y divide-[#eee5d8]">
              {importantRows.length > 0 ? importantRows.map((row) => (
                <div key={row.parameter_id} className="grid gap-1 py-3 sm:grid-cols-[1fr,auto] sm:gap-4">
                  <div>
                    <p className="font-medium text-[#332f29]">{row.parameter || prettyLabel(row.parameter_id)}</p>
                    <p className="mt-1 text-xs text-[#776e62]">Source: {row.source || "UNKNOWN"}{row.last_verified ? ` · Verified: ${row.last_verified}` : ""}</p>
                  </div>
                  <span className="font-semibold text-[#315f53]">{displayValue(row.raw_value ?? row.status_value)}</span>
                </div>
              )) : <p className="py-3 text-sm text-[#776e62]">No verified parameter evidence is currently available.</p>}
            </div>
          </div>

          <div className="rounded-3xl border border-[#e8ddcc] bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Nevada regulatory history</p>
            {history ? (
              <div className="mt-4 space-y-3 text-sm text-[#4f473d]">
                <p><span className="font-semibold">Source:</span> {regulatory?.source || "Nevada HCQC / ALiS"}</p>
                <p><span className="font-semibold">Inspections found:</span> {displayValue(history.inspection_count)}</p>
                <p><span className="font-semibold">Latest known grade:</span> {displayValue(history.latest_known_grade)}{history.latest_known_grade_date ? ` · ${history.latest_known_grade_date}` : ""}</p>
                <p><span className="font-semibold">Disciplinary action:</span> {displayValue(history.disciplinary_action)}</p>
                <div>
                  <p className="font-semibold">Grade history</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {["A", "B", "C", "D"].map((grade) => (
                      <span key={grade} className="rounded-full border border-[#d9cfbf] bg-[#faf7f1] px-3 py-1 text-xs">{grade}: {Number(gradeCounts[grade] || 0)}</span>
                    ))}
                  </div>
                </div>
                <p className="rounded-2xl border border-[#eedfbf] bg-[#fff9ed] p-3 text-xs leading-5 text-[#745e32]">Regulatory history is evidence used to distinguish otherwise similarly matched residential facilities. UNKNOWN is not treated as a failure.</p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-[#776e62]">Detailed ALiS grade history is not available for this facility. UNKNOWN is preserved.</p>
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Evidence ledger</p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[#e8ddcc] text-xs uppercase tracking-[0.08em] text-[#776e62]">
                <tr><th className="px-2 py-2">Parameter</th><th className="px-2 py-2">Value</th><th className="px-2 py-2">Source</th><th className="px-2 py-2">Evidence</th></tr>
              </thead>
              <tbody className="divide-y divide-[#f0e8dc]">
                {table.rows.map((row) => (
                  <tr key={row.parameter_id}>
                    <td className="px-2 py-3 font-medium text-[#332f29]">{row.parameter || prettyLabel(row.parameter_id)}</td>
                    <td className="px-2 py-3 text-[#315f53]">{displayValue(row.raw_value ?? row.status_value)}</td>
                    <td className="px-2 py-3 text-[#6d655b]">{row.source || "UNKNOWN"}</td>
                    <td className="px-2 py-3 text-[#6d655b]">{row.evidence_count} record{row.evidence_count === 1 ? "" : "s"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
