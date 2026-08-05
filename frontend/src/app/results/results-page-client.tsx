"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { VerificationOffer } from "@/app/results/verification-offer";
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
import { EvidenceDetailsModal, type EvidenceDetailsPayload, type EvidenceDetailRecord } from "@/components/compare/evidence-details-modal";
import {
  clearAssessmentData,
  clearFavoriteFacilities,
  loadDecisionResponseCache,
  loadPatientCaseId,
  loadFavoriteFacilities,
  saveDecisionResponseCache,
  saveFavoriteFacilities,
  saveRecommendationSession,
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
  if (value === null || value === undefined || value === "UNKNOWN" || value === "Not verified") return "We're verifying this now.";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  const text = String(value).trim();
  if (!text) return "We're verifying this now.";
  if (text === "YES") return "Yes";
  if (text === "NO") return "No";
  return text;
}

function formatParameterValue(parameterId: string, value: unknown): string {
  const formatted = formatRawValue(value);
  if (formatted === "We're verifying this now." || formatted === "Confirm directly with facility") return formatted;
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

function eligibilitySummary(status: DecisionEngineRecommendation["eligibility_status"]): string {
  if (status === "ELIGIBLE") return "Verified fit for current critical needs";
  if (status === "POTENTIALLY_ELIGIBLE") return "Potential fit pending direct verification";
  if (status === "INSUFFICIENT_EVIDENCE") return "Insufficient evidence for critical needs";
  return "Verified critical gaps present";
}

function summarizeVerificationNeeds(recommendation: DecisionEngineRecommendation): string {
  const items = recommendation.explanation.needs_verification || [];
  if (items.length === 0) return "No critical verification items flagged right now.";
  return items.slice(0, 2).join("; ");
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
      sourceLabel: "Official community photography is currently being verified.",
      isVerifiedFacilityImage: false,
      isFallback: true,
    };
  }

  const imageTruth = resolveFacilityImage(details);
  const hasVerifiedImage = !imageTruth.isPlaceholder && Boolean(imageTruth.url);
  return {
    url: hasVerifiedImage ? imageTruth.url : NEUTRAL_PLACEHOLDER_IMAGE,
    sourceLabel: hasVerifiedImage ? imageTruth.sourceLabel : "Official community photography is currently being verified.",
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
  const [visibleMoreCount, setVisibleMoreCount] = useState<number>(12);
  const [favoriteCanonicalIds, setFavoriteCanonicalIds] = useState<string[]>(() => loadFavoriteFacilities());
  const [hiddenNeedIds, setHiddenNeedIds] = useState<string[]>([]);
  const [showAllTopFiveParameters, setShowAllTopFiveParameters] = useState(false);
  const [topFiveComparisonTable, setTopFiveComparisonTable] = useState<FacilityParameterComparison | null>(null);
  const [facilityImagesByCanonicalId, setFacilityImagesByCanonicalId] = useState<Record<string, RecommendationImageInfo>>({});
  const [facilityDetailsByCanonicalId, setFacilityDetailsByCanonicalId] = useState<Record<string, FacilityDetailsData>>({});
  const [brokenImageByCanonicalId, setBrokenImageByCanonicalId] = useState<Record<string, boolean>>({});
  const [imageFetchAttemptedByCanonicalId, setImageFetchAttemptedByCanonicalId] = useState<Record<string, boolean>>({});
  const [activeEvidencePayload, setActiveEvidencePayload] = useState<EvidenceDetailsPayload | null>(null);
  const [mobileCompareFacilityId, setMobileCompareFacilityId] = useState<string>("");
  const [patientCaseId] = useState<number | null>(() => loadPatientCaseId());

  const relationship = relationshipCopy(searchParams.get("relationship") || state.relationship || "your loved one");
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";
  const notesQuery = searchParams.get("notes") || "";
  const naturalLanguageQuery = (textQuery || notesQuery || state.notes || "").trim();
  const decisionRequestKey = useMemo(
    () => JSON.stringify({ patient_case_id: patientCaseId, questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [patientCaseId, state, naturalLanguageQuery],
  );

  useEffect(() => {
    let isMounted = true;
    async function loadFacilities() {
      setIsLoading(true);
      setApiLoadError(null);
      try {
        const cached = loadDecisionResponseCache<DecisionEngineResponse>(decisionRequestKey);
        const recommendations = cached || await fetchPatientDecisionRecommendations(JSON.parse(decisionRequestKey) as {
          patient_case_id?: number;
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
            return [recommendation.canonical_facility_id, toRecommendationImageInfo(details), details] as const;
          } catch {
            return [recommendation.canonical_facility_id, toRecommendationImageInfo(null), null] as const;
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
      setFacilityDetailsByCanonicalId((current) => {
        const merged = { ...current };
        for (const [canonicalId, , details] of updates) {
          if (details) merged[canonicalId] = details;
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
    type TieBreakDecision = NonNullable<DecisionEngineResponse["tie_break_decisions"]>[number];
    const map = new Map<string, TieBreakDecision>();
    for (const item of decisionResponse?.tie_break_decisions || []) {
      map.set(`${item.higher_canonical_facility_id}::${item.lower_canonical_facility_id}`, item);
    }
    return map;
  }, [decisionResponse?.tie_break_decisions]);

  const rankingRows = useMemo(() => {
    return topRecommendations.map((recommendation, index) => {
      if (index === 0) {
        const leadReason = recommendation.tie_break_explanation_vs_next?.why_ranked_above || recommendation.explanation.why_matches?.[0] || "Top ranked from governed patient-specific evidence.";
        return {
          facilityId: recommendation.canonical_facility_id,
          label: "Why this rank",
          text: leadReason,
          payload: {
            facilityName: recommendation.facility_name,
            parameterLabel: "Ranking difference",
            summary: leadReason,
            records: [
              {
                title: "Why #1 leads",
                description: leadReason,
                sourceOrganization: "OPTIME decision engine explainability",
              },
            ],
          } satisfies EvidenceDetailsPayload,
        };
      }

      const above = topRecommendations[index - 1];
      const decision = rankingDifferenceByPair.get(`${above.canonical_facility_id}::${recommendation.canonical_facility_id}`);
      if (!decision) {
        return {
          facilityId: recommendation.canonical_facility_id,
          label: "True tie",
          text: "No governed ranking difference was verified at this comparison step.",
          payload: null,
        };
      }

      const summary = decision.reason || `${recommendation.facility_name} is below ${above.facility_name} because of a governed difference in ${decision.decision_dimension}.`;
      return {
        facilityId: recommendation.canonical_facility_id,
        label: "Ranking difference",
        text: summary,
        payload: {
          facilityName: recommendation.facility_name,
          parameterLabel: "Ranking difference",
          summary,
          records: [
            {
              title: `Why below ${above.facility_name}`,
              description: summary,
              eventType: decision.decision_dimension,
              sourceOrganization: "OPTIME decision engine explainability",
            },
          ],
        } satisfies EvidenceDetailsPayload,
      };
    });
  }, [rankingDifferenceByPair, topRecommendations]);

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
    clearAssessmentData();
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

  const renderMatrixCell = (cell: MatrixCell, key: string, wrapperClassName: string) => (
    <div key={key} className={wrapperClassName}>
      <p className="font-semibold text-[#2f2a24]">{cell.valueLabel}</p>
      {cell.clickableLabel && cell.payload ? (
        <button
          type="button"
          onClick={() => setActiveEvidencePayload(cell.payload)}
          className="mt-1 text-left text-xs font-medium text-[#1f5f94] hover:underline"
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
    const importantVerificationItems = recommendation.explanation.needs_verification.slice(0, 2);
    const topReasons = recommendation.explanation.why_matches.slice(0, 5);
    const concerns = recommendation.explanation.concerns.slice(0, 5);
    const structured = recommendation.explanation.structured;
    const runtimeVersion = recommendation.runtime_version || structured?.runtime_version || decisionResponse?.runtime_version || "unknown";
    const runtimeTimestamp = recommendation.runtime_timestamp || structured?.runtime_timestamp || decisionResponse?.runtime_timestamp || "unknown";
    const knowledgeUpdated = structured?.freshness?.knowledge_timestamp || runtimeTimestamp;
    const details = facilityDetailsByCanonicalId[recommendation.canonical_facility_id];
    const activities = details?.lifestyleCapabilities || [];
    const languages = [
      details?.hebrew_support === "YES" ? "Hebrew support" : "",
      ...(details?.matchBadges || []).filter((badge) => /language|hebrew|spanish|english/i.test(String(badge))),
    ].filter(Boolean);
    const careLevels = details?.careTypes || [];
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
              <span>{imageInfo.isVerifiedFacilityImage ? `Photo source: ${imageInfo.sourceLabel}` : "Official community photography is currently being verified."}</span>
              <span>{imageInfo.isVerifiedFacilityImage ? "Facility-specific image" : "Photo verification in progress"}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{index === 0 ? "#1 Recommended Community" : highlightLabel(index)}</p>
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

          <div className="rounded-2xl bg-[#f4f8f5] p-5">
            <h4 className="text-base font-semibold text-[#254c3a]">Why OPTIME recommends this community</h4>
            <ul className="mt-3 grid gap-2 text-sm leading-6 text-[#3f5549] sm:grid-cols-2">
              {(topReasons.length ? topReasons : ["A strong fit for the needs your family shared."]).slice(0, 6).map((item) => (
                <li key={`${recommendation.canonical_facility_id}-concierge-${item}`} className="flex gap-2"><span aria-hidden="true" className="text-[#4f8068]">•</span><span>{item}</span></li>
              ))}
            </ul>
          </div>

          <details className="rounded-2xl border border-[#dde5e1] bg-white p-4">
            <summary className="cursor-pointer text-sm font-semibold text-[#365446]">Technical Evidence</summary>
            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl bg-[#f7f9f8] px-3 py-2 text-xs"><p className="font-semibold">Overall match</p><p className="mt-1">{recommendation.patient_match_score}%</p></div>
              <div className="rounded-xl bg-[#f7f9f8] px-3 py-2 text-xs"><p className="font-semibold">Evidence confidence</p><p className="mt-1">{Math.round(structured?.confidence_score || recommendation.evidence_confidence || 0)}%</p></div>
              <div className="rounded-xl bg-[#f7f9f8] px-3 py-2 text-xs"><p className="font-semibold">Runtime version</p><p className="mt-1">{runtimeVersion}</p></div>
              <div className="rounded-xl bg-[#f7f9f8] px-3 py-2 text-xs"><p className="font-semibold">Knowledge updated</p><p className="mt-1">{knowledgeUpdated || "Unknown"}</p></div>
            </div>
            {!isMoreResults ? <p className={`mt-3 rounded-xl border px-3 py-2 text-xs font-semibold ${eligibilityTone(recommendation.eligibility_status)}`}>Eligibility: {recommendation.eligibility_status}</p> : null}
          </details>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fcff] p-3 text-sm text-[#355270]">
              <p className="font-semibold text-[#24425e]">Most relevant facts</p>
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

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-3 text-sm text-[#2d4c43]">
              <p className="font-semibold">Top 5 reasons</p>
              <ul className="mt-2 space-y-1">
                {(topReasons.length ? topReasons : ["No top reasons available"]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-top-reason-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-[#f0d7cf] bg-[#fff6f3] p-3 text-sm text-[#6b4137]">
              <p className="font-semibold">Potential concerns</p>
              <ul className="mt-2 space-y-1">
                {(concerns.length ? concerns : ["No major concerns currently surfaced"]).map((item) => (
                  <li key={`${recommendation.canonical_facility_id}-concern-${item}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-[#e4ebf3] bg-[#f8fbff] px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Price</p><p className="mt-1">{details?.priceRange || "Awaiting confirmation."}</p></div>
            <div className="rounded-xl border border-[#e4ebf3] bg-[#f8fbff] px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Distance</p><p className="mt-1">{recommendation.city ? `Near ${recommendation.city}` : "Distance not calculated"}</p></div>
            <div className="rounded-xl border border-[#e4ebf3] bg-[#f8fbff] px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Availability</p><p className="mt-1">Confirm directly with facility</p></div>
            <div className="rounded-xl border border-[#e4ebf3] bg-[#f8fbff] px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Inspection Summary</p><p className="mt-1">{qualitativeScoreLabel(recommendation.quality_safety_score)}</p></div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-[#e4ebf3] bg-white px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Staffing Summary</p><p className="mt-1">{qualitativeScoreLabel(recommendation.staffing_score)}</p></div>
            <div className="rounded-xl border border-[#e4ebf3] bg-white px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Activities</p><p className="mt-1">{activities.slice(0, 3).join(", ") || "Community has not yet confirmed."}</p></div>
            <div className="rounded-xl border border-[#e4ebf3] bg-white px-3 py-2 text-xs text-[#3a536e]"><p className="font-semibold uppercase tracking-[0.08em]">Care Levels</p><p className="mt-1">{careLevels.slice(0, 3).join(", ") || "Community has not yet confirmed."}</p></div>
          </div>
          {languages.length > 0 ? <p className="text-xs text-[#56708a]"><span className="font-semibold">Languages:</span> {languages.join(", ")}</p> : null}

          {isMoreResults ? (
            <div className="rounded-2xl border border-[#d9e3ec] bg-[#f8fcff] p-3 text-sm text-[#355270]">
              <p className="font-semibold text-[#24425e]">Why below Top 5</p>
              <p className="mt-1">{whyBelowTopFive}</p>
            </div>
          ) : null}

          <p className="text-xs text-[#5b5245]">{recommendation.explanation.availability_note}</p>

          {recommendation.tie_break_explanation_vs_next ? (
            <details className="rounded-xl border border-[#d9e3ec] bg-[#f8fcff] px-3 py-2 text-xs text-[#355270]">
              <summary className="cursor-pointer font-semibold">Technical ranking detail</summary>
              <p className="mt-1">{recommendation.tie_break_explanation_vs_next.why_ranked_above}</p>
              {recommendation.tie_break_explanation_vs_next.remained_equal.length > 0 ? (
                <p className="mt-1">Remained equal: {recommendation.tie_break_explanation_vs_next.remained_equal.join(", ")}</p>
              ) : null}
              {recommendation.tie_break_explanation_vs_next.remaining_unknown.length > 0 ? (
                <p className="mt-1">Unknown: {recommendation.tie_break_explanation_vs_next.remaining_unknown.join(", ")}</p>
              ) : null}
            </details>
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
                Compare
              </Link>
            ) : null}

            <button
              type="button"
              onClick={() => {
                const shareText = `${recommendation.facility_name} | Match ${recommendation.patient_match_score}% | Runtime ${runtimeVersion}`;
                if (typeof navigator !== "undefined" && navigator.share) {
                  void navigator.share({ title: "OPTIME Recommendation", text: shareText, url: window.location.href });
                  return;
                }
                if (typeof navigator !== "undefined" && navigator.clipboard) {
                  void navigator.clipboard.writeText(shareText);
                }
              }}
              className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]"
            >
              Share
            </button>

            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${recommendation.facility_name} ${recommendation.city || "Florida"}`)}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex rounded-full border border-[#dccfb9] px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]"
            >
              MAP
            </a>
          </div>

          {structured ? (
            <details className="rounded-xl border border-[#d4e2ed] bg-[#f7fbff] p-3 text-sm text-[#2f4f6e]">
              <summary className="cursor-pointer font-semibold">Why this match</summary>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <p><span className="font-semibold">Needs:</span> {(recommendation.matched_needs || []).length} matched, {(recommendation.unknown_critical_needs || []).length} unknown</p>
                <p><span className="font-semibold">Evidence Sources:</span> {(structured.evidence || []).length}</p>
                <p><span className="font-semibold">Weighted Parameters:</span> {(structured.match_breakdown || []).length}</p>
                <p><span className="font-semibold">Confidence:</span> {Math.round(structured.confidence_score || 0)}%</p>
              </div>
            </details>
          ) : null}
        </div>
      </article>
    );
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-5xl">We found your best matches.</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#6b645a]">These communities stand out for the needs, location, and priorities your family shared.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={backToSearch} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]">Back to search</button>
            <button type="button" onClick={startNewSearch} className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]">New search</button>
          </div>

          {visibleNeeds.length > 0 ? (
            <details className="mt-5">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Review family priorities</summary>
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
            </details>
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
                  <button
                    type="button"
                    onClick={() => {
                      if (!decisionResponse) return;
                      saveRecommendationSession({
                        id: `session-${Date.now()}`,
                        label: `Session ${new Date().toLocaleString()}`,
                        createdAt: new Date().toISOString(),
                        recommendationIds: recommendations.map((item) => item.canonical_facility_id),
                        requestKey: decisionRequestKey,
                      });
                    }}
                    className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]"
                  >
                    Save session
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

        {isLoading ? (
          <section className="mt-6 space-y-4" aria-label="Loading recommendations" aria-busy="true">
            {[0, 1, 2].map((index) => (
              <article key={`skeleton-${index}`} className="animate-pulse rounded-3xl border border-[#e8ddcc] bg-white p-5">
                <div className="h-5 w-44 rounded bg-[#eef2ea]" />
                <div className="mt-3 h-4 w-72 rounded bg-[#f2f5ef]" />
                <div className="mt-5 h-44 rounded-2xl bg-[#f2f5ef]" />
                <div className="mt-4 grid gap-2 sm:grid-cols-3">
                  <div className="h-12 rounded-xl bg-[#f3f7fc]" />
                  <div className="h-12 rounded-xl bg-[#f3f7fc]" />
                  <div className="h-12 rounded-xl bg-[#f3f7fc]" />
                </div>
              </article>
            ))}
          </section>
        ) : null}

        {!isLoading && apiLoadError ? (
          <section className="mt-6 rounded-3xl border border-[#e5b7b7] bg-[#fff4f4] p-6 text-sm text-[#7a2f2f]">
            <p className="font-semibold">Decision API unavailable</p>
            <p className="mt-2">{apiLoadError}</p>
          </section>
        ) : null}

        {!isLoading && recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            {primaryRecommendation ? (
              <section className="space-y-4 rounded-3xl bg-[#fffdf9] p-5 shadow-[0_24px_70px_-42px_rgba(45,58,48,0.4)] sm:p-7">
                {renderRecommendationCard(primaryRecommendation, 0)}
              </section>
            ) : null}

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">What still needs verification</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">A clear view of what we know and what comes next</h2>
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

                <div className="mt-4 space-y-4 md:hidden">
                  {topRecommendations.map((recommendation, index) => {
                    const facilityIndex = topRecommendations.findIndex((item) => item.canonical_facility_id === recommendation.canonical_facility_id);
                    const rankRow = rankingRows.find((item) => item.facilityId === recommendation.canonical_facility_id);
                    return (
                      <article key={`top5-mobile-${recommendation.canonical_facility_id}`} className="rounded-2xl border border-[#d9e3ec] bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#5f7f6b]">{recommendation.rank_display || `#${index + 1}`}</p>
                            <h3 className="mt-1 text-lg font-semibold text-[#2f2a24]">{recommendation.facility_name}</h3>
                            <p className="mt-1 text-sm text-[#6d655b]">{recommendation.city || "City unknown"}, {recommendation.state || "FL"}</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleFavoriteFacility(recommendation.canonical_facility_id)}
                            className="rounded-full border border-[#cddce5] bg-white px-3 py-1 text-xs font-semibold text-[#24425e]"
                          >
                            {favoriteCanonicalIds.includes(recommendation.canonical_facility_id) ? "Saved" : "Save"}
                          </button>
                        </div>

                        <div className="mt-3 space-y-2">
                          {priorityMatrixRows.slice(0, 5).map((row) => {
                            const cell = row.cells[facilityIndex];
                            return (
                              <div key={`mobile-priority-${recommendation.canonical_facility_id}-${row.parameterId}`} className="rounded-xl border border-[#eef3f7] bg-[#fbfdff] px-3 py-2 text-sm">
                                <p className="font-medium text-[#2f2a24]">{row.label}</p>
                                <p className="mt-1 text-[#355270]">{cell.valueLabel}</p>
                                {cell.clickableLabel && cell.payload ? (
                                  <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                                    {cell.clickableLabel}
                                  </button>
                                ) : null}
                              </div>
                            );
                          })}
                        </div>

                        {rankRow ? (
                          <div className="mt-3 rounded-xl border border-[#eef3f7] bg-[#fbfdff] px-3 py-2 text-sm text-[#4f473d]">
                            <p className="font-semibold text-[#2f2a24]">{rankRow.label}</p>
                            <p className="mt-1">{rankRow.text}</p>
                            {rankRow.payload ? (
                              <button type="button" onClick={() => setActiveEvidencePayload(rankRow.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                                View details {">"}
                              </button>
                            ) : null}
                          </div>
                        ) : null}
                      </article>
                    );
                  })}

                  {mobileCompareReference && mobileCompareTarget ? (
                    <article className="rounded-2xl border border-[#d9e3ec] bg-white p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">Compare recommendations</p>
                      <p className="mt-1 text-sm text-[#4a6076]">Focused comparison defaults to #{mobileCompareReference.rank_position || 1} versus your selected alternative.</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {topRecommendations.slice(1).map((item, idx) => (
                          <button
                            key={`mobile-compare-switch-${item.canonical_facility_id}`}
                            type="button"
                            onClick={() => setMobileCompareFacilityId(item.canonical_facility_id)}
                            className={`rounded-full border px-3 py-1 text-xs font-semibold ${mobileCompareTarget.canonical_facility_id === item.canonical_facility_id ? "border-[#24425e] bg-[#24425e] text-white" : "border-[#cddce5] bg-white text-[#24425e]"}`}
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
                            <div key={`mobile-compare-row-${row.parameterId}`} className="rounded-xl border border-[#eef3f7] bg-[#fbfdff] px-3 py-2 text-sm">
                              <p className="font-medium text-[#2f2a24]">{row.label}</p>
                              <p className="mt-1 text-[#355270]">#1: {leftCell.valueLabel}</p>
                              <p className="text-[#355270]">Selected: {rightCell.valueLabel}</p>
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
                        <th className="sticky left-0 z-20 w-52 border border-[#d9e3ec] bg-[#f6fbff] px-3 py-3 text-left text-[#24425e]">Decision factor</th>
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
                              <p className="mt-1 text-xs text-[#6d655b]">{imageInfo.isVerifiedFacilityImage ? `Image source: ${imageInfo.sourceLabel}` : "Official community photography is currently being verified."}</p>
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
                      <tr className="bg-[#eef6fd]">
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">A. Your priorities</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-a-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-[#eef6fd]" />
                        ))}
                      </tr>
                      {priorityMatrixRows.map((row) => (
                        <tr key={`table-priority-${row.parameterId}`}>
                          <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">
                            {row.label}
                            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[#6d655b]">{row.requirementLevel}</p>
                          </td>
                          {row.cells.map((cell, index) => (
                            <td key={`cell-priority-${row.parameterId}-${topRecommendations[index].canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top text-[#4f473d]">
                              {renderMatrixCell(cell, `priority-cell-${row.parameterId}-${index}`, "")}
                            </td>
                          ))}
                        </tr>
                      ))}

                      <tr className="bg-[#eef6fd]">
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">B. OPTIME recommends considering</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-b-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-[#eef6fd]" />
                        ))}
                      </tr>
                      {recommendedMatrixRows.map((row) => (
                        <tr key={`table-recommended-${row.parameterId}`}>
                          <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">
                            {row.label}
                            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[#6d655b]">OPTIME recommended</p>
                          </td>
                          {row.cells.map((cell, index) => (
                            <td key={`cell-recommended-${row.parameterId}-${topRecommendations[index].canonical_facility_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top text-[#4f473d]">
                              {renderMatrixCell(cell, `recommended-cell-${row.parameterId}-${index}`, "")}
                            </td>
                          ))}
                        </tr>
                      ))}

                      <tr className="bg-[#eef6fd]">
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">C. Why this rank</td>
                        {topRecommendations.map((recommendation) => (
                          <td key={`section-c-${recommendation.canonical_facility_id}`} className="border border-[#d9e3ec] bg-[#eef6fd]" />
                        ))}
                      </tr>
                      <tr>
                        <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 font-semibold text-[#2f2a24]">Ranking difference</td>
                        {rankingRows.map((rankRow) => (
                          <td key={`why-${rankRow.facilityId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-[#4f473d] align-top">
                            <p className="font-semibold text-[#2f2a24]">{rankRow.label}</p>
                            <p className="mt-1">{rankRow.text}</p>
                            {rankRow.payload ? (
                              <button type="button" onClick={() => setActiveEvidencePayload(rankRow.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                                View details {">"}
                              </button>
                            ) : null}
                          </td>
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
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-[#4a6076]">
                  <p>Needs verification is neutral. UNKNOWN never means no.</p>
                  <button type="button" onClick={() => setShowAllTopFiveParameters((current) => !current)} className="font-semibold text-[#1f5f94] hover:underline">
                    {showAllTopFiveParameters ? "Return to decision matrix" : `View all ${allComparisonParameterIds.length || 59} parameters`}
                  </button>
                </div>
              </section>
            ) : null}

            <section className="space-y-6">
              {topRecommendations.slice(1).map((recommendation, offset) => {
                const index = offset + 1;
                return (
                <section key={`top-${recommendation.canonical_facility_id}`} className="space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdf9] p-5 shadow-[0_12px_40px_-28px_rgba(69,58,43,0.35)]">
                  <div className="rounded-2xl border border-[#d9cfbf] bg-[linear-gradient(120deg,#f7efe0_0%,#fbf6ec_55%,#ffffff_100%)] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5f7f6b]">Advisor recommendation</p>
                    <h3 className="mt-1 text-2xl font-semibold text-[#2f2a24]">{recommendationTitle(index)}</h3>
                    <p className="mt-2 text-sm text-[#5f5548]">{highlightLabel(index)} for {relationship}, explained with patient-specific differences and clear verification next steps.</p>
                  </div>
                  {renderRecommendationCard(recommendation, index)}
                </section>
                );
              })}
            </section>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <div className="h-px w-full bg-[linear-gradient(90deg,transparent,#d9cfbf,transparent)]" />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#5f7f6b]">More Results</p>
                    <p className="mt-1 text-sm text-[#5c5347]">Additional ranked facilities continue from #{TOP_RECOMMENDATION_COUNT + 1} onward across all relevant ranked results.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setShowMoreCommunities((current) => {
                        const next = !current;
                        if (!next) setVisibleMoreCount(12);
                        return next;
                      });
                    }}
                    className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]"
                  >
                    {showMoreCommunities ? "HIDE MORE RESULTS" : "SHOW MORE RESULTS"}
                  </button>
                </div>
                {showMoreCommunities ? (
                  <section className="grid gap-4 md:grid-cols-2">
                    {remainingRecommendations.slice(0, visibleMoreCount).map((recommendation, index) =>
                      renderRecommendationCard(recommendation, index + TOP_RECOMMENDATION_COUNT, { isMoreResults: true })
                    )}
                    {visibleMoreCount < remainingRecommendations.length ? (
                      <div className="md:col-span-2">
                        <button
                          type="button"
                          onClick={() => setVisibleMoreCount((count) => Math.min(count + 12, remainingRecommendations.length))}
                          className="w-full rounded-2xl border border-[#d9cfbf] bg-white px-4 py-3 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]"
                        >
                          Load more recommendations
                        </button>
                      </div>
                    ) : null}
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

      {favoriteCanonicalIds.length > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-50 px-3 pb-3 md:px-6 md:pb-4">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 rounded-2xl border border-[#d9e3ec] bg-white/95 px-4 py-3 shadow-[0_14px_40px_-26px_rgba(22,37,53,0.55)] backdrop-blur">
            <div>
              <p className="text-sm font-semibold text-[#22394f]">Favorites selected: {favoriteCanonicalIds.length}</p>
              {favoriteCanonicalIds.length < 2 ? (
                <p className="text-xs text-[#4a6076]">Select one more facility to compare.</p>
              ) : (
                <p className="text-xs text-[#4a6076]">Favorites are ready for governed comparison.</p>
              )}
            </div>
            {favoriteCanonicalIds.length >= 2 ? (
              <button
                type="button"
                onClick={() => router.push(compareFavoritesHref)}
                className="rounded-full bg-[#24425e] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d3650]"
              >
                COMPARE MY FAVORITES ({favoriteCanonicalIds.length})
              </button>
            ) : (
              <span className="rounded-full border border-[#d1deea] bg-[#f6fbff] px-4 py-2 text-sm font-semibold text-[#4a6076]">Select one more facility</span>
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
