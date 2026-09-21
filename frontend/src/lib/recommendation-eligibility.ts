type Eligibility = { must_eligibility?: string; eligibility_status: string };

export function isFinalRecommendation(item: Eligibility): boolean {
  return item.must_eligibility
    ? item.must_eligibility === "MUST_ELIGIBLE"
    : item.eligibility_status === "ELIGIBLE";
}

export function isPendingRecommendation(item: Eligibility): boolean {
  return item.must_eligibility
    ? item.must_eligibility === "MUST_PENDING_VERIFICATION"
    : item.eligibility_status !== "ELIGIBLE" && item.eligibility_status !== "INELIGIBLE";
}
