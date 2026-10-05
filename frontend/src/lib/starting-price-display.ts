import type { DecisionEngineRecommendation } from "./api";

function sourceLabel(source?: string | null): string {
  if (source === "PROVIDER" || source === "OUTREACH") return "price received from the facility";
  if (source === "OFFICIAL_WEBSITE") return "price published on the facility's website";
  if (source === "RESEARCH") return "price found in public research, not yet confirmed by the facility";
  if (source === "MANUAL") return "manually recorded price; confirm its source with the facility";
  return "price source not confirmed";
}

/** Preserve the recorded price basis; a household total is never a room base price. */
export function startingPriceDisplay(row: DecisionEngineRecommendation, budget: number): string {
  const rooms = (row.room_pricing_options || []).filter(room =>
    typeof room.base_price === "number" && Number.isFinite(room.base_price) && room.base_price > 0);
  const room = [...rooms].sort((a, b) => a.base_price - b.base_price)[0];
  const amount = room?.base_price ?? row.starting_monthly_price;
  if (typeof amount !== "number" || !Number.isFinite(amount) || amount <= 0) {
    return "Starting price not verified; it cannot be compared with your budget. Request a current quote for the care needed.";
  }
  const householdTotal = !room && row.monthly_price_basis === "TWO_RESIDENT_TOTAL";
  const includesCare = !room && row.monthly_rate_includes_verified_care === true;
  const priceBasis = room ? "base price" : householdTotal || includesCare ? "recorded monthly total" : "recorded starting price";
  const fit = Number.isFinite(budget) && budget > 0
    ? `${priceBasis} ${amount <= budget ? "within" : "above"} your monthly budget`
    : "budget not provided; affordability not assessed";
  const scope = room ? `${room.room_type}; care program not specified`
    : `${householdTotal ? "two residents, including the second-resident fee; " : ""}${includesCare ? "verified care included; " : ""}room and care program not specified`;
  const source = row.synthetic_pilot ? "synthetic pilot test price" : sourceLabel(room?.price_source ?? row.price_source);
  return `Starting at $${Math.round(amount).toLocaleString("en-US")} / month (${scope}) — ${source}; ${fit}. Confirm the applicable care program, final total including care and fees, and availability directly with the facility.`;
}
