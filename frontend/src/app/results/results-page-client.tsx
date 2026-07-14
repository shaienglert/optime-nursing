"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";

const INITIAL_LOAD = 20;
const PAGE_SIZE = 10;

function scoreBadgeStyle(score: number): string {
  if (score >= 90) return "bg-[#5f8768] text-white";
  if (score >= 80) return "bg-[#dbe8d8] text-[#35523d]";
  if (score >= 70) return "bg-[#f0dfad] text-[#6c5322]";
  return "bg-[#f1caa4] text-[#7c4f23]";
}

function highlightLabel(index: number, relationship: string): string | null {
  if (index === 0) return `Best Match for ${relationship}`;
  if (index === 1) return "Excellent Alternative";
  if (index === 2) return "Best Value Option";
  return null;
}

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function cardReasons(facility: SearchFacility, activity: string, distance: string): string[] {
  return [
    `Excellent staffing levels (${facility.staffing_rating ?? 4}/5)`,
    `Strong ${activity.toLowerCase()} and activity program`,
    `Within ${distance.replace("Under ", "").toLowerCase()} from family`,
    "Fits budget requirements",
  ];
}

export function ResultsPageClient() {
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();
  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD);
  const [isLoading, setIsLoading] = useState(true);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const loaderRef = useRef<HTMLDivElement | null>(null);

  const selectedRelationship = searchParams.get("relationship") || state.relationship || "";
  const relationship = relationshipCopy(selectedRelationship);
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const activity = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const budget = Number(searchParams.get("budget") || state.budget || 7000);
  const distance = searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes";

  const [filters, setFilters] = useState<string[]>([
    `Age: ${age}`,
    `Care: ${care}`,
    `Activities: ${activity}`,
    `Budget: $${budget.toLocaleString()}`,
    `Distance: ${distance}`,
  ]);

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      const data = await fetchSearchFacilities();
      if (isMounted) {
        setFacilities(data);
        setVisibleCount(INITIAL_LOAD);
        setIsLoading(false);
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!loaderRef.current || isLoading) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((current) => Math.min(current + PAGE_SIZE, facilities.length));
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [facilities.length, isLoading]);

  const visibleFacilities = useMemo(() => facilities.slice(0, visibleCount), [facilities, visibleCount]);

  const removeFilter = (value: string) => {
    setFilters((current) => current.filter((item) => item !== value));
  };

  const toggleSaved = (id: number) => {
    setSavedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const toggleCompare = (id: number) => {
    setCompareIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const shareFacility = async (facility: SearchFacility) => {
    const message = `${facility.name} - OPTIME Score ${facility.optimeScore}`;
    try {
      await navigator.clipboard.writeText(message);
    } catch {
      // no-op fallback for restricted clipboard contexts
    }
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">These communities best match what matters most to {relationship}.</p>

          <div className="mt-5 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => removeFilter(filter)}
                className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-3 py-1 text-sm text-[#534a3d] hover:bg-[#efe8db]"
              >
                {filter} x
              </button>
            ))}
          </div>
        </header>

        {!isLoading && visibleFacilities.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn't find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          {visibleFacilities.map((facility, index) => (
            <article key={`${facility.id}-${facility.imageUrl}`} className="overflow-hidden rounded-3xl border border-[#e8ddcc] bg-white shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <div className="relative h-64 w-full">
                <Image src={facility.imageUrl} alt={facility.name} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 50vw" />
              </div>

              <div className="p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    {highlightLabel(index, relationship) ? (
                      <p className="mb-2 inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index, relationship)}</p>
                    ) : null}
                    <h2 className="text-2xl font-semibold text-[#2f2a24]">{facility.name}</h2>
                    <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                  </div>
                  <div className={`rounded-2xl px-3 py-2 text-center ${scoreBadgeStyle(facility.optimeScore)}`}>
                    <p className="text-2xl font-bold leading-none">{facility.optimeScore}</p>
                    <p className="mt-1 text-xs font-semibold">{facility.matchLabel}</p>
                  </div>
                </div>

                <div className="mt-4 rounded-2xl border border-[#e8dcc7] bg-[#fbf8f1] p-4">
                  <p className="text-sm font-semibold text-[#3d352b]">Why this is a great match:</p>
                  <ul className="mt-2 space-y-1 text-sm text-[#5c5347]">
                    {cardReasons(facility, activity, distance).map((reason) => (
                      <li key={`${facility.id}-${reason}`}>• {reason}</li>
                    ))}
                  </ul>
                </div>

                <p className="mt-4 text-sm font-semibold text-[#4f6f8f]">{facility.priceRange}</p>

                <div className="mt-4 flex flex-wrap gap-2">
                  {facility.careTypes.map((careType) => (
                    <span key={careType} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5f5548]">
                      {careType}
                    </span>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {facility.matchBadges.map((badge) => (
                    <span key={badge} className="rounded-full bg-[#edf3ea] px-3 py-1 text-xs font-medium text-[#4c6f5b]">
                      ✓ {badge}
                    </span>
                  ))}
                </div>

                <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <button type="button" onClick={() => toggleSaved(facility.id)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    {savedIds.includes(facility.id) ? "Saved" : "Save"}
                  </button>
                  <button type="button" onClick={() => toggleCompare(facility.id)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    {compareIds.includes(facility.id) ? "Compared" : "Compare"}
                  </button>
                  <button type="button" onClick={() => shareFacility(facility)} className="rounded-full border border-[#dccfb9] px-3 py-2 text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Share
                  </button>
                  <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer" className="rounded-full border border-[#dccfb9] px-3 py-2 text-center text-xs font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Map
                  </a>
                </div>

                <div className="mt-5">
                  <Link href={`/facilities/${facility.id}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                    View Details
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </section>

        <div ref={loaderRef} className="py-10 text-center text-sm text-[#6d655b]">
          {isLoading ? "Loading communities..." : visibleCount < facilities.length ? "Loading more results..." : "End of recommendations"}
        </div>
      </section>
    </main>
  );
}
