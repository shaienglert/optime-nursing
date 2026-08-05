"use client";

import { useMemo, useState } from "react";

import type { FacilityParameterTable } from "@/lib/api";

type FacilityEvidenceExplorerProps = {
  parameterTable: FacilityParameterTable;
};

const ROW_HEIGHT = 54;
const VIEWPORT_HEIGHT = 420;
const OVERSCAN = 8;

function formatValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "UNKNOWN";
  if (typeof value === "boolean") return value ? "YES" : "NO";
  return String(value);
}

export function FacilityEvidenceExplorer({ parameterTable }: FacilityEvidenceExplorerProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const totalRows = parameterTable.rows.length;
  const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + OVERSCAN * 2;
  const end = Math.min(totalRows, start + visibleCount);

  const visibleRows = useMemo(() => parameterTable.rows.slice(start, end), [parameterTable.rows, start, end]);
  const topSpacer = start * ROW_HEIGHT;
  const bottomSpacer = Math.max(0, (totalRows - end) * ROW_HEIGHT);

  return (
    <section id="evidence-explorer" className="rounded-3xl border border-[#d6e2e9] bg-[#f7fbff] p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold text-[#213547]">Evidence Explorer</h2>
        <p className="text-xs text-[#41596f]">{totalRows} parameters</p>
      </div>

      <div className="mt-3 grid grid-cols-9 gap-2 rounded-xl border border-[#d7e4ed] bg-white px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[#496076]">
        <span className="col-span-2">Parameter</span>
        <span>Facility Value</span>
        <span>Patient Need</span>
        <span>Match</span>
        <span>Weight</span>
        <span>Source</span>
        <span>Status</span>
        <span>Confidence</span>
      </div>

      <div
        className="mt-2 overflow-y-auto rounded-xl border border-[#d7e4ed] bg-white"
        style={{ maxHeight: `${VIEWPORT_HEIGHT}px` }}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        aria-label="Virtualized evidence table"
      >
        <div style={{ height: topSpacer }} aria-hidden="true" />
        {visibleRows.map((row) => {
          const rowKey = `${row.parameter_id}-${row.scope_name || "global"}`;
          const isExpanded = expandedKey === rowKey;
          const known = row.source && row.source !== "Not verified";
          const matchLabel = String(row.status_value) === "YES" ? "MATCH" : String(row.status_value) === "NO" ? "GAP" : "UNKNOWN";
          const weight = row.category.includes("CARE") || row.category.includes("REHABILITATION") ? "High" : row.category.includes("QUALITY") ? "Medium" : "Standard";

          return (
            <div key={rowKey} className="border-b border-[#edf2f7] last:border-b-0">
              <button
                type="button"
                onClick={() => setExpandedKey(isExpanded ? null : rowKey)}
                className="grid w-full grid-cols-9 gap-2 px-3 py-3 text-left text-xs text-[#233549] hover:bg-[#f7fbff] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f6d8a]"
                aria-expanded={isExpanded}
                aria-controls={`evidence-row-${rowKey}`}
              >
                <span className="col-span-2 font-semibold">{row.parameter}</span>
                <span>{formatValue(row.status_value)}</span>
                <span>{row.detail_scope || "N/A"}</span>
                <span>{matchLabel}</span>
                <span>{weight}</span>
                <span className="truncate" title={row.source}>{row.source}</span>
                <span>{known ? "Verified" : "Unverified"}</span>
                <span>{known ? "Medium" : "Low"}</span>
              </button>
              {isExpanded ? (
                <div id={`evidence-row-${rowKey}`} className="space-y-2 bg-[#f9fcff] px-4 py-3 text-xs text-[#334a61]">
                  <p>
                    <span className="font-semibold">Parameter ID:</span> {row.parameter_id}
                  </p>
                  <p>
                    <span className="font-semibold">Scope:</span> {row.detail_scope}{row.scope_name ? ` / ${row.scope_name}` : ""}
                  </p>
                  <p>
                    <span className="font-semibold">Last Updated:</span> {row.last_verified || "Not available"}
                  </p>
                  <p>
                    <span className="font-semibold">Evidence Records:</span> {row.evidence_count}
                  </p>
                  {(row.evidence_records || []).length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5">
                      {(row.evidence_records || []).slice(0, 5).map((record, index) => (
                        <li key={`${rowKey}-record-${index}`}>
                          {record.evidence_text || "Evidence entry"}
                          {record.evidence_date ? ` (${record.evidence_date})` : ""}
                          {record.source ? ` - ${record.source}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No expanded evidence records are available for this parameter.</p>
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
        <div style={{ height: bottomSpacer }} aria-hidden="true" />
      </div>
    </section>
  );
}
