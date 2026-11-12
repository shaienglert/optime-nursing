# OOMNIK Israel — owner decisions

Recorded 2026-11-12. Owner approvals required by AGENTS.md (classes C/D/E).

| # | Decision | Class | Owner answer |
|---|---|---|---|
| 1 | Deployment model | E | Separate deployment for Israel (`OPTIME_CANONICAL_MARKET=israel`); the Nevada pilot is untouched |
| 2 | Functional status (independent / frail / nursing / cognitively frail) as a MUST filter | C | Yes; unclear status means the system asks, never assumes |
| 3 | Funding pathway (MoH "code", Welfare assistance, private) as a MUST filter | D | Yes; a family with a MoH code sees only institutions with a MoH agreement |
| 4 | Commission on state-funded placements (MoH code / Welfare) | D | Charge the same as private placements. Legal question remains open and is the owner's accepted risk |
| 5 | Family interface languages | C | Hebrew, Russian, Arabic, English |
| 6 | Cross-list facility merging | C | None: every source row is its own facility record |

## Data (step 1, this branch)

- Raw sources: `data/israel/raw/` (received 2026-11-12).
- Build: `python scripts/build_israel_universe.py` → `database/israel_facility_universe_canonical.json` (467 records: 255 MoH geriatric nursing institutions, 115 Welfare old-age homes, 97 protected-housing homes).
- Missing fields (address, coordinates, availability, ward types in the MoH list) stay `null`/`UNKNOWN`; they are not negative evidence.

## Not done yet

- Startup still enforces the Nevada scope (`purge_non_nevada_facilities`, Las Vegas runtime import) and routes filter on `NEVADA_STATE_CODE`; these must become market-aware before an Israeli deployment can serve requests.
- Structured profile fields for functional status and funding pathway.
- Frontend i18n (he/ru/ar/en, RTL), ₪ and km.
- Addresses and coordinates for distance filtering.
