import type { CarePartnerOption, DecisionEngineRecommendation, PatientNeed } from "./api";

export const isOutsideCareConcern = (text: string) => /outside[- ]care|outside (?:agency|care)|external (?:agency|care)|separate (?:care )?arrangement/i.test(text);

export function serviceBudgetPlan(item: DecisionEngineRecommendation, budget: number, couple: boolean, needs: PatientNeed[] = []) {
  const solution = item.combined_care_solution;
  const services = needs.filter(need => ["REQUIRED", "HIGH"].includes(need.requirement_level) && ["adl_support", "medication_support", "transfer_assistance", "memory_care", "nursing_24_7"].includes(need.parameter_id)).map(need => need.need_text || need.parameter_id.replaceAll("_", " "));
  if (solution?.care_component?.adl_required && !services.length) services.push("Help with daily activities");
  if (solution?.medication_component?.medication_required && !services.some(text => /medication/i.test(text))) services.push("Required medication support");
  const external = [solution?.delivery_model, solution?.care_component?.delivery_model, solution?.medication_component?.delivery_model].some(model => model?.includes("EXTERNAL_AGENCY")) || (item.explanation?.concerns || []).some(isOutsideCareConcern);
  if (external && !services.length) services.push("Outside care — exact service package needs confirmation");
  const housing = typeof item.starting_monthly_price === "number" && Number.isFinite(item.starting_monthly_price) && item.starting_monthly_price > 0 ? item.starting_monthly_price : null;
  // The current response has no complete real household quote. Only synthetic
  // pilot inclusive prices explicitly support this calculation, labelled as tests.
  const inclusivePilot = !!(item.synthetic_pilot && item.monthly_rate_includes_verified_care && (!couple || item.monthly_price_basis === "TWO_RESIDENT_TOTAL") && !external);
  return { services, external, housing, allowance: budget > 0 && housing !== null ? Math.max(0, budget - housing) : null, housingOverBudget: budget > 0 && housing !== null && housing > budget, total: inclusivePilot ? housing : null, status: inclusivePilot && housing !== null && budget > 0 ? (housing <= budget ? "PILOT_WITHIN_BUDGET" : "OVER_BUDGET") : "TOTAL_UNCONFIRMED" };
}

export function licensedResearchOptions(options: CarePartnerOption[] = []) {
  return options.filter(option => option.license_status === "ACTIVE" && !!option.license_number && option.license_number !== "UNKNOWN" && option.care_agency_fit?.hard_gate !== "FAIL" && /^https?:\/\//i.test(option.primary_source_url));
}

export const serviceQuoteQuestions = [
  "Which required services are included in the housing price, and which cost extra?",
  "Does the community provide these services itself, or approve this specific licensed outside provider?",
  "Confirm the service type, visit duration, frequency, minimum billable hours and start date.",
  "Provide a written household monthly total, including care, all fees and any second resident, within the family's budget.",
  "Confirm current license, staff training, screening, insurance, continuity, backup and availability; provide sourced quality evidence.",
];
