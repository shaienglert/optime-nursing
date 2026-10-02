"use client";

import { useEffect, useState } from "react";

type Finding = { date: string; subject?: string; severity?: string; correction_status?: string; source_url?: string };
type Topic = {
  topic: string; label: string; source: string; status: string; observed_at?: string;
  source_url?: string; limitation?: string;
  known_findings?: Finding[];
  data: { findings?: Finding[]; published_finding_count?: number; processing_date?: string; [key: string]: unknown };
};
type Report = { status: string; topics: Topic[] };

function sourceLink(value?: string): string | null {
  try {
    const url = new URL(value || "");
    return url.protocol === "https:" ? url.href : null;
  } catch { return null; }
}

const STATUS: Record<string, string> = {
  VERIFIED: "Verified source data", PARTIAL: "Partial information", NOT_CHECKED: "Not checked yet",
  STALE: "Update overdue", SOURCE_FAILED: "Source currently unavailable", IDENTITY_UNRESOLVED: "Facility identity not confirmed",
  ACCESS_BLOCKED: "Source access blocked", NOT_APPLICABLE: "Not applicable to this facility",
  API_AND_ATTRIBUTION_REQUIRED: "Data connection not configured",
  REDISTRIBUTION_PERMISSION_REQUIRED: "Publication permission required",
  AUTHORIZED_FEED_REQUIRED: "Verified data connection required", DIRECT_VERIFICATION_REQUIRED: "Direct verification required",
  SYNTHETIC_PILOT_NOT_PUBLIC_RESEARCH: "Pilot example — no real public research",
};

export function FacilityResearchPanel({ canonicalFacilityId }: { canonicalFacilityId: string | number | null }) {
  const id = String(canonicalFacilityId || "");
  const [result, setResult] = useState<{ id: string; report: Report | null; state: string }>({ id: "", report: null, state: "loading" });
  const report = result.id === id ? result.report : null;
  const state = !id ? "unknown" : result.id === id ? result.state : "loading";
  useEffect(() => {
    const controller = new AbortController();
    if (!id) return;
    fetch(`/api/backend/canonical-facilities/${encodeURIComponent(id)}/research`, {
      cache: "no-store", signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error("Research unavailable");
      return await response.json() as Report;
    }).then(value => { if (!controller.signal.aborted) setResult({ id, report: value, state: "ready" }); })
      .catch(() => { if (!controller.signal.aborted) setResult({ id, report: null, state: "unavailable" }); });
    return () => controller.abort();
  }, [id]);

  return <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5" aria-label="Official findings and source ratings">
    <h2 className="text-xl font-semibold text-[#332f29]">Known official complaints, findings and source ratings</h2>
    <p className="mt-2 text-sm text-[#776e62]">Sources are shown separately. Each known complaint is distinguished from the findings of its investigation.</p>
    {state === "loading" ? <p className="mt-4 text-sm">Loading verified research…</p> : null}
    {state !== "ready" && state !== "loading" ? <p className="mt-4 text-sm">Current research is unavailable. Official complaints in the last 12 months have not been verified.</p> : null}
    {report?.topics.filter(topic => topic.topic === "official_complaints" || (["VERIFIED", "PARTIAL", "STALE"].includes(topic.status) && Object.keys(topic.data).length > 0)).map(topic => {
      const link = sourceLink(topic.source_url);
      const current = ["VERIFIED", "PARTIAL"].includes(topic.status);
      return <div key={topic.topic} className="mt-4 border-t border-[#e8ddcc] pt-4 text-sm text-[#4f473d]">
        <h3 className="font-semibold">{topic.label}</h3>
        <p className="mt-1">{STATUS[topic.status] || "Information unconfirmed"}</p>
        <p className="mt-1">Source: {topic.source}{topic.observed_at ? ` · Checked: ${topic.observed_at.slice(0, 10)}` : ""}</p>
        {topic.data.processing_date ? <p>Source publication date: {String(topic.data.processing_date)}</p> : null}
        {topic.topic === "official_complaints" ? <p className="mt-2 text-[#776e62]">Published records may provide only partial coverage of known complaints.</p> : null}
        {current && topic.topic === "cms_quality" ? <div className="mt-2 flex flex-wrap gap-3">
          {["overall_rating", "inspection_rating", "staffing_rating", "quality_rating"].map(key => <span key={key}>{key.replaceAll("_", " ")}: {topic.data[key] ? `${String(topic.data[key])}/5` : "Unknown"}</span>)}
          <span>Special focus status: {String(topic.data.special_focus_status || "Unknown")}</span>
          <span>Abuse indicator: {String(topic.data.abuse_icon || "Unknown")}</span>
        </div> : null}
        {current && (topic.data.published_finding_count || 0) > 0 ? <p className="mt-2">Known published complaint-related findings: {topic.data.published_finding_count}.</p> : null}
        {(topic.known_findings || (current ? topic.data.findings : []) || []).map((finding, i) => <div key={`${finding.date}-${i}`} className="mt-2 rounded-xl bg-[#fff9ed] p-3">
          <p>Inspection date: {finding.date} · Severity: {finding.severity || "Unknown"}</p>
          <p>{finding.subject || "See official report"}</p><p>Correction: {finding.correction_status || "Unknown"}</p>
          {sourceLink(finding.source_url) ? <a href={sourceLink(finding.source_url)!} target="_blank" rel="noopener noreferrer" className="underline">Official finding source</a> : null}
        </div>)}
        {link && current ? <a className="mt-2 inline-block underline" href={link} target="_blank" rel="noopener noreferrer">View source</a> : null}
      </div>;
    })}
  </section>;
}
