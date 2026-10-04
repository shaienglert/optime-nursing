"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchClientCase } from "@/lib/api";
import { saveSessionJson, QUESTIONNAIRE_SESSION_KEY } from "@/lib/search-session";

type SavedSearch = {
  id: string;
  title: string;
  naturalLanguageQuery: string;
  createdAt: string;
};

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

export default function WorkspacePage() {
  const router = useRouter();
  const [clientCaseAvailable, setClientCaseAvailable] = useState(false);
  useEffect(() => { setClientCaseAvailable(!!window.localStorage.getItem("oomnik.client.case.token")); }, []);
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
