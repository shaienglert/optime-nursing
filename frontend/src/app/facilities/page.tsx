"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Facility, fetchFacilities } from "@/lib/api";

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchFacilities(searchText);
        if (isMounted) {
          setFacilities(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load facilities.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [searchText]);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-700">Facilities</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Find Senior Living Matches</h1>
            <p className="mt-2 text-slate-600">Browse available facilities and compare key quality indicators.</p>
          </div>
          <Link href="/" className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-300">
            Home
          </Link>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4">
          <label htmlFor="facility-search" className="text-sm font-medium text-slate-700">Search communities</label>
          <input
            id="facility-search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Try English or Hebrew (e.g. Hebrew, עברית, זוד)"
            className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-800 outline-none ring-cyan-300 focus:ring-2"
          />
        </div>

        {isLoading ? (
          <div className="rounded-2xl border border-cyan-100 bg-white p-6 text-cyan-700">Loading facilities...</div>
        ) : null}

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-white p-6 text-rose-700">{error}</div>
        ) : null}

        {!isLoading && !error ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {facilities.map((facility) => (
              <Link
                key={facility.id}
                href={`/facilities/${facility.id}`}
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow-md"
              >
                <h2 className="text-lg font-semibold text-slate-900 group-hover:text-cyan-800">{facility.name}</h2>
                <p className="mt-1 text-sm text-slate-600">
                  {facility.city}, {facility.state}
                </p>
                <dl className="mt-4 space-y-2 text-sm text-slate-700">
                  <div className="flex items-center justify-between">
                    <dt>Overall rating</dt>
                    <dd className="font-semibold">{facility.overall_rating ?? "N/A"}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt>Staffing rating</dt>
                    <dd className="font-semibold">{facility.staffing_rating ?? "N/A"}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt>Beds</dt>
                    <dd className="font-semibold">{facility.beds ?? "N/A"}</dd>
                  </div>
                </dl>
              </Link>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
