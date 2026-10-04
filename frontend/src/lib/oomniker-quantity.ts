/** Numeric edits require a dimension. A distance can never become a price. */
export function parseOomnikerQuantities(text: string): {
  budget?: number; miles?: string; clearRadius?: boolean;
} {
  const lower = text.toLowerCase();
  const result: { budget?: number; miles?: string; clearRadius?: boolean } = {};
  // Currency is explicit; a bare number requires a budget label in its clause.
  const currency = lower.match(/(?:\$\s*|usd\s+)([0-9][0-9,]*(?:\.[0-9]{1,2})?)/)
    || lower.match(/([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:dollars|usd)\b/);
  const labelled = lower.match(/\bbudget\b[^\d$.;]{0,30}\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)(?![0-9])/);
  const amount = currency || (labelled && !/^\s*(?:miles?|km|kilometers?)\b/.test(lower.slice((labelled.index || 0) + labelled[0].length)) ? labelled : null);
  if (amount) {
    const value = Number(amount[1].replaceAll(",", ""));
    if (Number.isFinite(value) && value > 0) result.budget = value;
  }
  const miles = lower.match(/\b([0-9]+(?:\.[0-9]+)?)\s*miles?\b/);
  if (miles && Number(miles[1]) > 0) result.miles = miles[1];
  result.clearRadius = /(?:distance|radius|location).*(?:not important|no longer important|no preference)|(?:remove|drop|clear).*(?:distance|radius|location).*(?:limit|restriction)|(?:remove|drop|clear).*radius/.test(lower);
  return result;
}
