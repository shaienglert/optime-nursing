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

## Facility registration (step 4)

- `PUT /provider/facilities/{id}/israel-registration` (same portal identity and role model as capabilities; OWNER/ADMIN/CLINICAL_DIRECTOR). Stores functional levels served, MoH code agreement, license authority/number/expiry, monthly price and deposit (₪) in `facility_market_registrations`, with an audit row per change.
- On the Israeli market the shared evaluator overlays the registration onto the candidate row as `FACILITY_SUPPLIED` facts, including `license_status`/`expiration_date` for `LICENSE_CURRENTLY_VALID`. An unregistered facility stays PENDING.
- Hebrew RTL form: `/provider/{facilityId}/israel`.

## Family questionnaire (step 5)

- Hebrew RTL intake at `/he/intake`: relationship, age, functional level (with an explicit "not sure"), funding pathway, monthly budget in ₪ (private only), city, maximum distance in km, free text.
- Writes `questionnaireState.israelMarket` (schema fields allowlisted) and continues to `/results`. Free text goes to `notes` for the shared AI interpreter.
- "Not sure" is stored as UNCLEAR: the engine keeps every facility PENDING; the page tells the family no facility will be shown as a match until it is clear.

## Facility home pages (step 6)

- One uniform Hebrew home page per registry facility: `/he/facility/{canonical_id}` (API `GET /api/il/facilities/{id}`), directory `/he/facilities` (`GET /api/il/facilities`).
- Sections: photos, services and licensing (facility-supplied only), activities, and public-list details labelled with their source. Unknown is shown as "not yet updated by the facility" / "not in the list".

## Facility portal: owner requirements (2026-11-13), not built yet

- Each facility receives a personal link from OOMNIK outreach; the link is how it enters the portal.
- In the portal: fill the facility questionnaire, confirm the information on its page, upload photos, connect a calendar for events or upload a monthly activity plan.
- Photo upload: built (see below).
- Personal link and sessions: built (see below).
- Known gap still open: activity classification only recognises English words.

## Photo upload (step 7)

- `POST /provider/facilities/{id}/photos/upload` (multipart). Same role rule as URL photos (OWNER/ADMIN/MARKETING); permission is checked before anything is written.
- Every file is decoded and re-encoded as JPEG, max 1600px, EXIF stripped (removes phone GPS). Non-images are refused with a Hebrew reason. The browser shrinks to 2000px first because the Vercel proxy limits request size.
- Files are stored under `OPTIME_UPLOAD_DIR` and served at `/media/facility_photos/{id}/{uuid}.jpg` only while the photo is active.
- Hosting (owner, 2026-11-13): the Render workspace is on Pro and the existing service is on a paid compute plan, so a disk can be added ($0.25/GB/month per Render's screen). Decision: no disk on the Nevada service; the Israeli service gets a 1GB disk mounted at `/var/data` with `OPTIME_UPLOAD_DIR=/var/data`. Without a disk, uploads are lost on every deploy.
- Photos do not affect matching or ranking.

## Personal portal link (step 8)

- OOMNIK creates a link per facility (`POST /admin/portal/invites`, admin token; bulk: `scripts/create_israel_portal_links.py`, which writes a CSV outside the repo). Link: `/he/portal/{token}`.
- Opening the link redeems it for a 30-day session (`Authorization: Bearer`); the page then drops the token from the address bar. The link itself is the credential (owner decision): 90-day expiry, stored only as SHA-256, a new link revokes the old one, `POST /admin/portal/invites/{id}/revoke` also ends its sessions.
- Provider writes (registration, photos, capabilities, activities import, identity field updates, staff invites, role changes, audit revert, verification persist) take the acting user from the session; a session for facility A cannot write to B. In the Israeli deployment a session is required (`OPTIME_PROVIDER_SESSION_REQUIRED` defaults to on for `israel`) and the open email-claim flow is closed. Nevada keeps the old body `user_id` behaviour until it is migrated.
- The portal pre-fills the saved answers; resubmitting unchanged is logged as a confirmation (`israel_registration:confirmed`).

## Full facility questionnaire (step 9)

- Schema: `backend/app/services/israel_facility_questionnaire.py` (`il-facility-questionnaire-v1`), served at `GET /api/il/facility-questionnaire`; the portal renders it and the backend validates with the same definition.
- 8 sections, 50 questions: contact & address; population & licence (levels, special units, MoH agreement, licence, min age, couples, gender, beds); availability per level and short stays; funding tracks and prices (range, deposit, depreciation, maintenance fee, what is included); medical (24/7 nurse, physician, geriatrician, 12 clinical capabilities, therapists, hospital distance); language, religion and food; rooms and building (incl. shelter/ממ"ד, accessibility); family and visits.
- Required: address, contact name, phone, funding tracks, staff languages, plus the core licence/level questions. MoH agreement and the "MoH code" funding track must agree.
- Unanswered = UNKNOWN, never stored as "no". Unchanged resubmission = logged confirmation.
- Matching use: unchanged. Only the two approved MUST gates read the answers; every other answer is displayed on the facility page. Using any new answer to filter or rank needs owner approval.

## Not done yet

- Nevada-specific need gates (ADL, medication, memory care) still read Nevada evidence; for Israel they stay PENDING until Israeli evidence exists.
- Results page, adaptive interview and site shell are still English.
- A follow-up flow that helps a family who chose "not sure" settle the functional level.
- Distance filtering in km (needs facility addresses/coordinates).
- Russian, Arabic and English versions of the Israeli intake.
