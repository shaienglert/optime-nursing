"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  compareFacilityParameters,
  type DecisionEngineRecommendation,
  type DecisionEngineResponse,
  type FacilityParameterComparison,
  fetchFacilityProfileV3,
  fetchPatientDecisionRecommendations,
} from "@/lib/api";
import { personLabel, resolveFacilityImage, resolvePriceTruth } from "@/lib/facility-experience";
import { loadFavoriteFacilities, loadPatientCaseId, saveFavoriteFacilities } from "@/lib/search-session";
import { FacilityEvidenceExplorer } from "@/components/facility/facility-evidence-explorer";

type FacilityProfileClientProps = {
  facilityId: string;
  backHref: string;
  backLabel: string;
};

type SectionAnchor = { id: string; label: string };

type ScoreTile = {
  key: string;
  title: string;
  score: number | null;
  details: string[];
};

type FacilityProfileViewData = Awaited<ReturnType<typeof fetchFacilityProfileV3>>;

const SECTION_ANCHORS: SectionAnchor[] = [
  { id: "hero", label: "Hero" },
  { id: "why-optime", label: "Why OPTIME" },
  { id: "recommendation-summary", label: "Recommendation" },
  { id: "overall-scores", label: "Scores" },
  { id: "clinical-care", label: "Clinical" },
  { id: "staffing", label: "Staffing" },
  { id: "safety", label: "Safety" },
  { id: "quality", label: "Quality" },
  { id: "activities", label: "Activities" },
  { id: "dining", label: "Dining" },
  { id: "lifestyle", label: "Lifestyle" },
  { id: "memory-care", label: "Memory Care" },
  { id: "rehabilitation", label: "Rehabilitation" },
  { id: "specialized-programs", label: "Specialized" },
  { id: "languages", label: "Languages" },
  { id: "pricing", label: "Pricing" },
  { id: "availability", label: "Availability" },
  { id: "photos", label: "Photos" },
  { id: "videos", label: "Videos" },
  { id: "neighborhood", label: "Neighborhood" },
  { id: "nearby-hospitals", label: "Hospitals" },
  { id: "nearby-physicians", label: "Physicians" },
  { id: "nearby-pharmacies", label: "Pharmacies" },
  { id: "transportation", label: "Transport" },
  { id: "family-reviews", label: "Reviews" },
  { id: "government-findings", label: "Government" },
  { id: "inspection-history", label: "Inspections" },
  { id: "evidence-explorer", label: "Evidence" },
  { id: "timeline", label: "Timeline" },
  { id: "similar-communities", label: "Similar" },
];

const FALLBACK_IMAGE = "/cms-placeholder.svg";

function matchPercent(recommendation: DecisionEngineRecommendation | null): string {
  if (!recommendation) return "Not yet available";
  return `${Math.round(recommendation.patient_match_score)}%`;
}

function confidenceLabel(value?: number | null): string {
  if (value === null || value === undefined) return "Insufficient evidence";
  if (value >= 80) return "High";
  if (value >= 60) return "Medium";
  return "Low";
}

function scoreLabel(value?: number | null): string {
  if (value === null || value === undefined) return "Unknown";
  if (value >= 80) return "Strong";
  if (value >= 65) return "Good";
  if (value >= 45) return "Mixed";
  return "Needs review";
}

function yesNoUnknown(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text.toUpperCase() === "UNKNOWN" || text.toLowerCase() === "not verified") return "UNKNOWN";
  if (text.toUpperCase() === "YES") return "YES";
  if (text.toUpperCase() === "NO") return "NO";
  return text;
}

function sectionBadges(values: string[], fallback: string): string[] {
  if (values.length > 0) return values;
  return [fallback];
}

function buildMapUrl(lat?: number | null, lng?: number | null, label?: string): string {
  if (lat !== null && lat !== undefined && lng !== null && lng !== undefined) {
    const delta = 0.015;
    const bbox = `${lng - delta}%2C${lat - delta}%2C${lng + delta}%2C${lat + delta}`;
    return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lng}`;
  }
  return `https://www.openstreetmap.org/export/embed.html?bbox=-80.42%2C25.60%2C-80.10%2C25.90&layer=mapnik&marker=25.7617%2C-80.1918&q=${encodeURIComponent(label || "facility")}`;
}

function qualityStars(value?: number | null): string {
  if (value === null || value === undefined) return "Not rated";
  return `${value}/5 stars`;
}

function toScoreTiles(profile: FacilityProfileViewData, recommendation: DecisionEngineRecommendation | null): ScoreTile[] {
  const breakdown = profile.facility_score_breakdown_raw;
  return [
    {
      key: "overall",
      title: "Overall Match",
      score: recommendation ? recommendation.patient_match_score : null,
      details: [recommendation?.match_band?.replace(/_/g, " ") || "No personalized ranking context available."],
    },
    {
      key: "clinical",
      title: "Clinical",
      score: breakdown.medical_quality_score,
      details: Object.entries(breakdown.medical_components || {}).map(([key, value]) => `${key.replace(/_/g, " ")}: ${Math.round(Number(value))}`),
    },
    {
      key: "lifestyle",
      title: "Lifestyle",
      score: recommendation?.domain_breakdown?.lifestyle_fit ?? null,
      details: recommendation?.explanation?.structured?.patient_summary ? ["Personalized lifestyle synthesis available"] : ["Limited personalized lifestyle synthesis available"],
    },
    {
      key: "safety",
      title: "Safety",
      score: breakdown.safety_score,
      details: Object.entries(breakdown.safety_components || {}).map(([key, value]) => `${key.replace(/_/g, " ")}: ${Math.round(Number(value))}`),
    },
    {
      key: "staffing",
      title: "Staffing",
      score: breakdown.staffing_score,
      details: Object.entries(breakdown.staffing_components || {}).map(([key, value]) => `${key.replace(/_/g, " ")}: ${Math.round(Number(value))}`),
    },
    {
      key: "activities",
      title: "Activities",
      score: recommendation?.domain_breakdown?.social_fit ?? null,
      details: profile.facility.lifestyleCapabilities.length > 0 ? profile.facility.lifestyleCapabilities.slice(0, 4) : ["No verified activity details in current payload."],
    },
    {
      key: "dining",
      title: "Dining",
      score: recommendation?.domain_breakdown?.family_fit ?? null,
      details: profile.facility.diningCapabilities.length > 0 ? profile.facility.diningCapabilities.slice(0, 4) : ["No verified dining detail in current payload."],
    },
    {
      key: "environment",
      title: "Environment",
      score: profile.facility.visualIntelligence.visualCoverageScore,
      details: profile.facility.visualIntelligence.lifestyleTags.map((item) => item.label).slice(0, 4),
    },
    {
      key: "value",
      title: "Value",
      score: recommendation?.domain_breakdown?.financial_fit ?? null,
      details: [profile.facility.priceRange || "No verified pricing range available."],
    },
    {
      key: "confidence",
      title: "Confidence",
      score: recommendation?.evidence_confidence ?? null,
      details: [recommendation?.explanation?.structured?.confidence ? JSON.stringify(recommendation.explanation.structured.confidence) : "Confidence narrative not yet available in this view."],
    },
  ];
}

function listDiff(
  baselineCanonicalId: string | null,
  facilityId: string,
  comparison: FacilityParameterComparison | null,
): string[] {
  if (!comparison || !baselineCanonicalId) return [];

  const baseline = comparison.facilities.find((item) => item.canonical_facility_id === baselineCanonicalId);
  const target = comparison.facilities.find((item) => item.canonical_facility_id === facilityId);
  if (!baseline || !target) return [];

  const baselineMap = new Map(baseline.rows.map((row) => [row.parameter_id, yesNoUnknown(row.status_value)]));
  const differences: string[] = [];

  for (const row of target.rows) {
    const current = yesNoUnknown(row.status_value);
    const prior = baselineMap.get(row.parameter_id) || "UNKNOWN";
    if (current !== prior) {
      differences.push(`${row.parameter}: ${prior} -> ${current}`);
    }
    if (differences.length >= 5) break;
  }

  return differences;
}

function SectionCard({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="rounded-2xl bg-white p-6 shadow-[0_18px_55px_-40px_rgba(36,53,74,0.28)]">
      <h2 id={`${id}-title`} className="text-xl font-semibold text-[#203447]">
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function FacilityProfileClient({ facilityId, backHref, backLabel }: FacilityProfileClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();

  const [profile, setProfile] = useState<FacilityProfileViewData | null>(null);
  const [recommendations, setRecommendations] = useState<DecisionEngineResponse | null>(null);
  const [similarComparison, setSimilarComparison] = useState<FacilityParameterComparison | null>(null);
  const [favorites, setFavorites] = useState<string[]>(() => loadFavoriteFacilities());
  const [activeImage, setActiveImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecommendationLoading, setIsRecommendationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patientCaseId] = useState<number | null>(() => loadPatientCaseId());

  const canonicalFromQuery = searchParams.get("canonical")?.trim() || "";

  useEffect(() => {
    let mounted = true;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const payload = await fetchFacilityProfileV3(facilityId);
        if (!mounted) return;
        setProfile(payload);
      } catch (loadError) {
        if (!mounted) return;
        setError(loadError instanceof Error ? loadError.message : "Failed to load facility profile.");
        setProfile(null);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void load();
    return () => {
      mounted = false;
    };
  }, [facilityId]);

  useEffect(() => {
    if (!profile) return;
    const activeProfile = profile;
    let mounted = true;

    async function loadRecommendationContext() {
      setIsRecommendationLoading(true);
      try {
        const naturalLanguageQuery = String(searchParams.get("notes") || state.notes || "").trim();
        const response = await fetchPatientDecisionRecommendations({
          patient_case_id: patientCaseId || undefined,
          questionnaire_state: state,
          natural_language_query: naturalLanguageQuery,
          limit: 25,
        });
        if (!mounted) return;
        setRecommendations(response);

        const canonicalId = activeProfile.facility.canonical_facility_id || canonicalFromQuery;
        if (canonicalId) {
          const similar = response.results
            .filter((item) => item.canonical_facility_id !== canonicalId)
            .slice(0, 3)
            .map((item) => item.canonical_facility_id);

          if (similar.length > 0) {
            const comparison = await compareFacilityParameters({
              canonical_facility_ids: [canonicalId, ...similar],
              need_tags: response.patient_needs_profile.need_tags,
              priority_parameter_ids: response.patient_needs_profile.priority_parameter_ids,
              profile_key: response.patient_needs_profile.profile_key || undefined,
            });
            if (mounted) setSimilarComparison(comparison);
          } else if (mounted) {
            setSimilarComparison(null);
          }
        }
      } catch {
        if (mounted) {
          setRecommendations(null);
          setSimilarComparison(null);
        }
      } finally {
        if (mounted) setIsRecommendationLoading(false);
      }
    }

    void loadRecommendationContext();
    return () => {
      mounted = false;
    };
  }, [canonicalFromQuery, patientCaseId, profile, searchParams, state]);

  useEffect(() => {
    saveFavoriteFacilities(favorites);
  }, [favorites]);

  useEffect(() => {
    if (!profile) return;
    const canonicalId = profile.facility.canonical_facility_id || canonicalFromQuery;
    if (canonicalId) {
      router.prefetch(`/compare?facilities=${encodeURIComponent(canonicalId)}&returnTo=${encodeURIComponent(backHref)}`);
    }
    router.prefetch(backHref);
  }, [backHref, canonicalFromQuery, profile, router]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setActiveImage(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const recommendation = useMemo(() => {
    if (!recommendations || !profile) return null;
    const canonicalId = profile.facility.canonical_facility_id || canonicalFromQuery;
    if (!canonicalId) return null;
    return recommendations.results.find((item) => item.canonical_facility_id === canonicalId) || null;
  }, [canonicalFromQuery, profile, recommendations]);

  const profileFacility = profile?.facility || null;
  const person = personLabel(state.relationship || "your family member");
  const imageTruth = profileFacility ? resolveFacilityImage(profileFacility) : null;
  const priceTruth = profileFacility ? resolvePriceTruth(profileFacility) : null;

  const isFavorite = !!(profileFacility?.canonical_facility_id && favorites.includes(profileFacility.canonical_facility_id));

  const scoreTiles = useMemo(() => {
    if (!profile) return [];
    return toScoreTiles(profile, recommendation);
  }, [profile, recommendation]);

  const topReasons = useMemo(() => recommendation?.explanation?.why_matches || [], [recommendation]);
  const concerns = useMemo(() => recommendation?.explanation?.concerns || [], [recommendation]);
  const verificationNeeds = useMemo(() => recommendation?.explanation?.needs_verification || [], [recommendation]);

  const aiInsights = useMemo(() => {
    const bestFitFor = topReasons.slice(0, 4);
    const mayNotFit = concerns.slice(0, 4);
    const questionsToAsk = verificationNeeds.slice(0, 5);
    const verifyDuringVisit = recommendation?.explanation?.eligibility_reasons?.slice(0, 5) || [];
    const strengths = recommendation?.parameter_badges?.slice(0, 6) || [];

    return {
      bestFitFor,
      mayNotFit,
      questionsToAsk,
      verifyDuringVisit,
      potentialRisks: concerns.slice(0, 3),
      strengths,
    };
  }, [concerns, recommendation, topReasons, verificationNeeds]);

  const similarCommunities = useMemo(() => {
    if (!recommendations || !profileFacility) return [];
    const baselineCanonical = profileFacility.canonical_facility_id || canonicalFromQuery;
    return recommendations.results
      .filter((item) => item.canonical_facility_id !== baselineCanonical)
      .slice(0, 4)
      .map((item) => ({
        ...item,
        differences: listDiff(baselineCanonical || null, item.canonical_facility_id, similarComparison),
      }));
  }, [canonicalFromQuery, profileFacility, recommendations, similarComparison]);

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,#eef6ff_0%,#f8fbff_28%,#ffffff_58%)] px-4 py-8 sm:px-8">
        <section className="mx-auto max-w-7xl space-y-4" aria-live="polite">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={`facility-skeleton-${index}`} className="h-24 animate-pulse rounded-2xl border border-[#d8e3ec] bg-white" />
          ))}
        </section>
      </main>
    );
  }

  if (error || !profile || !profileFacility) {
    return (
      <main className="min-h-screen bg-[#f6f9fc] px-4 py-12 sm:px-8">
        <div className="mx-auto max-w-4xl rounded-3xl border border-[#e3ccd0] bg-white p-6">
          <p className="text-[#8b3d2e]">{error || "Facility not found."}</p>
          <Link href={backHref} className="mt-4 inline-flex rounded-full border border-[#d6e3ec] bg-white px-4 py-2 text-sm font-semibold text-[#294156]">
            {backLabel}
          </Link>
        </div>
      </main>
    );
  }

  const canonicalId = profileFacility.canonical_facility_id || canonicalFromQuery || "";
  const compareHref = canonicalId ? `/compare?facilities=${encodeURIComponent(canonicalId)}&returnTo=${encodeURIComponent(backHref)}` : "/compare";
  const galleryImages = profileFacility.visualIntelligence.galleryImages.length > 0
    ? profileFacility.visualIntelligence.galleryImages
    : [{ category: "facility", url: FALLBACK_IMAGE, source: "CMS Placeholder", collected_at: "" }];

  const latitude = Number(profile.neighborhood?.latitude || profileFacility.latitude || 0) || null;
  const longitude = Number(profile.neighborhood?.longitude || profileFacility.longitude || 0) || null;
  const embeddedMapUrl = buildMapUrl(latitude, longitude, `${profileFacility.name} ${profileFacility.city}`);

  const qualityRows = sectionBadges(
    profile.quality_measures.slice(0, 6).map((item) => `${item.measure_name}: ${item.measure_value ?? "Unknown"}`),
    "No verified quality measure details available.",
  );

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#dcebff_0%,#eff6ff_28%,#ffffff_62%)] px-4 py-6 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-6">
        <header id="hero" className="overflow-hidden rounded-3xl border border-[#c8d9e8] bg-[#f9fcff] shadow-[0_30px_90px_-56px_rgba(30,62,93,0.5)]">
          <div className="grid gap-0 lg:grid-cols-[1.15fr,1fr]">
            <div className="relative min-h-[260px] bg-[#dce9f7]">
              <Image
                src={imageTruth?.url || FALLBACK_IMAGE}
                alt={`${profileFacility.name} hero image`}
                fill
                unoptimized
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 55vw"
                priority
              />
            </div>
            <div className="space-y-4 p-6 sm:p-7">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#3f6f96]">Community profile</p>
                  <h1 className="mt-2 text-3xl font-semibold leading-tight text-[#182c3d]">{profileFacility.name}</h1>
                  <p className="mt-1 text-sm text-[#46617a]">{profileFacility.address}, {profileFacility.city}, {profileFacility.state} {profileFacility.zip_code}</p>
                </div>
                <Link href={backHref} className="rounded-full border border-[#c5d8e6] bg-white px-4 py-2 text-xs font-semibold tracking-[0.08em] text-[#294156] hover:bg-[#f3f9ff]">
                  {backLabel}
                </Link>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-[#d4e3ef] bg-white p-3">
                  <p className="text-[11px] uppercase tracking-[0.1em] text-[#4f6980]">Match</p>
                  <p className="mt-1 text-2xl font-semibold text-[#1f3f57]">{matchPercent(recommendation)}</p>
                </div>
                <div className="rounded-2xl border border-[#d4e3ef] bg-white p-3">
                  <p className="text-[11px] uppercase tracking-[0.1em] text-[#4f6980]">CMS Rating</p>
                  <p className="mt-1 text-lg font-semibold text-[#1f3f57]">{qualityStars(profileFacility.overall_rating)}</p>
                </div>
              </div>

              <p className="text-sm leading-6 text-[#46617a]">{topReasons[0] || `A community worth considering for ${person}, with important details clearly separated into what is known and what still needs confirmation.`}</p>

              <details className="rounded-xl border border-[#d4e3ef] bg-white p-3 text-sm text-[#46617a]">
                <summary className="cursor-pointer font-semibold text-[#294156]">Technical Details</summary>
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  <div><dt className="text-xs">Evidence confidence</dt><dd className="font-semibold">{confidenceLabel(recommendation?.evidence_confidence ?? null)}</dd></div>
                  <div><dt className="text-xs">Runtime version</dt><dd className="font-semibold">{profile.runtime_version || "Unavailable"}</dd></div>
                  <div><dt className="text-xs">Knowledge updated</dt><dd className="font-semibold">{profile.knowledge_updated || profile.runtime_timestamp || "Unavailable"}</dd></div>
                  <div><dt className="text-xs">Identity</dt><dd className="font-semibold">{canonicalId ? "Canonical linked" : "Unresolved"}</dd></div>
                </dl>
              </details>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-full border border-[#c5d8e6] bg-white px-4 py-2 text-xs font-semibold tracking-[0.08em] text-[#294156] hover:bg-[#f3f9ff]"
                  onClick={() => {
                    if (!canonicalId) return;
                    if (isFavorite) {
                      setFavorites((current) => current.filter((item) => item !== canonicalId));
                    } else {
                      setFavorites((current) => Array.from(new Set([...current, canonicalId])));
                    }
                  }}
                  aria-pressed={isFavorite}
                  aria-label="Toggle favorite facility"
                >
                  {isFavorite ? "Saved Favorite" : "Add Favorite"}
                </button>
                <button
                  type="button"
                  className="rounded-full border border-[#c5d8e6] bg-white px-4 py-2 text-xs font-semibold tracking-[0.08em] text-[#294156] hover:bg-[#f3f9ff]"
                  onClick={async () => {
                    const shareUrl = window.location.href;
                    if (navigator.share) {
                      try {
                        await navigator.share({ title: profileFacility.name, url: shareUrl });
                        return;
                      } catch {
                        // Fall through to clipboard copy.
                      }
                    }
                    await navigator.clipboard.writeText(shareUrl);
                  }}
                  aria-label="Share facility profile"
                >
                  Share
                </button>
                <Link href={compareHref} className="rounded-full border border-[#c5d8e6] bg-white px-4 py-2 text-xs font-semibold tracking-[0.08em] text-[#294156] hover:bg-[#f3f9ff]">
                  Compare
                </Link>
                <a
                  href={profileFacility.website || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(profileFacility.name + " " + profileFacility.city)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-[#2f6d8a] bg-[#2f6d8a] px-4 py-2 text-xs font-semibold tracking-[0.08em] text-white hover:bg-[#295e77]"
                >
                  Schedule Visit
                </a>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3" aria-label="Community trust summary">
          <article className="rounded-2xl bg-[#f4faf6] p-5"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#47725a]">What we know</p><p className="mt-2 text-sm leading-6 text-[#355343]">{topReasons[0] || "Verified community facts are available below."}</p></article>
          <article className="rounded-2xl bg-[#fff8ec] p-5"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#806332]">What we still need to confirm</p><p className="mt-2 text-sm leading-6 text-[#665132]">{verificationNeeds[0] || "No urgent verification item is currently flagged."}</p></article>
          <article className="rounded-2xl bg-[#f3f7fb] p-5"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#45637c]">What happens next</p><p className="mt-2 text-sm leading-6 text-[#354f65]">OPTIME can help confirm missing details directly with the community.</p></article>
        </section>

        <nav aria-label="Facility profile sections" className="sticky top-2 z-20 flex flex-wrap gap-2 rounded-2xl border border-[#d3e2ee] bg-white/95 p-3 backdrop-blur">
          {SECTION_ANCHORS.map((anchor) => (
            <a
              key={anchor.id}
              href={`#${anchor.id}`}
              className="rounded-full border border-[#d9e6f0] bg-[#f8fbff] px-3 py-1 text-xs font-semibold text-[#2d4d66] hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2f6d8a]"
            >
              {anchor.label}
            </a>
          ))}
        </nav>

        <SectionCard id="why-optime" title="Why OPTIME Recommends This Community">
          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-2xl border border-[#d6e5ef] bg-[#f6fbff] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#406480]">Patient-specific explanation</p>
              <p className="mt-2 text-sm leading-6 text-[#2b455a]">
                {recommendation?.explanation?.structured?.patient_summary
                  ? JSON.stringify(recommendation.explanation.structured.patient_summary)
                  : recommendation?.explanation?.why_matches?.[0] || `This profile is tailored for ${person}, using governed matching and current verified evidence.`}
              </p>
              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-semibold text-[#235173]">Expandable details</summary>
                <p className="mt-2 text-xs leading-6 text-[#375973]">{recommendation?.explanation?.structured?.confidence ? JSON.stringify(recommendation.explanation.structured.confidence) : "Evidence confidence details are not yet available in this response."}</p>
              </details>
            </article>

            <div className="grid gap-3">
              <article className="rounded-2xl border border-[#cde2d2] bg-[#f3fbf5] p-4">
                <h3 className="text-sm font-semibold text-[#2f6d3e]">Top Reasons</h3>
                <ul className="mt-2 space-y-1 text-xs text-[#376c43]">
                  {sectionBadges(topReasons.slice(0, 5), "No top reasons were provided in this run.").map((item) => (
                    <li key={`reason-${item}`}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="rounded-2xl border border-[#d9e3ec] bg-[#f8fbff] p-4">
                <h3 className="text-sm font-semibold text-[#24425e]">Strongest Matches</h3>
                <ul className="mt-2 space-y-1 text-xs text-[#2c4b66]">
                  {sectionBadges((recommendation?.matched_needs || []).slice(0, 5).map((item) => String(item.parameter_id || item.need_text || "Matched need")), "No verified strongest matches available.").map((item) => (
                    <li key={`strong-${item}`}>{item}</li>
                  ))}
                </ul>
              </article>
              <article className="rounded-2xl border border-[#f0c9bf] bg-[#fff3ef] p-4">
                <h3 className="text-sm font-semibold text-[#8b4f3f]">Potential Concerns</h3>
                <ul className="mt-2 space-y-1 text-xs text-[#8d5a4c]">
                  {sectionBadges(concerns.slice(0, 4), "No critical concerns were surfaced in this run.").map((item) => (
                    <li key={`concern-${item}`}>{item}</li>
                  ))}
                </ul>
              </article>
            </div>
          </div>
        </SectionCard>

        <SectionCard id="recommendation-summary" title="Recommendation Summary">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-[#d6e5ef] bg-[#f8fbff] p-4 text-sm text-[#2e4d66]">
              <p className="font-semibold">Best Fit For</p>
              <p className="mt-1 text-xs">{aiInsights.bestFitFor[0] || "No best-fit headline available."}</p>
            </div>
            <div className="rounded-2xl border border-[#efdab5] bg-[#fff9ec] p-4 text-sm text-[#6f5630]">
              <p className="font-semibold">May Not Fit</p>
              <p className="mt-1 text-xs">{aiInsights.mayNotFit[0] || "No explicit mismatch currently surfaced."}</p>
            </div>
            <div className="rounded-2xl border border-[#d5e4d5] bg-[#f6fcf6] p-4 text-sm text-[#2f5d37]">
              <p className="font-semibold">Availability</p>
              <p className="mt-1 text-xs">{recommendation?.explanation?.availability_note || profile.availability_note}</p>
            </div>
          </div>
          {isRecommendationLoading ? <p className="mt-3 text-xs text-[#567086]">Updating personalized recommendation context...</p> : null}
        </SectionCard>

        <SectionCard id="overall-scores" title="Overall Scores">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {scoreTiles.map((tile) => (
              <details key={tile.key} className="rounded-2xl border border-[#d5e3ee] bg-[#fbfdff] p-4">
                <summary className="cursor-pointer list-none">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#496581]">{tile.title}</p>
                  <p className="mt-1 text-2xl font-semibold text-[#1d3c53]">{tile.score === null ? "N/A" : `${Math.round(tile.score)}`}</p>
                  <p className="mt-1 text-xs text-[#61778f]">{scoreLabel(tile.score)}</p>
                </summary>
                <ul className="mt-3 space-y-1 text-xs text-[#36536d]">
                  {tile.details.length > 0 ? tile.details.map((detail) => <li key={`${tile.key}-${detail}`}>{detail}</li>) : <li>No detail available.</li>}
                </ul>
              </details>
            ))}
          </div>
        </SectionCard>

        <div className="grid gap-6 lg:grid-cols-2">
          <SectionCard id="clinical-care" title="Clinical Care">
            <div className="flex flex-wrap gap-2">
              {sectionBadges(profileFacility.medicalCapabilities, "No verified clinical capabilities available.").map((value) => (
                <span key={`clinical-${value}`} className="rounded-full border border-[#d2e3ef] bg-[#f4faff] px-3 py-1 text-xs font-semibold text-[#2f5f85]">{value}</span>
              ))}
            </div>
          </SectionCard>

          <SectionCard id="staffing" title="Staffing">
            <div className="space-y-2 text-sm text-[#2a455c]">
              <p>RN hours / resident day: {profile.staffing_history[0]?.rn_hours_per_resident_day ?? "Unknown"}</p>
              <p>Total nurse hours / resident day: {profile.staffing_history[0]?.total_nurse_hours_per_resident_day ?? "Unknown"}</p>
              <p>Staffing rating: {qualityStars(profileFacility.staffing_rating)}</p>
              <p>Staff stability index: {profileFacility.intelligenceSnapshot?.staff_stability_index ?? "Unknown"}</p>
              <p>Turnover: Provided only when present in governed data sources.</p>
            </div>
          </SectionCard>

          <SectionCard id="safety" title="Safety">
            <div className="space-y-2 text-sm text-[#2a455c]">
              <p>Inspection rating: {qualityStars(profileFacility.inspection_rating)}</p>
              <p>Total severe deficiencies: {profile.inspection_summary.total_severe_deficiencies as number ?? 0}</p>
              <p>Open issues in historical snapshots: {profile.inspection_summary.open_issue_count as number ?? 0}</p>
              <p>Trend note: {String(profile.inspection_summary.trend_note || "Unavailable")}</p>
            </div>
          </SectionCard>

          <SectionCard id="quality" title="Quality">
            <ul className="space-y-1 text-sm text-[#2a455c]">
              {qualityRows.map((row) => <li key={`quality-row-${row}`}>{row}</li>)}
            </ul>
          </SectionCard>

          <SectionCard id="activities" title="Activities">
            <div className="flex flex-wrap gap-2">
              {sectionBadges(profileFacility.lifestyleCapabilities, "No verified activities currently listed.").map((value) => (
                <span key={`activities-${value}`} className="rounded-full border border-[#d2e3ef] bg-[#f4faff] px-3 py-1 text-xs font-semibold text-[#2f5f85]">{value}</span>
              ))}
            </div>
          </SectionCard>

          <SectionCard id="dining" title="Dining">
            <div className="flex flex-wrap gap-2">
              {sectionBadges(profileFacility.diningCapabilities, "No verified dining details currently listed.").map((value) => (
                <span key={`dining-${value}`} className="rounded-full border border-[#d2e3ef] bg-[#f4faff] px-3 py-1 text-xs font-semibold text-[#2f5f85]">{value}</span>
              ))}
            </div>
          </SectionCard>

          <SectionCard id="lifestyle" title="Lifestyle">
            <div className="flex flex-wrap gap-2">
              {sectionBadges(profileFacility.housingCapabilities, "No verified lifestyle/housing evidence currently listed.").map((value) => (
                <span key={`lifestyle-${value}`} className="rounded-full border border-[#d2e3ef] bg-[#f4faff] px-3 py-1 text-xs font-semibold text-[#2f5f85]">{value}</span>
              ))}
            </div>
          </SectionCard>

          <SectionCard id="memory-care" title="Memory Care">
            <p className="text-sm text-[#2a455c]">Memory program: {profileFacility.memory_program}</p>
            <p className="mt-1 text-xs text-[#5a7489]">UNKNOWN means information is not confirmed yet and is not treated as a negative signal.</p>
          </SectionCard>

          <SectionCard id="rehabilitation" title="Rehabilitation">
            <div className="flex flex-wrap gap-2">
              {sectionBadges(profileFacility.rehabilitationCapabilities, "No verified rehabilitation services currently listed.").map((value) => (
                <span key={`rehab-${value}`} className="rounded-full border border-[#d2e3ef] bg-[#f4faff] px-3 py-1 text-xs font-semibold text-[#2f5f85]">{value}</span>
              ))}
            </div>
          </SectionCard>

          <SectionCard id="specialized-programs" title="Specialized Programs">
            <ul className="space-y-1 text-sm text-[#2a455c]">
              {sectionBadges(profileFacility.matchBadges, "No specialized program indicators currently verified.").map((item) => (
                <li key={`program-${item}`}>{item}</li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard id="languages" title="Languages">
            <p className="text-sm text-[#2a455c]">Language support data comes from governed evidence rows where available.</p>
            <ul className="mt-2 space-y-1 text-xs text-[#3b5a74]">
              {sectionBadges(
                (profile.parameter_table?.rows || [])
                  .filter((row) => row.parameter_id === "languages")
                  .map((row) => `${row.parameter}: ${yesNoUnknown(row.status_value)} (${row.source})`),
                "No verified language-support rows are currently available.",
              ).map((item) => <li key={`lang-${item}`}>{item}</li>)}
            </ul>
          </SectionCard>

          <SectionCard id="pricing" title="Pricing">
            <p className="text-sm text-[#2a455c]">{priceTruth?.label || "Estimated monthly range"}: {priceTruth?.value || "Current pricing not verified"}</p>
            <p className="mt-1 text-xs text-[#5a7489]">Pricing is not treated as a guaranteed quote and requires direct facility confirmation.</p>
          </SectionCard>

          <SectionCard id="availability" title="Availability">
            <p className="text-sm text-[#2a455c]">{profile.availability_note}</p>
          </SectionCard>
        </div>

        <SectionCard id="photos" title="Photos">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {galleryImages.map((image, index) => (
              <button
                type="button"
                key={`gallery-${image.url}-${index}`}
                className="group relative overflow-hidden rounded-2xl border border-[#d5e3ee] bg-[#eef5fb]"
                onClick={() => setActiveImage(image.url)}
              >
                <div className="relative h-36 w-full">
                  <Image src={image.url || FALLBACK_IMAGE} alt={`${profileFacility.name} photo ${index + 1}`} fill unoptimized className="object-cover transition duration-300 group-hover:scale-105" sizes="(max-width: 768px) 50vw, 25vw" loading="lazy" />
                </div>
                <p className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-[#375773]">{image.category || "Facility"}</p>
              </button>
            ))}
          </div>
        </SectionCard>

        <SectionCard id="videos" title="Videos">
          {profile.videos.length > 0 ? (
            <ul className="space-y-2 text-sm text-[#2a455c]">
              {profile.videos.map((video, index) => (
                <li key={`video-${index}`}>
                  <a href={video.url} target="_blank" rel="noreferrer" className="text-[#2f6d8a] underline">{video.title || video.url}</a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[#5b7488]">No verified facility video assets are currently available in the governed media registry.</p>
          )}
        </SectionCard>

        <SectionCard id="neighborhood" title="Neighborhood">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2 text-sm text-[#2a455c]">
              <p>City: {String(profile.neighborhood.city || profileFacility.city || "Unknown")}</p>
              <p>County: {String(profile.neighborhood.county || "Unknown")}</p>
              <p>ZIP: {String(profile.neighborhood.zip_code || profileFacility.zip_code || "Unknown")}</p>
              <p>Coordinates: {latitude && longitude ? `${latitude}, ${longitude}` : "Unavailable"}</p>
            </div>
            <iframe
              title="Facility neighborhood map"
              src={embeddedMapUrl}
              className="h-64 w-full rounded-2xl border border-[#d4e4ef]"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </div>
        </SectionCard>

        <div className="grid gap-6 lg:grid-cols-2">
          <SectionCard id="nearby-hospitals" title="Nearby Hospitals">
            {profile.nearby_hospitals.length > 0 ? (
              <ul className="space-y-1 text-sm text-[#2a455c]">{profile.nearby_hospitals.map((item) => <li key={`hospital-${item.name}`}>{item.name}</li>)}</ul>
            ) : (
              <p className="text-sm text-[#5b7488]">No verified nearby hospital dataset is currently attached to this facility profile payload.</p>
            )}
          </SectionCard>

          <SectionCard id="nearby-physicians" title="Nearby Physicians">
            {profile.nearby_physicians.length > 0 ? (
              <ul className="space-y-1 text-sm text-[#2a455c]">{profile.nearby_physicians.map((item) => <li key={`physician-${item.name}`}>{item.name}</li>)}</ul>
            ) : (
              <p className="text-sm text-[#5b7488]">No verified nearby physician dataset is currently attached to this facility profile payload.</p>
            )}
          </SectionCard>

          <SectionCard id="nearby-pharmacies" title="Nearby Pharmacies">
            {profile.nearby_pharmacies.length > 0 ? (
              <ul className="space-y-1 text-sm text-[#2a455c]">{profile.nearby_pharmacies.map((item) => <li key={`pharmacy-${item.name}`}>{item.name}</li>)}</ul>
            ) : (
              <p className="text-sm text-[#5b7488]">No verified nearby pharmacy dataset is currently attached to this facility profile payload.</p>
            )}
          </SectionCard>

          <SectionCard id="transportation" title="Transportation">
            {profile.transportation.length > 0 ? (
              <ul className="space-y-1 text-sm text-[#2a455c]">{profile.transportation.map((item) => <li key={`transport-${item.name}`}>{item.name}</li>)}</ul>
            ) : (
              <p className="text-sm text-[#5b7488]">No verified third-party transportation stop dataset is currently attached to this facility profile payload.</p>
            )}
          </SectionCard>
        </div>

        <SectionCard id="family-reviews" title="Family Reviews">
          {profile.family_reviews.length > 0 ? (
            <ul className="space-y-3">
              {profile.family_reviews.map((review, index) => (
                <li key={`review-${index}`} className="rounded-2xl border border-[#d5e3ee] bg-[#fbfdff] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#496581]">{review.source} · {review.rating}/5</p>
                  <p className="mt-2 text-sm text-[#2a455c]">{review.review_text || "No review text provided in the source feed."}</p>
                  <p className="mt-1 text-xs text-[#567086]">{review.created_at || "Date unavailable"}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[#5b7488]">No family review records are currently persisted for this facility.</p>
          )}
        </SectionCard>

        <SectionCard id="government-findings" title="Government Findings">
          <ul className="space-y-1 text-sm text-[#2a455c]">
            {sectionBadges(profile.government_findings, "No actionable government findings were surfaced from current evidence rows.").map((item) => <li key={`finding-${item}`}>{item}</li>)}
          </ul>
        </SectionCard>

        <SectionCard id="inspection-history" title="Inspection History">
          {profile.inspections.length > 0 ? (
            <div className="overflow-x-auto rounded-2xl border border-[#d5e3ee] bg-white">
              <table className="min-w-full border-collapse text-xs">
                <thead>
                  <tr>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Date</th>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Rating</th>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Deficiencies</th>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Severity</th>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Fines</th>
                    <th className="border-b border-[#e3edf4] px-3 py-2 text-left text-[#48637b]">Payment Denials</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.inspections.map((row, index) => (
                    <tr key={`inspection-${index}`}>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{row.inspection_date}</td>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{qualityStars(row.inspection_rating)}</td>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{row.deficiency_count}</td>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{row.severity}</td>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{row.fine_amount ? `$${Math.round(row.fine_amount).toLocaleString()}` : "N/A"}</td>
                      <td className="border-b border-[#edf3f8] px-3 py-2">{row.payment_denials_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-[#5b7488]">No inspection history rows are currently available for this facility ID.</p>
          )}
        </SectionCard>

        {profile.parameter_table ? <FacilityEvidenceExplorer parameterTable={profile.parameter_table} /> : null}

        <SectionCard id="timeline" title="Timeline">
          {profile.timeline.length > 0 ? (
            <ol className="space-y-2 text-sm text-[#2a455c]">
              {profile.timeline.slice(0, 40).map((event, index) => (
                <li key={`timeline-${index}`} className="rounded-2xl border border-[#d4e3ef] bg-[#f9fcff] p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#4a6882]">{event.event_type} · {event.timestamp}</p>
                  <p className="mt-1 font-semibold text-[#203d52]">{event.title}</p>
                  <p className="mt-1 text-xs text-[#3d5b74]">{event.summary}</p>
                  <p className="mt-1 text-[11px] text-[#4f6b82]">Source: {event.source}{event.severity ? ` · ${event.severity}` : ""}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-[#5b7488]">Timeline entries are not currently available.</p>
          )}
        </SectionCard>

        <SectionCard id="similar-communities" title="Similar Communities">
          {similarCommunities.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {similarCommunities.map((item) => (
                <article key={item.canonical_facility_id} className="rounded-2xl border border-[#d3e2ed] bg-[#fafdff] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#4a6780]">Rank #{item.rank_position || "N/A"}</p>
                  <h3 className="mt-1 text-lg font-semibold text-[#1f3f57]">{item.facility_name}</h3>
                  <p className="mt-1 text-xs text-[#577088]">{item.match_band.replace(/_/g, " ")} · {Math.round(item.patient_match_score)}%</p>
                  <p className="mt-2 text-xs text-[#375973]">Why ranked differently: {item.tie_break_explanation_vs_next?.why_ranked_above || item.explanation.why_matches[0] || "Differentiator details are limited in this context."}</p>
                  <ul className="mt-2 space-y-1 text-xs text-[#44627c]">
                    {(item.differences.length > 0 ? item.differences : ["No parameter difference set available from current comparison payload."]).map((difference) => (
                      <li key={`${item.canonical_facility_id}-${difference}`}>{difference}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#5b7488]">Similar communities are not available until personalized recommendation context is loaded.</p>
          )}
        </SectionCard>

        <SectionCard id="ai-insights" title="AI Insights">
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <article className="rounded-2xl border border-[#d6e5ef] bg-[#f8fbff] p-4">
              <h3 className="text-sm font-semibold text-[#24425e]">Best Fit For</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#3a5b75]">{sectionBadges(aiInsights.bestFitFor, "No specific best-fit bullets available.").map((item) => <li key={`bestfit-${item}`}>{item}</li>)}</ul>
            </article>
            <article className="rounded-2xl border border-[#efd7ba] bg-[#fff9ef] p-4">
              <h3 className="text-sm font-semibold text-[#7b5e2f]">May Not Fit</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#6f5630]">{sectionBadges(aiInsights.mayNotFit, "No specific mismatch bullets available.").map((item) => <li key={`notfit-${item}`}>{item}</li>)}</ul>
            </article>
            <article className="rounded-2xl border border-[#d5e4d5] bg-[#f5fcf6] p-4">
              <h3 className="text-sm font-semibold text-[#2f5d37]">Questions To Ask</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#396a41]">{sectionBadges(aiInsights.questionsToAsk, "No additional questions currently flagged.").map((item) => <li key={`ask-${item}`}>{item}</li>)}</ul>
            </article>
            <article className="rounded-2xl border border-[#d6e5ef] bg-[#f8fbff] p-4">
              <h3 className="text-sm font-semibold text-[#24425e]">Things To Verify During Visit</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#3a5b75]">{sectionBadges(aiInsights.verifyDuringVisit, "No specific visit verification list currently available.").map((item) => <li key={`verifyvisit-${item}`}>{item}</li>)}</ul>
            </article>
            <article className="rounded-2xl border border-[#f0c9bf] bg-[#fff3ef] p-4">
              <h3 className="text-sm font-semibold text-[#8b4f3f]">Potential Risks</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#8d5a4c]">{sectionBadges(aiInsights.potentialRisks, "No high-confidence risk notes available.").map((item) => <li key={`risk-${item}`}>{item}</li>)}</ul>
            </article>
            <article className="rounded-2xl border border-[#d5e4d5] bg-[#f5fcf6] p-4">
              <h3 className="text-sm font-semibold text-[#2f5d37]">Strengths</h3>
              <ul className="mt-2 space-y-1 text-xs text-[#396a41]">{sectionBadges(aiInsights.strengths, "No structured strength tags were provided.").map((item) => <li key={`strength-${item}`}>{item}</li>)}</ul>
            </article>
          </div>
        </SectionCard>
      </div>

      {activeImage ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#08121ccc] p-4" role="dialog" aria-modal="true" aria-label="Photo viewer" onClick={() => setActiveImage(null)}>
          <button
            type="button"
            onClick={() => setActiveImage(null)}
            className="absolute right-4 top-4 rounded-full border border-white/60 bg-black/40 px-3 py-1 text-sm font-semibold text-white"
          >
            Close
          </button>
          <div className="relative h-[80vh] w-[95vw] max-w-5xl" onClick={(event) => event.stopPropagation()}>
            <Image src={activeImage} alt="Facility photo full screen" fill unoptimized className="object-contain" sizes="95vw" priority />
          </div>
        </div>
      ) : null}
    </main>
  );
}
