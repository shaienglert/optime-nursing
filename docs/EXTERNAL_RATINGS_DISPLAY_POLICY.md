# External ratings — owner-approved display-only policy

RELEVANT EXISTING PRINCIPLES: PR-001 outcome-only optimization; PR-002 no evidence/no score; PR-003 visible uncertainty; PR-004 no commercial bias; PR-005 unknown is not negative evidence; PR-007 generic completeness must not drive ranking.

DOES THIS CHANGE ALTER ANY PRINCIPLE? YES — external public reputation is excluded from recommendation order, including tie-breaking and evidence-count advantages.

OWNER APPROVAL REQUIRED? YES — ALREADY PROVIDED in the 2026-11-06 conversation: display Google and U.S. News attribution while excluding them from Oomnik ranking, followed by explicit execution authorization.

Classification: D, explicitly owner-approved. Public ratings and third-party recognition are presentation only. Government inspection, licensing and care-capability evidence remain governed decision inputs. There is no new numerical score or weight.

Implementation requirements:
- Keep external ratings outside ranking payloads and comparable measures. No score, review volume, award, coverage or source availability may improve rank or resolve ties.
- Do not count a reputation-only research record or verified reputation identity as additional case-relevant evidence.
- Show original Google rating plus review count, attribution and source link. Fetch on demand from Places API only with server configuration and identity-bound Place ID; do not persist/cache Google content.
- Show the exact U.S. News recognition text and assessment year, with an identity-bound source URL and confirmed display permission. Never turn recognition into invented stars or percentages.
- Do not repurpose the legacy PUBLIC_LOCAL_BUSINESS_INDEX snapshot as Google. Synthetic facilities never inherit real reviews.
- Unavailable, failed and missing source data are not zero scores or evidence against a facility.
- Display plain source names and links; do not copy proprietary award logos.

Activation: approved source identities go in data/nevada/verified/external_rating_sources.json; set GOOGLE_PLACES_API_KEY on the backend for Google. No real ratings or permissions are fabricated in the initial empty registry. API keys stay server-side. The feature has no ranking-network dependencies; source failures only affect the display panel.

Each registry record requires canonical_facility_id, facility_name, address, city and identity_verified=true. The google object contains the approved place_id, not a stored Google score. The us_news object contains the exact recognition text, assessment_year, observed_at (ISO date), source_url on health.usnews.com, and display_permission_verified=true only after the permission check. Do not put API keys in this file. Duplicate identity mappings fail closed.

Removal of raw evidence-payload counts from the legacy fit count prevents a reputation-only agent record from creating a ranking advantage indirectly. The remaining count reflects matched requirements/preferences and case-relevant matched needs, not how many research records were collected.
