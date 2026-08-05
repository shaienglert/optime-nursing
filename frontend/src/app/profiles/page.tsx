"use client";

import Link from "next/link";
import { useState } from "react";

type PatientProfileRecord = {
  id: string;
  label: string;
  version: number;
  updatedAt: string;
  state: Record<string, unknown>;
};

const PATIENT_PROFILES_STORAGE_KEY = "optime.patient.profiles";

function loadProfiles(): PatientProfileRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(PATIENT_PROFILES_STORAGE_KEY);
    if (!raw) return [];
    const rows = JSON.parse(raw) as PatientProfileRecord[];
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

export default function ProfilesPage() {
  const [profiles] = useState<PatientProfileRecord[]>(() => loadProfiles());

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700">Profiles</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Saved Patient Profiles</h1>
            <p className="mt-2 text-sm text-slate-600">Previously stored questionnaire profiles available in this browser.</p>
          </div>
          <Link href="/" className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-300">
            Back Home
          </Link>
        </div>

        <section className="rounded-3xl border border-slate-200 bg-white p-6">
          <ul className="space-y-3 text-sm text-slate-700">
            {profiles.length > 0 ? profiles.map((profile) => (
              <li key={profile.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="font-medium text-slate-900">{profile.label}</p>
                <p className="mt-1 text-slate-600">Version {profile.version}</p>
                <p className="mt-1 text-xs text-slate-500">Updated {new Date(profile.updatedAt).toLocaleString()}</p>
              </li>
            )) : <li>No saved profiles yet.</li>}
          </ul>
        </section>
      </section>
    </main>
  );
}
