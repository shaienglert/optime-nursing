# Research Institute delivery contract

Classification: B — implementation completion.

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-004, PR-005, PR-007; Knowledge Is The Strategic Asset; Knowledge Never Stops Improving.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

## Daily reporting and owner delivery

Implementation completion under the same evidence/unknown principles. Daily audit
captures are append-only records in the existing database ledger, exposed only by
authenticated admin endpoints. They enumerate registered and observed agents,
runs, ingested records and guard decisions. Missing activity is MISSING. A guard's
USED label is permission, not demonstrated fact adoption; absent consumption
traces, adopted fact counts remain null. Exports omit resident and recommendation
identifiers. The monitor exports one file per agent plus a daily summary even when
facility coverage is degraded. GitHub retains these artifacts for 90 days; the
owner delivery task saves persistent copies in Daily-Reports and emails only the
authenticated owner. Repository code is not production activation. Owner policy
questions do not change eligibility until explicitly decided.

Owner scope: October 2, 2026 request to repair the Research Institute as a system,
include official complaints over the past year, keep source ratings separate, and
exclude referral-marketplace ratings.

## Ownership and delivery

The existing daily scheduler owns facility coverage, independently of searches.
Every real facility has seven explicit research obligations in addition to the
existing care, price, couple and rehabilitation research. Synthetic pilot entities
are excluded from live collection and from real-market coverage statistics.

The existing queue worker executes collection. Institutional observations persist
in the existing AgentKnowledgeRecord table (no schema migration). A task marked
DONE means an attempt finished. Only VERIFIED delivery counts as verified delivery.
Partial, inaccessible, unauthorized, stale and failed sources remain gaps.

The protected coverage endpoint exposes every facility/topic gap and the next
action. The latest attempt wins; source failures cannot be hidden behind an older
success. A time-to-live expires otherwise verified observations at read time.
Public facility pages and personal reports display this evidence. Report
enrichment happens after ranking; coverage does not become a ranking score.

## Source rules

- CMS and Medicare are one source. Original integer stars are preserved.
- CMS complaint-related deficiency rows are not counts of complaints filed.
  Their dates are survey dates. No findings does not mean no complaints.
- A Nevada portal page fetch does not establish complaint counts or correction.
  Exact inspection documents must be extracted and verified before those fields
  can be asserted. Current collector reports PARTIAL for a confirmed report page.
- Google requires an authorized API connection and attribution/storage compliance.
  This change does not store Google ratings or scrape them.
- U.S. News/Newsweek redistribution and Joint Commission data access remain
  explicit blockers until authorized connections exist.
- Staffing shift ratios require dated supporting documents; there is no invented
  common assisted-living care-level scale or automatic turnover cutoff.
- Referral marketplace ratings are excluded. Facility names, score proxies and
  hashes do not establish social activity, news, lawsuits or consumer opinions.

## Operation

Public: GET /canonical-facilities/{id}/research.
Protected: GET /admin/research-institute/coverage; POST refresh; POST process
(limit 1–50). The authenticated recurring workflow refreshes the queue daily,
drains bounded batches and captures the final coverage report. A non-current real
market produces a failed monitoring check, not a misleading green run.

The workflow needs OOMNIK_RESEARCH_BACKEND_URL as a repository variable and
OOMNIK_RESEARCH_ADMIN_TOKEN as a repository secret. Deployment and those values must be verified before
claiming production collection is active. Research source failures and missing
rights are not closed by this implementation.

## Validation on 24dde8c5

54 focused backend checks passed (research delivery, scheduler, event refresh,
pricing ingestion, provider evidence, readiness, golden decisions, independent
oracle and Oomniker). TypeScript and lint for the new panels passed. Protected
research endpoints reject missing admin credentials. The pilot report remains
explicitly synthetic. Seven existing personal-report tests fail identically on
the unmodified base because their decision-state fixtures are not authoritative.

A direct CMS fetch from the execution environment timed out. This is not proof
that production access works or that CMS itself is unavailable. Production source
connectivity, document extraction, credentials and redistribution rights remain
deployment acceptance requirements.

Owner clarification: show known complaints; never assert "no complaints". A
failed refresh preserves already collected official findings with their dates
and sources while marking current source coverage incomplete.
