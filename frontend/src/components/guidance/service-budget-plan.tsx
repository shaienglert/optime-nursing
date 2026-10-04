import type { CarePartnerOption, DecisionEngineRecommendation, PatientNeed } from "@/lib/api";
import { licensedResearchOptions, serviceBudgetPlan } from "@/lib/service-budget";

const money = (value: number) => `$${value.toLocaleString("en-US")}`;
const known = (value: unknown, suffix = "") => typeof value === "number" && Number.isFinite(value) && value >= 0 ? `${value}${suffix}` : "Needs confirmation";

export function ServiceBudgetPlan({ item, budget, couple, needs, options }: { item: DecisionEngineRecommendation; budget: number; couple: boolean; needs?: PatientNeed[]; options?: CarePartnerOption[] }) {
  const plan = serviceBudgetPlan(item, budget, couple, needs);
  const candidates = item.synthetic_pilot ? [] : licensedResearchOptions(options);
  return <section className="mt-8 text-xl leading-9 text-[#565d54]" data-testid="service-budget-plan">
    <h3 className="text-2xl font-semibold text-[#1a1d20]">Let’s make sure the whole plan works for you</h3>
    <p className="mt-3">{budget > 0 ? `You’ve set aside up to ${money(budget)} a month${couple ? " for both of you" : ""}. ` : "Let’s confirm the monthly budget you feel comfortable with. "}{plan.housing !== null ? `The ${plan.total !== null ? "inclusive test price" : "housing starting price"} here is ${money(plan.housing)} a month. ` : "We still need the community’s current housing price. "}{plan.housingOverBudget ? "That is already above your budget before any extras, so I want you to see the difference before considering this place." : plan.total !== null ? "This is synthetic pilot data, not a real provider quote." : plan.allowance !== null ? `At that starting price, ${money(plan.allowance)} would remain for all additional services and fees. That tells us what the plan needs to fit into; it doesn’t tell us what the care will cost yet.` : "We’ll need the full price before we can tell whether this fits your budget."}</p>
    <p className="mt-3">{plan.services.length ? `The plan needs to cover ${plan.services.join(", ")}. ` : "The room and included services are part of that conversation too. "}{plan.total === null ? "The next step is a written quote covering all of it, so you can consider the total with confidence. " : ""}{couple ? "It needs to cover both residents. " : ""}{plan.external ? "We also need the community to confirm which licensed provider it approves, what that provider can supply, and any extra charge. " : "We need the community to confirm what it provides and which services cost extra. "}Its enrollment with OOmnik alone doesn’t confirm those details.</p>
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
