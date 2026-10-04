import type { LocationScope } from "@/lib/api";

function placeName(label: string | null | undefined): string {
  const raw = String(label || "").trim();
  if (!raw) return "the area you chose";
  // The engine reports city names upper-case ("NORTH LAS VEGAS"); show them as people write them.
  return raw === raw.toUpperCase() ? raw.toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) : raw;
}

function communities(count: number): string {
  return `${count} communit${count === 1 ? "y" : "ies"}`;
}

/**
 * Says what the family's distance limit actually did -- never more.
 *
 * The limit is enforced only when the engine could measure from the place they chose. When
 * it could not, the page says so and that the results are not limited, rather than implying
 * a limit that was never applied. Widening is offered, never done on the family's behalf.
 */
export function DistanceScope({ scope, onWiden }: { scope?: LocationScope | null; onWiden: (miles: number) => void }) {
  if (!scope || scope.reason === "NO_RADIUS_REQUESTED" || scope.requested_miles == null) return null;
  const place = placeName(scope.reference?.label);
  const changeHint = "You can change the area or distance at any time with OOMNIKER below.";

  if (!scope.applied) {
    return (
      <div className="mt-4 rounded-2xl border border-[#e6d3a8] bg-[#fff8e8] p-5 text-lg leading-8 text-[#6d5426]" data-testid="distance-scope">
        <p>
          I couldn’t measure distances from {place} yet, so these results are <strong>not limited to {scope.requested_miles} miles</strong>.
          Please confirm travel distance before contacting a community.
        </p>
        <p className="mt-2 text-base">{changeHint}</p>
      </div>
    );
  }

  const offer = scope.expansion_offer;
  const excluded = scope.excluded_count || 0;
  const unknown = scope.distance_unknown_count || 0;
  return (
    <div className="mt-4 rounded-2xl border border-[#e4d8e8] bg-[#f6edf4] p-5 text-lg leading-8 text-[#302940]" data-testid="distance-scope">
      <p>
        Showing communities within <strong>{scope.effective_miles ?? scope.requested_miles} miles</strong> of {place}
        {scope.reference?.approximate ? ", measured from the middle of that area" : ""}.
        {excluded > 0 ? ` ${communities(excluded)} further away ${excluded === 1 ? "is" : "are"} not shown.` : ""}
      </p>
      {unknown > 0 ? (
        <p className="mt-2 text-base">
          {communities(unknown)} could not be measured and {unknown === 1 ? "is" : "are"} still included — please check {unknown === 1 ? "its" : "their"} distance.
        </p>
      ) : null}
      {offer ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <p className="text-base">
            {communities(offer.additional_count)} more {offer.additional_count === 1 ? "fits" : "fit"} within {offer.miles} miles (the nearest is {offer.nearest_excluded_miles} miles away).
          </p>
          <button type="button" onClick={() => onWiden(offer.miles)} className="rounded-full bg-[#675088] px-5 py-2 font-semibold text-white">
            Include up to {offer.miles} miles
          </button>
        </div>
      ) : null}
      <p className="mt-2 text-base">{changeHint}</p>
    </div>
  );
}
