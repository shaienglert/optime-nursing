# OOMNIK Israel — owner decisions

Recorded 2026-11-12. Owner approvals required by AGENTS.md (classes C/D/E).

| # | Decision | Class | Owner answer |
|---|---|---|---|
| 1 | Deployment model | E | One shared engine, a separate deployment per market (`OPTIME_CANONICAL_MARKET=israel`). No second matching engine; the Nevada pilot is untouched |
| 2 | Functional status (independent / frail / nursing / cognitively frail) as a MUST filter | C | Yes; unclear status means the system asks, never assumes |
| 3 | Funding pathway (MoH "code", Welfare assistance, private) as a MUST filter | D | Yes; a family with a MoH code sees only institutions with a MoH agreement |
| 4 | Commission on state-funded placements (MoH code / Welfare) | D | Charge the same as private placements. Legal question remains open and is the owner's accepted risk |
| 5 | Family interface languages | C | Hebrew, Russian, Arabic, English |
| 6 | Cross-list facility merging | C | None: every source row is its own facility record |

## Shared engine vs. Israeli layer (owner, 2026-11-12)

Shared by every market (one implementation, fixes land in both): interpreting the family's needs, MUST filtering, ranking, the match explanation, and OOmniker (suggests relaxing a preference only when at least two matching alternatives exist).

Israeli layer only: Hebrew (and ru/ar/en) questionnaire, setting types, the facility registry, licensing sources, ILS prices, funding pathways, and facility contact.

Licensing, pricing and care capabilities are stored as separate blocks with a source per field. Being on a list never makes a facility a match (`matching_eligibility: NOT_VERIFIED`); a MUST can pass only on a stated fact.

## Data (step 1, this branch)

- Raw sources: `data/israel/raw/` (received 2026-11-12).
- Build: `python scripts/build_israel_universe.py` → `database/israel_facility_universe_canonical.json` (467 records: 255 MoH geriatric nursing institutions, 115 Welfare old-age homes, 97 protected-housing homes).
- Missing fields (address, coordinates, availability, ward types in the MoH list) stay `null`/`UNKNOWN`; they are not negative evidence.

## Market scope (step 2)

- `market_scope.active_state_code()`: `IL` when `OPTIME_CANONICAL_MARKET=israel`, `NV` for every other market (unchanged behavior).
- Startup on the Israeli market purges non-IL rows and imports the Israeli universe; facility routes, market reports and external discovery filter on the active market.

## MUST gates (step 3)

Shared evaluator `client_intent_runtime.evaluate_candidate_intent` now handles two Israeli keys, added to the intent only when the market is Israel (`israel_must_gates.py`):

- `IL_FUNCTIONAL_LEVEL` from `israelMarket.functionalLevel` (INDEPENDENT / FRAIL / NURSING / COGNITIVE_FRAIL). PASS only on a ward or level stated by a source list; a license type's regulatory scope can only exclude; unknown is PENDING. An unknown family level is PENDING everywhere (ask the family).
- `IL_MOH_CODE_AGREEMENT` when `israelMarket.fundingPathway` = MOH_CODE. PASS on בהסכם=כן, FAIL on בהסכם=לא, otherwise PENDING.

Open owner question: the existing `LICENSE_CURRENTLY_VALID` MUST needs a license status and expiry date. The Israeli lists give neither, so every Israeli facility is PENDING on it and none can pass yet. Treating presence on a dated official list as license evidence would be a principle change (class C) and was not made.

## Not done yet

- Nevada-specific need gates (ADL, medication, memory care) still read Nevada evidence; for Israel they stay PENDING until Israeli evidence exists.
- Questionnaire screens that collect `israelMarket.functionalLevel` and `israelMarket.fundingPathway` (schema fields exist).
- Frontend i18n (he/ru/ar/en, RTL), ₪ and km.
- Addresses and coordinates for distance filtering.
