"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { VerificationOffer } from "@/app/results/verification-offer";
import { isFinalRecommendation, isPendingRecommendation } from "@/lib/recommendation-eligibility";
import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  compareFacilityParameters,
  DecisionEngineRecommendation,
  DecisionEngineResponse,
  FacilityDetailsData,
  FacilityParameterComparison,
  ParameterTableRow,
  fetchFacilityDetails,
  fetchPatientDecisionRecommendations,
} from "@/lib/api";
import {
  deriveRelevantParameterIds,
  displayParameterLabel,
  isPatientNeed,
  sortRelevantParameterIds,
} from "@/lib/comparison-flow";
import { resolveFacilityImage } from "@/lib/facility-experience";
import { facilityRankingExplanation } from "@/lib/ranking-explanation";
import { EvidenceDetailsModal, type EvidenceDetailsPayload, type EvidenceDetailRecord } from "@/components/compare/evidence-details-modal";
import {
  clearCompareSelection,
  clearFavoriteFacilities,
  clearSearchSession,
  loadDecisionResponseCache,
  loadFavoriteFacilities,
  saveDecisionResponseCache,
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

type MatrixCell = {
  valueLabel: string;
  clickableLabel?: string;
  payload: EvidenceDetailsPayload | null;
};

type MatrixRow = {
  parameterId: string;
  label: string;
  requirementLevel: string;
  section: "PRIORITIES" | "RECOMMENDED";
  cells: MatrixCell[];
};

function formatRawValue(value: unknown): string {
  if (value === null || value === undefined || value === "UNKNOWN" || value === "Not verified") return "Not verified";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  const text = String(value).trim();
  if (!text) return "Not verified";
  if (text === "YES") return "Yes";
  if (text === "NO") return "No";
  return text;
}

function formatParameterValue(parameterId: string, value: unknown): string {
  const formatted = formatRawValue(value);
  if (formatted === "Not verified" || formatted === "Confirm directly with facility") return formatted;
  if (/(_rating$|rating$)/i.test(parameterId) && /^\d+(\.\d+)?$/.test(formatted)) {
    return `${formatted} stars`;
  }
  return formatted;
}

function toMoney(value: unknown): string | null {
  if (typeof value !== "number") return null;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function toEvidenceRecord(entry: NonNullable<ParameterTableRow["evidence_records"]>[number]): EvidenceDetailRecord {
  const provenance = (entry.provenance || {}) as Record<string, unknown>;
  const sourceOrg = typeof provenance.source_family === "string" ? provenance.source_family : undefined;
  const sourceUrl = typeof provenance.source_url === "string" ? provenance.source_url : undefined;
  const evidenceValue = entry.evidence_value;
  const amount = typeof evidenceValue === "number" && evidenceValue > 0 && /fine|penalt|dollar|amount/i.test(String(entry.evidence_text || ""))
    ? toMoney(evidenceValue)
    : null;

  return {
    title: typeof entry.evidence_text === "string" && entry.evidence_text.trim() ? entry.evidence_text : undefined,
    eventType: typeof entry.evidence_strength === "string" ? entry.evidence_strength : undefined,
    date: typeof entry.evidence_date === "string" ? entry.evidence_date : undefined,
    amount: amount || undefined,
    severityScope: [entry.scope, entry.scope_name].filter(Boolean).join(" / ") || undefined,
    description: typeof entry.evidence_value === "string" || typeof entry.evidence_value === "number" ? `Reported value: ${String(entry.evidence_value)}` : undefined,
    status: typeof entry.conflict_status === "string" ? entry.conflict_status : undefined,
    identifier: entry.source_record_id ? String(entry.source_record_id) : undefined,
    sourceOrganization: sourceOrg || (typeof entry.source === "string" ? entry.source : undefined),
    sourceDate: typeof entry.last_verified === "string" ? entry.last_verified : undefined,
    sourceUrl,
  };
}

function isCountStyleParameter(parameterId: string): boolean {
  return /(count|find|complaint|deficien|penalt|fine|inspection|denial)/i.test(parameterId);
}

function isSameValueAcrossCells(cells: MatrixCell[]): boolean {
  const unique = new Set(cells.map((cell) => cell.valueLabel));
  return unique.size <= 1;
}

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
  if (status === "ELIGIBLE") return "text-forest bg-sand border-line";
  if (status === "POTENTIALLY_ELIGIBLE") return "text-[#7a5a2f] bg-sand border-line";
  if (status === "INSUFFICIENT_EVIDENCE") return "text-muted bg-sand border-line";
  return "text-[#8b4f3f] bg-sand border-line";
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
  if (status === "ELIGIBLE") return "Verified care capabilities; admission details need confirmation";
  if (status === "POTENTIALLY_ELIGIBLE") return "Potential fit pending direct verification";
  if (status === "INSUFFICIENT_EVIDENCE") return "Insufficient evidence for critical needs";
  return "Verified critical gaps present";
}

function summarizeVerificationNeeds(recommendation: DecisionEngineRecommendation): string {
  const items = recommendation.explanation.needs_verification || [];
  if (items.length === 0) return "No critical verification items flagged right now.";
  return items.slice(0, 3).join("; ");
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
  const [showMoreCommunities, setShowMoreCommunities] = useState<boolean>(() => searchParams.get("show_more") === "1");
  const [favoriteCanonicalIds, setFavoriteCanonicalIds] = useState<string[]>(() => loadFavoriteFacilities());
  const [hiddenNeedIds, setHiddenNeedIds] = useState<string[]>([]);
  const [showAllTopFiveParameters, setShowAllTopFiveParameters] = useState(false);
  const [topFiveComparisonTable, setTopFiveComparisonTable] = useState<FacilityParameterComparison | null>(null);
  const [facilityImagesByCanonicalId, setFacilityImagesByCanonicalId] = useState<Record<string, RecommendationImageInfo>>({});
  const [brokenImageByCanonicalId, setBrokenImageByCanonicalId] = useState<Record<string, boolean>>({});
  const [imageFetchAttemptedByCanonicalId, setImageFetchAttemptedByCanonicalId] = useState<Record<string, boolean>>({});
  const [activeEvidencePayload, setActiveEvidencePayload] = useState<EvidenceDetailsPayload | null>(null);
  const [mobileCompareFacilityId, setMobileCompareFacilityId] = useState<string>("");

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
        const cached = loadDecisionResponseCache<DecisionEngineResponse>(decisionRequestKey);
        const recommendations = cached || await fetchPatientDecisionRecommendations(JSON.parse(decisionRequestKey) as {
          questionnaire_state: Record<string, unknown>;
          natural_language_query: string;
          limit: number;
        });
        if (!isMounted) return;
        setDecisionResponse(recommendations);
        if (!cached) {
          saveDecisionResponseCache(decisionRequestKey, recommendations);
        }
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
    const params = new URLSearchParams(searchParams.toString());
    if (showMoreCommunities) {
      params.set("show_more", "1");
    } else {
      params.delete("show_more");
    }
    const next = `/results${params.toString() ? `?${params.toString()}` : ""}`;
    const current = `/results${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
    if (next !== current) {
      router.replace(next, { scroll: false });
    }
  }, [router, searchParams, showMoreCommunities]);

  useEffect(() => {
    if (favoriteCanonicalIds.length > 0) {
      saveFavoriteFacilities(favoriteCanonicalIds);
      return;
    }
    clearFavoriteFacilities();
  }, [favoriteCanonicalIds]);

  const recommendations = useMemo(() => (decisionResponse?.results || []).filter(isFinalRecommendation), [decisionResponse?.results]);
  const pendingRecommendations = useMemo(() => (decisionResponse?.results || []).filter(isPendingRecommendation), [decisionResponse?.results]);
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

  useEffect(() => {
    let cancelled = false;

    async function loadTopFiveComparisonTable() {
      if (!decisionResponse || topRecommendations.length === 0) {
        setTopFiveComparisonTable(null);
        return;
      }

      try {
        const payload = await compareFacilityParameters({
          canonical_facility_ids: topRecommendations.map((item) => item.canonical_facility_id),
          need_tags: decisionResponse.patient_needs_profile.need_tags,
          priority_parameter_ids: decisionResponse.patient_needs_profile.priority_parameter_ids,
          profile_key: decisionResponse.patient_needs_profile.profile_key || undefined,
        });
        if (cancelled) return;
        setTopFiveComparisonTable(payload);
      } catch {
        if (cancelled) return;
        setTopFiveComparisonTable(null);
      }
    }

    void loadTopFiveComparisonTable();

    return () => {
      cancelled = true;
    };
  }, [decisionResponse, topRecommendations]);

  const matrixRows = useMemo(() => {
    const rowsByFacilityId = new Map<string, Map<string, ParameterTableRow>>();
    for (const facility of topFiveComparisonTable?.facilities || []) {
      rowsByFacilityId.set(
        facility.canonical_facility_id,
        new Map((facility.rows || []).map((row) => [row.parameter_id, row] as const)),
      );
    }

    const needsById = new Map((decisionResponse?.patient_needs_profile.needs || []).map((need) => [need.parameter_id, need] as const));
    const matrixParameterIds = showAllTopFiveParameters
      ? (topFiveComparisonTable?.parameter_ids || allComparisonParameterIds)
      : visibleTopFiveParameterIds;

    return matrixParameterIds
      .map((parameterId) => {
        const need = needsById.get(parameterId);
        const cells: MatrixCell[] = topRecommendations.map((recommendation) => {
          const row = rowsByFacilityId.get(recommendation.canonical_facility_id)?.get(parameterId);
          const fallbackValue = row?.status_value ?? row?.raw_value ?? "Not verified";
          const valueLabel = formatParameterValue(parameterId, fallbackValue);
          const evidenceRecords = (row?.evidence_records || []).map(toEvidenceRecord);
          const numericValue = typeof fallbackValue === "number" ? fallbackValue : Number.NaN;
          const hasVerifiedSource = Boolean(row && row.source && row.source !== "Not verified");

          let summary = hasVerifiedSource
            ? `${valueLabel} is shown from governed evidence sources checked by OPTIME.`
            : "Not verified in OPTIME's governed evidence sources.";
          let unavailableDetailsMessage: string | undefined;
          let clickableLabel: string | undefined;

          if (isCountStyleParameter(parameterId) && Number.isFinite(numericValue) && Number.isInteger(numericValue) && numericValue >= 0) {
            if (numericValue === 0) {
              summary = "No records found in the verified reporting period.";
              clickableLabel = hasVerifiedSource ? "No records found in the verified reporting period >" : undefined;
            } else {
              summary = `${numericValue} records reported in the verified reporting period.`;
              clickableLabel = `${numericValue} found >`;
              if ((row?.evidence_records || []).length <= 1 && (row?.evidence_count || 0) <= 1) {
                unavailableDetailsMessage = `${numericValue} records reported. Detailed records are not currently available in OPTIME.`;
              }
            }
          } else if (hasVerifiedSource) {
            clickableLabel = "View details >";
          }

          const payload: EvidenceDetailsPayload | null = clickableLabel
            ? {
                facilityName: recommendation.facility_name,
                parameterLabel: displayParameterLabel(parameterId),
                summary,
                records: evidenceRecords,
                unavailableDetailsMessage,
              }
            : null;

          return {
            valueLabel,
            clickableLabel,
            payload,
          };
        });

        const keepVisible = showAllTopFiveParameters || isPatientNeed(decisionResponse?.patient_needs_profile, parameterId) || !isSameValueAcrossCells(cells);
        if (!keepVisible) return null;

        return {
          parameterId,
          label: displayParameterLabel(parameterId),
          requirementLevel: need?.requirement_level || "OPTIME_RECOMMENDED",
          section: need ? "PRIORITIES" : "RECOMMENDED",
          cells,
        } satisfies MatrixRow;
      })
      .filter(Boolean) as MatrixRow[];
  }, [
    allComparisonParameterIds,
    decisionResponse?.patient_needs_profile,
    showAllTopFiveParameters,
    topFiveComparisonTable,
    topRecommendations,
    visibleTopFiveParameterIds,
  ]);

  const priorityMatrixRows = useMemo(() => matrixRows.filter((row) => row.section === "PRIORITIES"), [matrixRows]);
  const recommendedMatrixRows = useMemo(() => matrixRows.filter((row) => row.section === "RECOMMENDED"), [matrixRows]);

  const rankingDifferenceByPair = useMemo(() => {
    const map = new Map<string, NonNullable<DecisionEngineResponse["tie_break_decisions"]>[number]>();
    for (const item of decisionResponse?.tie_break_decisions || []) {
      map.set(`${item.higher_canonical_facility_id}::${item.lower_canonical_facility_id}`, item);
    }
    return map;
  }, [decisionResponse?.tie_break_decisions]);

  const rankingRows = useMemo(() => topRecommendations.map((recommendation) => {
    const reason = facilityRankingExplanation(recommendation);
    return {
      facilityId: recommendation.canonical_facility_id,
      label: "Why this rank",
      text: reason || "An explanation for this ranking is not yet available.",
      payload: reason ? {
        facilityName: recommendation.facility_name,
        parameterLabel: "Ranking explanation",
        summary: reason,
        records: [{ title: "Why this option was ranked here", description: reason, sourceOrganization: "OOmnik recommendation evidence" }],
      } satisfies EvidenceDetailsPayload : null,
    };
  }), [topRecommendations]);

  const mobileCompareReference = topRecommendations[0] || null;
  const effectiveMobileCompareFacilityId =
    mobileCompareFacilityId && topRecommendations.some((item) => item.canonical_facility_id === mobileCompareFacilityId)
      ? mobileCompareFacilityId
      : (topRecommendations[1]?.canonical_facility_id || "");
  const mobileCompareTarget = topRecommendations.find((item) => item.canonical_facility_id === effectiveMobileCompareFacilityId) || topRecommendations[1] || null;
  const mobileCompareRows = useMemo(() => {
    if (!mobileCompareReference || !mobileCompareTarget) return [] as MatrixRow[];
    const referenceIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === mobileCompareReference.canonical_facility_id);
    const targetIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === mobileCompareTarget.canonical_facility_id);
    if (referenceIndex < 0 || targetIndex < 0) return [] as MatrixRow[];

    return priorityMatrixRows
      .filter((row) => row.cells[referenceIndex].valueLabel !== row.cells[targetIndex].valueLabel || row.requirementLevel === "REQUIRED" || row.requirementLevel === "HIGH")
      .slice(0, 6);
  }, [mobileCompareReference, mobileCompareTarget, priorityMatrixRows, topRecommendations]);

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
    // "Back to search" and "New search" both leave this completed case behind via
    // the same home-page destination. Without also clearing state here, a family
    // starting a new intake for a different person inherits the finished case's
    // sessionStorage answers -- mergeSavedState() in questionnaire-context.tsx
    // layers the new free-text story on top of the old structured answers field by
    // field instead of replacing them, so the wrong relationship/age/needs can
    // silently survive into someone else's profile.
    clearSearchSession();
    clearCompareSelection();
    clearFavoriteFacilities();
    resetState();
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

  const renderMatrixCell = (cell: MatrixCell, key: string, wrapperClassName: string) => (
    <div key={key} className={wrapperClassName}>
      <p className="font-semibold text-ink">{cell.valueLabel}</p>
      {cell.clickableLabel && cell.payload ? (
        <button
          type="button"
          onClick={() => setActiveEvidencePayload(cell.payload)}
          className="mt-1 text-left text-xs font-medium text-forest hover:underline"
        >
          {cell.clickableLabel}
        </button>
      ) : null}
    </div>
  );

  const renderRecommendationCard = (
    recommendation: DecisionEngineRecommendation,
    index: number,
    options?: { isMoreResults?: boolean }
  ) => {
    const isMoreResults = options?.isMoreResults || false;
    const isFavorite = favoriteCanonicalIds.includes(recommendation.canonical_facility_id);
    const imageInfo = getRecommendationImage(recommendation);
    const importantStrengths = recommendation.explanation.why_matches.slice(0, isMoreResults ? 4 : 2);
    const importantVerificationItems = recommendation.explanation.needs_verification.slice(0, 3);
    const topBoundary = topRecommendations[TOP_RECOMMENDATION_COUNT - 1] || null;
    const belowTopFiveDecision = topBoundary
      ? rankingDifferenceByPair.get(`${topBoundary.canonical_facility_id}::${recommendation.canonical_facility_id}`)
      : null;
    const whyBelowTopFive = isMoreResults
      ? (belowTopFiveDecision?.reason
          || (recommendation.rank_tie_status === "JOINT_RANK"
            ? "Effectively tied with the primary recommendation set based on currently verified evidence."
            : "Ranked below the primary Top 5 based on governed verified differences currently available."))
      : "";

    return (
      <article
        key={recommendation.canonical_facility_id}
        className={`rounded-2xl border bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)] ${isFavorite ? "border-forest ring-1 ring-forest/30" : "border-line"}`}
      >
        <div className="space-y-3">
          <div className="overflow-hidden rounded-2xl border border-line bg-sand">
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
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-white px-3 py-2 text-xs text-muted">
              <span>{imageInfo.isVerifiedFacilityImage ? `Photo source: ${imageInfo.sourceLabel}` : "No verified facility photo yet"}</span>
              <span>{imageInfo.isVerifiedFacilityImage ? "Facility-specific image" : "General image shown"}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="inline-flex rounded-full bg-sand px-3 py-1 text-xs font-semibold text-forest">{highlightLabel(index)}</p>
              <h3 className="mt-2 text-xl font-semibold text-ink">{recommendation.facility_name}</h3>
              <p className="mt-1 text-sm text-muted">{recommendation.city || "City unknown"}, {recommendation.state || "NV"}</p>
              <p className="mt-1 text-xs font-semibold text-forest">
                {recommendation.rank_display || `#${index + 1}`}
                {recommendation.rank_tie_status === "JOINT_RANK" ? " (Tied)" : ""}
              </p>
            </div>
            <div className="rounded-2xl border border-line bg-sand px-3 py-2 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-forest">Recommendation</p>
              <p className="mt-1 text-sm font-semibold text-forest">{recommendationFitLabel(recommendation.match_band)}</p>
              <p className="text-[10px] text-muted">{eligibilitySummary(recommendation.eligibility_status)}</p>
            </div>
          </div>

          {recommendation.synthetic_pilot && recommendation.monthly_price_basis === "TWO_RESIDENT_TOTAL" ? (
            <p className="text-sm text-muted">Pilot monthly total for two residents: ${Number(recommendation.starting_monthly_price || 0).toLocaleString()}, including verified care and the second-resident fee. The comparison table's current price is the single-resident base.</p>
          ) : null}
          {recommendation.synthetic_pilot && Number(recommendation.entrance_fee || 0) > 0 ? (
            <p className="text-sm text-[#6a5431]">Separate one-time entrance fee: ${Number(recommendation.entrance_fee).toLocaleString()}. This is additional to the monthly budget.</p>
          ) : null}

          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-xl border border-line bg-sand px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">Quality & Safety</p>
              <p className="text-sm font-semibold text-muted">{qualitativeScoreLabel(recommendation.quality_safety_score)}</p>
            </div>
            <div className="rounded-xl border border-line bg-sand px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">Staffing</p>
              <p className="text-sm font-semibold text-muted">{qualitativeScoreLabel(recommendation.staffing_score)}</p>
            </div>
            <div className="rounded-xl border border-line bg-sand px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">Evidence certainty</p>
              <p className="text-sm font-semibold text-muted">{confidenceBand(recommendation.evidence_confidence ?? recommendation.evidence_certainty)}</p>
            </div>
          </div>

          {!isMoreResults ? (
            <div className={`rounded-2xl border px-3 py-2 text-xs font-semibold ${eligibilityTone(recommendation.eligibility_status)}`}>
              Eligibility: {recommendation.eligibility_status}
            </div>
          ) : null}

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-line bg-sand p-3 text-sm text-muted">
              <p className="font-semibold text-muted">Most relevant facts</p>
              <ul className="mt-2 space-y-1">
                {(importantStrengths.length > 0 ? importantStrengths : ["Strong governed match for this patient profile."]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-strength-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-line bg-sand p-3 text-sm text-[#6a5431]">
              <p className="font-semibold text-[#6a5431]">Important items to verify</p>
              <ul className="mt-2 space-y-1">
                {(importantVerificationItems.length > 0 ? importantVerificationItems : ["No critical verification item is currently flagged."]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-verify-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          {isMoreResults ? (
            <div className="rounded-2xl border border-line bg-sand p-3 text-sm text-muted">
              <p className="font-semibold text-muted">Why below Top 5</p>
              <p className="mt-1">{whyBelowTopFive}</p>
            </div>
          ) : null}

          <p className="text-xs text-muted">{recommendation.explanation.availability_note}</p>

          {recommendation.tie_break_explanation_vs_next ? (
            <div className="rounded-xl border border-line bg-sand px-3 py-2 text-xs text-muted">
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
              <span key={`${recommendation.canonical_facility_id}-${badge}`} className="rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-muted">
                {badge}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {recommendation.canonical_facility_id ? (
              <Link href={`/facility/canonical?canonical=${encodeURIComponent(recommendation.canonical_facility_id)}&back=${encodeURIComponent(currentResultsPath)}`} className="inline-flex rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover">
                VIEW DETAILS
              </Link>
            ) : (
              <span className="inline-flex rounded-full border border-line bg-sand px-4 py-2 text-sm font-semibold text-muted">
                VIEW DETAILS (not linked)
              </span>
            )}

            <button
              type="button"
              onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
              className={`inline-flex rounded-full border px-4 py-2 text-sm font-semibold ${isFavorite ? "border-forest bg-sand text-forest" : "border-line bg-white text-muted"}`}
            >
              {isFavorite ? "Favorited" : "Favorite"}
            </button>

            {primaryRecommendation && primaryRecommendation.canonical_facility_id !== recommendation.canonical_facility_id ? (
              <Link href={buildFavoriteVsOptimeHref(recommendation.canonical_facility_id)} className="inline-flex rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-muted hover:bg-sand">
                Compare with OPTIME recommendation
              </Link>
            ) : null}

            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${recommendation.facility_name} ${recommendation.city || "Nevada"}`)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex rounded-full border border-line px-4 py-2 text-sm font-semibold text-muted hover:bg-sand"
            >
              MAP
            </a>
          </div>
        </div>
      </article>
    );
  };

  return (
    <main className="min-h-screen bg-canvas px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-line bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)] oomnik-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-forest">OOmnik Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-ink sm:text-4xl">{recommendations.length ? "Recommended communities" : "Community review"} for {relationship}</h1>
          <p className="mt-2 text-muted">Results are personalized to your current needs profile and governed parameter evidence.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={backToSearch} className="rounded-full border border-line bg-sand px-4 py-2 text-sm font-semibold text-muted transition hover:bg-sand">Back to search</button>
            <button type="button" onClick={startNewSearch} className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white transition hover:bg-forest-hover">New search</button>
          </div>

          {visibleNeeds.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-forest">Active patient needs</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {visibleNeedLabels.map((need) => (
                  <button
                    key={need.parameter_id}
                    type="button"
                    onClick={() => setHiddenNeedIds((current) => [...current, need.parameter_id])}
                    className="rounded-full border border-line bg-sand px-3 py-1 text-sm text-muted hover:bg-sand"
                  >
                    {need.requirement_level}: {need.label} x
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {favoriteTrayItems.length > 0 ? (
            <div className="mt-5 rounded-3xl border border-line bg-sand p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">Favorites</p>
                  <p className="mt-1 text-sm text-muted">Your saved shortlist ({favoriteTrayItems.length})</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={favoriteTrayItems.length < 2}
                    onClick={() => router.push(compareFavoritesHref)}
                    className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-sand"
                  >
                    Compare My Favorites
                  </button>
                  <button
                    type="button"
                    onClick={() => setFavoriteCanonicalIds([])}
                    className="rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-muted hover:bg-sand"
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
                    className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 text-sm text-muted hover:bg-sand"
                  >
                    <span>{facility.facilityName}</span>
                    <span aria-hidden="true">x</span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">Favorites stay with you during normal navigation. Compare uses the same governed comparison engine as every other decision surface.</p>
            </div>
          ) : null}
        </header>

        {!isLoading && apiLoadError ? (
          <section className="mt-6 rounded-3xl border border-line bg-sand p-6 text-sm text-muted">
            <p className="font-semibold">Decision API unavailable</p>
            <p className="mt-2">{apiLoadError}</p>
          </section>
        ) : null}

        {!isLoading && pendingRecommendations.length > 0 ? (
          <section className="mt-6 rounded-3xl border border-line bg-white p-6 oomnik-panel">
            <h2 className="text-xl font-semibold">Candidates awaiting verification</h2>
            <p className="mt-2">These communities are not final recommendations. Required evidence is still unresolved.</p>
            <ul className="mt-3 list-disc pl-5">
              {pendingRecommendations.map((item) => <li key={item.canonical_facility_id}>{item.facility_name}</li>)}
            </ul>
          </section>
        ) : null}

        {!isLoading && recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            <article className="rounded-3xl border border-line bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)] oomnik-panel">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-forest">Results Summary</p>
              <h2 className="mt-2 text-xl font-semibold text-ink">Personalized Recommendations</h2>
              <p className="mt-2 text-sm text-muted">
                Recommendations reflect the needs and preferences currently provided. Availability and unresolved unknowns should still be confirmed directly with each facility.
              </p>
              <p className="mt-2 text-sm text-muted">{decisionResponse?.availability_policy}</p>
              {decisionResponse?.tie_break_policy ? (
                <p className="mt-2 text-xs text-muted">
                  True-tie support is active: {decisionResponse.tie_break_policy.true_tie_label}. Recommendations preserve unknowns as neutral and keep confidence separate from ranking.
                </p>
              ) : null}
            </article>

            <VerificationOffer />

            {topRecommendations.length > 0 ? (
              <section className="rounded-3xl border border-line bg-sand p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">Primary Top 5 recommendations</p>
                    <p className="mt-2 text-sm text-muted">This patient-specific decision table answers which five facilities OPTIME currently recommends, why, and what meaningful differences matter most for this person.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setShowAllTopFiveParameters((current) => !current)}
                      className="rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold text-muted hover:bg-sand"
                    >
                      {showAllTopFiveParameters ? "Show patient-relevant parameters" : `View all ${allComparisonParameterIds.length || 59} parameters`}
                    </button>
                    <Link href={topFiveCompareHref} className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover">
                      Compare all Top 5
                    </Link>
                  </div>
                </div>

                <div className="mt-4 space-y-4 md:hidden">
                  {topRecommendations.map((recommendation, index) => {
                    const facilityIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === recommendation.canonical_facility_id);
                    const rankRow = rankingRows.find((item) => item.facilityId === recommendation.canonical_facility_id);
                    return (
                      <article key={`top5-mobile-${recommendation.canonical_facility_id}`} className="rounded-3xl border border-line bg-white p-4 oomnik-panel">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-forest">{recommendation.rank_display || `#${index + 1}`}</p>
                            <h3 className="mt-1 text-lg font-semibold text-ink">{recommendation.facility_name}</h3>
                            <p className="mt-1 text-sm text-muted">{recommendation.city || "City unknown"}, {recommendation.state || "NV"}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
                            className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-muted"
                          >
                            {favoriteCanonicalIds.includes(recommendation.canonical_facility_id) ? "Saved" : "Save"}
                          </button>
                        </div>

                        <div className="mt-3 space-y-2">
                          {priorityMatrixRows.slice(0, 5).map((row) => {
                            const cell = row.cells[facilityIndex];
                            return (
                              <div key={`mobile-priority-${recommendation.canonical_facility_id}-${row.parameterId}`} className="rounded-xl border border-line bg-sand px-3 py-2 text-sm">
                                <p className="font-medium text-ink">{row.label}</p>
                                <p className="mt-1 text-muted">{cell.valueLabel}</p>
                                {cell.clickableLabel && cell.payload ? (
                                  <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-forest hover:underline">
                                    {cell.clickableLabel}
                                  </button>
                                ) : null}
                              </div>
                            );
                          })}
                        </div>

                        {rankRow ? (
                          <div className="mt-3 rounded-xl border border-line bg-sand px-3 py-2 text-sm text-muted">
                            <p className="font-semibold text-ink">{rankRow.label}</p>
                            <p className="mt-1">{rankRow.text}</p>
                            {rankRow.payload ? (
                              <button type="button" onClick={() => setActiveEvidencePayload(rankRow.payload)} className="mt-1 text-xs font-medium text-forest hover:underline">
                                View details {">"}
                              </button>
                            ) : null}
                          </div>
                        ) : null}
                      </article>
                    );
                  })}

                  {mobileCompareReference && mobileCompareTarget ? (
                    <article className="rounded-3xl border border-line bg-white p-4 oomnik-panel">
                      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">Compare recommendations</p>
                      <p className="mt-1 text-sm text-muted">Focused comparison defaults to #{mobileCompareReference.rank_position || 1} versus your selected alternative.</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {topRecommendations.slice(1).map((item, idx) => (
                          <button
                            key={`mobile-compare-switch-${item.canonical_facility_id}`}
                            type="button"
                            onClick={() => setMobileCompareFacilityId(item.canonical_facility_id)}
                            className={`rounded-full border px-3 py-1 text-xs font-semibold ${mobileCompareTarget.canonical_facility_id === item.canonical_facility_id ? "border-line bg-forest text-white" : "border-line bg-white text-muted"}`}
                          >
                            Compare with #{idx + 2}
                          </button>
                        ))}
                      </div>

                      <div className="mt-3 space-y-2">
                        {mobileCompareRows.map((row) => {
                          const refIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === mobileCompareReference.canonical_facility_id);
                          const targetIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === mobileCompareTarget.canonical_facility_id);
                          const leftCell = row.cells[refIndex];
                          const rightCell = row.cells[targetIndex];
                          return (
                            <div key={`mobile-compare-row-${row.parameterId}`} className="rounded-xl border border-line bg-sand px-3 py-2 text-sm">
                              <p className="font-medium text-ink">{row.label}</p>
                              <p className="mt-1 text-muted">#1: {leftCell.valueLabel}</p>
                              <p className="text-muted">Selected: {rightCell.valueLabel}</p>
                            </div>
                          );
                        })}
                      </div>
                    </article>
                  ) : null}
                </div>

                <div className="mt-4 hidden overflow-x-auto md:block">
                  <table className="min-w-[980px] border-collapse text-xs sm:text-sm">
                    <thead>
                      <tr>
                        <th className="sticky left-0 z-20 w-52 border border-line bg-sand px-3 py-3 text-left text-muted">Decision factor</th>
                        {topRecommendations.map((recommendation, index) => {
                          const imageInfo = getRecommendationImage(recommendation);
                          return (
                            <th key={`top5-head-${recommendation.canonical_facility_id}`} className="w-64 border border-line bg-white p-3 align-top text-left">
                              <div className="overflow-hidden rounded-xl border border-line">
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
                              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-forest">{recommendation.rank_display || `#${index + 1}`}</p>
                              <p className="mt-1 text-sm font-semibold text-ink">{recommendation.facility_name}</p>
                              <p className="mt-1 text-xs text-muted">{recommendation.city || "City unknown"}, {recommendation.state || "NV"}</p>
                              <p className="mt-1 text-xs text-muted">{imageInfo.isVerifiedFacilityImage ? `Image source: ${imageInfo.sourceLabel}` : "No verified facility image available"}</p>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {recommendation.canonical_facility_id ? (
                                  <Link href={`/facility/canonical?canonical=${encodeURIComponent(recommendation.canonical_facility_id)}&back=${encodeURIComponent(currentResultsPath)}`} className="rounded-full bg-forest px-3 py-1 text-xs font-semibold text-white hover:bg-forest-hover">
                                    Facility profile
                                  </Link>
                                ) : null}
                                <button
                                  type="button"
                                  onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
                                  className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-muted hover:bg-sand"
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
                      <tr className="bg-sand">
                        <td className="sticky left-0 z-10 border border-line px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">A. Your priorities</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-a-${recommendation.canonical_facility_id}`} className="border border-line bg-sand" />
                        ))}
                      </tr>
                      {priorityMatrixRows.map((row) => (
                        <tr key={`table-priority-${row.parameterId}`}>
                          <td className="sticky left-0 z-10 border border-line bg-white px-3 py-2 font-semibold text-ink">
                            {row.label}
                            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-muted">{row.requirementLevel}</p>
                          </td>
                          {row.cells.map((cell, index) => (
                            <td key={`cell-priority-${row.parameterId}-${topRecommendations[index].canonical_facility_id}`} className="border border-line bg-white px-3 py-2 align-top text-muted">
                              {renderMatrixCell(cell, `priority-cell-${row.parameterId}-${index}`, "")}
                            </td>
                          ))}
                        </tr>
                      ))}

                      <tr className="bg-sand">
                        <td className="sticky left-0 z-10 border border-line px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">B. OPTIME recommends considering</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-b-${recommendation.canonical_facility_id}`} className="border border-line bg-sand" />
                        ))}
                      </tr>
                      {recommendedMatrixRows.map((row) => (
                        <tr key={`table-recommended-${row.parameterId}`}>
                          <td className="sticky left-0 z-10 border border-line bg-white px-3 py-2 font-semibold text-ink">
                            {row.label}
                            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-muted">OPTIME recommended</p>
                          </td>
                          {row.cells.map((cell, index) => (
                            <td key={`cell-recommended-${row.parameterId}-${topRecommendations[index].canonical_facility_id}`} className="border border-line bg-white px-3 py-2 align-top text-muted">
                              {renderMatrixCell(cell, `recommended-cell-${row.parameterId}-${index}`, "")}
                            </td>
                          ))}
                        </tr>
                      ))}

                      <tr className="bg-sand">
                        <td className="sticky left-0 z-10 border border-line px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted">C. Why this rank</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-c-${recommendation.canonical_facility_id}`} className="border border-line bg-sand" />
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-line bg-white px-3 py-2 font-semibold text-ink">Ranking difference</td>
                        {rankingRows.map((rankRow) => (
                          <td key={`why-${rankRow.facilityId}`} className="border border-line bg-white px-3 py-2 text-muted align-top">
                            <p className="font-semibold text-ink">{rankRow.label}</p>
                            <p className="mt-1">{rankRow.text}</p>
                            {rankRow.payload ? (
                              <button type="button" onClick={() => setActiveEvidencePayload(rankRow.payload)} className="mt-1 text-xs font-medium text-forest hover:underline">
                                View details {">"}
                              </button>
                            ) : null}
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-line bg-white px-3 py-2 font-semibold text-ink">Important things to verify</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`verify-${recommendation.canonical_facility_id}`} className="border border-line bg-white px-3 py-2 text-muted">{summarizeVerificationNeeds(recommendation)}</td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                  <p>Needs verification is neutral. UNKNOWN never means no.</p>
                  <button type="button" onClick={() => setShowAllTopFiveParameters((current) => !current)} className="font-semibold text-forest hover:underline">
                    {showAllTopFiveParameters ? "Return to decision matrix" : `View all ${allComparisonParameterIds.length || 59} parameters`}
                  </button>
                </div>
              </section>
            ) : null}

            <section className="space-y-6">
              {topRecommendations.map((recommendation, index) => (
                <section key={`top-${recommendation.canonical_facility_id}`} className="space-y-4 rounded-3xl border border-line bg-sand p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
                  <div className="rounded-2xl border border-line bg-sand p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-forest">Advisor recommendation</p>
                    <h3 className="mt-1 text-2xl font-semibold text-ink">{recommendationTitle(index)}</h3>
                    <p className="mt-2 text-sm text-muted">{highlightLabel(index)} for {relationship}, explained with patient-specific differences and clear verification next steps.</p>
                  </div>
                  {renderRecommendationCard(recommendation, index)}
                </section>
              ))}
            </section>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <div className="h-px w-full bg-line" />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.14em] text-forest">More Results</p>
                    <p className="mt-1 text-sm text-muted">Additional ranked facilities continue from #{TOP_RECOMMENDATION_COUNT + 1} onward across all relevant ranked results.</p>
                  </div>
                  <button type="button" onClick={() => setShowMoreCommunities((current) => !current)} className="rounded-full border border-line bg-white px-5 py-2 text-sm font-semibold text-muted hover:bg-sand">
                    {showMoreCommunities ? "HIDE MORE RESULTS" : "SHOW MORE RESULTS"}
                  </button>
                </div>
                {showMoreCommunities ? (
                  <section className="grid gap-4 md:grid-cols-2">
                    {remainingRecommendations.map((recommendation, index) =>
                      renderRecommendationCard(recommendation, index + TOP_RECOMMENDATION_COUNT, { isMoreResults: true })
                    )}
                  </section>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-muted">
          {isLoading ? (
            "Loading communities..."
          ) : apiLoadError ? (
            "Decision API unavailable"
          ) : recommendations.length > 0 ? (
            "End of recommendations"
          ) : decisionResponse ? (
            <div className="mx-auto max-w-2xl rounded-2xl border border-line bg-sand p-6 text-left">
              <p className="text-lg font-semibold text-[#5f4827]">No facility is ready to recommend yet.</p>
              <p className="mt-2 leading-6 text-[#6d5b3e]">
                {decisionResponse.total_candidates_scored > 0
                  ? `We reviewed ${decisionResponse.total_candidates_scored} facilities, but none passed every required condition with enough verified evidence. This is not the same as proving that no facility can help.`
                  : decisionResponse.candidate_discovery?.total_facilities_classified
                    ? `We classified ${decisionResponse.candidate_discovery.total_facilities_classified} facilities before ranking. ${decisionResponse.candidate_discovery.relevant_candidate_count} are in potentially relevant care categories, but matching and facility names remain paused until the missing client answer is provided.`
                  : "The request stopped before any facility reached the comparison stage. This can happen when a required client fact or market fact is still unresolved; it does not mean that no facility can help."}
              </p>
              <p className="mt-2 leading-6 text-[#6d5b3e]">Review the answers or ask us to verify the missing clinical and facility evidence before changing the care requirements.</p>
              <Link href="/adaptive-interview?review=1&next=/results" className="mt-4 inline-flex font-semibold text-forest underline underline-offset-4">
                Review the intake answers →
              </Link>
            </div>
          ) : (
            "No verified communities are ready to compare yet."
          )}
        </div>
      </section>

      {favoriteCanonicalIds.length > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-50 px-3 pb-3 md:px-6 md:pb-4">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 rounded-2xl border border-line bg-white/95 px-4 py-3 shadow-[0_14px_40px_-26px_rgba(22,37,53,0.55)] backdrop-blur oomnik-panel">
            <div>
              <p className="text-sm font-semibold text-muted">Favorites selected: {favoriteCanonicalIds.length}</p>
              {favoriteCanonicalIds.length < 2 ? (
                <p className="text-xs text-muted">Select one more facility to compare.</p>
              ) : (
                <p className="text-xs text-muted">Favorites are ready for governed comparison.</p>
              )}
            </div>
            {favoriteCanonicalIds.length >= 2 ? (
              <button
                type="button"
                onClick={() => router.push(compareFavoritesHref)}
                className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover"
              >
                COMPARE MY FAVORITES ({favoriteCanonicalIds.length})
              </button>
            ) : (
              <span className="rounded-full border border-line bg-sand px-4 py-2 text-sm font-semibold text-muted">Select one more facility</span>
            )}
          </div>
        </div>
      ) : null}

      <EvidenceDetailsModal
        isOpen={Boolean(activeEvidencePayload)}
        payload={activeEvidencePayload}
        onClose={() => setActiveEvidencePayload(null)}
      />
    </main>
  );
}
