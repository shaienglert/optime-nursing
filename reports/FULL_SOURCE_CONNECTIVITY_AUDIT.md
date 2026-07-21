# Full Source Connectivity Audit

- Generated: 2026-07-21T09:56:51.856733+00:00
- Total sources discovered: 33
- Total sources tested: 28
- Connected with verified real data: 16

## Executive Summary

- CMS/Medicare: PARTIAL
- CMS real facility data: YES
- Inspections/Deficiencies: YES
- Staffing/PBJ: YES
- Penalties/Fines: YES
- Ownership: YES
- Florida AHCA: NO
- Facility Websites: PARTIAL
- Reviews/Reputation: PARTIAL
- News/Public Web: YES
- Legal/Regulatory: YES
- Large-scale enrichment readiness: PARTIALLY_READY

## Status Counts

- CONNECTED_REAL_DATA: 16
- GEO_BLOCKED_OR_SUSPECTED: 4
- BOT_CHALLENGE: 4
- DNS_OR_NETWORK_FAILURE: 0
- NOT_TESTABLE_WITH_CURRENT_CONFIG: 5
- ACCESS_DENIED: 2
- RATE_LIMITED: 1
- TIMEOUT: 0
- ENDPOINT_BROKEN: 0
- CONNECTED_NO_USEFUL_DATA: 1
- AUTH_REQUIRED: 0

## Source Results

| Source | Category | Network | Real Data | Connector | Functional | Status | Previous | Action Required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Florida AHCA License Profile Sample | FLORIDA | NO | NO | PARTIAL | NO | GEO_BLOCKED_OR_SUSPECTED | UNKNOWN | YES |
| Florida AHCA Portal | FLORIDA | NO | NO | PARTIAL | NO | BOT_CHALLENGE | UNKNOWN | YES |
| Official Facility Website Sample - Prior Failure 2 | FACILITY_PRIMARY | NO | NO | YES | PARTIAL | GEO_BLOCKED_OR_SUSPECTED | SOURCE_GEO_BLOCKED_OR_SUSPECTED | YES |
| Official Facility Website Sample - Prior Failure 3 | FACILITY_PRIMARY | NO | NO | YES | PARTIAL | GEO_BLOCKED_OR_SUSPECTED | SOURCE_GEO_BLOCKED_OR_SUSPECTED | YES |
| Official Facility Website Sample - Prior Failure 4 | FACILITY_PRIMARY | NO | NO | YES | PARTIAL | GEO_BLOCKED_OR_SUSPECTED | SOURCE_GEO_BLOCKED_OR_SUSPECTED | YES |
| Official Facility Website Sample - Prior Failure 5 | FACILITY_PRIMARY | NO | NO | YES | PARTIAL | ACCESS_DENIED | SOURCE_ACCESS_FAILED | YES |
| Official Facility Website Sample - Prior Failure 1 | FACILITY_PRIMARY | NO | NO | YES | PARTIAL | RATE_LIMITED | SOURCE_RATE_LIMITED | YES |
| Medicare Care Compare | FEDERAL/MEDICARE | YES | NO | NO | NO | CONNECTED_NO_USEFUL_DATA | UNKNOWN | YES |
| CMS Inspection Dataset (r5ix-sfxw) | FEDERAL/CMS | YES | YES | YES | YES | CONNECTED_REAL_DATA | UNKNOWN | NO |
| CMS Ownership Fields | FEDERAL/CMS | YES | YES | PARTIAL | PARTIAL | CONNECTED_REAL_DATA | UNKNOWN | YES |
| CMS Penalties/Fines Fields | FEDERAL/CMS | YES | YES | PARTIAL | PARTIAL | CONNECTED_REAL_DATA | UNKNOWN | YES |
| CMS Provider Dataset (4pq5-n9py) | FEDERAL/CMS | YES | YES | YES | YES | CONNECTED_REAL_DATA | UNKNOWN | NO |
| CMS Quality Dataset (djen-97ju) | FEDERAL/CMS | YES | YES | YES | YES | CONNECTED_REAL_DATA | UNKNOWN | NO |
| CMS Staffing/PBJ Fields | FEDERAL/CMS | YES | YES | YES | YES | CONNECTED_REAL_DATA | UNKNOWN | NO |
| Official Facility Website Sample - Prior Success | FACILITY_PRIMARY | YES | YES | YES | PARTIAL | CONNECTED_REAL_DATA | RAN_CONNECTED_NO_NEW_VALUE | YES |
| BBB | OTHER | NO | NO | NO | NO | ACCESS_DENIED | UNKNOWN | YES |
| Glassdoor | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | BOT_CHALLENGE | UNKNOWN | YES |
| LinkedIn | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | BOT_CHALLENGE | UNKNOWN | YES |
| Yelp | REVIEWS/REPUTATION | NO | NO | PARTIAL | NO | BOT_CHALLENGE | UNKNOWN | YES |
| Facebook | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | NOT_TESTABLE_WITH_CURRENT_CONFIG | UNKNOWN | YES |
| Google Reviews / Maps | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | NOT_TESTABLE_WITH_CURRENT_CONFIG | UNKNOWN | YES |
| Indeed | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | NOT_TESTABLE_WITH_CURRENT_CONFIG | UNKNOWN | YES |
| Instagram | REVIEWS/REPUTATION | YES | NO | PARTIAL | NO | NOT_TESTABLE_WITH_CURRENT_CONFIG | UNKNOWN | YES |
| Public Event Calendars | OTHER | NO | NO | NO | NO | NOT_TESTABLE_WITH_CURRENT_CONFIG | UNKNOWN | YES |
| A Place for Mom | REVIEWS/REPUTATION | YES | YES | NO | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| CMS Survey Dataset (svdt-c123) | FEDERAL/CMS | YES | YES | PARTIAL | PARTIAL | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Caring.com | REVIEWS/REPUTATION | YES | YES | NO | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Local News (Google News) | NEWS/PUBLIC_WEB | YES | YES | PARTIAL | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Press Releases (PRNewswire) | NEWS/PUBLIC_WEB | YES | YES | PARTIAL | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Public Court Records (CourtListener) | LEGAL/REGULATORY | YES | YES | PARTIAL | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Reddit | OTHER | YES | YES | NO | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| SeniorAdvisor | REVIEWS/REPUTATION | YES | YES | NO | NO | CONNECTED_REAL_DATA | UNKNOWN | YES |
| Seniorly Sample Profile | REPUTATION/PROFILE | YES | YES | YES | PARTIAL | CONNECTED_REAL_DATA | UNKNOWN | YES |

## Critical Fix Queue

- P0 | Florida AHCA License Profile Sample | GEO_BLOCKED_OR_SUSPECTED | 403/access denied | Would require parsing and facility mapping
- P0 | Florida AHCA Portal | BOT_CHALLENGE | 403 with challenge markers | Would require live AHCA connector
- P0 | Medicare Care Compare | CONNECTED_NO_USEFUL_DATA | Connected but expected content markers not found | Would require explicit connector/search path
- P0 | Official Facility Website Sample - Prior Failure 1 | RATE_LIMITED | HTTP 429 | Monitor if current network environment restores access
- P0 | Official Facility Website Sample - Prior Failure 2 | GEO_BLOCKED_OR_SUSPECTED | 403/access denied | Monitor if current network environment restores access
- P0 | Official Facility Website Sample - Prior Failure 3 | GEO_BLOCKED_OR_SUSPECTED | 403/access denied | Monitor if current network environment restores access
- P0 | Official Facility Website Sample - Prior Failure 4 | GEO_BLOCKED_OR_SUSPECTED | 403/access denied | Monitor if current network environment restores access
- P0 | Official Facility Website Sample - Prior Failure 5 | ACCESS_DENIED | HTTP 403 | Monitor if current network environment restores access
- P1 | CMS Ownership Fields | CONNECTED_REAL_DATA | Useful real dataset rows retrieved | No direct dedicated ownership connector
- P1 | CMS Penalties/Fines Fields | CONNECTED_REAL_DATA | Useful real dataset rows retrieved | No dedicated live penalties connector
- P1 | Official Facility Website Sample - Prior Success | CONNECTED_REAL_DATA | Found useful content marker: skilled nursing | Monitor variability by domain
- P2 | A Place for Mom | CONNECTED_REAL_DATA | Found useful content marker: senior living | No configured connector or endpoint
- P2 | BBB | ACCESS_DENIED | HTTP 403 | Source marked unconfigured in repo audits
- P2 | CMS Survey Dataset (svdt-c123) | CONNECTED_REAL_DATA | Useful real dataset rows retrieved | Needed if survey-level usage is expected
- P2 | Caring.com | CONNECTED_REAL_DATA | Found useful content marker: senior living | No configured connector or endpoint
- P2 | Facebook | NOT_TESTABLE_WITH_CURRENT_CONFIG | Landing page reachable but Facebook connector auth missing: ['FACEBOOK_ACCESS_TOKEN'] | Token missing for real connector
- P2 | Glassdoor | BOT_CHALLENGE | Challenge page | Auth missing for real connector
- P2 | Google Reviews / Maps | NOT_TESTABLE_WITH_CURRENT_CONFIG | Missing required auth: ['GOOGLE_PLACES_API_KEY'] | Auth/config missing for real connector
- P2 | Indeed | NOT_TESTABLE_WITH_CURRENT_CONFIG | Landing page reachable but Indeed connector auth missing: ['INDEED_API_KEY'] | Auth missing for real connector
- P2 | Instagram | NOT_TESTABLE_WITH_CURRENT_CONFIG | Landing page reachable but Instagram connector auth missing: ['INSTAGRAM_ACCESS_TOKEN'] | Token missing for real connector
- P2 | LinkedIn | BOT_CHALLENGE | Challenge page | Auth missing for real connector
- P2 | Local News (Google News) | CONNECTED_REAL_DATA | Found useful content marker: nursing | No dedicated article ingestion connector
- P2 | Press Releases (PRNewswire) | CONNECTED_REAL_DATA | Found useful content marker: press release | No dedicated press-release ingestion connector
- P2 | Public Court Records (CourtListener) | CONNECTED_REAL_DATA | Found useful content marker: courtlistener | No live legal ingestion connector
- P2 | Public Event Calendars | NOT_TESTABLE_WITH_CURRENT_CONFIG | Needs endpoint inventory before testing | Needs endpoint inventory before testing
- P2 | Reddit | CONNECTED_REAL_DATA | Found useful content marker: reddit | Source marked unconfigured in repo audits
- P2 | SeniorAdvisor | CONNECTED_REAL_DATA | Found useful content marker: senior | No configured connector or endpoint
- P2 | Seniorly Sample Profile | CONNECTED_REAL_DATA | Found useful content marker: reviews | Profile parsing remains shallow
- P2 | Yelp | BOT_CHALLENGE | 403 with challenge markers | Auth/config missing for real connector
