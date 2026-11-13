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
| 8 | Status of facility-supplied data (2026-11-13) | C | Data the facility fills in itself counts as verified |
| 7 | Role of the source lists (2026-11-13) | C | The lists are an outreach catalog for inviting facilities to register. Matching uses only what the facility fills in at registration (`basis: FACILITY_SUPPLIED`); list data and license type decide nothing |

## Shared engine vs. Israeli layer (owner, 2026-11-12)

Shared by every market (one implementation, fixes land in both): interpreting the family's needs, MUST filtering, ranking, the match explanation, and OOmniker (suggests relaxing a preference only when at least two matching alternatives exist).

Israeli layer only: Hebrew (and ru/ar/en) questionnaire, setting types, the facility registry, licensing sources, ILS prices, funding pathways, and facility contact.

Licensing, pricing and care capabilities are stored as separate blocks with a source and basis per field. Every listed facility starts `registration_status: NOT_REGISTERED`; being on a list never makes it a match.

Owner decision (2026-11-13): information the facility fills in itself counts as verified. `FACILITY_SUPPLIED` facts can pass or fail a MUST without further verification.

## Data (step 1, this branch)

- Raw sources: `data/israel/raw/` (received 2026-11-12).
- Build: `python scripts/build_israel_universe.py` → `database/israel_facility_universe_canonical.json` (467 records: 255 MoH geriatric nursing institutions, 115 Welfare old-age homes, 97 protected-housing homes).
- Missing fields (address, coordinates, availability, ward types in the MoH list) stay `null`/`UNKNOWN`; they are not negative evidence.

## Market scope (step 2)

- `market_scope.active_state_code()`: `IL` when `OPTIME_CANONICAL_MARKET=israel`, `NV` for every other market (unchanged behavior).
- Startup on the Israeli market purges non-IL rows and imports the Israeli universe; facility routes, market reports and external discovery filter on the active market.

## MUST gates (step 3)

Shared evaluator `client_intent_runtime.evaluate_candidate_intent` handles two Israeli keys, added to the intent only on the Israeli market (`israel_must_gates.py`). Both are decided only by facility-supplied registration data; otherwise PENDING.

- `IL_FUNCTIONAL_LEVEL` from `israelMarket.functionalLevel` (INDEPENDENT / FRAIL / NURSING / COGNITIVE_FRAIL). An unknown family level is PENDING everywhere (ask the family).
- `IL_MOH_CODE_AGREEMENT` when `israelMarket.fundingPathway` = MOH_CODE.

The existing `LICENSE_CURRENTLY_VALID` MUST reads license status and expiry; for Israel these come from the facility's registration.

## Not done yet

- Nevada-specific need gates (ADL, medication, memory care) still read Nevada evidence; for Israel they stay PENDING until Israeli evidence exists.
- Facility registration form that writes FACILITY_SUPPLIED levels/wards, MoH agreement, license status/expiry, prices.
- Questionnaire screens that collect `israelMarket.functionalLevel` and `israelMarket.fundingPathway` (schema fields exist).
- Frontend i18n (he/ru/ar/en, RTL), ₪ and km.
- Addresses and coordinates for distance filtering.
