"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Facility, fetchFacilityById } from "@/lib/api";

export default function FacilityDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [facility, setFacility] = useState<Facility | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadFacility() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchFacilityById(id);
        if (isMounted) {
          setFacility(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Failed to load facility details.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    if (id) {
      loadFacility();
    }

    return () => {
      isMounted = false;
    };
  }, [id]);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-4xl">
        <Link href="/facilities" className="inline-flex rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-300">
          Back to facilities
        </Link>

        {isLoading ? <p className="mt-6 text-cyan-700">Loading facility details...</p> : null}

        {error ? <p className="mt-6 rounded-xl border border-rose-200 bg-white p-4 text-rose-700">{error}</p> : null}

        {facility ? (
          <article className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-2xl font-semibold text-slate-900">{facility.name}</h1>
            <p className="mt-1 text-slate-600">
              {facility.address}, {facility.city}, {facility.state} {facility.zip_code}
            </p>

            <dl className="mt-6 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">CMS ID</dt>
                <dd className="mt-1 font-semibold">{facility.cms_id}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Phone</dt>
                <dd className="mt-1 font-semibold">{facility.phone || "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Overall rating</dt>
                <dd className="mt-1 font-semibold">{facility.overall_rating ?? "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Staffing rating</dt>
                <dd className="mt-1 font-semibold">{facility.staffing_rating ?? "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Quality rating</dt>
                <dd className="mt-1 font-semibold">{facility.quality_rating ?? "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Inspection rating</dt>
                <dd className="mt-1 font-semibold">{facility.inspection_rating ?? "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Beds</dt>
                <dd className="mt-1 font-semibold">{facility.beds ?? "N/A"}</dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="font-medium text-slate-500">Coordinates</dt>
                <dd className="mt-1 font-semibold">
                  {facility.latitude ?? "N/A"}, {facility.longitude ?? "N/A"}
                </dd>
              </div>
            </dl>
          </article>
        ) : null}
      </section>
    </main>
  );
}
