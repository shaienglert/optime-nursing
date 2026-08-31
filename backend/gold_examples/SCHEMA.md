# NURSING Gold Example Schema (v1)

Adapted from the OPTIME HR gold-dataset methodology. Same principles, different domain
objects: HR matches **candidate ↔ job**; NURSING matches **resident ↔ facility**.

## Ground-truth sources (never let the model be its own truth)

Every example's `decision` must be traceable to one of:

1. **Code-checkable fact** — a deterministic rule already in the codebase (e.g. a
   canonical registry value, a Nevada license type, a regulatory field).
2. **Reasoned verdict from the strong model** — an AI ranking/reasoning output, always
   attached with its own evidence citations.
3. **Human approval** — required for every `DISPUTED` case and every borderline case;
   required from a **senior-care domain expert**, not just an engineer, whenever the
   question is "is this evidence sufficient to call a facility safe/eligible for this
   need" — the failure mode here is a family being steered wrong, not a wasted resume.

## Case-type targets (mirrors the HR table, NURSING-adapted)

| Case type | Target count | NURSING meaning |
|---|---:|---|
| Clear MUST pass — `ELIGIBLE` | 80 | Facility verifiably meets every MUST for this resident |
| Clear MUST fail — `INELIGIBLE` | 80 | A MUST is verifiably, definitively unmet (not just unknown) |
| Needs more info from the family | 50 | A client-owned fact is missing (location, budget, in-house-only preference, etc.) |
| Needs facility-side research | 50 | A provider-owned fact is missing (medication support, regulatory history, etc.) |
| Alternative-path fit | 50 | MUST is satisfiable via a complementary product (external care agency), not just in-house |
| Ambiguous/implicit wording | 40 | Free-text statement requires interpretation before it maps to a MUST/NICE |
| Duplicate/agency-vs-facility confusion | 30 | Same physical facility under two records, or provider vs. licensed entity mismatch |
| Inactive/unverified license | 30 | License expired, suspended, or facility record stale |
| Edge cases and misleading data | 50 | Third-party directories disagree with the primary regulatory source, etc. |
| Cases that already caused a production error | 40 | Real bugs found and fixed (or still open) — start here, we already have 8 |
| **Total** | **500** | |

First milestone: **200** (140 train / 30 validation / 30 held-out test), expanding by
targeting whatever error categories the current engine still gets wrong.

## Record shape

```json
{
  "case_id": "",
  "created_at": "",
  "resident": {
    "relationship": "",
    "age_group": "",
    "assistance_level": "",
    "memory_status": "",
    "budget_monthly_usd": null,
    "location_city": "",
    "natural_language_query": "",
    "unknowns": []
  },
  "facility": {
    "canonical_facility_id": "",
    "facility_name": "",
    "canonical_type": "",
    "nevada_license_id": "",
    "license_status": "",
    "address": "",
    "source_url": "",
    "verified_at": ""
  },
  "decision": "ELIGIBLE | INELIGIBLE | PENDING_VERIFICATION | DISPUTED",
  "reason_code": "",
  "must_gates": [
    {"key": "", "status": "PASS | FAIL | PENDING_VERIFICATION", "evidence_source": ""}
  ],
  "resident_evidence": [
    {"claim": "", "quote": "", "source": "natural_language | questionnaire | UNKNOWN"}
  ],
  "facility_evidence": [
    {"claim": "", "quote_or_value": "", "source": "", "confidence": null}
  ],
  "reasoning_summary": "",
  "correct_next_action": "",
  "ground_truth_basis": "CODE_RULE | STRONG_MODEL_REASONING | HUMAN_EXPERT",
  "human_verified": false,
  "verified_by_role": "engineer | domain_expert | null",
  "disputed": false,
  "dispute_notes": "",
  "linked_fix_commit": ""
}
```

Rules, unchanged from the HR version:
- Every claim must point to an actual quote from the resident's statement or the
  facility's evidence record. No quote → `UNKNOWN`, never inferred.
- MUST requirements are listed separately from NICE-to-have preferences.
- A second reviewer must be able to read the evidence and reach the same `decision`
  independently.
- Disagreement is never discarded — mark `disputed: true`, keep both readings in
  `dispute_notes`, and route to an expert. Disputed cases are frequently the most
  valuable ones once resolved.

## Do not start large-scale harvesting yet

The static-registry eligibility system and the agent-evidence MUST-gate system
disagreed with each other until commit `31b8aa7` (2026-08-27) connected them. Any
example harvested before that fix was live in production risks encoding the same
contradiction as "gold." Wait for that PR to merge and deploy, then re-verify the six
seed cases below against live production before harvesting at volume.
