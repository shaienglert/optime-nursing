type IdentityState = { relationship: string; gender: string };
type IdentityPatch = IdentityState;

const RELATIONSHIP_FACTS: Record<string, IdentityPatch> = {
  mom: { relationship: "Mom", gender: "Female" },
  mother: { relationship: "Mom", gender: "Female" },
  "my mom": { relationship: "Mom", gender: "Female" },
  "my mother": { relationship: "Mom", gender: "Female" },
  dad: { relationship: "Dad", gender: "Male" },
  father: { relationship: "Dad", gender: "Male" },
  "my dad": { relationship: "Dad", gender: "Male" },
  "my father": { relationship: "Dad", gender: "Male" },
  grandma: { relationship: "Grandma", gender: "Female" },
  grandmother: { relationship: "Grandma", gender: "Female" },
  grandpa: { relationship: "Grandpa", gender: "Male" },
  grandfather: { relationship: "Grandpa", gender: "Male" },
  wife: { relationship: "Spouse", gender: "Female" },
  "my wife": { relationship: "Spouse", gender: "Female" },
  husband: { relationship: "Spouse", gender: "Male" },
  "my husband": { relationship: "Spouse", gender: "Male" },
  spouse: { relationship: "Spouse", gender: "" },
  "my spouse": { relationship: "Spouse", gender: "" },
  myself: { relationship: "Myself", gender: "" },
  self: { relationship: "Myself", gender: "" },
  couple: { relationship: "Couple", gender: "" },
  relative: { relationship: "Relative", gender: "" },
  friend: { relationship: "Friend", gender: "" },
};

export function canonicalIdentityFacts(relationship: string): IdentityPatch {
  const trimmed = relationship.trim();
  return RELATIONSHIP_FACTS[trimmed.toLowerCase()] || { relationship: trimmed, gender: "" };
}

export function applyCanonicalIdentity<T extends IdentityState>(
  state: T,
  relationship: string,
  explicitGender = "",
): T {
  const facts = canonicalIdentityFacts(relationship);
  return {
    ...state,
    relationship: facts.relationship,
    gender: state.gender.trim() || explicitGender.trim() || facts.gender,
  } as T;
}
