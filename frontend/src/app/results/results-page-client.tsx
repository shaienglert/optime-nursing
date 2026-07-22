"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { VerificationOffer } from "@/app/results/verification-offer";
import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  DecisionEngineRecommendation,
  DecisionEngineResponse,
  FacilityDetailsData,
  fetchFacilityDetails,
  fetchPatientDecisionRecommendations,
} from "@/lib/api";
import {
  buildNeedStatusMap,
  deriveRelevantParameterIds,
  displayParameterLabel,
  isPatientNeed,
  sortRelevantParameterIds,
} from "@/lib/comparison-flow";
import { resolveFacilityImage } from "@/lib/facility-experience";
import {
  clearCompareSelection,
  clearFavoriteFacilities,
  clearSearchSession,
  loadFavoriteFacilities,
  saveFavoriteFacilities,
} from "@/lib/search-session";

const TOP_RECOMMENDATION_COUNT = 5;
const NEUTRAL_PLACEHOLDER_IMAGE = "/cms-placeholder.svg";

type RecommendationImageInfo = {
  url: string;
  sourceLabel: string;
  isVerifiedFacilityImage: boolean;
  isFallback: boolean;
};

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function highlightLabel(index: number): string {
  if (index === 0) return "Best Match";
  if (index === 1) return "Strong Alternative";
  if (index === 2) return "Good Alternative";
  return "Worth Considering";
}

function recommendationTitle(index: number): string {
  if (index === 0) return "#1 Recommendation";
  if (index === 1) return "#2 Recommendation";
  if (index === 2) return "#3 Recommendation";
  return `#${index + 1} Recommendation`;
}

function eligibilityTone(status: string): string {
  if (status === "ELIGIBLE") return "text-[#2f6d3e] bg-[#f3fbf5] border-[#cde2d2]";
  if (status === "POTENTIALLY_ELIGIBLE") return "text-[#7a5a2f] bg-[#fff8ea] border-[#f0d9b0]";
  if (status === "INSUFFICIENT_EVIDENCE") return "text-[#24425e] bg-[#f6fbff] border-[#d9e3ec]";
  return "text-[#8b4f3f] bg-[#fff3ef] border-[#f0c9bf]";
}

function qualitativeScoreLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Not enough verified evidence";
  if (value >= 80) return "Strong";
  if (value >= 65) return "Good";
  if (value >= 45) return "Mixed";
  return "Needs caution";
}

function confidenceBand(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Insufficient evidence";
  if (value >= 80) return "High confidence";
  if (value >= 60) return "Medium confidence";
  return "Low confidence";
}

function eligibilitySummary(status: DecisionEngineRecommendation["eligibility_status"]): string {
  if (status === "ELIGIBLE") return "Verified fit for current critical needs";
  if (status === "POTENTIALLY_ELIGIBLE") return "Potential fit pending direct verification";
  if (status === "INSUFFICIENT_EVIDENCE") return "Insufficient evidence for critical needs";
  return "Verified critical gaps present";
}

function comparisonStatusLabel(status: "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"): string {
  if (status === "MATCH") return "Supported";
  if (status === "VERIFIED_GAP") return "Not currently supported";
  return "Needs verification";
}

function matchBandLabel(band: DecisionEngineRecommendation["match_band"]): string {
  if (band === "STRONG_MATCH") return "Best fit";
  if (band === "GOOD_MATCH") return "Strong fit";
  if (band === "PARTIAL_MATCH") return "Good fit";
  return "Limited fit";
}

function summarizeVerificationNeeds(recommendation: DecisionEngineRecommendation): string {
  const items = recommendation.explanation.needs_verification || [];
  if (items.length === 0) return "No critical verification items flagged right now.";
  return items.slice(0, 2).join("; ");
}

function summarizeRankReason(recommendation: DecisionEngineRecommendation, index: number): string {
  const primary = recommendation.explanation.why_matches?.[0] || "Strong governed match for this patient profile.";
  const tie = recommendation.tie_break_explanation_vs_next?.why_ranked_above || "";
  if (index === 0) {
    return primary;
  }
  return tie || primary;
}

function recommendationFitLabel(band: DecisionEngineRecommendation["match_band"]): string {
  if (band === "STRONG_MATCH") return "Best fit";
  if (band === "GOOD_MATCH") return "Strong fit";
  if (band === "PARTIAL_MATCH") return "Good fit";
  return "Needs closer review";
}

function toRecommendationImageInfo(details: FacilityDetailsData | null): RecommendationImageInfo {
  if (!details) {
    return {
      url: NEUTRAL_PLACEHOLDER_IMAGE,
      sourceLabel: "Neutral placeholder",
      isVerifiedFacilityImage: false,
      isFallback: true,
    };
  }

  const imageTruth = resolveFacilityImage(details);
  const hasVerifiedImage = !imageTruth.isPlaceholder && Boolean(imageTruth.url);
  return {
    url: hasVerifiedImage ? imageTruth.url : NEUTRAL_PLACEHOLDER_IMAGE,
    sourceLabel: hasVerifiedImage ? imageTruth.sourceLabel : "Neutral placeholder",
    isVerifiedFacilityImage: hasVerifiedImage,
    isFallback: !hasVerifiedImage,
  };
}

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();

  const [decisionResponse, setDecisionResponse] = useState<DecisionEngineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiLoadError, setApiLoadError] = useState<string | null>(null);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [favoriteCanonicalIds, setFavoriteCanonicalIds] = useState<string[]>(() => loadFavoriteFacilities());
  const [hiddenNeedIds, setHiddenNeedIds] = useState<string[]>([]);
  const [showAllTopFiveParameters, setShowAllTopFiveParameters] = useState(false);
  const [facilityImagesByCanonicalId, setFacilityImagesByCanonicalId] = useState<Record<string, RecommendationImageInfo>>({});
  const [brokenImageByCanonicalId, setBrokenImageByCanonicalId] = useState<Record<string, boolean>>({});
  const [imageFetchAttemptedByCanonicalId, setImageFetchAttemptedByCanonicalId] = useState<Record<string, boolean>>({});

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";
  const notesQuery = searchParams.get("notes") || "";
  const naturalLanguageQuery = (textQuery || notesQuery || state.notes || "").trim();
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );

  useEffect(() => {
    let isMounted = true;
    async function loadFacilities() {
      setIsLoading(true);
      setApiLoadError(null);
      try {
        const recommendations = await fetchPatientDecisionRecommendations(JSON.parse(decisionRequestKey) as {
          questionnaire_state: Record<string, unknown>;
          natural_language_query: string;
          limit: number;
        });
        if (!isMounted) return;
        setDecisionResponse(recommendations);
      } catch (error) {
        if (!isMounted) return;
        setDecisionResponse(null);
        setApiLoadError(error instanceof Error ? error.message : "Unable to load decision recommendations from backend API.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [decisionRequestKey]);

  useEffect(() => {
    if (favoriteCanonicalIds.length > 0) {
      saveFavoriteFacilities(favoriteCanonicalIds);
      return;
    }
    clearFavoriteFacilities();
  }, [favoriteCanonicalIds]);

  const recommendations = useMemo(() => decisionResponse?.results || [], [decisionResponse?.results]);
  const topRecommendations = useMemo(() => recommendations.slice(0, TOP_RECOMMENDATION_COUNT), [recommendations]);
  const remainingRecommendations = useMemo(() => recommendations.slice(TOP_RECOMMENDATION_COUNT), [recommendations]);

  const visibleNeeds = useMemo(() => {
    const allNeeds = decisionResponse?.patient_needs_profile.needs || [];
    return allNeeds.filter((need) => !hiddenNeedIds.includes(need.parameter_id));
  }, [decisionResponse, hiddenNeedIds]);

  const visibleNeedLabels = useMemo(
    () => visibleNeeds.map((need) => ({ ...need, label: displayParameterLabel(need.parameter_id) })),
    [visibleNeeds],
  );

  const recommendationByCanonicalId = useMemo(() => {
    const map = new Map<string, DecisionEngineRecommendation>();
    for (const recommendation of recommendations) {
      map.set(recommendation.canonical_facility_id, recommendation);
    }
    return map;
  }, [recommendations]);

  const favoriteTrayItems = useMemo(
    () => favoriteCanonicalIds.map((facilityId) => {
      const recommendation = recommendationByCanonicalId.get(facilityId);
      return {
        facilityId,
        facilityName: recommendation?.facility_name || facilityId,
      };
    }),
    [favoriteCanonicalIds, recommendationByCanonicalId],
  );
  const currentResultsPath = `/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  const visibleRecommendations = useMemo(() => {
    if (showMoreCommunities) return recommendations;
    return topRecommendations;
  }, [recommendations, showMoreCommunities, topRecommendations]);

  const primaryRecommendation = topRecommendations[0] || null;
  const allComparisonParameterIds = useMemo(() => primaryRecommendation?.comparison_parameter_ids || [], [primaryRecommendation?.comparison_parameter_ids]);
  const relevantParameterIds = useMemo(() => {
    return sortRelevantParameterIds(
      decisionResponse?.patient_needs_profile,
      deriveRelevantParameterIds(decisionResponse?.patient_needs_profile, allComparisonParameterIds)
    );
  }, [allComparisonParameterIds, decisionResponse?.patient_needs_profile]);
  const visibleTopFiveParameterIds = showAllTopFiveParameters ? allComparisonParameterIds : relevantParameterIds;

  useEffect(() => {
    let cancelled = false;

    async function hydrateFacilityImages() {
      const nextDefaults: Record<string, RecommendationImageInfo> = {};
      for (const recommendation of visibleRecommendations) {
        if (!facilityImagesByCanonicalId[recommendation.canonical_facility_id]) {
          nextDefaults[recommendation.canonical_facility_id] = toRecommendationImageInfo(null);
        }
      }

      if (Object.keys(nextDefaults).length > 0) {
        setFacilityImagesByCanonicalId((current) => ({ ...nextDefaults, ...current }));
      }

      const pending = visibleRecommendations.filter(
        (recommendation) =>
          recommendation.facility_profile_id &&
          !imageFetchAttemptedByCanonicalId[recommendation.canonical_facility_id],
      );

      if (pending.length === 0) return;

      const updates = await Promise.all(
        pending.map(async (recommendation) => {
          try {
            const details = await fetchFacilityDetails(String(recommendation.facility_profile_id));
            return [recommendation.canonical_facility_id, toRecommendationImageInfo(details)] as const;
          } catch {
            return [recommendation.canonical_facility_id, toRecommendationImageInfo(null)] as const;
          }
        }),
      );

      if (cancelled) return;
      setImageFetchAttemptedByCanonicalId((current) => {
        const merged = { ...current };
        for (const recommendation of pending) {
          merged[recommendation.canonical_facility_id] = true;
        }
        return merged;
      });
      setFacilityImagesByCanonicalId((current) => {
        const merged = { ...current };
        for (const [canonicalId, imageInfo] of updates) {
          merged[canonicalId] = imageInfo;
        }
        return merged;
      });
    }

    void hydrateFacilityImages();
    return () => {
      cancelled = true;
    };
  }, [visibleRecommendations, facilityImagesByCanonicalId, imageFetchAttemptedByCanonicalId]);

  const topFiveComparisonRows = useMemo(() => {
    const needsById = new Map((decisionResponse?.patient_needs_profile.needs || []).map((need) => [need.parameter_id, need] as const));

    return visibleTopFiveParameterIds
      .map((parameterId) => {
        const need = needsById.get(parameterId);
        const cells = topRecommendations.map((recommendation) => {
          const status = buildNeedStatusMap(recommendation).get(parameterId) || "NOT_VERIFIED";
          return comparisonStatusLabel(status);
        });

        const allEqual = new Set(cells).size === 1;
        const keepVisible = showAllTopFiveParameters || isPatientNeed(decisionResponse?.patient_needs_profile, parameterId) || !allEqual;
        if (!keepVisible) {
          return null;
        }

        return {
          rowId: parameterId,
          label: displayParameterLabel(parameterId),
          requirementLevel: need?.requirement_level || "OPTIME_RECOMMENDED",
          cells,
        };
      })
      .filter(Boolean) as Array<{ rowId: string; label: string; requirementLevel: string; cells: string[] }>;
  }, [decisionResponse?.patient_needs_profile, showAllTopFiveParameters, topRecommendations, visibleTopFiveParameterIds]);

  const topFiveCompareHref = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("facilities", topRecommendations.map((item) => item.canonical_facility_id).join(","));
    params.set("returnTo", currentResultsPath);
    return `/compare?${params.toString()}`;
  }, [currentResultsPath, searchParams, topRecommendations]);

  const compareFavoritesHref = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("facilities", favoriteCanonicalIds.join(","));
    params.set("comparison_mode", "favorites");
    params.set("returnTo", currentResultsPath);
    return `/compare?${params.toString()}`;
  }, [currentResultsPath, favoriteCanonicalIds, searchParams]);

  const startNewSearch = () => {
    clearSearchSession();
    clearCompareSelection();
    clearFavoriteFacilities();
    resetState();
    router.replace("/");
  };

  const backToSearch = () => {
    router.push("/");
  };

  const toggleFavoriteFacility = (canonicalFacilityId: string) => {
    setFavoriteCanonicalIds((current) =>
      current.includes(canonicalFacilityId)
        ? current.filter((item) => item !== canonicalFacilityId)
        : [...current, canonicalFacilityId]
    );
  };

  const buildFavoriteVsOptimeHref = (favoriteFacilityId: string) => {
    if (!primaryRecommendation) return currentResultsPath;
    const params = new URLSearchParams(searchParams.toString());
    params.set("facilities", [favoriteFacilityId, primaryRecommendation.canonical_facility_id].join(","));
    params.set("comparison_mode", "favorite-vs-optime");
    params.set("favorite", favoriteFacilityId);
    params.set("optime_reference", primaryRecommendation.canonical_facility_id);
    params.set("returnTo", currentResultsPath);
    return `/compare?${params.toString()}`;
  };

  const getRecommendationImage = (recommendation: DecisionEngineRecommendation): RecommendationImageInfo => {
    const imageInfo = facilityImagesByCanonicalId[recommendation.canonical_facility_id];
    if (!imageInfo) return toRecommendationImageInfo(null);
    if (brokenImageByCanonicalId[recommendation.canonical_facility_id]) {
      return toRecommendationImageInfo(null);
    }
    return imageInfo;
  };

  const renderRecommendationCard = (recommendation: DecisionEngineRecommendation, index: number) => {
    const isFavorite = favoriteCanonicalIds.includes(recommendation.canonical_facility_id);
    const imageInfo = getRecommendationImage(recommendation);
    const importantStrengths = recommendation.explanation.why_matches.slice(0, 2);
    const importantVerificationItems = recommendation.explanation.needs_verification.slice(0, 2);

    return (
      <article
        key={recommendation.canonical_facility_id}
        className={`rounded-2xl border bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)] ${isFavorite ? "border-[#6f9a86] ring-1 ring-[#6f9a86]/30" : "border-[#e8ddcc]"}`}
      >
        <div className="space-y-3">
          <div className="overflow-hidden rounded-2xl border border-[#dfd4c3] bg-[linear-gradient(140deg,#f5efe3_0%,#ffffff_70%)]">
            <div className="relative h-44 w-full">
              <img
                src={imageInfo.url}
                alt={`${recommendation.facility_name} photo`}
                loading="lazy"
                className="h-full w-full object-cover"
                onError={() => {
                  setBrokenImageByCanonicalId((current) => ({ ...current, [recommendation.canonical_facility_id]: true }));
                }}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#dfd4c3] bg-white px-3 py-2 text-xs text-[#6d655b]">
              <span>{imageInfo.isVerifiedFacilityImage ? `Photo source: ${imageInfo.sourceLabel}` : "No verified facility photo yet"}</span>
              <span>{imageInfo.isVerifiedFacilityImage ? "Facility-specific image" : "Neutral placeholder"}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
              <h3 className="mt-2 text-xl font-semibold text-[#2f2a24]">{recommendation.facility_name}</h3>
              <p className="mt-1 text-sm text-[#6d655b]">{recommendation.city || "City unknown"}, {recommendation.state || "FL"}</p>
              <p className="mt-1 text-xs font-semibold text-[#2f6d3e]">
                {recommendation.rank_display || `#${index + 1}`}
                {recommendation.rank_tie_status === "JOINT_RANK" ? " (Tied)" : ""}
              </p>
            </div>
            <div className="rounded-2xl border border-[#d8e7dc] bg-[#f4fbf6] px-3 py-2 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#3e7a4d]">Recommendation</p>
              <p className="mt-1 text-sm font-semibold text-[#2f6d3e]">{recommendationFitLabel(recommendation.match_band)}</p>
              <p className="text-[10px] text-[#5e7264]">{eligibilitySummary(recommendation.eligibility_status)}</p>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Quality & Safety</p>
              <p className="text-sm font-semibold text-[#24425e]">{qualitativeScoreLabel(recommendation.quality_safety_score)}</p>
            </div>
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Staffing</p>
              <p className="text-sm font-semibold text-[#24425e]">{qualitativeScoreLabel(recommendation.staffing_score)}</p>
            </div>
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f6fbff] px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">Evidence certainty</p>
              <p className="text-sm font-semibold text-[#24425e]">{confidenceBand(recommendation.evidence_confidence ?? recommendation.evidence_certainty)}</p>
            </div>
          </div>

          <div className={`rounded-2xl border px-3 py-2 text-xs font-semibold ${eligibilityTone(recommendation.eligibility_status)}`}>
            Eligibility: {recommendation.eligibility_status}
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fcff] p-3 text-sm text-[#355270]">
              <p className="font-semibold text-[#24425e]">Important strengths</p>
              <ul className="mt-2 space-y-1">
                {(importantStrengths.length > 0 ? importantStrengths : ["Strong governed match for this patient profile."]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-strength-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-[#efe1cb] bg-[#fffaf0] p-3 text-sm text-[#6a5431]">
              <p className="font-semibold text-[#6a5431]">Important items to verify</p>
              <ul className="mt-2 space-y-1">
                {(importantVerificationItems.length > 0 ? importantVerificationItems : ["No critical verification item is currently flagged."]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-verify-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <p className="text-xs text-[#5b5245]">{recommendation.explanation.availability_note}</p>

          {recommendation.tie_break_explanation_vs_next ? (
            <div className="rounded-xl border border-[#d9e3ec] bg-[#f8fcff] px-3 py-2 text-xs text-[#355270]">
              <p className="font-semibold">Tie-break explanation</p>
              <p className="mt-1">{recommendation.tie_break_explanation_vs_next.why_ranked_above}</p>
              {recommendation.tie_break_explanation_vs_next.remained_equal.length > 0 ? (
                <p className="mt-1">Remained equal: {recommendation.tie_break_explanation_vs_next.remained_equal.join(", ")}</p>
              ) : null}
              {recommendation.tie_break_explanation_vs_next.remaining_unknown.length > 0 ? (
                <p className="mt-1">Unknown: {recommendation.tie_break_explanation_vs_next.remaining_unknown.join(", ")}</p>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {recommendation.parameter_badges.slice(0, 6).map((badge) => (
              <span key={`${recommendation.canonical_facility_id}-${badge}`} className="rounded-full border border-[#d9cfbf] bg-white px-3 py-1 text-xs font-medium text-[#5b5245]">
                {badge}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {recommendation.facility_profile_id ? (
              <Link href={`/facility/${recommendation.facility_profile_id}?canonical=${encodeURIComponent(recommendation.canonical_facility_id)}&back=${encodeURIComponent(currentResultsPath)}`} className="inline-flex rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                VIEW DETAILS
              </Link>
            ) : (
              <span className="inline-flex rounded-full border border-[#d9cfbf] bg-[#f9f6ef] px-4 py-2 text-sm font-semibold text-[#8a7d6e]">
                VIEW DETAILS (not linked)
              </span>
            )}

            <button
              type="button"
              onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
              className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isFavorite ? "border-[#6f9a86] bg-[#f1faf3] text-[#2f6d3e]" : "border-[#dccfb9] bg-white text-[#5b5245]"}`}
            >
              {isFavorite ? "Favorited" : "Favorite"}
            </button>

            {primaryRecommendation && primaryRecommendation.canonical_facility_id !== recommendation.canonical_facility_id ? (
              <Link href={buildFavoriteVsOptimeHref(recommendation.canonical_facility_id)} className="inline-flex rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#f6fbff]">
                Compare with OPTIME recommendation
              </Link>
            ) : null}

            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${recommendation.facility_name} ${recommendation.city || "Florida"}`)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]"
            >
              MAP
            </a>
          </div>
        </div>
      </article>
    );
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">Results are personalized to your current needs profile and governed parameter evidence.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={backToSearch} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]">Back to search</button>
            <button type="button" onClick={startNewSearch} className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]">New search</button>
          </div>

          {visibleNeeds.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Active patient needs</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {visibleNeedLabels.map((need) => (
                  <button
                    key={need.parameter_id}
                    type="button"
                    onClick={() => setHiddenNeedIds((current) => [...current, need.parameter_id])}
                    className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-3 py-1 text-sm text-[#534a3d] hover:bg-[#efe8db]"
                  >
                    {need.requirement_level}: {need.label} x
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {favoriteTrayItems.length > 0 ? (
            <div className="mt-5 rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#24425e]">Favorites</p>
                  <p className="mt-1 text-sm text-[#4a6076]">Your saved shortlist ({favoriteTrayItems.length})</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={favoriteTrayItems.length < 2}
                    onClick={() => router.push(compareFavoritesHref)}
                    className="rounded-full bg-[#24425e] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb0c1]"
                  >
                    Compare My Favorites
                  </button>
                  <button
                    type="button"
                    onClick={() => setFavoriteCanonicalIds([])}
                    className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]"
                  >
                    Clear favorites
                  </button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {favoriteTrayItems.map((facility) => (
                  <button
                    key={`tray-${facility.facilityId}`}
                    type="button"
                    onClick={() => setFavoriteCanonicalIds((current) => current.filter((id) => id !== facility.facilityId))}
                    className="inline-flex items-center gap-2 rounded-full border border-[#cddce5] bg-white px-3 py-1.5 text-sm text-[#24425e] hover:bg-[#edf6fb]"
                  >
                    <span>{facility.facilityName}</span>
                    <span aria-hidden="true">x</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-[#4a6076]">Favorites stay with you during normal navigation. Compare uses the same governed comparison engine as every other decision surface.</p>
            </div>
          ) : null}
        </header>

        {!isLoading && apiLoadError ? (
          <section className="mt-6 rounded-3xl border border-[#e5b7b7] bg-[#fff4f4] p-6 text-sm text-[#7a2f2f]">
            <p className="font-semibold">Decision API unavailable</p>
            <p className="mt-2">{apiLoadError}</p>
          </section>
        ) : null}

        {!isLoading && recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Personalized Recommendations</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                Recommendations reflect the needs and preferences currently provided. Availability and unresolved unknowns should still be confirmed directly with each facility.
              </p>
              <p className="mt-2 text-sm text-[#5c5347]">{decisionResponse?.availability_policy}</p>
              {decisionResponse?.tie_break_policy ? (
                <p className="mt-2 text-xs text-[#5c5347]">
                  True-tie support is active: {decisionResponse.tie_break_policy.true_tie_label}. Recommendations preserve unknowns as neutral and keep confidence separate from ranking.
                </p>
              ) : null}
            </article>

            <VerificationOffer />

            {topRecommendations.length > 0 ? (
              <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Primary Top 5 recommendations</p>
                    <p className="mt-2 text-sm text-[#4a6076]">This patient-specific decision table answers which five facilities OPTIME currently recommends, why, and what meaningful differences matter most for this person.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setShowAllTopFiveParameters((current) => !current)}
                      className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]"
                    >
                      {showAllTopFiveParameters ? "Show patient-relevant parameters" : `View all ${allComparisonParameterIds.length || 59} parameters`}
                    </button>
                    <Link href={topFiveCompareHref} className="rounded-full bg-[#24425e] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d3650]">
                      Compare all Top 5
                    </Link>
                  </div>
                </div>

                <div className="mt-4 md:hidden space-y-4">
                  {topRecommendations.map((recommendation, index) => (
                    <article key={`top5-mobile-${recommendation.canonical_facility_id}`} className="rounded-2xl border border-[#d9e3ec] bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#5f7f6b]">{recommendation.rank_display || `#${index + 1}`}</p>
                          <h3 className="mt-1 text-lg font-semibold text-[#2f2a24]">{recommendation.facility_name}</h3>
                          <p className="mt-1 text-sm text-[#6d655b]">{recommendation.city || "City unknown"}, {recommendation.state || "FL"}</p>
                        </div>
                        <span className="rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{recommendationFitLabel(recommendation.match_band)}</span>
                      </div>
                      <div className="mt-3 space-y-2">
                        {topFiveComparisonRows.map((row) => {
                          const cellIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === recommendation.canonical_facility_id);
                          if (cellIndex === -1) return null;
                          return (
                            <div key={`mobile-row-${recommendation.canonical_facility_id}-${row.rowId}`} className="flex items-start justify-between gap-3 rounded-xl border border-[#eef3f7] bg-[#fbfdff] px-3 py-2 text-sm">
                              <div>
                                <p className="font-medium text-[#2f2a24]">{row.label}</p>
                                <p className="text-[10px] uppercase tracking-[0.08em] text-[#6d655b]">{row.requirementLevel === "OPTIME_RECOMMENDED" ? "OPTIME recommended" : row.requirementLevel}</p>
                              </div>
                              <span className="text-right font-semibold text-[#355270]">{row.cells[cellIndex]}</span>
                            </div>
                          );
                        })}
                      </div>
                      <div className="mt-3 rounded-xl border border-[#eef3f7] bg-[#fbfdff] px-3 py-2 text-sm text-[#4f473d]">
                        <p className="font-semibold text-[#2f2a24]">Why this rank</p>
                        <p className="mt-1">{summarizeRankReason(recommendation, index)}</p>
                      </div>
                    </article>
                  ))}
                </div>

                <div className="mt-4 hidden overflow-x-auto md:block">
                  <table className="min-w-[980px] border-collapse text-xs sm:text-sm">
                    <thead>
                      <tr>
                        <th className="sticky left-0 z-20 w-52 border border-[#d9e3ec] bg-[#f6fbff] px-3 py-3 text-left text-[#24425e]">Patient priorities</th>
                        {topRecommendations.map((recommendation, index) => {
                          const imageInfo = getRecommendationImage(recommendation);
                          return (
                            <th key={`top5-head-${recommendation.canonical_facility_id}`} className="w-64 border border-[#d9e3ec] bg-white p-3 align-top text-left">
                              <div className="overflow-hidden rounded-xl border border-[#e2d8c8]">
                                <img
                                  src={imageInfo.url}
                                  alt={`${recommendation.facility_name} image`}
                                  loading="lazy"
                                  className="h-28 w-full object-cover"
                                  onError={() => {
                                    setBrokenImageByCanonicalId((current) => ({ ...current, [recommendation.canonical_facility_id]: true }));
                                  }}
                                />
                              </div>
                              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#5f7f6b]">{recommendation.rank_display || `#${index + 1}`}</p>
                              <p className="mt-1 text-sm font-semibold text-[#2f2a24]">{recommendation.facility_name}</p>
                              <p className="mt-1 text-xs text-[#6d655b]">{recommendation.city || "City unknown"}, {recommendation.state || "FL"}</p>
                              <p className="mt-1 text-xs text-[#6d655b]">{imageInfo.isVerifiedFacilityImage ? `Photo: ${imageInfo.sourceLabel}` : "Photo: neutral fallback"}</p>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {recommendation.facility_profile_id ? (
                                  <Link href={`/facility/${recommendation.facility_profile_id}?canonical=${encodeURIComponent(recommendation.canonical_facility_id)}&back=${encodeURIComponent(currentResultsPath)}`} className="rounded-full bg-[#6f9a86] px-3 py-1 text-xs font-semibold text-white hover:bg-[#618a77]">
                                    Facility profile
                                  </Link>
                                ) : null}
                                <button
                                  type="button"
                                  onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
                                  className="rounded-full border border-[#cddce5] bg-white px-3 py-1 text-xs font-semibold text-[#24425e] hover:bg-[#edf6fb]"
                                >
                                  {favoriteCanonicalIds.includes(recommendation.canonical_facility_id) ? "Favorited" : "Favorite"}
                                </button>
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Overall recommendation</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`overall-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{recommendationFitLabel(recommendation.match_band)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Patient match</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`match-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{matchBandLabel(recommendation.match_band)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Quality &amp; Safety</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`quality-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{qualitativeScoreLabel(recommendation.quality_safety_score)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Staffing</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`staff-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{qualitativeScoreLabel(recommendation.staffing_score)}</td>
                        ))}
                      </tr>
                      {topFiveComparisonRows.map((row) => (
                        <tr key={`table-${row.rowId}`}>
                          <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">
                            {row.label}
                            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[#6d655b]">{row.requirementLevel}</p>
                          </td>
                          {row.cells.map((cell, index) => (
                            <td key={`cell-${row.rowId}-${topRecommendations[index].canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{cell}</td>
                          ))}
                        </tr>
                      ))}
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Why this rank</td>
                        {topRecommendations.map((recommendation, index) => (
                          <td key={`why-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{summarizeRankReason(recommendation, index)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Important things to verify</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`verify-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d]">{summarizeVerificationNeeds(recommendation)}</td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-[#4a6076]">Needs verification is neutral. UNKNOWN never means no. Expanded comparison preserves the full canonical {allComparisonParameterIds.length || 59}-parameter view.</p>
              </section>
            ) : null}

            <section className="space-y-6">
              {topRecommendations.map((recommendation, index) => (
                <section key={`top-${recommendation.canonical_facility_id}`} className="space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdf9] p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
                  <div className="rounded-2xl border border-[#d9cfbf] bg-[linear-gradient(120deg,#f7efe0_0%,#fbf6ec_55%,#ffffff_100%)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Advisor recommendation</p>
                    <h3 className="mt-1 text-2xl font-semibold text-[#2f2a24]">{recommendationTitle(index)}</h3>
                    <p className="mt-2 text-sm text-[#5f5548]">{highlightLabel(index)} for {relationship}, explained with patient-specific differences and clear verification next steps.</p>
                  </div>
                  {renderRecommendationCard(recommendation, index)}
                </section>
              ))}
            </section>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <div className="h-px w-full bg-[linear-gradient(90deg,transparent,#d9cfbf,transparent)]" />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">More Results</p>
                    <p className="mt-1 text-sm text-[#5c5347]">Additional ranked facilities continue from #{TOP_RECOMMENDATION_COUNT + 1} onward.</p>
                  </div>
                  <button type="button" onClick={() => setShowMoreCommunities((current) => !current)} className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]">
                    {showMoreCommunities ? "Hide more results" : "Show more results"}
                  </button>
                </div>
                {showMoreCommunities ? (
                  <section className="grid gap-4 md:grid-cols-2">
                    {remainingRecommendations.map((recommendation, index) => renderRecommendationCard(recommendation, index + TOP_RECOMMENDATION_COUNT))}
                  </section>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">
          {isLoading ? "Loading communities..." : apiLoadError ? "Decision API unavailable" : recommendations.length > 0 ? "End of recommendations" : "No communities available"}
        </div>
      </section>
    </main>
  );
}
