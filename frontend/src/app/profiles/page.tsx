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
    <main className="min-h-screen bg-canvas px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-forest">Profiles</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">The people you’re helping</h1>
            <p className="mt-2 text-sm text-muted">Return to the answers you saved on this device, whenever you’re ready to continue.</p>
          </div>
          <Link href="/" className="rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-muted hover:border-line">
            Back Home
          </Link>
        </div>

        <section className="rounded-3xl border border-line bg-white p-6 oomnik-panel">
          <ul className="space-y-3 text-sm text-muted">
            {profiles.length > 0 ? profiles.map((profile) => (
              <li key={profile.id} className="rounded-2xl border border-line bg-canvas px-4 py-3">
                <p className="font-medium text-ink">{profile.label}</p>
                <p className="mt-1 text-muted">Version {profile.version}</p>
                <p className="mt-1 text-xs text-muted">Updated {new Date(profile.updatedAt).toLocaleString()}</p>
              </li>
            )) : <li>Your saved answers will appear here. We’ll start by getting to know the person and what matters to them.</li>}
          </ul>
        </section>
      </section>
    </main>
  );
}
