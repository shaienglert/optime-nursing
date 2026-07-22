"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  DecisionEngineRecommendation,
  DecisionEngineResponse,
  FacilityParameterComparison,
  ParameterTableRow,
  PatientComparisonContextResponse,
  fetchPatientComparisonContext,
  fetchPatientDecisionRecommendations,
  compareFacilityParameters,
} from "@/lib/api";
import { EvidenceDetailsModal, type EvidenceDetailsPayload, type EvidenceDetailRecord } from "@/components/compare/evidence-details-modal";
import {
  deriveRelevantParameterIds,
  displayParameterLabel,
  isPatientNeed,
  sortRelevantParameterIds,
} from "@/lib/comparison-flow";
import {
  clearCompareSelection,
  loadDecisionResponseCache,
  loadCompareSelection,
  loadFavoriteFacilities,
  saveDecisionResponseCache,
  saveCompareSelection,
  saveFavoriteFacilities,
} from "@/lib/search-session";

type ComparisonCell = {
  rawValue: string;
  displayValue: string;
  source: string;
  lastVerified: string;
  scopeLabel: string;
  statusLabel: string;
  evidenceCount: number;
  payload: EvidenceDetailsPayload | null;
  clickableLabel?: string;
};

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "you";
  if (relationship === "Couple") return "you both";
  return relationship || "your loved one";
}

function summarizeRecommendation(recommendation?: DecisionEngineRecommendation): { patientMatch: string; qualitySafety: string; evidenceConfidence: string; headline: string } {
  const qualityScore = recommendation?.quality_safety_score ?? null;
  return {
    headline: recommendation?.facility_name || "Selected facility",
    patientMatch: recommendation ? recommendation.match_band.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Patient match available",
    qualitySafety: recommendation ? (qualityScore !== null ? (qualityScore >= 80 ? "Strong" : qualityScore >= 65 ? "Good" : qualityScore >= 45 ? "Mixed" : "Needs caution") : "Not enough verified evidence") : "Not enough verified evidence",
    evidenceConfidence: recommendation ? (recommendation.evidence_confidence !== null && recommendation.evidence_confidence !== undefined ? (recommendation.evidence_confidence >= 80 ? "High confidence" : recommendation.evidence_confidence >= 60 ? "Medium confidence" : "Low confidence") : "Insufficient evidence") : "Insufficient evidence",
  };
}

function needLabel(parameterId: string): string {
  return displayParameterLabel(parameterId);
}

function fullCellStatusLabel(rawValue: string): string {
  if (rawValue === "YES") return "Verified match";
  if (rawValue === "NO") return "Verified gap";
  if (rawValue === "Confirm directly with facility") return "Needs verification";
  if (rawValue === "Not verified" || rawValue === "UNKNOWN") return "Needs verification";
  return "Verified match";
}

function scopeLabel(scope: string, scopeName?: string | null): string {
  const normalized = (scope || "").toUpperCase();
  if (normalized === "FACILITY") return "Available facility-wide";
  if (normalized === "PROGRAM") return `Available in a specific program${scopeName ? ` (${scopeName})` : ""}`;
  if (normalized === "UNIT") return `Available in a specific unit${scopeName ? ` (${scopeName})` : ""}`;
  if (normalized === "SERVICE") return "Verified service";
  return "Needs verification";
}

function formatVerifiedDate(value?: string | null): string {
  if (!value) return "Not verified";
  return value;
}

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

function isCountParameter(parameterId: string): boolean {
  return /(count|find|complaint|deficien|penalt|fine|inspection|denial)/i.test(parameterId);
}

function toEvidenceRecord(entry: NonNullable<ParameterTableRow["evidence_records"]>[number]): EvidenceDetailRecord {
  const provenance = (entry.provenance || {}) as Record<string, unknown>;
  return {
    title: typeof entry.evidence_text === "string" ? entry.evidence_text : undefined,
    eventType: typeof entry.evidence_strength === "string" ? entry.evidence_strength : undefined,
    date: typeof entry.evidence_date === "string" ? entry.evidence_date : undefined,
    description: entry.evidence_value !== undefined && entry.evidence_value !== null ? `Reported value: ${String(entry.evidence_value)}` : undefined,
    status: typeof entry.conflict_status === "string" ? entry.conflict_status : undefined,
    identifier: entry.source_record_id ? String(entry.source_record_id) : undefined,
    severityScope: [entry.scope, entry.scope_name].filter(Boolean).join(" / ") || undefined,
    sourceOrganization: typeof provenance.source_family === "string" ? provenance.source_family : (typeof entry.source === "string" ? entry.source : undefined),
    sourceDate: typeof entry.last_verified === "string" ? entry.last_verified : undefined,
    sourceUrl: typeof provenance.source_url === "string" ? provenance.source_url : undefined,
  };
}

function normalizeSelectedIds(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).slice(0, 5);
}

function parseSelectedIds(raw?: string | null): string[] {
  return normalizeSelectedIds((raw || "").split(","));
}

export function ComparePageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();
  const comparisonMode = searchParams.get("comparison_mode") || "standard";
  const favoriteFacilityId = searchParams.get("favorite") || "";
  const optimeReferenceId = searchParams.get("optime_reference") || "";
  const isFavoritesComparison = comparisonMode === "favorites";
  const isFocusedComparison = comparisonMode === "favorite-vs-optime";
  const facilitiesFromQuery = useMemo(
    () => parseSelectedIds(searchParams.get("facilities")),
    [searchParams],
  );

  const [decisionResponse, setDecisionResponse] = useState<DecisionEngineResponse | null>(null);
  const [comparisonContext, setComparisonContext] = useState<PatientComparisonContextResponse | null>(null);
  const [comparisonTable, setComparisonTable] = useState<FacilityParameterComparison | null>(null);
  const [selectedFacilityIds, setSelectedFacilityIds] = useState<string[]>(facilitiesFromQuery);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllParameters, setShowAllParameters] = useState(false);
  const [activeEvidencePayload, setActiveEvidencePayload] = useState<EvidenceDetailsPayload | null>(null);
  const [mobileFocusedFacilityId, setMobileFocusedFacilityId] = useState<string>("");

  const searchParamsString = searchParams.toString();
  const returnTo = searchParams.get("returnTo") || "/results";
  const relationship = relationshipCopy(String(searchParams.get("relationship") || state.relationship || "your loved one"));
  const naturalLanguageQuery = String(searchParams.get("notes") || state.notes || "").trim();
  const decisionRequestPayload = useMemo(
    () => ({ questionnaire_state: state, natural_language_query: naturalLanguageQuery, limit: 50 }),
    [state, naturalLanguageQuery],
  );
  const selectedIdsKey = useMemo(() => JSON.stringify(decisionRequestPayload), [decisionRequestPayload]);

  useEffect(() => {
    setSelectedFacilityIds((current) => {
      if (facilitiesFromQuery.length > 0) {
        const same =
          current.length === facilitiesFromQuery.length &&
          current.every((value, index) => value === facilitiesFromQuery[index]);
        return same ? current : facilitiesFromQuery;
      }
      if (current.length > 0) {
        return current;
      }

      const fallback = isFavoritesComparison
        ? normalizeSelectedIds(loadFavoriteFacilities())
        : normalizeSelectedIds(loadCompareSelection());
      return fallback;
    });
  }, [facilitiesFromQuery, isFavoritesComparison]);

  useEffect(() => {
    if (isFavoritesComparison) {
      saveFavoriteFacilities(selectedFacilityIds);
    }
    if (selectedFacilityIds.length > 0) {
      saveCompareSelection(selectedFacilityIds);
    } else {
      clearCompareSelection();
    }
  }, [isFavoritesComparison, selectedFacilityIds]);

  useEffect(() => {
    const params = new URLSearchParams(searchParamsString);
    if (selectedFacilityIds.length > 0) {
      params.set("facilities", selectedFacilityIds.join(","));
    } else {
      params.delete("facilities");
    }
    if (!params.get("returnTo") && returnTo) {
      params.set("returnTo", returnTo);
    }
    const nextUrl = `/compare${params.toString() ? `?${params.toString()}` : ""}`;
    const currentUrl = `/compare${searchParamsString ? `?${searchParamsString}` : ""}`;
    if (nextUrl !== currentUrl) {
      router.replace(nextUrl, { scroll: false });
    }
  }, [router, returnTo, searchParamsString, selectedFacilityIds]);

  useEffect(() => {
    let mounted = true;

    async function load() {
      if (selectedFacilityIds.length < 2) {
        setIsLoading(false);
        setDecisionResponse(null);
        setComparisonContext(null);
        setComparisonTable(null);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const requestKey = JSON.stringify(decisionRequestPayload);
        const cached = loadDecisionResponseCache<DecisionEngineResponse>(requestKey);
        const recommendations = cached || await fetchPatientDecisionRecommendations(decisionRequestPayload);
        if (!mounted) return;
        setDecisionResponse(recommendations);
        if (!cached) {
          saveDecisionResponseCache(requestKey, recommendations);
        }

        const [comparisonContextResponse, comparisonTableResponse] = await Promise.all([
          fetchPatientComparisonContext({
            canonical_facility_ids: selectedFacilityIds,
            patient_needs_profile: recommendations.patient_needs_profile,
          }),
          compareFacilityParameters({
            canonical_facility_ids: selectedFacilityIds,
            need_tags: recommendations.patient_needs_profile.need_tags,
            priority_parameter_ids: recommendations.patient_needs_profile.priority_parameter_ids,
            profile_key: recommendations.patient_needs_profile.profile_key || undefined,
          }),
        ]);
        if (!mounted) return;
        setComparisonContext(comparisonContextResponse);
        setComparisonTable(comparisonTableResponse);
      } catch (fetchError) {
        if (!mounted) return;
        setError(fetchError instanceof Error ? fetchError.message : "Failed to load compare details.");
        setDecisionResponse(null);
        setComparisonContext(null);
        setComparisonTable(null);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, [decisionRequestPayload, selectedFacilityIds, selectedIdsKey]);

  const recommendationById = useMemo(() => {
    const map = new Map<string, DecisionEngineRecommendation>();
    for (const recommendation of decisionResponse?.results || []) {
      map.set(recommendation.canonical_facility_id, recommendation);
    }
    return map;
  }, [decisionResponse]);

  const comparisonRows = useMemo(() => {
    if (!comparisonTable) return [];
    const facilityTableById = new Map(comparisonTable.facilities.map((facility) => [facility.canonical_facility_id, facility] as const));
    return comparisonTable.parameter_ids.map((parameterId) => {
      const sampleRow = comparisonTable.facilities
        .flatMap((facility) => facility.rows || [])
        .find((row) => row.parameter_id === parameterId);
      const parameterName = sampleRow?.parameter || needLabel(parameterId);
      const cells = selectedFacilityIds.map((facilityId) => {
        const facility = facilityTableById.get(facilityId);
        const row = (facility?.rows || []).find((item) => item.parameter_id === parameterId);
        const rawValue = String(row?.raw_value ?? row?.status_value ?? "UNKNOWN");
        const formattedValue = formatRawValue(row?.status_value ?? row?.raw_value ?? "UNKNOWN");
        const evidenceRecords = (row?.evidence_records || []).map(toEvidenceRecord);

        let summary = `${parameterName}: ${formattedValue}.`;
        let clickableLabel: string | undefined;
        let unavailableDetailsMessage: string | undefined;
        if (isCountParameter(parameterId) && typeof row?.raw_value === "number" && Number.isInteger(row.raw_value) && row.raw_value >= 0) {
          summary = row.raw_value === 0 ? "No records found in the verified reporting period." : `${row.raw_value} records reported in the verified reporting period.`;
          clickableLabel = row.raw_value === 0 ? "No records found in the verified reporting period >" : `${row.raw_value} found >`;
          if ((row.evidence_count || 0) <= 1 && row.raw_value > 0) {
            unavailableDetailsMessage = `${row.raw_value} records reported. Detailed records are not currently available in OPTIME.`;
          }
        } else if (row?.source && row.source !== "Not verified") {
          clickableLabel = "View details >";
        }

        return {
          rawValue,
          displayValue: formattedValue,
          source: String(row?.source || "Not verified"),
          lastVerified: formatVerifiedDate(row?.last_verified),
          scopeLabel: scopeLabel(row?.detail_scope || "", row?.scope_name),
          statusLabel: fullCellStatusLabel(rawValue),
          evidenceCount: row?.evidence_count || 0,
          clickableLabel,
          payload: clickableLabel ? {
            facilityName: facility?.facility_name || facilityId,
            parameterLabel: parameterName,
            summary,
            records: evidenceRecords,
            unavailableDetailsMessage,
          } : null,
        } satisfies ComparisonCell;
      });
      return {
        parameterId,
        parameterName,
        cells,
      };
    });
  }, [comparisonTable, selectedFacilityIds]);

  const patientNeedsRows = useMemo(() => {
    const rows = [
      ...(comparisonContext?.required_needs || []),
      ...(comparisonContext?.high_priority_needs || []),
      ...(comparisonContext?.preferences || []),
    ];
    return rows;
  }, [comparisonContext]);

  const fullParameterIds = useMemo(
    () => comparisonContext?.comparison_parameter_ids || comparisonTable?.parameter_ids || [],
    [comparisonContext?.comparison_parameter_ids, comparisonTable?.parameter_ids]
  );
  const relevantParameterIds = useMemo(() => {
    return sortRelevantParameterIds(
      decisionResponse?.patient_needs_profile,
      deriveRelevantParameterIds(decisionResponse?.patient_needs_profile, fullParameterIds)
    );
  }, [decisionResponse?.patient_needs_profile, fullParameterIds]);

  const relevantComparisonRows = useMemo(() => {
    const relevantSet = new Set(relevantParameterIds);
    return comparisonRows.filter((row) => {
      if (!relevantSet.has(row.parameterId)) return false;
      const values = new Set(row.cells.map((cell) => cell.displayValue));
      return isPatientNeed(decisionResponse?.patient_needs_profile, row.parameterId) || values.size > 1 || values.has("Needs verification") || values.has("Verified gap");
    });
  }, [comparisonRows, decisionResponse?.patient_needs_profile, relevantParameterIds]);

  const priorityRelevantRows = useMemo(
    () => relevantComparisonRows.filter((row) => isPatientNeed(decisionResponse?.patient_needs_profile, row.parameterId)),
    [decisionResponse?.patient_needs_profile, relevantComparisonRows],
  );

  const recommendedRelevantRows = useMemo(
    () => relevantComparisonRows.filter((row) => !isPatientNeed(decisionResponse?.patient_needs_profile, row.parameterId)),
    [decisionResponse?.patient_needs_profile, relevantComparisonRows],
  );

  const whatToVerify = useMemo(() => {
    if (!comparisonContext) return [];
    const rows = patientNeedsRows.flatMap((need) => {
      const facilityStatuses = comparisonContext.facilities.map((facility) => facility.need_rows.find((row) => row.parameter_id === need.parameter_id));
      if (facilityStatuses.every((status) => status?.status === "MATCH")) return [];
      const label = needLabel(need.parameter_id);
      const shouldVerify = need.requirement_level === "REQUIRED" || facilityStatuses.some((status) => status?.status !== "MATCH");
      if (!shouldVerify) return [];
      return [`Confirm current ${label} availability`];
    });
    return Array.from(new Set(rows)).slice(0, 5);
  }, [comparisonContext, patientNeedsRows]);

  const selectedFacilities = selectedFacilityIds.map((facilityId) => {
    const recommendation = recommendationById.get(facilityId);
    const comparisonFacility = comparisonContext?.facilities.find((facility) => facility.canonical_facility_id === facilityId);
    return {
      facilityId,
      facilityName: comparisonFacility?.facility_name || recommendation?.facility_name || facilityId,
      recommendation,
      comparisonFacility,
    };
  });

  const effectiveMobileFocusedFacilityId =
    mobileFocusedFacilityId && selectedFacilities.some((facility) => facility.facilityId === mobileFocusedFacilityId)
      ? mobileFocusedFacilityId
      : (selectedFacilities[0]?.facilityId || "");

  const mobileFocusedRows = useMemo(() => {
    const focusedIndex = selectedFacilities.findIndex((facility) => facility.facilityId === effectiveMobileFocusedFacilityId);
    if (focusedIndex < 0) return [] as typeof relevantComparisonRows;
    return relevantComparisonRows
      .filter((row) => row.cells[focusedIndex].displayValue !== "Not verified" || isPatientNeed(decisionResponse?.patient_needs_profile, row.parameterId))
      .slice(0, 12);
  }, [decisionResponse?.patient_needs_profile, effectiveMobileFocusedFacilityId, relevantComparisonRows, selectedFacilities]);

  const removeFacility = (facilityId: string) => {
    setSelectedFacilityIds((current) => {
      const next = current.filter((item) => item !== facilityId);
      if (isFavoritesComparison) {
        saveFavoriteFacilities(next);
      }
      return next;
    });
  };

  const addAnotherFacility = () => {
    saveCompareSelection(selectedFacilityIds);
    router.push(returnTo);
  };

  const compareBackHref = returnTo;
  const currentCompareParams = new URLSearchParams(searchParamsString);
  currentCompareParams.set("facilities", selectedFacilityIds.join(","));
  currentCompareParams.set("returnTo", returnTo);
  const currentComparePath = `/compare${currentCompareParams.toString() ? `?${currentCompareParams.toString()}` : ""}`;
  const currentOptimeRecommendation = decisionResponse?.results?.[0];

  const buildFavoriteVsOptimeHref = (canonicalFacilityId: string) => {
    if (!currentOptimeRecommendation) return currentComparePath;
    const params = new URLSearchParams(searchParamsString);
    params.set("comparison_mode", "favorite-vs-optime");
    params.set("favorite", canonicalFacilityId);
    params.set("optime_reference", currentOptimeRecommendation.canonical_facility_id);
    params.set("facilities", [canonicalFacilityId, currentOptimeRecommendation.canonical_facility_id].join(","));
    params.set("returnTo", returnTo);
    return `/compare?${params.toString()}`;
  };

  const focusedNarrative = useMemo(() => {
    if (!isFocusedComparison || selectedFacilities.length < 2) return [] as string[];

    const favoriteFacility = selectedFacilities.find((facility) => facility.facilityId === favoriteFacilityId) || selectedFacilities[0];
    const optimeFacility = selectedFacilities.find((facility) => facility.facilityId === optimeReferenceId) || selectedFacilities[1];
    if (!favoriteFacility || !optimeFacility) return [] as string[];

    const favoriteNeeds = new Map((favoriteFacility.comparisonFacility?.need_rows || []).map((row) => [row.parameter_id, row] as const));
    const optimeNeeds = new Map((optimeFacility.comparisonFacility?.need_rows || []).map((row) => [row.parameter_id, row] as const));

    const sharedStrengths = patientNeedsRows
      .filter((need) => favoriteNeeds.get(need.parameter_id)?.status === "MATCH" && optimeNeeds.get(need.parameter_id)?.status === "MATCH")
      .slice(0, 3)
      .map((need) => needLabel(need.parameter_id));

    const optimeAdvantages = patientNeedsRows
      .filter((need) => optimeNeeds.get(need.parameter_id)?.status === "MATCH" && favoriteNeeds.get(need.parameter_id)?.status !== "MATCH")
      .slice(0, 3)
      .map((need) => needLabel(need.parameter_id));

    const favoriteAdvantages = patientNeedsRows
      .filter((need) => favoriteNeeds.get(need.parameter_id)?.status === "MATCH" && optimeNeeds.get(need.parameter_id)?.status !== "MATCH")
      .slice(0, 3)
      .map((need) => needLabel(need.parameter_id));

    const verificationGaps = patientNeedsRows
      .filter((need) => favoriteNeeds.get(need.parameter_id)?.status === "NOT_VERIFIED" || optimeNeeds.get(need.parameter_id)?.status === "NOT_VERIFIED")
      .slice(0, 3)
      .map((need) => needLabel(need.parameter_id));

    const lines: string[] = [];

    if (sharedStrengths.length > 0) {
      lines.push(`Both facilities are similarly strong for ${sharedStrengths.join(", ")}.`);
    }

    if (optimeAdvantages.length > 0) {
      lines.push(`${optimeFacility.facilityName} has stronger verified evidence for ${optimeAdvantages.join(", ")}.`);
    }

    if (favoriteAdvantages.length > 0) {
      lines.push(`${favoriteFacility.facilityName} has a supported advantage for ${favoriteAdvantages.join(", ")}.`);
    }

    if (verificationGaps.length > 0) {
      lines.push(`${verificationGaps.join(", ")} is not currently verified for at least one of these facilities and should be confirmed directly.`);
    }

    const favoriteSummary = summarizeRecommendation(favoriteFacility.recommendation);
    const optimeSummary = summarizeRecommendation(optimeFacility.recommendation);
    if (favoriteSummary.qualitySafety !== optimeSummary.qualitySafety) {
      lines.push(`Quality and safety differ: ${favoriteFacility.facilityName} is currently assessed as ${favoriteSummary.qualitySafety.toLowerCase()}, while ${optimeFacility.facilityName} is currently assessed as ${optimeSummary.qualitySafety.toLowerCase()}.`);
    }

    if (favoriteSummary.patientMatch !== optimeSummary.patientMatch) {
      lines.push(`Overall patient fit differs: ${favoriteFacility.facilityName} is shown as ${favoriteSummary.patientMatch.toLowerCase()}, while ${optimeFacility.facilityName} is shown as ${optimeSummary.patientMatch.toLowerCase()}.`);
    }

    return lines;
  }, [favoriteFacilityId, isFocusedComparison, optimeReferenceId, patientNeedsRows, selectedFacilities]);

  const compareTitle = isFocusedComparison
    ? "Your choice vs OPTIME's current recommendation"
    : isFavoritesComparison
      ? "Compare My Favorites"
      : "Compare Facilities";

  const compareSubtitle = isFocusedComparison
    ? "See where your chosen facility and OPTIME's current best recommendation are similarly strong, where verified differences exist, and what still needs direct confirmation."
    : isFavoritesComparison
      ? "Compare your saved shortlist using the same patient-specific questions and verified evidence that shaped the recommendations."
      : "Compare facilities using the same patient-specific questions and verified evidence that shaped the recommendations.";

  if (error) {
    return (
      <main className="min-h-screen bg-[#fffdf8] px-6 py-12">
        <p className="text-[#8b3d2e]">{error}</p>
        <button type="button" onClick={addAnotherFacility} className="mt-4 rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245]">
          Back to results
        </button>
      </main>
    );
  }

  if (selectedFacilityIds.length < 2) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
        <section className="mx-auto max-w-5xl rounded-3xl border border-[#e8ddcc] bg-white p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#5f7f6b]">Compare</p>
          <h1 className="mt-2 text-3xl font-semibold text-[#2f2a24]">{compareTitle} for {relationship}</h1>
          <p className="mt-3 text-sm text-[#5c5347]">Select at least 2 facilities on the results page to build a comparison.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href={compareBackHref} className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white">Back to results</Link>
          </div>
        </section>
      </main>
    );
  }

  if ((isLoading || !comparisonContext || !comparisonTable) && selectedFacilityIds.length >= 2) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
        <section className="mx-auto max-w-7xl space-y-6">
          <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">Compare</p>
            <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">{compareTitle} for {relationship}</h1>
            <p className="mt-2 text-[#6b645a]">{compareSubtitle}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button type="button" onClick={addAnotherFacility} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]">Add another facility</button>
              <Link href={compareBackHref} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">Back to results</Link>
            </div>
          </header>

          <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Selected facilities</p>
                <p className="mt-1 text-sm text-[#4a6076]">Loading patient-specific comparison details...</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {selectedFacilityIds.map((facilityId, index) => (
                <span key={facilityId} className="inline-flex items-center gap-2 rounded-full border border-[#cddce5] bg-white px-3 py-1.5 text-sm text-[#24425e]">
                  <span>Selected facility #{index + 1}</span>
                </span>
              ))}
            </div>
          </section>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">Compare</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">{compareTitle} for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">{compareSubtitle}</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={addAnotherFacility} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]">Add another facility</button>
            <Link href={compareBackHref} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">Back to results</Link>
          </div>
        </header>

        <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Selected facilities</p>
              <p className="mt-1 text-sm text-[#4a6076]">Remove or add facilities, then compare again. Favorites stay in session while you move between pages.</p>
            </div>
            <button
              type="button"
              onClick={() => setShowAllParameters((current) => !current)}
              className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]"
            >
              {showAllParameters ? "Show patient-relevant parameters" : `View all ${fullParameterIds.length || 59} parameters`}
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {selectedFacilities.map((facility) => (
              <button
                key={facility.facilityId}
                type="button"
                onClick={() => removeFacility(facility.facilityId)}
                className="inline-flex items-center gap-2 rounded-full border border-[#cddce5] bg-white px-3 py-1.5 text-sm text-[#24425e] hover:bg-[#edf6fb]"
              >
                <span>{facility.facilityName}</span>
                <span aria-hidden="true">x</span>
              </button>
            ))}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {selectedFacilities.map(({ facilityId, facilityName, recommendation }) => {
            const summary = summarizeRecommendation(recommendation);
            return (
              <article key={facilityId} className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Comparison overview</p>
                <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">{facilityName}</h2>
                <p className="mt-1 text-sm text-[#6d655b]">{recommendation?.city || "City unknown"}, {recommendation?.state || "FL"}</p>
                <div className="mt-4 space-y-2 text-sm text-[#4f473d]">
                  <p><span className="font-semibold text-[#2f2a24]">Patient Match:</span> {summary.patientMatch}</p>
                  <p><span className="font-semibold text-[#2f2a24]">Quality & Safety:</span> {summary.qualitySafety}</p>
                  <p><span className="font-semibold text-[#2f2a24]">Evidence Confidence:</span> {summary.evidenceConfidence}</p>
                </div>
                <div className="mt-4 rounded-2xl border border-[#d9cfbf] bg-[#fffdf9] p-4 text-sm text-[#5c5347]">
                  <p className="font-semibold text-[#2f2a24]">What to verify before choosing</p>
                  <ul className="mt-2 space-y-1">
                    {(whatToVerify.length > 0 ? whatToVerify : ["No additional verification questions surfaced"]).map((item) => (
                      <li key={`${facilityId}-${item}`}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {recommendation?.facility_profile_id ? (
                    <Link href={`/facility/${recommendation.facility_profile_id}?canonical=${encodeURIComponent(facilityId)}&back=${encodeURIComponent(currentComparePath)}`} className="rounded-full bg-[#6f9a86] px-4 py-2 text-sm font-semibold text-white hover:bg-[#618a77]">
                      Open facility
                    </Link>
                  ) : null}
                  {currentOptimeRecommendation && currentOptimeRecommendation.canonical_facility_id !== facilityId ? (
                    <Link href={buildFavoriteVsOptimeHref(facilityId)} className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]">
                      Compare with OPTIME recommendation
                    </Link>
                  ) : null}
                  <button type="button" onClick={() => removeFacility(facilityId)} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Remove
                  </button>
                </div>
              </article>
            );
          })}
        </section>

        {isFocusedComparison && focusedNarrative.length > 0 ? (
          <section className="rounded-3xl border border-[#d9e3ec] bg-[#f8fcff] p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">What you should know</p>
            <h2 className="mt-2 text-lg font-semibold text-[#2f2a24]">
              Your choice: {selectedFacilities.find((facility) => facility.facilityId === favoriteFacilityId)?.facilityName || "Selected facility"}
              {" "}vs{" "}
              OPTIME recommendation {decisionResponse?.results.find((item) => item.canonical_facility_id === optimeReferenceId)?.rank_display || "#1"}: {selectedFacilities.find((facility) => facility.facilityId === optimeReferenceId)?.facilityName || "Current best applicable recommendation"}
            </h2>
            <p className="mt-2 text-sm text-[#4a6076]">
              Current OPTIME reference: {selectedFacilities.find((facility) => facility.facilityId === optimeReferenceId)?.facilityName || "current highest applicable recommendation"}.
            </p>
            <div className="mt-4 space-y-3 text-sm text-[#355270]">
              {focusedNarrative.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          </section>
        ) : null}

        <section className="rounded-3xl border border-[#d9e3ec] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Patient-relevant comparison</p>
              <p className="mt-2 text-sm text-[#4a6076]">Selected patient needs and OPTIME-recommended relevant parameters appear first. UNKNOWN remains neutral and never becomes NO.</p>
            </div>
            <p className="text-xs text-[#4a6076]">Required and high-priority needs stay visible even when facilities are tied.</p>
          </div>

          <div className="mt-4 space-y-3 md:hidden">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">Focused mobile comparison</p>
            <div className="flex flex-wrap gap-2">
              {selectedFacilities.map((facility) => (
                <button
                  key={`mobile-focus-${facility.facilityId}`}
                  type="button"
                  onClick={() => setMobileFocusedFacilityId(facility.facilityId)}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${effectiveMobileFocusedFacilityId === facility.facilityId ? "border-[#24425e] bg-[#24425e] text-white" : "border-[#cddce5] bg-white text-[#24425e]"}`}
                >
                  {facility.facilityName}
                </button>
              ))}
            </div>
            {mobileFocusedRows.map((row) => {
              const focusedIndex = selectedFacilities.findIndex((facility) => facility.facilityId === effectiveMobileFocusedFacilityId);
              const cell = row.cells[focusedIndex];
              if (!cell) return null;
              return (
                <article key={`mobile-focused-row-${row.parameterId}`} className="rounded-xl border border-[#e6edf3] bg-[#fbfdff] px-3 py-2 text-sm">
                  <p className="font-semibold text-[#2f2a24]">{row.parameterName}</p>
                  <p className="mt-1 text-[#4f473d]">{cell.displayValue}</p>
                  <p className="text-[11px] text-[#6b6257]">{cell.scopeLabel}</p>
                  {cell.clickableLabel && cell.payload ? (
                    <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                      {cell.clickableLabel}
                    </button>
                  ) : null}
                </article>
              );
            })}
          </div>

          <div className="mt-4 hidden overflow-x-auto md:block">
            <table className="min-w-full border-collapse text-xs sm:text-sm">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 text-left">Parameter</th>
                  {selectedFacilities.map((facility) => (
                    <th key={`relevant-${facility.facilityId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-left">{facility.facilityName}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="bg-[#eef6fd]">
                  <td className="sticky left-0 z-10 border border-[#d9e3ec] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">A. Your priorities</td>
                  {selectedFacilities.map((facility) => (
                    <td key={`section-priority-${facility.facilityId}`} className="border border-[#d9e3ec] bg-[#eef6fd]" />
                  ))}
                </tr>
                {priorityRelevantRows.map((row) => (
                  <tr key={`relevant-row-${row.parameterId}`}>
                    <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                      <p className="font-semibold text-[#2f2a24]">{row.parameterName}</p>
                      <p className="mt-1 text-[10px] text-[#6b6257]">Selected or implied need</p>
                    </td>
                    {row.cells.map((cell, cellIndex) => {
                      const facility = selectedFacilities[cellIndex];
                      return (
                        <td key={`relevant-cell-${facility.facilityId}-${row.parameterId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                          <p className="font-semibold text-[#2f2a24]">{cell.statusLabel}</p>
                          <p className="mt-1 text-[#4f473d]">{cell.displayValue}</p>
                          <p className="mt-1 text-[10px] text-[#6b6257]">{cell.scopeLabel}</p>
                          <p className="text-[10px] text-[#6b6257]">Source: {cell.source}</p>
                          {cell.clickableLabel && cell.payload ? (
                            <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                              {cell.clickableLabel}
                            </button>
                          ) : null}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr className="bg-[#eef6fd]">
                  <td className="sticky left-0 z-10 border border-[#d9e3ec] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-[#24425e]">B. OPTIME recommends considering</td>
                  {selectedFacilities.map((facility) => (
                    <td key={`section-recommended-${facility.facilityId}`} className="border border-[#d9e3ec] bg-[#eef6fd]" />
                  ))}
                </tr>
                {recommendedRelevantRows.map((row) => (
                  <tr key={`recommended-row-${row.parameterId}`}>
                    <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                      <p className="font-semibold text-[#2f2a24]">{row.parameterName}</p>
                      <p className="mt-1 text-[10px] text-[#6b6257]">OPTIME-recommended relevant parameter</p>
                    </td>
                    {row.cells.map((cell, cellIndex) => {
                      const facility = selectedFacilities[cellIndex];
                      return (
                        <td key={`recommended-cell-${facility.facilityId}-${row.parameterId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                          <p className="font-semibold text-[#2f2a24]">{cell.statusLabel}</p>
                          <p className="mt-1 text-[#4f473d]">{cell.displayValue}</p>
                          <p className="mt-1 text-[10px] text-[#6b6257]">{cell.scopeLabel}</p>
                          <p className="text-[10px] text-[#6b6257]">Source: {cell.source}</p>
                          {cell.clickableLabel && cell.payload ? (
                            <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                              {cell.clickableLabel}
                            </button>
                          ) : null}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {showAllParameters ? (
          <section className="rounded-3xl border border-[#d9e3ec] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">All 59 parameters</p>
              <p className="mt-2 text-sm text-[#4a6076]">This is the full canonical comparison. Missing evidence stays visible as needs verification or not verified.</p>
              {fullParameterIds.length !== 59 ? (
                <p className="mt-1 text-xs text-[#8b4f3f]">Current payload includes {fullParameterIds.length} parameters. Canonical target is 59.</p>
              ) : null}
            </div>
            <button type="button" onClick={() => setShowAllParameters(false)} className="rounded-full border border-[#cddce5] bg-[#f6fbff] px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]">
              Return to patient-relevant view
            </button>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 text-left">Parameter</th>
                  {selectedFacilities.map((facility) => (
                    <th key={`full-${facility.facilityId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 text-left">{facility.facilityName}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.parameterId}>
                    <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                      <p className="font-semibold text-[#2f2a24]">{row.parameterName}</p>
                    </td>
                    {row.cells.map((cell, cellIndex) => {
                      const facility = selectedFacilities[cellIndex];
                      return (
                        <td key={`${facility.facilityId}-${row.parameterId}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                          <p className="font-semibold text-[#2f2a24]">{cell.statusLabel}</p>
                          <p className="mt-1 text-[#4f473d]">{cell.displayValue}</p>
                          <p className="mt-1 text-[10px] text-[#6b6257]">{cell.scopeLabel}</p>
                          <p className="text-[10px] text-[#6b6257]">Source: {cell.source}</p>
                          <p className="text-[10px] text-[#6b6257]">Last verified: {cell.lastVerified}</p>
                          {cell.clickableLabel && cell.payload ? (
                            <button type="button" onClick={() => setActiveEvidencePayload(cell.payload)} className="mt-1 text-xs font-medium text-[#1f5f94] hover:underline">
                              {cell.clickableLabel}
                            </button>
                          ) : null}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </section>
        ) : null}
      </section>

      <EvidenceDetailsModal
        isOpen={Boolean(activeEvidencePayload)}
        payload={activeEvidencePayload}
        onClose={() => setActiveEvidencePayload(null)}
      />
    </main>
  );
}