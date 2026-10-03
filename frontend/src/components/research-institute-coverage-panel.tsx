"use client";
import { useEffect, useState } from "react";
import { getApiBaseUrl, joinApiUrl } from "@/lib/api";

type Coverage = {
  status: string; real_facilities: number; synthetic_excluded: number; status_counts: Record<string, number>;
  facilities: { canonical_facility_id: string; status: string; topics: { label: string; status: string; next_action: string }[] }[];
};

export function ResearchInstituteCoveragePanel({ adminToken }: { adminToken: string }) {
  const [result, setResult] = useState<{ token: string; data: Coverage | null; error: string }>({ token: "", data: null, error: "" });
  const data = result.token === adminToken ? result.data : null;
  const error = result.token === adminToken ? result.error : "";
  useEffect(() => {
    const controller = new AbortController();
    if (!adminToken) return;
    fetch(joinApiUrl(getApiBaseUrl(), "/admin/research-institute/coverage"), {
      headers: { "X-Admin-Token": adminToken }, cache: "no-store", signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error(`Research coverage unavailable (${response.status})`);
      return await response.json() as Coverage;
    }).then(value => { if (!controller.signal.aborted) setResult({ token: adminToken, data: value, error: "" }); })
      .catch(err => { if (!controller.signal.aborted) setResult({ token: adminToken, data: null, error: err.message }); });
    return () => controller.abort();
  }, [adminToken]);
  return <section className="mt-5 rounded-2xl border border-slate-700 p-4 text-sm text-slate-200">
    <h3 className="font-semibold">Research Institute — evidence delivery and freshness</h3>
    {error ? <p className="mt-2 text-rose-300">{error}</p> : null}
    {!data && !error ? <p className="mt-2">Loading source coverage…</p> : null}
    {data ? <>
      <p className="mt-2">{data.status} · {data.real_facilities} real facilities · {data.synthetic_excluded} pilot examples excluded</p>
      <p className="mt-2">{Object.entries(data.status_counts).map(([key, count]) => `${key}: ${count}`).join(" · ")}</p>
      <p className="mt-2 text-slate-400">Completed tasks are attempts, not proof. Partial and stale data remain gaps.</p>
      <div className="mt-3 max-h-96 overflow-auto">
        {data.facilities.filter(f => f.status === "DEGRADED").map(f => <details key={f.canonical_facility_id} className="border-t border-slate-700 py-2">
          <summary>{f.canonical_facility_id}</summary>
          {f.topics.filter(t => !["VERIFIED", "NOT_APPLICABLE"].includes(t.status)).map(t => <p key={t.label} className="mt-2">{t.label}: {t.status}. {t.next_action}</p>)}
        </details>)}
      </div>
    </> : null}
  </section>;
}
