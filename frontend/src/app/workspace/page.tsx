"use client";

import Link from "next/link";
import { useState } from "react";

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
  const [recent] = useState<SavedSearch[]>(() => loadRows(RECENT_SEARCHES_STORAGE_KEY));
  const [saved] = useState<SavedSearch[]>(() => loadRows(SAVED_SEARCHES_STORAGE_KEY));

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl space-y-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700">Workspace</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Saved Case Workspace</h1>
            <p className="mt-2 text-sm text-slate-600">Reuse and review saved natural-language case descriptions from this browser.</p>
          </div>
          <Link href="/" className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-300">
            Back Home
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900">Recent Searches</h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-700">
              {recent.length > 0 ? recent.map((item) => (
                <li key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="mt-1 text-slate-600">{item.naturalLanguageQuery}</p>
                  <p className="mt-1 text-xs text-slate-500">{new Date(item.createdAt).toLocaleString()}</p>
                </li>
              )) : <li>No recent searches saved yet.</li>}
            </ul>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900">Saved Searches</h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-700">
              {saved.length > 0 ? saved.map((item) => (
                <li key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="mt-1 text-slate-600">{item.naturalLanguageQuery}</p>
                  <p className="mt-1 text-xs text-slate-500">{new Date(item.createdAt).toLocaleString()}</p>
                </li>
              )) : <li>No saved searches yet.</li>}
            </ul>
          </section>
        </div>
      </section>
    </main>
  );
}
