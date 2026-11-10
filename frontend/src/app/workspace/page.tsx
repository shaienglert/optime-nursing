"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { fetchClientCase, type FacilityCaseLetter } from "@/lib/api";
import { saveSessionJson, QUESTIONNAIRE_SESSION_KEY } from "@/lib/search-session";

type SavedSearch = {
  id: string;
  title: string;
  naturalLanguageQuery: string;
  createdAt: string;
};

type FacilityReply = {
  id: number;
  facility_name: string;
  letter: FacilityCaseLetter;
  reply: { answers: Record<string, string>; notes: string; monthly_price_cents?: number; availability?: string };
  files: string[];
};

function FacilityReplies() {
  const [data, setData] = useState<{ token: string; replies: FacilityReply[] } | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const token = window.localStorage.getItem("oomnik.client.case.token");
    if (!token) return;
    const controller = new AbortController();
    fetch(`/api/backend/api/client-cases/${encodeURIComponent(token)}/facility-replies`, { cache: "no-store", signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(); return response.json(); })
      .then(replies => { if (!controller.signal.aborted) setData({ token, replies }); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, []);
  if (error) return <p role="status">We couldn’t load community replies. Try refreshing this page.</p>;
  if (!data?.replies.length) return null;
  return <section className="rounded-3xl border border-line bg-white p-6">
    <h2 className="text-xl font-semibold">Replies from communities</h2>
    {data.replies.map(({ id, facility_name, letter, reply, files }) => <article key={id} className="mt-4 border-t border-line pt-4">
      <h3 className="font-semibold">{facility_name}</h3>
      <p className="text-sm text-muted">Reported by the community. Final care, price and availability may require confirmation.</p>
      <ul className="mt-2 space-y-1">{letter.items.map((item, index) => <li key={index}>
        {item.label}: <strong>{({ yes: "Yes", no: "No", depends: "Depends" } as Record<string, string>)[reply.answers[index]] || "Not answered"}</strong>
        {item.priority === "MUST" ? " (required)" : ""}
      </li>)}</ul>
      {reply.availability ? <p>Availability: {reply.availability}</p> : null}
      {reply.monthly_price_cents ? <p>Estimated monthly cost: {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(reply.monthly_price_cents / 100)}</p> : null}
      {reply.notes ? <p className="mt-2 whitespace-pre-wrap">{reply.notes}</p> : null}
      {files.map((name, index) => <a key={index} download={name} className="mt-2 block underline" href={`/api/backend/api/client-cases/${encodeURIComponent(data.token)}/facility-replies/${id}/files/${index}`}>{name}</a>)}
    </article>)}
  </section>;
}

const RECENT_SEARCHES_STORAGE_KEY = "optime.recent.searches";
const SAVED_SEARCHES_STORAGE_KEY = "optime.saved.searches";

function loadRows(key: string): SavedSearch[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return [];
    const rows = JSON.parse(raw) as SavedSearch[];
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

function subscribeCaseStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}
const hasCase = () => !!window.localStorage.getItem("oomnik.client.case.token");

export default function WorkspacePage() {
  const router = useRouter();
  const clientCaseAvailable = useSyncExternalStore(subscribeCaseStorage, hasCase, () => false);
  async function resumeQuestionnaire() {
    const token = window.localStorage.getItem("oomnik.client.case.token");
    if (!token) return;
    const record = await fetchClientCase(token);
    if (!record.questionnaire_state) return;
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, record.questionnaire_state);
    router.push("/intake");
  }

  const [recent] = useState<SavedSearch[]>(() => loadRows(RECENT_SEARCHES_STORAGE_KEY));
  const [saved] = useState<SavedSearch[]>(() => loadRows(SAVED_SEARCHES_STORAGE_KEY));

  return (
    <main className="min-h-screen bg-canvas px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl space-y-8">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-forest">Workspace</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Your saved conversations</h1>
            <p className="mt-2 text-sm text-muted">Pick up where you left off. Your saved conversations and searches are here whenever you want to return.</p>
          </div>
          <Link href="/" className="rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-muted hover:border-line">
            Back Home
          </Link>
        </div>

        {clientCaseAvailable ? <section className="rounded-3xl border border-line bg-white p-6 oomnik-panel"><h2 className="text-xl font-semibold">Your questionnaire</h2><p className="mt-2 text-sm text-muted">Resume with your saved answers, change anything that has changed, and keep the previous version in the case history.</p><button type="button" onClick={resumeQuestionnaire} className="mt-4 rounded-full bg-forest px-6 py-3 font-semibold text-white">Resume / edit questionnaire</button></section> : null}
        {clientCaseAvailable ? <FacilityReplies /> : null}
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-3xl border border-line bg-white p-6 oomnik-panel">
            <h2 className="text-lg font-semibold text-ink">Recent Searches</h2>
            <ul className="mt-4 space-y-3 text-sm text-muted">
              {recent.length > 0 ? recent.map((item) => (
                <li key={item.id} className="rounded-2xl border border-line bg-canvas px-4 py-3">
                  <p className="font-medium text-ink">{item.title}</p>
                  <p className="mt-1 text-muted">{item.naturalLanguageQuery}</p>
                  <p className="mt-1 text-xs text-muted">{new Date(item.createdAt).toLocaleString()}</p>
                </li>
              )) : <li>Your recent searches will appear here. Start with a few answers about what matters to you.</li>}
            </ul>
          </section>

          <section className="rounded-3xl border border-line bg-white p-6 oomnik-panel">
            <h2 className="text-lg font-semibold text-ink">Saved Searches</h2>
            <ul className="mt-4 space-y-3 text-sm text-muted">
              {saved.length > 0 ? saved.map((item) => (
                <li key={item.id} className="rounded-2xl border border-line bg-canvas px-4 py-3">
                  <p className="font-medium text-ink">{item.title}</p>
                  <p className="mt-1 text-muted">{item.naturalLanguageQuery}</p>
                  <p className="mt-1 text-xs text-muted">{new Date(item.createdAt).toLocaleString()}</p>
                </li>
              )) : <li>When you save a search, you can return to it here at your own pace.</li>}
            </ul>
          </section>
        </div>
      </section>
    </main>
  );
}
