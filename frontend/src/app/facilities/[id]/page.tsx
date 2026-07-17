"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { FacilityDetailsData, fetchFacilityDetails } from "@/lib/api";

export default function FacilityDetailPage() {
  const params = useParams<{ id: string }>();
  const facilityId = String(params?.id || "");

  const [facility, setFacility] = useState<FacilityDetailsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchFacilityDetails(facilityId);
        if (mounted) {
          setFacility(data);
          setActiveIndex(0);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load facility details.");
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    if (facilityId) {
      void load();
    }

    return () => {
      mounted = false;
    };
  }, [facilityId]);

  const galleryImages = useMemo(() => facility?.visualIntelligence.galleryImages || [], [facility]);
  const activeImage = galleryImages[activeIndex] || facility?.visualIntelligence.heroImage;

  if (isLoading) {
    return <main className="min-h-screen bg-[#f8f5ee] px-6 py-10 text-[#4b443a]">Loading facility details...</main>;
  }

  if (error || !facility) {
    return (
      <main className="min-h-screen bg-[#f8f5ee] px-6 py-10">
        <p className="text-[#8b3d2e]">{error || "Facility not found."}</p>
        <Link href="/results" className="mt-4 inline-flex rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245]">
          Back to results
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#5f7f6b]">Facility Profile</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#2f2a24]">{facility.name}</h1>
              <p className="mt-1 text-[#6d655b]">{facility.city}, {facility.state}</p>
            </div>
            <Link href="/results" className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
              Back to results
            </Link>
          </div>
        </header>

        <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
          <div className="overflow-hidden rounded-2xl border border-[#e3d8c8]">
            <img
              src={activeImage?.url || "/cms-placeholder.svg"}
              alt={`${facility.name} gallery image`}
              className="h-[360px] w-full object-cover"
              onError={(event) => {
                event.currentTarget.src = "/cms-placeholder.svg";
              }}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#e3d8c8] bg-white px-4 py-3 text-sm text-[#5f5548]">
              <p>Source: {activeImage?.source || "CMS Placeholder"}</p>
              <p>Category: {activeImage?.category || "exterior"}</p>
              <p>Collected: {activeImage?.collected_at || "Unknown"}</p>
            </div>
          </div>

          {galleryImages.length > 0 ? (
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
              {galleryImages.map((image, index) => (
                <button
                  key={`${image.url}-${index}`}
                  type="button"
                  onClick={() => setActiveIndex(index)}
                  className={`overflow-hidden rounded-xl border ${index === activeIndex ? "border-[#6f9a86]" : "border-[#e3d8c8]"}`}
                >
                  <img
                    src={image.url}
                    alt={`${facility.name} ${image.category}`}
                    className="h-20 w-full object-cover"
                    onError={(event) => {
                      event.currentTarget.src = "/cms-placeholder.svg";
                    }}
                  />
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Community Snapshot</p>
          <p className="mt-2 text-xl font-semibold text-[#2f2a24]">Photo and lifestyle highlights</p>
          <p className="mt-1 text-sm text-[#5f5548]">These highlights help families quickly understand the community environment.</p>

          <div className="mt-3 flex flex-wrap gap-2">
            {facility.visualIntelligence.lifestyleTags.map((tag) => (
              <span key={tag.label} className="rounded-full border border-[#d7e5e2] bg-[#f4fbfa] px-3 py-1 text-sm font-semibold text-[#2f5f5a]">
                {tag.icon} {tag.label}
              </span>
            ))}
          </div>

        </section>
      </section>
    </main>
  );
}
