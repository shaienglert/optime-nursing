"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { fetchFacilityDetails, fetchGovernanceRuntimeContext, fetchSearchFacilities, FacilityDetailsData, GovernanceRuntimeContext, SearchFacility } from "@/lib/api";
import { personLabel, resolveFacilityImage, resolvePriceTruth } from "@/lib/facility-experience";
import { runOptimeV2Engine } from "@/lib/optime-v2-engine";

type FacilityProfileClientProps = {
  facilityId: string;
  backHref: string;
  backLabel: string;
};

function sectionItems(items: string[], fallback: string): string[] {
  return items.length > 0 ? items : [fallback];
}

function truthLabel(value?: string | null): string {
  return value || "Unknown";
}

function useFacilityRecommendation(facilityId: string, facilities: SearchFacility[], governanceContext: GovernanceRuntimeContext | null, state: ReturnType<typeof useQuestionnaire>["state"]) {
  return useMemo(() => {
    if (!governanceContext || facilities.length === 0) return null;
    const engineOutput = runOptimeV2Engine(facilities, state, { governanceContext });
    return engineOutput.displayedRecommendations.find((item) => String(item.facility.id) === facilityId)
      || engineOutput.accepted.find((item) => String(item.facility.id) === facilityId)
      || engineOutput.rejected.find((item) => String(item.facility.id) === facilityId)
      || null;
  }, [facilities, facilityId, governanceContext, state]);
}

function badgeRow(title: string, values: string[]) {
  return (
    <section className="rounded-2xl border border-[#e3d8c8] bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">{title}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((value) => (
          <span key={`${title}-${value}`} className="rounded-full border border-[#d7e5e2] bg-[#f4fbfa] px-3 py-1 text-sm font-semibold text-[#2f5f5a]">
            {value}
          </span>
        ))}
      </div>
    </section>
  );
}

export function FacilityProfileClient({ facilityId, backHref, backLabel }: FacilityProfileClientProps) {
  const { state } = useQuestionnaire();
  const [facility, setFacility] = useState<FacilityDetailsData | null>(null);
  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [governanceContext, setGovernanceContext] = useState<GovernanceRuntimeContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [facilityDetails, governedFacilities, runtimeContext] = await Promise.all([
          fetchFacilityDetails(facilityId),
          fetchSearchFacilities(""),
          fetchGovernanceRuntimeContext(),
        ]);
        if (!mounted) return;
        setFacility(facilityDetails);
        setFacilities(governedFacilities);
        setGovernanceContext(runtimeContext);
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load facility profile.");
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    if (facilityId) {
      void load();
    }

    return () => {
      mounted = false;
    };
  }, [facilityId]);

  const recommendation = useFacilityRecommendation(facilityId, facilities, governanceContext, state);
  const person = personLabel(state.relationship || "your family member");
  const imageTruth = facility ? resolveFacilityImage(facility) : null;
  const priceTruth = facility ? resolvePriceTruth(facility) : null;

  const verifiedItems = recommendation?.report.audit.verificationChecklist.filter((item) => item.state === "YES") || [];
  const unknownItems = recommendation?.report.audit.verificationChecklist.filter((item) => item.state === "UNKNOWN") || [];
  const noItems = recommendation?.report.audit.verificationChecklist.filter((item) => item.state === "NO") || [];
  const questions = recommendation?.report.audit.clinicalReasoning.questionsForFacility || [];
  const mustFailed = recommendation?.report.audit.governedFacilityDecision?.must_failed || [];
  const mustUnknown = recommendation?.report.audit.governedFacilityDecision?.must_unknown || [];
  const identity = recommendation?.report.audit.governedFacilityDecision?.identity_status || "UNRESOLVED_IDENTITY";
  const canonicalFacilityId = recommendation?.report.audit.governedFacilityDecision?.canonical_facility_id || facility?.id || null;

  const whySelected = recommendation?.report.audit.clinicalReasoning.whyThisCommunity || recommendation?.whyThisFits || facility?.shortExplanation || "OPTIME selected this facility based on the strongest verified fit signals currently available.";
  const rankReason = recommendation?.rankReason || recommendation?.confidenceExplanation || "One of the strongest available options for this search.";
  const priceLine = priceTruth ? `${priceTruth.label}: ${priceTruth.value}` : "Current pricing not verified — contact facility";
  const priceDisclosure = priceTruth?.truthState === "UNKNOWN"
    ? "Pricing is not published by the backend for this facility."
    : "Pricing is a derived estimate from the governed frontend model, not a facility quote.";

  if (isLoading) {
    return <main className="min-h-screen bg-[#fffdf8] px-6 py-12 text-[#5d5548]">Loading facility profile...</main>;
  }

  if (error || !facility) {
    return (
      <main className="min-h-screen bg-[#fffdf8] px-6 py-12">
        <p className="text-[#8b3d2e]">{error || "Facility not found."}</p>
        <Link href={backHref} className="mt-4 inline-flex rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245]">
          {backLabel}
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
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#5f7f6b]">Facility Intelligence Profile</p>
              <h1 className="mt-2 text-3xl font-semibold text-[#2f2a24]">{facility.name}</h1>
              <p className="mt-1 text-[#6d655b]">{facility.city}, {facility.state}</p>
            </div>
            <Link href={backHref} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
              {backLabel}
            </Link>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[360px,1fr]">
          <div className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
            <div className="overflow-hidden rounded-2xl border border-[#e3d8c8] bg-[#f7f2e8]">
              <img
                src={imageTruth?.url || "/cms-placeholder.svg"}
                alt={`${facility.name} facility image`}
                className="h-72 w-full object-cover"
                onError={(event) => {
                  event.currentTarget.src = "/cms-placeholder.svg";
                }}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#e3d8c8] bg-white px-3 py-2 text-xs text-[#6b6257]">
                <span>Image source: {imageTruth?.sourceLabel || "Placeholder"}</span>
                <span>{imageTruth?.isPlaceholder ? "Compact neutral placeholder" : "Governed public image"}</span>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-sm text-[#4f473d]">
              <p><span className="font-semibold text-[#2f2a24]">Canonical ID:</span> {canonicalFacilityId ?? "Unknown"}</p>
              <p><span className="font-semibold text-[#2f2a24]">Identity:</span> {identity}</p>
              <p><span className="font-semibold text-[#2f2a24]">Website:</span> {facility.website ? <a className="text-[#5f7f6b] underline" href={facility.website} target="_blank" rel="noreferrer">Verified website</a> : "Not verified"}</p>
              <p><span className="font-semibold text-[#2f2a24]">Phone:</span> {facility.phone || "Not verified"}</p>
              <p><span className="font-semibold text-[#2f2a24]">Price truth:</span> {priceLine}</p>
              <p className="text-xs text-[#6f6148]">{priceDisclosure}</p>
            </div>
          </div>

          <div className="space-y-6">
            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Why OPTIME selected this facility for {person}</p>
              <p className="mt-3 text-xl font-semibold text-[#2f2a24]">What this facility means for {person}</p>
              <p className="mt-3 text-sm leading-6 text-[#5f5548]">{whySelected}</p>
              <p className="mt-2 text-sm leading-6 text-[#5f5548]">{rankReason}</p>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-2xl border border-[#cde2d2] bg-[#f3fbf5] p-4">
                <p className="font-semibold text-[#2f6d3e]">Strong matches</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {sectionItems(verifiedItems.slice(0, 6).map((item) => item.label), "No verified matches yet").map((item) => (
                    <span key={`yes-${item}`} className="rounded-full border border-[#bcd9c0] bg-[#eef8f1] px-3 py-1 text-xs font-medium text-[#2f6d3e]">✔ {item}</span>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-[#f0c9bf] bg-[#fff3ef] p-4">
                <p className="font-semibold text-[#8b4f3f]">Potential concerns</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {sectionItems(noItems.slice(0, 4).map((item) => item.label), "No confirmed negative items yet").map((item) => (
                    <span key={`no-${item}`} className="rounded-full border border-[#e9c5bc] bg-[#fff7f4] px-3 py-1 text-xs font-medium text-[#8b4f3f]">✖ {item}</span>
                  ))}
                </div>
                <p className="mt-2 text-xs text-[#8b5f53]">{mustFailed.length > 0 ? mustFailed.join("; ") : "No governed MUST failure is currently confirmed."}</p>
              </section>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-2xl border border-[#f0d9b0] bg-[#fff8ea] p-4">
                <p className="font-semibold text-[#8a6a2f]">Still unknown</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {sectionItems(unknownItems.slice(0, 6).map((item) => item.label), "No unknowns currently surfaced").map((item) => (
                    <span key={`unknown-${item}`} className="rounded-full border border-[#e3d2a6] bg-[#fffdf4] px-3 py-1 text-xs font-medium text-[#7a6847]">? {item}</span>
                  ))}
                </div>
                <p className="mt-2 text-xs text-[#7a6847]">{mustUnknown.length > 0 ? mustUnknown.join("; ") : "Unknown is preserved where evidence is incomplete."}</p>
              </section>

              <section className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4">
                <p className="font-semibold text-[#24425e]">Questions to ask this facility</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {sectionItems(questions.slice(0, 6), "No unanswered questions currently surfaced").map((item) => (
                    <span key={`q-${item}`} className="rounded-full border border-[#d5e1ea] bg-white px-3 py-1 text-xs font-medium text-[#24425e]">{item}</span>
                  ))}
                </div>
              </section>
            </div>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Facility data sections</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {facility.careTypes.length > 0 ? badgeRow("Care & services", facility.careTypes) : null}
                {facility.rehabilitationCapabilities.length > 0 ? badgeRow("Rehabilitation", facility.rehabilitationCapabilities) : null}
                {facility.memory_program !== "UNKNOWN" ? badgeRow("Memory / dementia", [facility.memory_program]) : null}
                {facility.lifestyleCapabilities.length > 0 ? badgeRow("Activities & social life", facility.lifestyleCapabilities) : null}
                {facility.diningCapabilities.length > 0 ? badgeRow("Food & diet", facility.diningCapabilities) : null}
                {facility.housingCapabilities.length > 0 ? badgeRow("Amenities / housing", facility.housingCapabilities) : null}
                {facility.visualIntelligence.lifestyleTags.length > 0 ? badgeRow("Visual intelligence", facility.visualIntelligence.lifestyleTags.map((tag) => tag.label)) : null}
                {facility.matchBadges.length > 0 ? badgeRow("OPTIME tags", facility.matchBadges) : null}
              </div>
            </section>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Location, quality, and evidence</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#24425e]">Quality snapshot</p>
                  <p className="mt-2">Overall: {truthLabel(String(facility.overall_rating ?? "N/A"))}</p>
                  <p>Staffing: {truthLabel(String(facility.staffing_rating ?? "N/A"))}</p>
                  <p>Inspection: {truthLabel(String(facility.inspection_rating ?? "N/A"))}</p>
                  <p>Score breakdown categories: {facility.scoreBreakdown?.length || 0}</p>
                  <p className="mt-1 text-xs text-[#6b6257]">{(facility.scoreBreakdown || []).slice(0, 3).map((item) => `${item.category}: ${item.score}`).join(" · ") || "No score breakdown available"}</p>
                </div>
                <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#24425e]">Location</p>
                  <p className="mt-2">{facility.address}</p>
                  <p>{facility.city}, {facility.state} {facility.zip_code}</p>
                  <p className="mt-2"><a className="text-[#5f7f6b] underline" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${facility.name} ${facility.city}`)}`} target="_blank" rel="noreferrer">Open in maps</a></p>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Sources & evidence</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#24425e]">Governed evidence</p>
                  <p className="mt-2">{facility.intelligenceSnapshot ? `Confidence: ${facility.intelligenceSnapshot.intelligence_confidence}` : "No facility intelligence snapshot available."}</p>
                  <p>Source count: {facility.intelligenceSnapshot?.sources_used.length || 0}</p>
                </div>
                <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#24425e]">Source details</p>
                  <ul className="mt-2 space-y-1 text-xs text-[#5b5b5b]">
                    {(facility.intelligenceSnapshot?.signal_details || []).slice(0, 6).map((detail, index) => (
                      <li key={`${detail.source}-${index}`}>
                        {detail.source} · {detail.provenance} · {detail.collection_timestamp}
                        {detail.raw_url ? <a className="ml-2 text-[#5f7f6b] underline" href={detail.raw_url} target="_blank" rel="noreferrer">source</a> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">Personalized fit summary</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-[#e3d8c8] bg-[#fffaf2] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#2f2a24]">Match</p>
                  <p className="mt-1">{recommendation ? `${Math.round(recommendation.totalScore)}%` : "Not yet ranked"}</p>
                </div>
                <div className="rounded-2xl border border-[#e3d8c8] bg-[#fffaf2] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#2f2a24]">Confidence</p>
                  <p className="mt-1">{recommendation?.confidenceExplanation || "Governed confidence not yet available."}</p>
                </div>
                <div className="rounded-2xl border border-[#e3d8c8] bg-[#fffaf2] p-4 text-sm text-[#4f473d]">
                  <p className="font-semibold text-[#2f2a24]">Next step</p>
                  <p className="mt-1">{recommendation?.report.audit.verificationRequest.nextStepMessage || "Verify the unresolved items with the facility."}</p>
                </div>
              </div>
            </section>
          </div>
        </section>
      </section>
    </main>
  );
}
