# Provider Portal Review

## Part 4: Provider Journey Assessment

Journey reviewed:

Provider Registration -> Identity Verification -> Provider Dashboard -> Questionnaire -> Photos -> Activities -> Verification Inbox -> Lead Management -> Profile Completeness -> Analytics

## Current State By Stage

| Stage | Current State | Strength | Gaps |
| --- | --- | --- | --- |
| Registration | API endpoints for registration start/verify | Domain and OTP controls exist | Full self-serve onboarding UX not complete |
| Identity Verification | License validation, role checks, reverification flows exist | Strong security intent and audit reversibility | Need production-grade anti-abuse + monitoring |
| Provider Dashboard | Data model and service capabilities exist | Good backend primitives | Missing robust dashboard UI |
| Questionnaire | Facility questionnaire schema exists | Structured capability model | Needs workflow UX and completion guidance |
| Photos | Photo table exists | Basic metadata captured | Missing moderation and quality scoring UX |
| Activities | Import APIs and category model exist | Useful category abstraction | Missing recurring sync and calendar health UX |
| Verification Inbox | Request/response persistence exists | Workflow core is present | Missing inbox queue UI, assignment, SLA states |
| Lead Management | Not fully implemented | Opportunity clear | Missing lead lifecycle tables/APIs/UI |
| Profile Completeness | Completeness table exists | Tie-break and provider value alignment | Missing provider-facing recommendation actions |
| Analytics | Reports exist in scripts | Rich internal signals | Missing provider-facing analytics portal |

## Detailed Gap List

1. No full provider dashboard frontend experience matching backend depth.
2. Lead management lifecycle absent as first-class domain.
3. Verification inbox lacks list/filter/assignment/escalation interfaces.
4. Missing provider-focused retention and conversion analytics UI.
5. Limited workflow guidance for improving profile completeness.
6. No subscription/entitlement boundary for premium provider features.

## Recommended API Additions

1. GET /provider/facilities/{facility_id}/inbox
2. POST /provider/facilities/{facility_id}/inbox/{item_id}/ack
3. POST /provider/facilities/{facility_id}/inbox/{item_id}/resolve
4. GET /provider/facilities/{facility_id}/leads
5. POST /provider/facilities/{facility_id}/leads/{lead_id}/stage
6. GET /provider/facilities/{facility_id}/analytics
7. GET /provider/facilities/{facility_id}/profile-completeness/actions

## Monetization Opportunities

1. Fast-response verification tier with SLA guarantees.
2. Premium lead analytics and occupancy forecasting.
3. Enterprise multi-community command center.
4. CRM connector add-ons for referral pipelines.

## Provider Readiness Scorecard

- Security primitives: 8/10
- Workflow completeness: 5/10
- UX maturity: 4/10
- Revenue readiness: 5/10

Overall provider portal maturity: Medium, with strong backend foundations and notable productization gaps.
