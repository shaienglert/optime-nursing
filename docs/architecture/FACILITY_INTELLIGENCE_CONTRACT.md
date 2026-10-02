# OOmnik Facility Intelligence Contract — Draft v0.1

Status: OWNER-APPROVED DIRECTION / SHADOW IMPLEMENTATION. This contract defines facility-side truth used by Research Institute and Decision Engine.

## Core principle

OOmnik maintains a continuously updated Facility Evidence Profile for every real community in the catalog. Family searches read a consistent evidence snapshot; they do not trigger ad-hoc web research that can advantage communities researched earlier.

Synthetic pilot communities never go to the public web. Their closed synthetic fixtures are their complete test truth.

## Evidence authority

### Provider-entered facts
Facts entered by an authorized facility through its OOmnik portal are operational facts for matching and display. They do not require independent web confirmation before use.

Store:
- value
- source_type = PROVIDER
- provider_reported_at
- observed_at
- profile_version
- previous_value where applicable

### License exception
A provider-entered license number/status is not LICENSE_VERIFIED until checked against the applicable government/regulatory source. Provider claim may be displayed as provider-reported, but regulatory verification controls any legal licensing gate.

### Availability exception — always verify
Availability is never final truth, in either direction.
AVAILABLE, LIMITED, WAITLIST, UNAVAILABLE/NO and UNKNOWN all require current direct verification with the facility before OOmnik treats availability as final for a family.

Website/provider availability is stored as LAST_REPORTED_AVAILABILITY with source and timestamp.

For a move around 30 days or later, current availability does not change initial fit ranking.
For an immediate move, recent availability may affect practical presentation/order, but even NO/UNAVAILABLE is not a permanent exclusion because inventory is fluid. It must be rechecked.

Every client-facing availability statement must make clear that OOmnik will verify final availability directly with the selected community.

## Research Institute

The Research Institute continuously maintains intelligence on every real catalog community through three paths:

1. Provider updates: changes in the OOmnik facility portal become available immediately.
2. Daily active research: search official facility websites, government/regulatory sources, CMS where applicable, and relevant public sources for every real facility, even when no family searched for it.
3. Event-driven refresh: detected source/page/regulatory changes create immediate evidence-refresh work rather than waiting for the next daily sweep.

Research findings never silently erase provider-entered facts. A material contradiction creates REVIEW_REQUIRED / CONFLICT with both pieces of evidence retained.

## Rooms and floor plans

Facility profile supports multiple room/unit types. For each type store when known:
- room_type_id
- name (Studio, One Bedroom, Two Bedroom, Private Care Room, Shared/Companion, etc.)
- care setting / eligible resident type
- single/couple occupancy
- floor-plan details and size
- accessibility features
- room-specific photos
- base monthly rent
- mandatory recurring fees
- known care fee / level-of-care fee
- second-person/couple surcharge
- entrance/community fee
- total_known_monthly_cost
- pricing qualifier (EXACT / STARTING_AT / RANGE / UNKNOWN)
- source and observed_at
- last reported availability + timestamp
- final_availability_status = REQUIRES_DIRECT_VERIFICATION

Provider-entered room facts are facts, subject only to the license and availability exceptions above.

Research Institute extracts room/floor-plan information from official facility sites when published and monitors it for changes.

## Pricing

Do not collapse pricing to one current_price when richer information exists.

A published “starting at $4,450” remains STARTING_AT $4,450; OOmnik never represents it as an exact total price.

Pricing model distinguishes:
- base rent
- care/level-of-care fee
- mandatory monthly fees
- second resident/couple fee
- entrance/community fee
- known total monthly cost

A base rent within the family budget does not prove total affordability when required care charges are unknown. In that case total affordability is UNKNOWN/PENDING.

Result cards should show relevant room types and known prices, e.g. Studio — Starting at $5,200; One Bedroom — Starting at $6,100, together with what is known/unknown about care fees.

Budget presentation follows the owner rule: best fully eligible options at/below stated budget first, then otherwise-eligible options up to +10%, with exact deviation shown. Unknown total cost is never silently treated as within budget.

## Evidence states

Facility facts may carry:
- PROVIDER_REPORTED
- REGULATORY_VERIFIED
- RESEARCH_OBSERVED
- UNKNOWN
- CONFLICT
- REVIEW_REQUIRED

Availability additionally always carries REQUIRES_DIRECT_VERIFICATION.

UNKNOWN is not negative evidence and not PASS for a MUST.
A verified negative on a MUST excludes.
A provider-entered non-license, non-availability fact may satisfy the relevant facility fact requirement unless a governed conflict requires review.

## Search snapshot and ranking

Decision Engine reads a versioned Facility Evidence Profile snapshot. It does not wait for live internet research during a family search.

Missing NICE evidence does not penalize a community as if it were negative.
Missing MUST evidence is PENDING VERIFICATION.
Provider facts can satisfy MUSTs under the authority rules above.
License MUST requires regulatory verification.
Availability never becomes a permanent MUST PASS/FAIL without direct current verification.

## Oomniker

When the candidate universe is constrained, Oomniker analyzes the confirmed client profile against the actual evidence snapshot and identifies which user-changeable constraints reduce supply. It explains which changes (budget, radius, preference strictness, etc.) would expose meaningful additional options and the expected effect. It never changes a parameter without the family's action.

## Versioning

Every evidence snapshot has facility_evidence_schema_version and snapshot_version. Historical decisions retain the snapshot/version used so the recommendation can be reconstructed even after facility facts change.
