"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { SearchFacility, fetchSearchFacilities } from "@/lib/api";

const TOP_RECOMMENDATION_COUNT = 3;

function scoreBadgeStyle(score: number): string {
  if (score >= 90) return "bg-[#5f8768] text-white";
  if (score >= 80) return "bg-[#dbe8d8] text-[#35523d]";
  if (score >= 70) return "bg-[#f0dfad] text-[#6c5322]";
  return "bg-[#f1caa4] text-[#7c4f23]";
}

function highlightLabel(index: number): string {
  if (index === 0) return "Best Match";
  if (index === 1) return "Strong Alternative";
  if (index === 2) return "Good Alternative";
  return "Worth Considering";
}

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function parsePriceRange(priceRange: string): { low: number; high: number } {
  const matches = priceRange.match(/\$([\d,]+)/g) || [];
  const amounts = matches
    .map((value) => Number(value.replace(/[$,]/g, "")))
    .filter((value) => Number.isFinite(value));

  if (amounts.length >= 2) {
    return { low: amounts[0], high: amounts[1] };
  }

  return { low: 0, high: 0 };
}

function careAlignmentScore(facility: SearchFacility, care: string): number {
  const normalizedCare = care.toLowerCase();
  const facilityCareTypes = facility.careTypes.map((item) => item.toLowerCase());

  if (normalizedCare.includes("skilled nursing") && facilityCareTypes.includes("skilled nursing")) return 100;
  if ((normalizedCare.includes("supervision") || normalizedCare.includes("medication") || normalizedCare.includes("bathing") || normalizedCare.includes("dressing")) && facilityCareTypes.includes("assisted living")) return 92;
  if (normalizedCare.includes("independent") && facilityCareTypes.includes("independent living")) return 90;
  if (normalizedCare.includes("memory") && facilityCareTypes.includes("memory care")) return 96;
  return 58;
}

type MatchFactor = {
  label: string;
  detail: string;
  score: number;
};

type ExplanationTableRow = {
  label: string;
  evidence: string;
  score: number | string;
  const strictBudget = strictBudgetRequested(context.notes);
  const memoryNeedsMedical = context.memory.toLowerCase().includes("memory") || context.memory.toLowerCase().includes("significant");
  const wheelchairIsHard = wheelchairMandatory(context.notes);
  const safetyIsHard = criticalSafetyRequired(context.notes);

  return [
    { field: "Care level", value: context.care || "Not specified", classification: "HARD_CONSTRAINT", reason: "Clinical care compatibility is mandatory." },
    { field: "Critical medical limitations", value: context.memory || "Not specified", classification: memoryNeedsMedical ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: memoryNeedsMedical ? "Critical medical requirements must be satisfied." : "No critical medical limitation was marked mandatory." },
    { field: "Critical safety requirements", value: safetyIsHard ? "Mandatory from notes" : "Not marked mandatory", classification: safetyIsHard || wheelchairIsHard ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: safetyIsHard || wheelchairIsHard ? "Safety requirement explicitly marked as required." : "No critical safety requirement was marked mandatory." },
    { field: "Maximum budget", value: `$${context.budget.toLocaleString()}`, classification: strictBudget ? "HARD_CONSTRAINT" : "SOFT_PREFERENCE", reason: strictBudget ? "User notes indicate strict budget cap." : "Budget treated as preference unless explicitly strict." },
    { field: "Language", value: profile.languageProfile.preferredSpokenLanguage || "Not specified", classification: "SOFT_PREFERENCE", reason: "Strong preference, affects ranking only." },
    { field: "Culture", value: profile.culturalProfile.whatFeelsLikeHome.join(", ") || profile.culturalProfile.religionImportance || "Not specified", classification: "SOFT_PREFERENCE", reason: "Strong preference for belonging and identity fit." },
    { field: "Family proximity", value: context.distance || "Not specified", classification: "SOFT_PREFERENCE", reason: "Strong preference, affects engagement and visits." },
    { field: "Continuum of care", value: profile.futureCareProfile.continuumOfCarePreference || "Not specified", classification: "SOFT_PREFERENCE", reason: "Strong preference for long-term transition fit." },
    { field: "Hobbies / Activities", value: context.activity || "Not specified", classification: "SOFT_PREFERENCE", reason: "Nice-to-have quality-of-life preference." },
    { field: "Facilities", value: "Derived from badges", classification: "SOFT_PREFERENCE", reason: "Nice-to-have amenities preference." },
    { field: "Luxury", value: "Derived from badges", classification: "SOFT_PREFERENCE", reason: "Nice-to-have comfort preference." },
  ];
}

function buildRelaxedRecommendations(
  facilities: SearchFacility[],
  context: RelaxationContext,
): {
  recommendations: SearchFacility[];
  relaxations: RelaxationNotice[];
  constraintAudit: ConstraintAuditRow[];
  debug: RecommendationPipelineDebug;
  exactMatchAudit: ExactMatchAuditRow[];
  signalClassifications: SignalClassificationRow[];
  explainableByFacility: Record<number, ExplainableMatchingBreakdown>;
} {
  const baseFacilities = facilities.filter((facility) => facility.matching_confidence !== "LOW");
  const profile = context.profile;
  const notesLower = context.notes.toLowerCase();
  const auditRows = buildConstraintAudit(context);
  const strictBudget = strictBudgetRequested(context.notes);
  const requiresWheelchair = wheelchairMandatory(context.notes);
  const requiresCriticalSafety = criticalSafetyRequired(context.notes);
  const memoryNeedsMedical = context.memory.toLowerCase().includes("memory") || context.memory.toLowerCase().includes("significant");
  const languagePreference = profile.languageProfile.preferredSpokenLanguage;
  const religionImportant = ["Important", "Very important"].includes(profile.culturalProfile.religionImportance);
  const wantsJewishSetting = profile.culturalProfile.israeliJewishCommunityPreference === "Yes" || notesLower.includes("jewish");
  const hardConstraintFailures = (facility: SearchFacility): string[] => {
    const failures: string[] = [];
    const price = midpointPrice(facility.priceRange);
    const careScore = careAlignmentScore(facility, context.care);

    if (careScore < 80) {
      failures.push(`care level mismatch (${context.care})`);
    }
    if (memoryNeedsMedical && !facility.careTypes.some((item) => item.toLowerCase().includes("memory"))) {
      failures.push("critical medical limitation not supported (memory care)");
    }
    if (strictBudget && price !== null && price > context.budget) {
      failures.push(`budget exceeds by $${Math.max(0, Math.round(price - context.budget)).toLocaleString()}`);
    }
    if (requiresWheelchair && !hasBadgeMatch(facility, [/wheelchair/i, /accessible/i, /accessibility/i, /ada/i, /mobility/i])) {
      failures.push("critical safety requirement not verified (accessibility)");
    }
    if (requiresCriticalSafety && !hasBadgeMatch(facility, [/secure/i, /security/i, /fall/i, /monitor/i, /supervision/i, /memory/i])) {
      failures.push("critical safety requirement not verified");
    }

    return failures;
  };

  const hardFiltered = baseFacilities.filter((facility) => hardConstraintFailures(facility).length === 0);

  const candidates = hardFiltered.length > 0 ? hardFiltered : baseFacilities;

  const hasActivityData = (facility: SearchFacility): boolean =>
    hasBadgeMatch(facility, [/social/i, /active/i, /movie/i, /cinema/i, /film/i, /music/i, /garden/i, /swim/i, /art/i, /pet/i, /luxury/i, /program/i]);
  const hasDistanceData = (facility: SearchFacility): boolean => hasBadgeMatch(facility, [/close to family/i, /family/i, /distance/i, /drive/i]);
  const hasFacilityData = (facility: SearchFacility): boolean => hasBadgeMatch(facility, [/amenity/i, /facility/i, /pool/i, /gym/i, /garden/i, /library/i, /spa/i]);
  const hasLuxurySignal = (facility: SearchFacility): boolean => hasBadgeMatch(facility, [/luxury/i, /premium/i, /upscale/i, /resort/i]);

  const softPreferences: Array<{
    key: string;
    originalRequirement: string;
    relaxedRequirement: string;
    enabled: boolean;
    weight: number;
    category: SignalCategory;
    score: (facility: SearchFacility) => number;
    rejectionReason: (facility: SearchFacility) => string;
  }> = [
    {
      key: "hobbies-activities",
      originalRequirement: context.activity || "Not specified",
      relaxedRequirement: "Activity mix differs from preference",
      enabled: Boolean(context.activity),
      weight: 10,
      category: "NICE TO HAVE",
      score: (facility) => {
        if (!context.activity) return 60;
        const normalized = context.activity.toLowerCase();
        if (normalized.includes("social")) return hasBadgeMatch(facility, [/social/i, /active/i]) ? 100 : 35;
        if (normalized.includes("religious")) return hasBadgeMatch(facility, [/religious/i, /faith/i, /synagogue/i, /jewish/i]) ? 100 : 30;
        if (normalized.includes("music")) return hasBadgeMatch(facility, [/active/i, /program/i]) ? 85 : 45;
        return 55;
      },
      rejectionReason: (facility) => {
        const normalized = context.activity.toLowerCase();
        if (normalized.includes("movie")) {
          return hasBadgeMatch(facility, [/movie/i, /cinema/i, /film/i]) ? "" : "no movie activity";
        }
        if (normalized.includes("music")) {
          return hasBadgeMatch(facility, [/music/i, /program/i]) ? "" : "no music activity signal";
        }
        if (normalized.includes("social")) {
          return hasBadgeMatch(facility, [/social/i, /active/i]) ? "" : "no social activity signal";
        }
        return "activity preference not fully matched";
      },
    },
    {
      key: "facilities",
      originalRequirement: "Preferred amenities",
      relaxedRequirement: "Facility amenities may differ",
      enabled: true,
      weight: 7,
      category: "NICE TO HAVE",
      score: (facility) => hasFacilityData(facility) ? 90 : 55,
      rejectionReason: () => "",
    },
    {
      key: "luxury",
      originalRequirement: "Luxury level",
      relaxedRequirement: "Luxury signals may be limited",
      enabled: true,
      weight: 5,
      category: "NICE TO HAVE",
      score: (facility) => hasLuxurySignal(facility) ? 88 : 52,
      rejectionReason: () => "",
    },
    {
      key: "language",
      originalRequirement: languagePreference || "Not specified",
      relaxedRequirement: "Language support may be partial",
      enabled: Boolean(languagePreference && languagePreference !== "English"),
      weight: 12,
            <details className="rounded-3xl border border-[#d9decb] bg-[#f8fbf1] p-4 shadow-[0_12px_34px_-28px_rgba(54,84,32,0.35)]">
              <summary className="cursor-pointer list-none text-sm font-semibold uppercase tracking-[0.16em] text-[#5c7340]">
                Show recommendation diagnostics
              </summary>
              <div className="mt-4 space-y-6">
                <article className="rounded-3xl border border-[#d9decb] bg-[#f8fbf1] p-6 shadow-[0_12px_34px_-28px_rgba(54,84,32,0.35)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5c7340]">Signal Classification Engine V1</p>
                  <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Preference signal categories</h2>
                  <div className="mt-4 overflow-x-auto rounded-2xl border border-[#dfe7cf] bg-white">
                    <table className="min-w-full divide-y divide-[#e9efdd] text-sm text-[#425041]">
                      <thead className="bg-[#f2f7e8] text-left text-xs uppercase tracking-[0.14em] text-[#6b775a]">
                        <tr>
                          <th className="px-4 py-3">Signal</th>
                          <th className="px-4 py-3">Category</th>
                          <th className="px-4 py-3">Value</th>
                          <th className="px-4 py-3">Rationale</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#edf2e4]">
                        {relaxedAvailability.signalClassifications.map((row) => (
                          <tr key={`${row.signal}-${row.category}`}>
                            <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.signal}</td>
                            <td className="px-4 py-3">
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                row.category === "HARD REQUIREMENT"
                                  ? "bg-[#fde7e2] text-[#a54c34]"
                                  : row.category === "STRONG PREFERENCE"
                                    ? "bg-[#edf3ea] text-[#4c6f5b]"
                                    : row.category === "NICE TO HAVE"
                                      ? "bg-[#e7eefb] text-[#3f5f8c]"
                                      : "bg-[#f5f1e5] text-[#6f644e]"
                              }`}>
                                {row.category}
                              </span>
                            </td>
                            <td className="px-4 py-3">{row.value}</td>
                            <td className="px-4 py-3">{row.rationale}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-3 text-xs text-[#6a655b]">Engine rules: UNKNOWN SIGNAL and NICE TO HAVE never reject; STRONG PREFERENCE rarely rejects exact matching; only HARD REQUIREMENT can reject recommendation eligibility.</p>
                </article>

                <article className="rounded-3xl border border-[#d8dbe2] bg-[#f7f9fc] p-6 shadow-[0_12px_34px_-28px_rgba(36,49,72,0.45)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#44526b]">Recommendation Pipeline Debug</p>
                  <div className="mt-3 overflow-x-auto rounded-2xl border border-[#d5dbe6] bg-white">
                    <table className="min-w-full divide-y divide-[#e3e8f0] text-sm text-[#334155]">
                      <tbody className="divide-y divide-[#eef2f7]">
                        <tr><td className="px-4 py-3 font-medium">communities_loaded</td><td className="px-4 py-3">{relaxedAvailability.debug.communities_loaded}</td></tr>
                        <tr><td className="px-4 py-3 font-medium">exact_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.exact_matches}</td></tr>
                        <tr><td className="px-4 py-3 font-medium">soft_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.soft_matches}</td></tr>
                        <tr><td className="px-4 py-3 font-medium">fallback_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.fallback_matches}</td></tr>
                        <tr><td className="px-4 py-3 font-medium">rendered_results</td><td className="px-4 py-3">{relaxedAvailability.debug.rendered_results}</td></tr>
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf2] p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Recommendation Filter Audit</p>
                  <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Hard constraints vs soft preferences</h2>
                  <p className="mt-2 text-sm text-[#5c5347]">Default rule applied: everything is SOFT_PREFERENCE unless explicitly mandatory.</p>
                  <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                    <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                      <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                        <tr>
                          <th className="px-4 py-3">Input field</th>
                          <th className="px-4 py-3">Value</th>
                          <th className="px-4 py-3">Classification</th>
                          <th className="px-4 py-3">Why</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#efe6d8]">
                        {relaxedAvailability.constraintAudit.map((row) => (
                          <tr key={`${row.field}-${row.value}`}>
                            <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.field}</td>
                            <td className="px-4 py-3">{row.value}</td>
                            <td className="px-4 py-3">{row.classification}</td>
                            <td className="px-4 py-3">{row.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                {relaxedAvailability.exactMatchAudit.length > 0 ? (
                  <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Exact Match Audit</p>
                    <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Rejected communities and reasons</h2>
                    <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                      <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                        <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                          <tr>
                            <th className="px-4 py-3">community_name</th>
                            <th className="px-4 py-3">rejection_reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#efe6d8]">
                          {relaxedAvailability.exactMatchAudit.slice(0, 100).map((row) => (
                            <tr key={`${row.community_name}-${row.rejection_reason}`}>
                              <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.community_name}</td>
                              <td className="px-4 py-3">{row.rejection_reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </article>
                ) : null}

                {relaxedAvailability.relaxations.length > 0 ? (
                  <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf2] p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                    <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Soft Preference Gaps</p>
                    <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Best available communities returned; these preferences are not fully satisfied:</h2>
                    <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                      <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                        <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                          <tr>
                            <th className="px-4 py-3">Preference</th>
                            <th className="px-4 py-3">Original requirement</th>
                            <th className="px-4 py-3">Not fully satisfied note</th>
                            <th className="px-4 py-3">Top-3 communities meeting this</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#efe6d8]">
                          {relaxedAvailability.relaxations.map((item) => (
                            <tr key={`${item.preference}-${item.originalRequirement}`}>
                              <td className="px-4 py-3 font-medium text-[#2f2a24]">{item.preference}</td>
                              <td className="px-4 py-3">{item.originalRequirement}</td>
                              <td className="px-4 py-3">{item.relaxedRequirement}</td>
                              <td className="px-4 py-3">{item.impactOnResultsCount}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </article>
                ) : null}

                <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Expert Advisor Mode</p>
                  <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Personal explanation</h2>
                  <p className="mt-3 text-sm leading-7 text-[#554c41]">{personalAdvisorSummary}</p>
                </article>

                <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.35)]">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Cultural Intelligence Scorecard</p>
                  <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Belonging and adjustment signals</h2>
                  <p className="mt-2 text-sm text-[#5c5347]">
                    These scores come from direct answers only and support mixed identities and multicultural households.
                  </p>

                  <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                    <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                      <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                        <tr>
                          <th className="px-4 py-3">Output score</th>
                          <th className="px-4 py-3">Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#efe6d8]">
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">language_match_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.language_fit_score}</td></tr>
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">religious_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.religious_fit_score}</td></tr>
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">cultural_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.cultural_fit_score}</td></tr>
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">food_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.food_fit_score}</td></tr>
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">family_engagement_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.family_engagement_score}</td></tr>
                        <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">community_style_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.community_style_score}</td></tr>
                      </tbody>
                    </table>
                  </div>

                  {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.length > 0 ? (
                    <div className="mt-4 rounded-2xl border border-[#e7dbc6] bg-[#fffdfa] p-4">
                      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Recommendation impact</p>
                      <ul className="mt-3 space-y-2 text-sm text-[#564d42]">
                        {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.map((impact) => (
                          <li key={impact}>• {impact}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {state.humanIntelligenceV2.scoringEngine.overallConfidence < state.humanIntelligenceV2.scoringEngine.confidenceThreshold ? (
                    <p className="mt-4 text-sm text-[#8c5c40]">
                      Confidence is below threshold; additional question asked: {state.humanIntelligenceV2.scoringEngine.additionalQuestionAsked || "How often do you expect to visit?"}
                    </p>
                  ) : null}
                </article>
              </div>
            </details>
          normalizedWeight: 0.7,
          score: Math.round(baseScore),
          weightedScore: Number((baseScore * BASE_WEIGHT).toFixed(2)),
          contributionToFinal: Number((baseScore * BASE_WEIGHT).toFixed(2)),
        },
        ...softRows.map((row) => ({
          signal: row.preference.key,
          category: row.preference.category,
          rawWeight: row.preference.weight,
          normalizedWeight: Number(row.normalizedWeight.toFixed(4)),
          score: Math.round(row.score),
          weightedScore: Number(row.weightedScore.toFixed(2)),
          contributionToFinal: Number(row.contributionToFinal.toFixed(2)),
        })),
      ];

      const finalScore: ExplainableFinalScore = {
        baseScore: Math.round(baseScore),
        baseWeight: BASE_WEIGHT,
        preferenceAggregate: Number(softScore.toFixed(2)),
        preferenceWeight: SOFT_WEIGHT,
        weightedBase: Number((baseScore * BASE_WEIGHT).toFixed(2)),
        weightedPreferences: Number((softScore * SOFT_WEIGHT).toFixed(2)),
        softPenalty: Number(softPenalty.toFixed(2)),
        hardPenalty,
        finalScore: combined,
      };

      explainableByFacility[facility.id] = {
        positiveContributors,
        negativeContributors,
        tradeoffs,
        uncertainty,
        weightBreakdown,
        finalScore,
      };

      return { facility, combined, softScore };
    })
    .sort((left, right) => right.combined - left.combined || right.softScore - left.softScore || left.facility.id - right.facility.id)
    .map((item) => item.facility);

  const recommendations = ranked.length > 0 ? ranked : baseFacilities;
  const topForAudit = recommendations.slice(0, Math.min(3, recommendations.length));
  const relaxations: RelaxationNotice[] = enabledSoft
    .map((preference) => {
      const satisfiedCount = topForAudit.filter((facility) => preference.score(facility) >= 70).length;
      return {
        preference: preference.key,
        originalRequirement: preference.originalRequirement,
        relaxedRequirement: preference.relaxedRequirement,
        impactOnResultsCount: satisfiedCount,
      };
    })
    .filter((item) => item.impactOnResultsCount < topForAudit.length);

  if (hardFiltered.length === 0 && baseFacilities.length > 0) {
    relaxations.unshift({
      preference: "hard-constraint-inventory",
      originalRequirement: "All hard constraints",
      relaxedRequirement: "No exact hard-constraint inventory found; returning closest available communities",
      impactOnResultsCount: recommendations.length,
    });
  }

  const exactMatchAudit: ExactMatchAuditRow[] = [];
  const exactMatches = candidates.filter((facility) => {
    const hardFailures = hardConstraintFailures(facility);
    const reasons = [...hardFailures];
    if (reasons.length > 0) {
      exactMatchAudit.push({
        community_name: facility.name,
        rejection_reason: reasons.join("; "),
      });
      return false;
    }

    return true;
  }).length;
  const softMatches = hardFiltered.length;
  const fallbackMatches = exactMatches === 0 ? recommendations.length : 0;

  const debug: RecommendationPipelineDebug = {
    communities_loaded: facilities.length,
    exact_matches: exactMatches,
    soft_matches: softMatches,
    fallback_matches: fallbackMatches,
    rendered_results: recommendations.length,
  };

  return { recommendations, relaxations, constraintAudit: auditRows, debug, exactMatchAudit, signalClassifications, explainableByFacility };
}

function buildResidentProfileSummary(
  relationship: string,
  age: string,
  care: string,
  memory: string,
  activity: string,
  distance: string,
  notes: string,
): string {
  const noteWords = normalizeWords(notes);
  const profileFacts = [
    `${relationship.toLowerCase()} in the ${age} age range`,
    `${care.toLowerCase()} support needs`,
  ];

  if (!memory.toLowerCase().includes("no") && !memory.toLowerCase().includes("not sure")) {
    profileFacts.push(memory.toLowerCase());
  }

  if (activity) {
    profileFacts.push(`${activity.toLowerCase()} matters day to day`);
  }

  if (distance) {
    profileFacts.push(`family distance preference is ${distance.toLowerCase()}`);
  }

  if (noteWords.includes("widowed")) {
    profileFacts.push("recently widowed")
  }

  if (noteWords.includes("jewish")) {
    profileFacts.push("prefers a Jewish environment");
  }

  if (noteWords.includes("hebrew")) {
    profileFacts.push("speaks Hebrew and English");
  }

  if (noteWords.includes("independent") || care.toLowerCase().includes("independent")) {
    profileFacts.push("wants to remain independent");
  }

  if (notes.trim()) {
    profileFacts.push(`additional family note: ${notes.trim()}`);
  }

  return profileFacts.join(", ");
}

function inferCommunitySizeLabel(beds?: number): string {
  if (!beds) return "unknown community size";
  if (beds <= 55) return `small ${beds}-bed community`;
  if (beds <= 120) return `mid-sized ${beds}-bed community`;
  return `large ${beds}-bed campus`;
}

function buildSourcesAnalyzed(facility: SearchFacility): string[] {
  const sources = [
    facility.cms_verified ? "CMS profile" : "",
    facility.license_verified ? "State license profile" : "",
    facility.website_verified ? "Official website" : "",
    facility.phone_verified ? "Phone verification" : "",
    ...(facility.scoreBreakdown?.flatMap((item) => item.dataSource) ?? []),
  ];

  return uniqueStrings(sources);
}

function buildConfidenceScore(facility: SearchFacility, sourcesAnalyzed: string[]): number {
  const sourceBoost = Math.min(18, sourcesAnalyzed.length * 3);
  const ratingBoost = ((facility.overall_rating ?? 0) + (facility.staffing_rating ?? 0) + (facility.inspection_rating ?? 0)) * 2;
  return Math.max(42, Math.min(98, Math.round(facility.verification_score * 0.55 + sourceBoost + ratingBoost)));
}

function buildPersonalizedExplanation(
  facility: SearchFacility,
  context: {
    relationship: string;
    age: string;
    care: string;
    activity: string;
    memory: string;
    budget: number;
    distance: string;
    notes: string;
    distanceProfile?: DistanceProfile;
  },
): PersonalizedExplanation {
  const factors = buildMatchFactors(facility, context);
  const notesLower = context.notes.toLowerCase();
  const sourcesAnalyzed = buildSourcesAnalyzed(facility);
  const confidenceScore = buildConfidenceScore(facility, sourcesAnalyzed);
  const communitySize = inferCommunitySizeLabel(facility.beds);
  const hasMemoryCare = facility.careTypes.some((item) => item.toLowerCase().includes("memory"));
  const hasSkilledNursing = facility.careTypes.some((item) => item.toLowerCase().includes("skilled nursing"));
  const hasHebrewSupport = facility.matchBadges.some((badge) => badge.toLowerCase().includes("hebrew"));
  const isSocial = facility.matchBadges.some((badge) => badge.toLowerCase().includes("social") || badge.toLowerCase().includes("active"));
  const priceRange = parsePriceRange(facility.priceRange);
  const averagePrice = priceRange.low && priceRange.high ? Math.round((priceRange.low + priceRange.high) / 2) : 0;
  const overBudget = averagePrice > context.budget;
  const distanceProfile = context.distanceProfile;
  const distanceFlexible = context.distance.toLowerCase() === "anywhere" || distanceProfile?.optimizationStrategy === "Family visit maximization";
  const mentionsJewish = notesLower.includes("jewish");
  const mentionsHebrew = notesLower.includes("hebrew");
  const mentionsWidowed = notesLower.includes("widowed");
  const familyVisitExpectation = distanceProfile?.familyVisitExpectation || context.distance;
  const normalDriveTime = distanceProfile?.driveTimes.normal || "unknown";
  const rushHourDriveTime = distanceProfile?.driveTimes.rushHour || "unknown";
  const emergencyDriveTime = distanceProfile?.driveTimes.emergency || "unknown";
  const familyDistanceScore = distanceProfile?.scores.family_distance_score;
  const familyEngagementScore = distanceProfile?.scores.family_engagement_score;

  const fitsYou = [
    `${sentenceCase(context.relationship)} is looking for ${context.care.toLowerCase()} support, and ${facility.name} explicitly offers ${facility.careTypes.join(", ")}.`,
    `${sentenceCase(context.relationship)} values ${context.activity.toLowerCase()}, and the community profile highlights ${facility.matchBadges[0] ?? "relevant daily programming"}.`,
    `Family distance now includes ${familyVisitExpectation.toLowerCase()} with normal drive time ${normalDriveTime}, rush-hour drive time ${rushHourDriveTime}, and emergency access ${emergencyDriveTime}. That should be weighed against ${communitySize}, the current $${context.budget.toLocaleString()} monthly budget, and the stated family engagement priority${familyEngagementScore ? ` (${familyEngagementScore}/100)` : ""}${familyDistanceScore ? `, family distance score ${familyDistanceScore}/100` : ""}.`
  ];

  if (mentionsWidowed) {
    fitsYou.push(`${sentenceCase(context.relationship)} was described as recently widowed, so the social rhythm and daily interaction level matter more than a generic rating.`);
  }

  if (mentionsJewish || mentionsHebrew) {
    fitsYou.push(`${sentenceCase(context.relationship)} also has a cultural or language preference in the profile notes, so visible evidence like ${hasHebrewSupport ? "Hebrew-speaking staff" : "the absence of verified Hebrew-language support"} should be part of the tour discussion.`);
  }

  const strengths: ExplanationListItem[] = [
    {
      title: "Care alignment",
      detail: `${facility.careTypes.join(", ")} directly covers the requested ${context.care.toLowerCase()} support profile.`
    },
    {
      title: "Regulatory quality",
      detail: `The current ratings show overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, and inspection ${facility.inspection_rating ?? "n/a"}/5.`
    },
    {
      title: "Lifestyle signal",
      detail: `${communitySize} with badges such as ${facility.matchBadges.slice(0, 2).join(" and ")} gives a concrete view of how daily life may feel.`
    },
  ];

  if (hasHebrewSupport) {
    strengths.push({
      title: "Language support",
      detail: `The community profile explicitly surfaces Hebrew-speaking staff, which is directly relevant to the resident profile.`
    });
  }

  if (hasMemoryCare && !context.memory.toLowerCase().includes("no")) {
    strengths.push({
      title: "Memory support",
      detail: `Memory care appears in the care mix, which matters because the profile mentions ${context.memory.toLowerCase()}.`
    });
  }

  const weaknesses: ExplanationListItem[] = [];

  if (!hasMemoryCare && !context.memory.toLowerCase().includes("no") && !context.memory.toLowerCase().includes("not sure")) {
    weaknesses.push({
      title: "Limited memory support",
      detail: `The listed care types do not show memory care even though the profile mentions ${context.memory.toLowerCase()}.`
    });
  }

  if (!hasHebrewSupport && (mentionsHebrew || mentionsJewish)) {
    weaknesses.push({
      title: "Unverified cultural match",
      detail: `The current community evidence does not verify Hebrew-speaking staff or a Jewish program, even though the profile notes make that relevant.`
    });
  }

  if (facility.beds && facility.beds > 120) {
    weaknesses.push({
      title: "Large setting",
      detail: `${communitySize} may feel overwhelming if the resident does better in a more intimate environment.`
    });
  }

  if (overBudget) {
    weaknesses.push({
      title: "Budget pressure",
      detail: `The midpoint of ${facility.priceRange} is above the stated $${context.budget.toLocaleString()} monthly budget.`
    });
  }

  if (!weaknesses.length) {
    weaknesses.push({
      title: "Distance clarity needed",
      detail: `The current recommendation view does not verify actual drive time, so family visit practicality still needs confirmation during the tour.`
    });
  }

  const tradeoffs: ExplanationListItem[] = [
    {
      title: "Clinical support vs. familiarity",
      detail: `${hasSkilledNursing ? "Stronger medical support is visible in the care mix" : "The setting leans more residential than clinical"}, but the family still needs to confirm whether that matches the resident's day-to-day comfort.`
    },
    {
      title: "Lifestyle vs. cost",
      detail: `${isSocial ? "The community signals an active social rhythm" : "The lifestyle signal is quieter and less activity-led"}, while ${overBudget ? "pricing may stretch the budget" : "pricing appears more manageable against the stated budget"}.`
    },
    {
      title: "Verification depth",
      detail: `${confidenceScore >= 80 ? "Several verified sources are present" : "Verification is still moderate"}, so some family-specific fit details need live confirmation on the tour.`
    },
  ];

  const questions = uniqueStrings([
    mentionsHebrew ? "Are there Hebrew-speaking residents or staff available during the day and overnight?" : "How do new residents get introduced into daily life and activities during the first month?",
    context.activity.toLowerCase().includes("social") ? "How many residents typically participate in the main social activities each week?" : `How often are ${context.activity.toLowerCase()} options available each week?`,
    !context.memory.toLowerCase().includes("no") ? "How do staff handle changes in memory, confusion, or redirection during evenings?" : "How quickly does staff respond when a resident needs help during evenings or overnight?",
    overBudget ? "Which fees are fixed, and which services could increase the monthly cost over time?" : "What services are included in the current monthly price range, and which ones are billed separately?",
    "How long has the Executive Director and the nursing leadership team been in place?",
  ]).slice(0, 5);

  const strongMatches = uniqueStrings(factors.map((factor) => factor.label).concat(strengths.slice(0, 2).map((item) => item.title))).slice(0, 5);
  const majorConcerns = uniqueStrings(weaknesses.map((item) => item.title)).slice(0, 5);

  const matchingDimensions: ExplanationTableRow[] = [
    ...factors.map((factor) => ({ label: factor.label, evidence: factor.detail, score: factor.score })),
    { label: "Community scale", evidence: communitySize, score: facility.beds ?? "n/a" },
    { label: "Regulatory confidence", evidence: `Overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, inspection ${facility.inspection_rating ?? "n/a"}/5`, score: confidenceScore },
  ].slice(0, 5);

  const profileSummary = buildResidentProfileSummary(
    context.relationship,
    context.age,
    context.care,
    context.memory,
    context.activity,
    familyVisitExpectation,
    context.notes,
  );

  const narrative = [
    `${sentenceCase(context.relationship)} is not looking for a generic top-rated community. The profile here is more specific: ${profileSummary}. That matters because ${facility.name} needs to be judged on whether its actual operating profile lines up with those lived priorities, not just on a single score. In practical terms, this community appears most aligned where it can directly support ${context.care.toLowerCase()} needs through ${facility.careTypes.join(", ")}, while also showing visible lifestyle signals such as ${facility.matchBadges.slice(0, 3).join(", ")}.`,
    `What stands out for this particular resident is the combination of care coverage and day-to-day environment. The current evidence shows regulatory performance at overall ${facility.overall_rating ?? "n/a"}/5, staffing ${facility.staffing_rating ?? "n/a"}/5, and inspection ${facility.inspection_rating ?? "n/a"}/5. That gives the family a concrete starting point on safety and staffing. At the same time, ${communitySize} changes how the experience may actually feel. If ${context.activity.toLowerCase()} and regular engagement are important, the social and activity badges matter because they suggest how easy it may be for ${context.relationship.toLowerCase()} to settle into a routine instead of feeling passive or isolated.` ,
    `${mentionsWidowed ? `Because the profile notes mention that ${context.relationship.toLowerCase()} is recently widowed, the emotional side of transition should carry real weight during the visit. ` : ""}${mentionsJewish || mentionsHebrew ? `Because the family also noted a Jewish or Hebrew preference, the team should verify whether that support is truly part of daily life rather than a one-time marketing claim. ` : ""}The limitations are just as important. ${weaknesses[0].detail} ${weaknesses[1]?.detail ?? "There are also still fit questions that cannot be answered from the current data alone."} That means the tour should test the lived experience, not just confirm availability.` ,
    `The real tradeoff here is that ${facility.name} may offer ${hasSkilledNursing ? "stronger medical depth" : "a more residential feel"} while still requiring the family to check whether distance, leadership stability, culture, and pricing work in the resident's actual routine. This is why the recommendation needs to stay personalized: for ${context.relationship.toLowerCase()} in the ${context.age} range, with ${context.care.toLowerCase()} needs and ${context.activity.toLowerCase()} priorities, the question is not whether the community looks good in general. The question is whether this specific place can support a stable first year after move-in.`
  ].join(" ");

  return {
    profileSummary,
    fitsYou,
    strengths,
    weaknesses,
    tradeoffs,
    questions,
    strongMatches,
    majorConcerns,
    sourcesAnalyzed,
    confidenceScore,
    matchingDimensions,
    narrative,
  };
}

function buildMatchFactors(
  facility: SearchFacility,
  context: { budget: number; care: string; activity: string; memory: string; distance: string; distanceProfile?: DistanceProfile },
): MatchFactor[] {
  const priceRange = parsePriceRange(facility.priceRange);
  const priceTarget = priceRange.low > 0 && priceRange.high > 0 ? (priceRange.low + priceRange.high) / 2 : context.budget;
  const budgetGap = Math.abs(priceTarget - context.budget);
  const budgetScore = Math.max(40, 100 - Math.round(budgetGap / 180));

  const factors: MatchFactor[] = [
    {
      label: "Budget fit",
      detail: `${facility.priceRange} sits against your $${context.budget.toLocaleString()} budget`,
      score: budgetScore,
    },
    {
      label: "Staffing strength",
      detail: `Staffing rating is ${facility.staffing_rating ?? 0}/5`,
      score: (facility.staffing_rating ?? 0) * 20,
    },
    {
      label: "Activity alignment",
      detail: `${context.activity} preference lines up with ${facility.matchBadges[0] ?? "the community profile"}`,
      score: facility.matchBadges.some((badge) => badge.toLowerCase().includes("social") || badge.toLowerCase().includes("active")) ? 88 : 60,
    },
    {
      label: "Care level fit",
      detail: `${context.care} is supported by ${facility.careTypes.join(", ")}`,
      score: careAlignmentScore(facility, context.care),
    },
    {
      label: "Memory support",
      detail: `${context.memory} matches ${facility.matchBadges.includes("Memory support available") ? "available memory support" : "the current service profile"}`,
      score: context.memory.toLowerCase().includes("memory") ? (facility.matchBadges.includes("Memory support available") ? 94 : 55) : 50,
    },
    {
      label: "Community size",
      detail: `${facility.beds ?? 0} beds defines the community scale`,
      score: facility.beds ? Math.max(50, 100 - Math.abs((facility.beds ?? 0) - 80) / 2) : 40,
    },
    {
      label: "Language support",
      detail: facility.matchBadges.includes("Hebrew speaking staff") ? "Hebrew speaking staff surfaced in the profile" : "No language-specific claim surfaced",
      score: facility.matchBadges.includes("Hebrew speaking staff") ? 93 : 42,
    },
    {
      label: "Distance preference",
      detail: context.distance,
      score: context.distance.toLowerCase() === "anywhere" ? 48 : 72,
    },
  ];

  return factors
    .sort((left, right) => right.score - left.score || left.label.localeCompare(right.label))
    .slice(0, 3);
}

export function ResultsPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { state, resetState } = useQuestionnaire();
  const [facilities, setFacilities] = useState<SearchFacility[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showMoreCommunities, setShowMoreCommunities] = useState(false);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [dismissedFilters, setDismissedFilters] = useState<string[]>([]);
  const recommendationsRef = useRef<HTMLDivElement | null>(null);

  const searchKey = searchParams.toString();
  const hasExplicitSearch = searchKey.length > 0;

  const selectedRelationship = searchParams.get("relationship") || state.relationship || "";
  const relationship = relationshipCopy(selectedRelationship);
  const age = searchParams.get("age") || state.ageGroup || "80-84";
  const care = searchParams.get("care") || state.assistanceLevel || "Help with bathing";
  const activity = (searchParams.get("activities") || state.happinessPreferences?.[0] || "Movies").split(",")[0];
  const memory = searchParams.get("memory") || state.memoryStatus || "Not sure";
  const budget = Number(searchParams.get("budget") || state.budget || 7000);
  const notes = searchParams.get("notes") || state.notes || "";
  const textQuery = searchParams.get("q") || searchParams.get("search") || "";

  const hasRealAddresses = Boolean(
    state.humanIntelligenceV2.distanceProfile.referenceLocations.parentCurrentHome ||
    state.humanIntelligenceV2.distanceProfile.referenceLocations.primaryCaregiverHome ||
    state.humanIntelligenceV2.distanceProfile.referenceLocations.secondaryFamilyHomes ||
    state.humanIntelligenceV2.distanceProfile.referenceLocations.preferredHospital ||
    state.humanIntelligenceV2.distanceProfile.referenceLocations.placeOfWorship ||
    state.humanIntelligenceV2.distanceProfile.driveTimes.normal ||
    state.humanIntelligenceV2.distanceProfile.driveTimes.rushHour ||
    state.humanIntelligenceV2.distanceProfile.driveTimes.emergency,
  );

  const distance = hasRealAddresses
    ? (searchParams.get("distance") || state.distanceFromFamily || "Under 25 minutes")
    : "";

  const visibleFilters = useMemo(() => {
    const items: Array<{ label: string; disabled?: boolean }> = [];
    if (!hasExplicitSearch || searchParams.get("age")) items.push({ label: `Age: ${age}` });
    if (!hasExplicitSearch || searchParams.get("care")) items.push({ label: `Care: ${care}` });
    if (!hasExplicitSearch || searchParams.get("activities")) items.push({ label: `Activities: ${activity}` });
    if (!hasExplicitSearch || searchParams.get("budget")) items.push({ label: `Budget: $${budget.toLocaleString()}` });
    items.push({ label: hasRealAddresses ? `Distance: ${distance || "Not specified"}` : "Distance: Not used", disabled: !hasRealAddresses });
    return items;
  }, [hasExplicitSearch, searchParams, age, care, activity, budget, distance, hasRealAddresses]);

  useEffect(() => {
    setDismissedFilters([]);
  }, [searchKey, hasRealAddresses]);

  const filters = visibleFilters.filter((filter) => !dismissedFilters.includes(filter.label));

  const rankedFacilities = useMemo(
    () =>
      [...facilities]
        .filter((facility) => facility.matching_confidence !== "LOW")
        .sort((left, right) => right.optimeScore - left.optimeScore || left.id - right.id),
    [facilities],
  );

  const relaxedAvailability = useMemo(
    () =>
      buildRelaxedRecommendations(rankedFacilities, {
        budget,
        care,
        memory,
        activity,
        distance,
        notes,
        profile: hasRealAddresses ? state.humanIntelligenceV2 : {
          ...state.humanIntelligenceV2,
          distanceProfile: {
            ...state.humanIntelligenceV2.distanceProfile,
            referenceLocations: {
              parentCurrentHome: "",
              primaryCaregiverHome: "",
              secondaryFamilyHomes: "",
              preferredHospital: "",
              placeOfWorship: "",
            },
            driveTimes: { normal: "", rushHour: "", emergency: "" },
            familyVisitExpectation: "",
            familyGeographyModel: {
              involvedFamilyMembers: "",
              familyCenterOfGravity: "",
              multiLocationOptimization: "",
            },
            emotionalDistanceFactors: {
              emergencyAccessImportance: "",
              spontaneousVisitsImportance: "",
              grandchildrenVisitsImportance: "",
            },
            careLevelWeight: 0,
            optimizationStrategy: "",
            scores: {
              family_distance_score: null,
              visit_probability_score: null,
              emergency_access_score: null,
              grandchildren_access_score: null,
              travel_burden_score: null,
              family_engagement_score: null,
            },
            inferredConfidence: {},
          },
        },
      }),
    [rankedFacilities, budget, care, memory, activity, distance, notes, state.humanIntelligenceV2, hasRealAddresses],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadFacilities() {
      setIsLoading(true);
      const data = await fetchSearchFacilities(textQuery);
      if (isMounted) {
        setFacilities(data);
        setIsLoading(false);
      }
    }

    loadFacilities();
    return () => {
      isMounted = false;
    };
  }, [textQuery]);

  useEffect(() => {
    if (isLoading) return;
    console.info("Recommendation Pipeline Debug", relaxedAvailability.debug);
  }, [isLoading, relaxedAvailability.debug]);

  const topRecommendations = useMemo(
    () => relaxedAvailability.recommendations.slice(0, TOP_RECOMMENDATION_COUNT),
    [relaxedAvailability.recommendations],
  );
  const remainingRecommendations = useMemo(
    () => relaxedAvailability.recommendations.slice(TOP_RECOMMENDATION_COUNT),
    [relaxedAvailability.recommendations],
  );

  useEffect(() => {
    if (isLoading || topRecommendations.length === 0) return;
    recommendationsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [isLoading, topRecommendations.length]);

  const personalAdvisorSummary = useMemo(() => {
    const profile = state.humanIntelligenceV2;
    const relationshipNarrative = relationship === "You" || relationship === "You both" ? relationship : `your ${relationship.toLowerCase()}`;
    const lonelinessRisk = profile.transitionRiskProfile.lonelinessRisk || "unknown";
    const livingAlone = profile.socialProfile.livingAloneDuration || "unknown duration";
    const social = profile.socialProfile.socialInteractionFrequency || "unknown social rhythm";
    const language = profile.languageProfile.preferredSpokenLanguage || "English";
    const religion = profile.culturalProfile.religionImportance || "not specified";
    const hobbies = profile.socialProfile.hobbyParticipation.join(", ") || "not specified";
    const fear = profile.transitionRiskProfile.biggestFear || "not specified";
    const proximity = hasRealAddresses ? (profile.distanceProfile.familyVisitExpectation || distance || "not specified") : "not used yet";
    const scoreCard = profile.scoringEngine.outputScores;
    const culturalSignals = profile.scoringEngine.recommendationImpacts.slice(0, 3).join(" ") || "No additional high-impact cultural signals were detected.";

    return `${relationshipNarrative} profile shows ${age} age range, living alone for ${livingAlone}, with social rhythm ${social}. Preferred language is ${language}, religion importance is ${religion}, hobbies include ${hobbies}, and family proximity requirement is ${proximity}. Biggest transition fear is ${fear}. Loneliness risk appears ${lonelinessRisk}. Cultural intelligence outputs: language match ${scoreCard.language_fit_score}, religious fit ${scoreCard.religious_fit_score}, cultural fit ${scoreCard.cultural_fit_score}, food fit ${scoreCard.food_fit_score}, family engagement ${scoreCard.family_engagement_score}, community style ${scoreCard.community_style_score}. Recommendation impacts: ${culturalSignals}`;
  }, [state.humanIntelligenceV2, relationship, age, distance, hasRealAddresses]);

  const removeFilter = (value: string) => {
    setDismissedFilters((current) => current.concat(value));
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

  const startNewSearch = () => {
    resetState();
    router.replace("/");
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#fffdf8_0%,#f8f5ec_22%,#ffffff_45%)] px-4 py-6 sm:px-8 lg:px-12">
      <section className="mx-auto max-w-7xl">
        <header className="rounded-3xl border border-[#e9dfce] bg-white/90 p-6 shadow-[0_22px_80px_-42px_rgba(82,65,42,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5f7f6b]">OPTIME Results</p>
          <h1 className="mt-3 text-3xl font-semibold text-[#2f2a24] sm:text-4xl">Recommended communities for {relationship}</h1>
          <p className="mt-2 text-[#6b645a]">These communities best match what matters most to {relationship}.</p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={startNewSearch}
              className="rounded-full bg-[#5f7f6b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#4d6756]"
            >
              New search
            </button>
            <Link href="/" className="rounded-full border border-[#d9cfbf] bg-[#f6f2ea] px-4 py-2 text-sm font-semibold text-[#534a3d] transition hover:bg-[#efe8db]">
              Back to home
            </Link>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter.label}
                type="button"
                onClick={() => removeFilter(filter.label)}
                disabled={filter.disabled}
                className={`rounded-full border px-3 py-1 text-sm ${
                  filter.disabled
                    ? "cursor-default border-[#d9d3c7] bg-[#f0ede6] text-[#8b8578]"
                    : "border-[#d9cfbf] bg-[#f6f2ea] text-[#534a3d] hover:bg-[#efe8db]"
                }`}
              >
                {filter.label}{filter.disabled ? "" : " x"}
              </button>
            ))}
          </div>
        </header>

        {!isLoading && relaxedAvailability.recommendations.length === 0 ? (
          <section className="mt-6 rounded-3xl border border-[#eadfcd] bg-white p-8 text-center text-[#5f554a]">
            <p className="text-xl font-semibold">We couldn't find perfect matches, but we found nearby alternatives.</p>
          </section>
        ) : null}

        {!isLoading && relaxedAvailability.recommendations.length > 0 ? (
          <section className="mt-6 space-y-6">
            <details className="rounded-3xl border border-[#d9decb] bg-[#f8fbf1] p-4 shadow-[0_12px_34px_-28px_rgba(54,84,32,0.35)]">
              <summary className="cursor-pointer list-none text-sm font-semibold uppercase tracking-[0.16em] text-[#5c7340]">
                Show recommendation diagnostics
              </summary>
              <div className="mt-4 space-y-6">
            <article className="rounded-3xl border border-[#d9decb] bg-[#f8fbf1] p-6 shadow-[0_12px_34px_-28px_rgba(54,84,32,0.35)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5c7340]">Signal Classification Engine V1</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Preference signal categories</h2>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-[#dfe7cf] bg-white">
                <table className="min-w-full divide-y divide-[#e9efdd] text-sm text-[#425041]">
                  <thead className="bg-[#f2f7e8] text-left text-xs uppercase tracking-[0.14em] text-[#6b775a]">
                    <tr>
                      <th className="px-4 py-3">Signal</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Value</th>
                      <th className="px-4 py-3">Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#edf2e4]">
                    {relaxedAvailability.signalClassifications.map((row) => (
                      <tr key={`${row.signal}-${row.category}`}>
                        <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.signal}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                            row.category === "HARD REQUIREMENT"
                              ? "bg-[#fde7e2] text-[#a54c34]"
                              : row.category === "STRONG PREFERENCE"
                                ? "bg-[#edf3ea] text-[#4c6f5b]"
                                : row.category === "NICE TO HAVE"
                                  ? "bg-[#e7eefb] text-[#3f5f8c]"
                                  : "bg-[#f5f1e5] text-[#6f644e]"
                          }`}>
                            {row.category}
                          </span>
                        </td>
                        <td className="px-4 py-3">{row.value}</td>
                        <td className="px-4 py-3">{row.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-[#6a655b]">Engine rules: UNKNOWN SIGNAL and NICE TO HAVE never reject; STRONG PREFERENCE rarely rejects exact matching; only HARD REQUIREMENT can reject recommendation eligibility.</p>
            </article>

            <article className="rounded-3xl border border-[#d8dbe2] bg-[#f7f9fc] p-6 shadow-[0_12px_34px_-28px_rgba(36,49,72,0.45)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#44526b]">Recommendation Pipeline Debug</p>
              <div className="mt-3 overflow-x-auto rounded-2xl border border-[#d5dbe6] bg-white">
                <table className="min-w-full divide-y divide-[#e3e8f0] text-sm text-[#334155]">
                  <tbody className="divide-y divide-[#eef2f7]">
                    <tr><td className="px-4 py-3 font-medium">communities_loaded</td><td className="px-4 py-3">{relaxedAvailability.debug.communities_loaded}</td></tr>
                    <tr><td className="px-4 py-3 font-medium">exact_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.exact_matches}</td></tr>
                    <tr><td className="px-4 py-3 font-medium">soft_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.soft_matches}</td></tr>
                    <tr><td className="px-4 py-3 font-medium">fallback_matches</td><td className="px-4 py-3">{relaxedAvailability.debug.fallback_matches}</td></tr>
                    <tr><td className="px-4 py-3 font-medium">rendered_results</td><td className="px-4 py-3">{relaxedAvailability.debug.rendered_results}</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Recommendation Filter Audit</p>
              <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Hard constraints vs soft preferences</h2>
              <p className="mt-2 text-sm text-[#5c5347]">Default rule applied: everything is SOFT_PREFERENCE unless explicitly mandatory.</p>
              <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                  <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                    <tr>
                      <th className="px-4 py-3">Input field</th>
                      <th className="px-4 py-3">Value</th>
                      <th className="px-4 py-3">Classification</th>
                      <th className="px-4 py-3">Why</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#efe6d8]">
                    {relaxedAvailability.constraintAudit.map((row) => (
                      <tr key={`${row.field}-${row.classification}`}>
                        <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.field}</td>
                        <td className="px-4 py-3">{row.value}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.classification === "HARD_CONSTRAINT" ? "bg-[#fde7e2] text-[#a54c34]" : "bg-[#edf3ea] text-[#4c6f5b]"}`}>
                            {row.classification}
                          </span>
                        </td>
                        <td className="px-4 py-3">{row.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            {relaxedAvailability.exactMatchAudit.length > 0 ? (
              <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffdfa] p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Exact Match Audit</p>
                <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Rejected communities and reasons</h2>
                <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                  <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                    <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                      <tr>
                        <th className="px-4 py-3">community_name</th>
                        <th className="px-4 py-3">rejection_reason</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#efe6d8]">
                      {relaxedAvailability.exactMatchAudit.slice(0, 100).map((row) => (
                        <tr key={`${row.community_name}-${row.rejection_reason}`}>
                          <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.community_name}</td>
                          <td className="px-4 py-3">{row.rejection_reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ) : null}

            {relaxedAvailability.relaxations.length > 0 ? (
              <article className="rounded-3xl border border-[#e8ddcc] bg-[#fffaf2] p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Soft Preference Gaps</p>
                <h2 className="mt-2 text-xl font-semibold text-[#2f2a24]">Best available communities returned; these preferences are not fully satisfied:</h2>
                <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                  <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                    <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                      <tr>
                        <th className="px-4 py-3">Preference</th>
                        <th className="px-4 py-3">Original requirement</th>
                        <th className="px-4 py-3">Not fully satisfied note</th>
                        <th className="px-4 py-3">Top-3 communities meeting this</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#efe6d8]">
                      {relaxedAvailability.relaxations.map((item) => (
                        <tr key={`${item.preference}-${item.originalRequirement}`}>
                          <td className="px-4 py-3 font-medium text-[#2f2a24]">{item.preference}</td>
                          <td className="px-4 py-3">{item.originalRequirement}</td>
                          <td className="px-4 py-3">{item.relaxedRequirement}</td>
                          <td className="px-4 py-3">{item.impactOnResultsCount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ) : null}

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Expert Advisor Mode</p>
              <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Personal explanation</h2>
              <p className="mt-3 text-sm leading-7 text-[#554c41]">{personalAdvisorSummary}</p>
            </article>

            <article className="rounded-3xl border border-[#e8ddcc] bg-white p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.35)]">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Cultural Intelligence Scorecard</p>
              <h2 className="mt-2 text-2xl font-semibold text-[#2f2a24]">Belonging and adjustment signals</h2>
              <p className="mt-2 text-sm text-[#5c5347]">
                These scores come from direct answers only and support mixed identities and multicultural households.
              </p>

              <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e7dbc6] bg-white">
                <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                  <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                    <tr>
                      <th className="px-4 py-3">Output score</th>
                      <th className="px-4 py-3">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#efe6d8]">
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">language_match_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.language_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">religious_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.religious_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">cultural_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.cultural_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">food_fit_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.food_fit_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">family_engagement_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.family_engagement_score}</td></tr>
                    <tr><td className="px-4 py-3 font-medium text-[#2f2a24]">community_style_score</td><td className="px-4 py-3">{state.humanIntelligenceV2.scoringEngine.outputScores.community_style_score}</td></tr>
                  </tbody>
                </table>
              </div>

              {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.length > 0 ? (
                <div className="mt-4 rounded-2xl border border-[#e7dbc6] bg-[#fffdfa] p-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Recommendation impact</p>
                  <ul className="mt-3 space-y-2 text-sm text-[#564d42]">
                    {state.humanIntelligenceV2.scoringEngine.recommendationImpacts.map((impact) => (
                      <li key={impact}>• {impact}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {state.humanIntelligenceV2.scoringEngine.overallConfidence < state.humanIntelligenceV2.scoringEngine.confidenceThreshold ? (
                <p className="mt-4 text-sm text-[#8c5c40]">
                  Confidence is below threshold; additional question asked: {state.humanIntelligenceV2.scoringEngine.additionalQuestionAsked || "How often do you expect to visit?"}
                </p>
              ) : null}
            </article>

            <div ref={recommendationsRef} className="space-y-4">
              {topRecommendations.map((facility, index) => {
              const explanation = buildPersonalizedExplanation(facility, {
                relationship,
                age,
                care,
                activity,
                memory,
                budget,
                distance,
                notes,
              });
              const explainable = relaxedAvailability.explainableByFacility[facility.id];

              const renderRows = (rows: ExplanationListItem[]) => (
                <div className="overflow-x-auto rounded-2xl border border-[#e7dbc6]">
                  <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                    <thead className="bg-[#f5efe4] text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                      <tr>
                        <th className="px-4 py-3">Dimension</th>
                        <th className="px-4 py-3">Explanation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#efe6d8] bg-white">
                      {rows.map((row) => (
                        <tr key={`${facility.id}-${row.title}`}>
                          <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.title}</td>
                          <td className="px-4 py-3">{row.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );

              return (
                <div key={`${facility.id}-${facility.imageUrl}`} className="space-y-4">
                  {explainable ? (
                    <article className="rounded-3xl border border-[#d7dfeb] bg-[#f7fbff] p-5 shadow-[0_16px_50px_-34px_rgba(45,74,112,0.35)]">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#3f5f8c]">Explainable Matching Engine V1</p>
                      <h3 className="mt-2 text-xl font-semibold text-[#2f2a24]">Why this recommendation exists</h3>

                      <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        <div className="overflow-hidden rounded-2xl border border-[#d9e2f0] bg-white">
                          <div className="bg-[#ecf3fd] px-4 py-3 text-sm font-semibold text-[#2f4f73]">Positive contributors</div>
                          <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-[#e4ebf5] text-sm text-[#34495f]">
                              <thead className="bg-white text-left text-xs uppercase tracking-[0.14em] text-[#64748b]">
                                <tr>
                                  <th className="px-4 py-3">Signal</th>
                                  <th className="px-4 py-3">Score</th>
                                  <th className="px-4 py-3">Weight</th>
                                  <th className="px-4 py-3">Contribution</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-[#edf2f8]">
                                {explainable.positiveContributors.length > 0 ? explainable.positiveContributors.map((row) => (
                                  <tr key={`${facility.id}-pos-${row.signal}-${row.reason}`}>
                                    <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.signal}</td>
                                    <td className="px-4 py-3">{row.score}</td>
                                    <td className="px-4 py-3">{row.weight}</td>
                                    <td className="px-4 py-3">{row.contribution}</td>
                                  </tr>
                                )) : (
                                  <tr><td className="px-4 py-3" colSpan={4}>No high-scoring positive contributors were detected.</td></tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        <div className="overflow-hidden rounded-2xl border border-[#efdccf] bg-white">
                          <div className="bg-[#fef1ea] px-4 py-3 text-sm font-semibold text-[#8c5c40]">Negative contributors and penalties</div>
                          <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-[#f0e4da] text-sm text-[#5b4d41]">
                              <thead className="bg-white text-left text-xs uppercase tracking-[0.14em] text-[#8a7769]">
                                <tr>
                                  <th className="px-4 py-3">Signal</th>
                                  <th className="px-4 py-3">Score</th>
                                  <th className="px-4 py-3">Penalty/Contribution</th>
                                  <th className="px-4 py-3">Why</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-[#f4e9df]">
                                {explainable.negativeContributors.length > 0 ? explainable.negativeContributors.map((row) => (
                                  <tr key={`${facility.id}-neg-${row.signal}-${row.reason}`}>
                                    <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.signal}</td>
                                    <td className="px-4 py-3">{row.score}</td>
                                    <td className="px-4 py-3">{row.contribution}</td>
                                    <td className="px-4 py-3">{row.reason}</td>
                                  </tr>
                                )) : (
                                  <tr><td className="px-4 py-3" colSpan={4}>No explicit penalties were applied for this community.</td></tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 overflow-hidden rounded-2xl border border-[#e4dcca] bg-white">
                        <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Tradeoffs (never hidden)</div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                            <thead className="bg-white text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                              <tr>
                                <th className="px-4 py-3">Benefit</th>
                                <th className="px-4 py-3">Cost</th>
                                <th className="px-4 py-3">Summary</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#efe6d8]">
                              {explainable.tradeoffs.map((row) => (
                                <tr key={`${facility.id}-tradeoff-${row.summary}`}>
                                  <td className="px-4 py-3">{row.benefit}</td>
                                  <td className="px-4 py-3">{row.cost}</td>
                                  <td className="px-4 py-3">{row.summary}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="mt-4 overflow-hidden rounded-2xl border border-[#d9e2f0] bg-white">
                        <div className="bg-[#ecf3fd] px-4 py-3 text-sm font-semibold text-[#2f4f73]">Weight breakdown</div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-[#e4ebf5] text-sm text-[#34495f]">
                            <thead className="bg-white text-left text-xs uppercase tracking-[0.14em] text-[#64748b]">
                              <tr>
                                <th className="px-4 py-3">Signal</th>
                                <th className="px-4 py-3">Category</th>
                                <th className="px-4 py-3">Raw weight</th>
                                <th className="px-4 py-3">Normalized</th>
                                <th className="px-4 py-3">Score</th>
                                <th className="px-4 py-3">Weighted score</th>
                                <th className="px-4 py-3">Contribution to final</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[#edf2f8]">
                              {explainable.weightBreakdown.map((row) => (
                                <tr key={`${facility.id}-weight-${row.signal}-${row.rawWeight}`}>
                                  <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.signal}</td>
                                  <td className="px-4 py-3">{row.category}</td>
                                  <td className="px-4 py-3">{row.rawWeight}</td>
                                  <td className="px-4 py-3">{row.normalizedWeight}</td>
                                  <td className="px-4 py-3">{row.score}</td>
                                  <td className="px-4 py-3">{row.weightedScore}</td>
                                  <td className="px-4 py-3">{row.contributionToFinal}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="mt-4 overflow-hidden rounded-2xl border border-[#e4dcca] bg-white">
                        <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Final score calculation</div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                            <tbody className="divide-y divide-[#efe6d8]">
                              <tr><td className="px-4 py-3 font-medium">Base score</td><td className="px-4 py-3">{explainable.finalScore.baseScore}</td><td className="px-4 py-3 font-medium">Base weight</td><td className="px-4 py-3">{explainable.finalScore.baseWeight}</td></tr>
                              <tr><td className="px-4 py-3 font-medium">Preference aggregate</td><td className="px-4 py-3">{explainable.finalScore.preferenceAggregate}</td><td className="px-4 py-3 font-medium">Preference weight</td><td className="px-4 py-3">{explainable.finalScore.preferenceWeight}</td></tr>
                              <tr><td className="px-4 py-3 font-medium">Weighted base</td><td className="px-4 py-3">{explainable.finalScore.weightedBase}</td><td className="px-4 py-3 font-medium">Weighted preferences</td><td className="px-4 py-3">{explainable.finalScore.weightedPreferences}</td></tr>
                              <tr><td className="px-4 py-3 font-medium">Soft penalties</td><td className="px-4 py-3">-{explainable.finalScore.softPenalty}</td><td className="px-4 py-3 font-medium">Hard penalty</td><td className="px-4 py-3">-{explainable.finalScore.hardPenalty}</td></tr>
                              <tr><td className="px-4 py-3 font-medium">Final score</td><td className="px-4 py-3">{explainable.finalScore.finalScore}</td><td className="px-4 py-3" colSpan={2}></td></tr>
                            </tbody>
                          </table>
                        </div>
                        <p className="px-4 py-3 text-xs text-[#6a655b]">Formula: final = (base_score x base_weight) + (preference_aggregate x preference_weight) - soft_penalties - hard_penalty.</p>
                      </div>

                      <div className="mt-4 rounded-2xl border border-[#f0e4da] bg-[#fffaf7] p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">Uncertainty (never hidden)</p>
                        <ul className="mt-2 space-y-2 text-sm text-[#5b4d41]">
                          {explainable.uncertainty.map((item) => (
                            <li key={`${facility.id}-unc-${item}`}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                    </article>
                  ) : null}

                  <article className="rounded-3xl border border-[#e8ddcc] bg-white p-5 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5f7f6b]">Recommendation #{index + 1} explanation</p>
                    <p className="mt-3 text-sm text-[#5c5347]">Resident profile: {explanation.profileSummary}</p>
                    <ul className="mt-3 space-y-2 text-sm text-[#5c5347]">
                      {explanation.fitsYou.map((item) => (
                        <li key={`${facility.id}-${item}`}>• {item}</li>
                      ))}
                    </ul>
                  </article>

                  <article className="overflow-hidden rounded-3xl border border-[#e8ddcc] bg-white shadow-[0_16px_50px_-34px_rgba(69,58,43,0.45)]">
              <div className="relative h-64 w-full">
                <Image src={facility.imageUrl} alt={facility.name} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 50vw" />
              </div>

              <div className="p-5 sm:p-6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="mb-2 inline-flex rounded-full bg-[#e9f1e7] px-3 py-1 text-xs font-semibold text-[#4c6f5b]">{highlightLabel(index)}</p>
                    <h2 className="text-2xl font-semibold text-[#2f2a24]">{facility.name}</h2>
                    <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                      {facility.matching_confidence === "HIGH" ? (
                        <p className="rounded-full bg-[#e8f3e7] px-3 py-1 text-[#46694c]">Verified Community</p>
                      ) : facility.matching_confidence === "MEDIUM" ? (
                        <p className="rounded-full bg-[#f6efd7] px-3 py-1 text-[#816a2d]">Name verified with minor variation</p>
                      ) : (
                        <p className="rounded-full bg-[#fde7e2] px-3 py-1 text-[#a54c34]">Community name could not be verified.</p>
                      )}
                    </div>
                  </div>
                  <div className={`rounded-2xl px-3 py-2 text-center ${scoreBadgeStyle(facility.optimeScore)}`}>
                    <p className="text-2xl font-bold leading-none">{facility.optimeScore}</p>
                    <p className="mt-1 text-xs font-semibold">{facility.matching_confidence}</p>
                  </div>
                </div>

                <div className="mt-4 overflow-hidden rounded-2xl border border-[#e7dbc6]">
                  <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Matching dimensions</div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                      <thead className="bg-white/80 text-left text-xs uppercase tracking-[0.14em] text-[#7a6f63]">
                        <tr>
                          <th className="px-4 py-3">Dimension</th>
                          <th className="px-4 py-3">Evidence</th>
                          <th className="px-4 py-3">Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#efe6d8] bg-white">
                        {explanation.matchingDimensions.map((row) => (
                          <tr key={`${facility.id}-${row.label}`}>
                            <td className="px-4 py-3 font-medium text-[#2f2a24]">{row.label}</td>
                            <td className="px-4 py-3">{row.evidence}</td>
                            <td className="px-4 py-3">{row.score}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
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

                <section className="mt-6 space-y-4 rounded-3xl border border-[#e8ddcc] bg-[#fffdfa] p-4 sm:p-5">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">What This Community Does Well For You</p>
                        <div className="mt-2">{renderRows(explanation.strengths)}</div>
                      </div>

                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#8c5c40]">What This Community Does Not Solve</p>
                        <div className="mt-2">{renderRows(explanation.weaknesses)}</div>
                      </div>

                      <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f657f]">Tradeoffs</p>
                        <div className="mt-2">{renderRows(explanation.tradeoffs)}</div>
                      </div>

                      <div className="rounded-2xl border border-[#e7dbc6] bg-white p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Questions To Ask During The Tour</p>
                        <ul className="mt-3 space-y-2 text-sm text-[#564d42]">
                          {explanation.questions.map((question) => (
                            <li key={`${facility.id}-${question}`}>• {question}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="overflow-hidden rounded-2xl border border-[#e7dbc6]">
                        <div className="bg-[#f5efe4] px-4 py-3 text-sm font-semibold text-[#3f372e]">Confidence</div>
                        <div className="overflow-x-auto bg-white">
                          <table className="min-w-full divide-y divide-[#eadfce] text-sm text-[#564d42]">
                            <tbody className="divide-y divide-[#efe6d8]">
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Match score</td>
                                <td className="px-4 py-3">{facility.optimeScore}</td>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Confidence score</td>
                                <td className="px-4 py-3">{explanation.confidenceScore}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Sources analyzed</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.sourcesAnalyzed.join(", ") || "Current recommendation data only"}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Strong matches</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.strongMatches.join(", ")}</td>
                              </tr>
                              <tr>
                                <td className="px-4 py-3 font-medium text-[#2f2a24]">Major concerns</td>
                                <td className="px-4 py-3" colSpan={3}>{explanation.majorConcerns.join(", ")}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-[#e7dbc6] bg-white p-4">
                        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5f7f6b]">Advisor Explanation</p>
                        <p className="mt-3 text-sm leading-7 text-[#554c41]">{explanation.narrative}</p>
                      </div>
                    </section>
              </div>
            </article>
                </div>
              );
              })}
              </div>
            </details>
            </div>

            {remainingRecommendations.length > 0 ? (
              <div className="space-y-4">
                <button
                  type="button"
                  onClick={() => setShowMoreCommunities((current) => !current)}
                  className="rounded-full border border-[#d9cfbf] bg-white px-5 py-2 text-sm font-semibold text-[#534a3d] hover:bg-[#efe8db]"
                >
                  {showMoreCommunities ? "Hide additional communities" : "Show more communities"}
                </button>

                {showMoreCommunities ? (
                  <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {remainingRecommendations.map((facility) => (
                      <article key={`compact-${facility.id}`} className="rounded-2xl border border-[#e8ddcc] bg-white p-4 shadow-[0_10px_30px_-24px_rgba(69,58,43,0.45)]">
                        <h3 className="text-lg font-semibold text-[#2f2a24]">{facility.name}</h3>
                        <p className="mt-1 text-sm text-[#6d655b]">{facility.city}, {facility.state}</p>
                        <p className="mt-2 text-sm text-[#4f6f8f]">{facility.priceRange}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {facility.matchBadges.slice(0, 3).map((badge) => (
                            <span key={`compact-${facility.id}-${badge}`} className="rounded-full bg-[#edf3ea] px-3 py-1 text-xs font-medium text-[#4c6f5b]">
                              {badge}
                            </span>
                          ))}
                        </div>
                        <div className="mt-4 flex items-center justify-between">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${scoreBadgeStyle(facility.optimeScore)}`}>Score {facility.optimeScore}</span>
                          <Link href={`/facilities/${facility.id}`} className="text-sm font-semibold text-[#5f7f6b] hover:text-[#4f6f8f]">
                            View
                          </Link>
                        </div>
                      </article>
                    ))}
                  </section>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <div className="py-10 text-center text-sm text-[#6d655b]">{isLoading ? "Loading communities..." : "End of recommendations"}</div>
      </section>
    </main>
  );
}
