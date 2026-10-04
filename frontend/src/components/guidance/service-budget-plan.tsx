import type { CarePartnerOption, DecisionEngineRecommendation, PatientNeed } from "@/lib/api";
import { licensedResearchOptions, serviceBudgetPlan } from "@/lib/service-budget";

const money = (value: number) => `$${value.toLocaleString("en-US")}`;
const known = (value: unknown, suffix = "") => typeof value === "number" && Number.isFinite(value) && value >= 0 ? `${value}${suffix}` : "Needs confirmation";

export function ServiceBudgetPlan({ item, budget, couple, needs, options }: { item: DecisionEngineRecommendation; budget: number; couple: boolean; needs?: PatientNeed[]; options?: CarePartnerOption[] }) {
  const plan = serviceBudgetPlan(item, budget, couple, needs);
  const candidates = item.synthetic_pilot ? [] : licensedResearchOptions(options);
  return <section className="mt-5 rounded-2xl border border-[#cdded5] bg-[#f4f8f6] p-5 sm:p-6 text-lg leading-8" data-testid="service-budget-plan">
    <h3 className="text-2xl font-semibold">Your services and monthly budget</h3>
    <p className="mt-3">We need one plan covering the home and every required service, within {budget > 0 ? `your ${money(budget)} monthly family budget` : "a monthly family budget you confirm"}.</p>
    <dl className="mt-4 grid gap-4 sm:grid-cols-3">
      <div><dt className="text-base">Family budget</dt><dd className="font-semibold">{budget > 0 ? `${money(budget)} / month` : "Needs confirmation"}</dd></div>
      <div><dt className="text-base">{plan.total !== null ? "Inclusive pilot price" : "Housing starting price"}</dt><dd className="font-semibold">{plan.housing !== null ? `${money(plan.housing)} / month` : "Needs confirmation"}</dd></div>
      <div><dt className="text-base">{plan.total !== null ? "Pilot total" : "Allowance left for all extras"}</dt><dd className="font-semibold">{plan.total !== null ? money(plan.total) : plan.allowance !== null ? `${money(plan.allowance)} at this starting price` : "Needs confirmation"}</dd></div>
    </dl>
    <p className="mt-4 font-semibold">{plan.housingOverBudget ? "Housing alone exceeds your budget." : plan.status === "PILOT_WITHIN_BUDGET" ? "Synthetic test total is within budget — this is not a real provider quote." : "Total affordability is awaiting a complete written quote."}</p>
    {plan.total === null ? <p>The remaining allowance is a spending ceiling for care and other extras, not a care-price estimate. A higher room price reduces it.</p> : null}
    <h4 className="mt-5 font-semibold">Services to include in the plan</h4>
    <p>{plan.services.length ? plan.services.join("; ") : "Confirm the room, included services and any additional support with the community."}{couple ? " The quote must cover both residents." : ""}</p>
    <p className="mt-3">Ask the community to confirm what it provides, any additional charge, and which outside providers it approves for this plan. OOmnik enrollment alone does not confirm a service or price.</p>
    {plan.external ? <details className="mt-5"><summary className="cursor-pointer font-semibold underline underline-offset-4">Licensed providers to investigate ({candidates.length})</summary>
      <p className="mt-3">These are regional research candidates from our license snapshot. Current licensing, the exact service, price, availability and permission to work in this community still need confirmation.</p>
      {candidates.length ? <div className="mt-4 space-y-4">{candidates.map(option => <article key={option.agency_id} className="rounded-xl border bg-white p-4">
        <h5 className="font-semibold">{option.agency_name}</h5>
        <p className="text-base">License {option.license_number} · Recorded active{option.license_snapshot_date && option.license_snapshot_date !== "UNKNOWN" ? ` as of ${option.license_snapshot_date}` : " — snapshot date unavailable"}. Community approval pending.</p>
        <p>Recorded services: {[option.bathing_assistance === true && "bathing assistance", option.dressing_assistance === true && "dressing assistance", option.transfer_assistance === true && "transfer assistance"].filter(Boolean).join(", ") || "Needs confirmation"}.</p>
        <p>Hourly rate: {known(option.hourly_rate, " USD")} · Minimum billed visit: {known(option.minimum_billable_hours, " hours")} · Visit length: {known(option.minimum_visit_minutes, " minutes")}</p>
        <p>Quality, caregiver continuity and availability: request current evidence for your service plan.</p>
        <a href={option.primary_source_url} target="_blank" rel="noreferrer" className="font-semibold underline underline-offset-4">Provider website and services ↗</a>
      </article>)}</div> : <p className="mt-3">No licensed provider candidates are available for this search. Provider research is still required.</p>}
      <a href="https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HF&PubliSearch=Y" target="_blank" rel="noreferrer" className="mt-4 inline-block underline">Check the current Nevada license ↗</a>
    </details> : null}
  </section>;
}
