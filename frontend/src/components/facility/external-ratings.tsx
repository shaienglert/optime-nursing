"use client";

import { useEffect, useState } from "react";

type Source = {
  status: "AVAILABLE" | "UNAVAILABLE" | "SOURCE_UNAVAILABLE";
  rating: number | null;
  review_count: number | null;
  recognition: string | null;
  assessment_year: number | null;
  observed_at: string | null;
  source_url: string | null;
};
type Ratings = { google: Source; us_news: Source };
type Snapshot = { id: string; data: Ratings | null; failed: boolean };

export function ExternalRatings({ canonicalFacilityId }: { canonicalFacilityId: string | null }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  useEffect(() => {
    if (!canonicalFacilityId) return;
    const controller = new AbortController();
    const id = canonicalFacilityId;
    async function load() {
      try {
        const response = await fetch(`/api/backend/canonical-facilities/${encodeURIComponent(id)}/external-ratings`, {
          cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error("External source unavailable");
        const data: Ratings = await response.json();
        if (!controller.signal.aborted) setSnapshot({ id, data, failed: false });
      } catch {
        if (!controller.signal.aborted) setSnapshot({ id, data: null, failed: true });
      }
    }
    void load();
    return () => controller.abort();
  }, [canonicalFacilityId]);

  const current = snapshot?.id === canonicalFacilityId ? snapshot : null;
  const loading = Boolean(canonicalFacilityId && !current);
  return <ExternalRatingsPanel data={current?.data ?? null} loading={loading} failed={current?.failed ?? false} />;
}

export function ExternalRatingsPanel({ data, loading = false, failed = false }: { data: Ratings | null; loading?: boolean; failed?: boolean }) {
  const google = data?.google;
  const usNews = data?.us_news;
  return <section aria-labelledby="external-ratings-title" className="rounded-3xl border border-line bg-white p-5 oomnik-panel">
    <h2 id="external-ratings-title" className="text-2xl font-semibold">External ratings</h2>
    <p className="mt-2 text-sm leading-6 text-muted">External ratings are provided for reference only. They do not affect Oomnik&apos;s match ranking or break ties.</p>
    <div className="mt-4 grid gap-4 sm:grid-cols-2" aria-busy={loading}>
      <article className="rounded-xl border border-line bg-canvas p-4">
        <h3 className="font-semibold">Google Maps</h3>
        {google?.status === "AVAILABLE" ? <>
          <p className="mt-2 text-xl font-semibold">{google.rating} / 5</p>
          <p className="text-sm text-muted">{google.review_count?.toLocaleString()} reviews · Public reviews</p>
          {google.observed_at ? <p className="mt-1 text-xs text-muted">Retrieved {google.observed_at.slice(0, 10)}</p> : null}
          {google.source_url ? <a href={google.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm underline">View on Google Maps</a> : null}
        </> : <p className="mt-2 text-sm text-muted" role="status">{loading ? "Loading source…" : failed || google?.status === "SOURCE_UNAVAILABLE" ? "Source temporarily unavailable" : "No rating available"}</p>}
      </article>
      <article className="rounded-xl border border-line bg-canvas p-4">
        <h3 className="font-semibold">U.S. News &amp; World Report</h3>
        {usNews?.status === "AVAILABLE" ? <>
          <p className="mt-2 font-semibold">{usNews.recognition}</p>
          <p className="text-sm text-muted">{usNews.assessment_year} assessment · U.S. News recognition</p>
          {usNews.observed_at ? <p className="mt-1 text-xs text-muted">Checked {usNews.observed_at}</p> : null}
          {usNews.source_url ? <a href={usNews.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm underline">View U.S. News assessment</a> : null}
        </> : <p className="mt-2 text-sm text-muted" role="status">{loading ? "Loading source…" : failed ? "Source temporarily unavailable" : "No assessment available"}</p>}
      </article>
    </div>
    <p className="mt-3 text-xs leading-5 text-muted">Each source uses its own method. An unavailable rating does not mean poor quality.</p>
  </section>;
}
