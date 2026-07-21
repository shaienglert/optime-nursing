import { SearchFacility } from "@/lib/api";

export type FacilityImageTruth = {
  url: string;
  sourceLabel: string;
  isPlaceholder: boolean;
};

export type PriceTruthState = "VERIFIED_CURRENT" | "VERIFIED_STALE" | "PUBLIC_ESTIMATE" | "THIRD_PARTY_ESTIMATE" | "DERIVED" | "PLACEHOLDER" | "UNKNOWN";

export type PriceTruth = {
  label: string;
  value: string;
  truthState: PriceTruthState;
};

export function resolveFacilityImage(facility: SearchFacility): FacilityImageTruth {
  const hero = facility.visualIntelligence.heroImage;
  const normalizedUrl = String(hero.url || "").trim().toLowerCase();
  const usesGenericUnsplash = normalizedUrl.includes("source.unsplash.com");
  const isPlaceholder = hero.source === "CMS Placeholder" || !hero.url || usesGenericUnsplash;
  return {
    url: isPlaceholder ? "/cms-placeholder.svg" : hero.url,
    sourceLabel: isPlaceholder ? "Neutral placeholder" : hero.source,
    isPlaceholder,
  };
}

export function resolvePriceTruth(facility: SearchFacility): PriceTruth {
  return {
    label: "Estimated monthly range",
    value: facility.priceRange || "Current pricing not verified — contact facility",
    truthState: facility.priceRange ? "DERIVED" : "UNKNOWN",
  };
}

export function personLabel(relationship: string): string {
  const value = (relationship || "").trim();
  if (!value) return "your family member";
  if (value === "Myself") return "yourself";
  return value;
}
