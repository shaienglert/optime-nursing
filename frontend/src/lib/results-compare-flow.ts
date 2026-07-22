export type RankedItem = { rank_position?: number | null; canonical_facility_id: string };

export function getResultsAfterTopFive<T extends RankedItem>(items: T[], topCount = 5): T[] {
  return items.filter((item) => (item.rank_position || 0) > topCount);
}

export function isStrictRankOrder(items: RankedItem[]): boolean {
  const ranks = items.map((item) => item.rank_position || 0).filter((rank) => rank > 0);
  for (let i = 1; i < ranks.length; i += 1) {
    if (ranks[i] < ranks[i - 1]) return false;
  }
  return true;
}

export function toggleFavorite(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
}

export function canCompareFavorites(ids: string[]): boolean {
  return ids.length >= 2;
}

export function selectOptimeReference(results: RankedItem[], disqualifiedIds: string[] = []): RankedItem | null {
  const disqualified = new Set(disqualifiedIds);
  return results.find((item) => !disqualified.has(item.canonical_facility_id)) || null;
}

export function uniqueCanonicalParameters(parameterIds: string[]): string[] {
  return Array.from(new Set(parameterIds.filter(Boolean)));
}

export function hasCanonicalParameterCount(parameterIds: string[], expected = 59): boolean {
  return uniqueCanonicalParameters(parameterIds).length === expected;
}

export function unknownIsNeutral(status: "MATCH" | "VERIFIED_GAP" | "NOT_VERIFIED"): boolean {
  return status === "NOT_VERIFIED";
}

export function mobileCardsPerRow(containerWidthPx: number): 1 | 2 {
  return containerWidthPx >= 640 ? 2 : 1;
}
