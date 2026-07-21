"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import {
  DecisionEngineRecommendation,
  DecisionEngineResponse,
  FacilityParameterComparison,
  PatientComparisonContextResponse,
  fetchPatientComparisonContext,
  fetchPatientDecisionRecommendations,
  compareFacilityParameters,
} from "@/lib/api";
import { clearCompareSelection, loadCompareSelection, saveCompareSelection } from "@/lib/search-session";

type ComparisonCell = {
  rawValue: string;
  displayValue: string;
  source: string;
  lastVerified: string;
  scopeLabel: string;
  statusLabel: string;
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
  const labels: Record<string, string> = {
    nursing_24_7: "24/7 nursing",
    skilled_nursing_capabilities: "Skilled nursing",
    adl_support: "ADL support",
    medication_support: "Medication management",
    ot: "Occupational therapy",
    pt: "Physical therapy",
    speech_therapy: "Speech therapy",
    transfer_assistance: "Transfer assistance",
    post_stroke_neuro_evidence: "Stroke / neurological rehabilitation",
    memory_care: "Memory care",
    published_rates: "Transparent pricing",
    transportation: "Transportation support",
    medicare_attributes: "Medicare acceptance",
  };
  return labels[parameterId] || parameterId.replace(/_/g, " ");
}

function statusLabel(status: "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"): string {
  if (status === "MATCH") return "Verified match";
  if (status === "VERIFIED_GAP") return "Verified gap";
  return "Needs verification";
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

function normalizeSelectedIds(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).slice(0, 5);
}

function parseSelectedIds(raw?: string | null): string[] {
  return normalizeSelectedIds((raw || "").split(","));
}

function isInterestingParameter(parameterId: string, visibleNeedIds: Set<string>, rowCells: ComparisonCell[]): boolean {
  if (visibleNeedIds.has(parameterId)) return true;
  const values = new Set(rowCells.map((cell) => cell.displayValue));
  return values.size > 1 || values.has("Needs verification") || values.has("Verified gap");
}

export function ComparePageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state } = useQuestionnaire();

  const [decisionResponse, setDecisionResponse] = useState<DecisionEngineResponse | null>(null);
  const [comparisonContext, setComparisonContext] = useState<PatientComparisonContextResponse | null>(null);
  const [comparisonTable, setComparisonTable] = useState<FacilityParameterComparison | null>(null);
  const [selectedFacilityIds, setSelectedFacilityIds] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    const fromQuery = parseSelectedIds(new URLSearchParams(window.location.search).get("facilities"));
    return fromQuery.length > 0 ? fromQuery : normalizeSelectedIds(loadCompareSelection());
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDifferencesOnly, setShowDifferencesOnly] = useState(true);

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
    if (selectedFacilityIds.length > 0) {
      saveCompareSelection(selectedFacilityIds);
    } else {
      clearCompareSelection();
    }
  }, [selectedFacilityIds]);

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
        const recommendations = await fetchPatientDecisionRecommendations(decisionRequestPayload);
        if (!mounted) return;
        setDecisionResponse(recommendations);

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
    const facilityTableById = new Map(
      comparisonTable.facilities.map((facility) => [facility.canonical_facility_id, facility] as const),
    );
    return comparisonTable.parameter_ids.map((parameterId, index) => {
      const parameterName = comparisonTable.facilities[0]?.rows[index]?.parameter || needLabel(parameterId);
      const cells = selectedFacilityIds.map((facilityId) => {
        const facility = facilityTableById.get(facilityId);
        const row = facility?.rows[index];
        const rawValue = String(row?.raw_value ?? row?.status_value ?? "UNKNOWN");
        return {
          rawValue,
          displayValue: String(row?.status_value ?? rawValue),
          source: String(row?.source || "Not verified"),
          lastVerified: formatVerifiedDate(row?.last_verified),
          scopeLabel: scopeLabel(row?.detail_scope || "", row?.scope_name),
          statusLabel: fullCellStatusLabel(rawValue),
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

  const visibleComparisonRows = useMemo(() => {
    if (!comparisonTable || !comparisonContext) return [];
    const visibleNeedIds = new Set(patientNeedsRows.map((need) => need.parameter_id));
    return comparisonRows.filter((row) => !showDifferencesOnly || isInterestingParameter(row.parameterId, visibleNeedIds, row.cells));
  }, [comparisonContext, comparisonRows, patientNeedsRows, showDifferencesOnly, comparisonTable]);

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

  const removeFacility = (facilityId: string) => {
    setSelectedFacilityIds((current) => current.filter((item) => item !== facilityId));
  };

  const addAnotherFacility = () => {
    router.push(returnTo);
  };

  const compareBackHref = returnTo;
  const currentCompareParams = new URLSearchParams(searchParamsString);
  currentCompareParams.set("facilities", selectedFacilityIds.join(","));
  currentCompareParams.set("returnTo", returnTo);
  const currentComparePath = `/compare${currentCompareParams.toString() ? `?${currentCompareParams.toString()}` : ""}`;

  if (isLoading) {
    return <main className="min-h-screen bg-[#fffdf8] px-6 py-12 text-[#5d5548]">Loading compare view...</main>;
  }

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

  if (selectedFacilityIds.length < 2 || !comparisonContext || !comparisonTable) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
        <section className="mx-auto max-w-5xl rounded-3xl border border-[#e8ddcc] bg-white p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#5f7f6b]">Compare</p>
          <h1 className="mt-2 text-3xl font-semibold text-[#2f2a24]">Comparing facilities for {relationship}</h1>
          <p className="mt-3 text-sm text-[#5c5347]">Select at least 2 facilities on the results page to build a comparison.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href={compareBackHref} className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white">Back to results</Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">Compare</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Comparing facilities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">Compare selected facilities using the same governed parameter IDs and patient context.</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={addAnotherFacility} className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]">Add another facility</button>
            <Link href={compareBackHref} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">Back to results</Link>
          </div>
        </header>

        <section className="rounded-3xl border border-[#d9e3ec] bg-[#f6fbff] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Selected facilities</p>
              <p className="mt-1 text-sm text-[#4a6076]">Remove or add facilities, then compare again. Selected facilities stay in session while you move between pages.</p>
            </div>
            <button
              type="button"
              onClick={() => setShowDifferencesOnly((current) => !current)}
              className="rounded-full border border-[#cddce5] bg-white px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]"
            >
              {showDifferencesOnly ? "Show all 59 parameters" : "Show key differences"}
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
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">OPTIME Recommendation</p>
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
                  <button type="button" onClick={() => removeFacility(facilityId)} className="rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#5b5245] hover:bg-[#f5eee2]">
                    Remove
                  </button>
                </div>
              </article>
            );
          })}
        </section>

        <section className="rounded-3xl border border-[#d9e3ec] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">Patient-first comparison</p>
              <p className="mt-2 text-sm text-[#4a6076]">Required and high-priority needs stay at the top. Unknown remains neutral and not treated as a failure.</p>
            </div>
            <p className="text-xs text-[#4a6076]">Same governed parameter IDs underneath</p>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 text-left">Need</th>
                  {selectedFacilities.map((facility) => (
                    <th key={facility.facilityId} className="border border-[#d9e3ec] bg-white px-3 py-2 text-left align-top">
                      <p className="font-semibold text-[#2f2a24]">{facility.facilityName}</p>
                      <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#24425e]">OPTIME Recommendation</p>
                      <p className="mt-1 text-[#24425e]">Patient Match: {summarizeRecommendation(facility.recommendation).patientMatch}</p>
                      <p className="text-[#24425e]">Quality & Safety: {summarizeRecommendation(facility.recommendation).qualitySafety}</p>
                      <p className="text-[#24425e]">Evidence Confidence: {summarizeRecommendation(facility.recommendation).evidenceConfidence}</p>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {patientNeedsRows.map((need) => {
                  const statuses = selectedFacilities.map((facility) => facility.comparisonFacility?.need_rows.find((row) => row.parameter_id === need.parameter_id));
                  return (
                    <tr key={`patient-${need.parameter_id}`}>
                      <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2">
                        <p className="font-semibold text-[#2f2a24]">{need.requirement_level}: {needLabel(need.parameter_id)}</p>
                        <p className="mt-1 text-[10px] text-[#6b6257]">{need.applicable_scope === "FACILITY" ? "Facility-wide" : need.applicable_scope === "PROGRAM" ? "Program-level" : need.applicable_scope === "UNIT" ? "Unit-level" : "Service-level"}</p>
                      </td>
                      {statuses.map((status, index) => {
                        const facility = selectedFacilities[index];
                        if (!facility) return null;
                        return (
                        <td key={`${facility.facilityId}-${need.parameter_id}`} className="border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                          <p className="font-semibold text-[#2f2a24]">{statusLabel(status?.status || "NOT_VERIFIED")}</p>
                          <p className="mt-1 text-[10px] text-[#6b6257]">{status?.scope === "FACILITY" ? "Available facility-wide" : status?.scope === "PROGRAM" ? `Available in a specific program${status?.scope_name ? ` (${status.scope_name})` : ""}` : status?.scope === "UNIT" ? `Available in a specific unit${status?.scope_name ? ` (${status.scope_name})` : ""}` : status?.scope === "SERVICE" ? "Verified service" : "Needs verification"}</p>
                          <p className="text-[10px] text-[#6b6257]">Source: {status?.source || "Not verified"}</p>
                        </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-3xl border border-[#d9e3ec] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#24425e]">All 59 parameters</p>
              <p className="mt-2 text-sm text-[#4a6076]">This section uses the same governed parameter IDs for every facility. Toggle key differences to reduce noise.</p>
            </div>
            <button type="button" onClick={() => setShowDifferencesOnly((current) => !current)} className="rounded-full border border-[#cddce5] bg-[#f6fbff] px-4 py-2 text-sm font-semibold text-[#24425e] hover:bg-[#edf6fb]">
              {showDifferencesOnly ? "Show all rows" : "Show key differences"}
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
                {visibleComparisonRows.map((row) => (
                  <tr key={row.parameterId}>
                    <td className="sticky left-0 z-10 border border-[#d9e3ec] bg-white px-3 py-2 align-top">
                      <p className="font-semibold text-[#2f2a24]">{row.parameterName}</p>
                      <p className="mt-1 text-[10px] text-[#6b6257]">{row.parameterId}</p>
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
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}