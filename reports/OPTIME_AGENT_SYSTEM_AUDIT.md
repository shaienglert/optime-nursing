# OPTIME Agent System Audit

## Exact Agent Inventory

- Total known agents/systems: 15
- Automatic runtime-backed agents: 11
- Manual/spec-only or unknown-status agents: 4

## Schema Root Cause

- `FacilityIntelligenceProfile` in `backend/app/models/facility.py` expects these columns in `facility_intelligence_profiles`:
  - `signal_details`
  - `visual_hero_image`
  - `visual_gallery_images`
  - `visual_lifestyle_tags`
  - `visual_confidence_score`
  - `visual_coverage_score`
- The live backend SQLite database at `backend/optime_nursing.db` did not contain those columns.
- `Base.metadata.create_all()` does not alter existing tables.
- Startup previously only applied `ensure_provider_identity_schema(engine)`, so the facility-intelligence table drift remained unapplied.

## Schema Fix Applied

- Added `ensure_facility_intelligence_profile_schema(engine)` in `backend/app/services/schema_migrations.py`.
- Wired that upgrade into backend startup in `backend/app/main.py`.
- Applied the upgrade safely to the live backend database without recreating the table or losing data.
- Fixed timezone-aware vs timezone-naive datetime comparisons in `backend/app/services/agent_knowledge_reports.py`.
- Fixed successful refresh bookkeeping so `failed_refresh_count`, `refresh_error`, and `freshness_status` now clear correctly on success.

## Controlled Automatic Agent Execution

- Automatic agents attempted in controlled run: 11
- Controlled refresh result: 11 refreshed, 0 failures
- Successful refresh events in last 24h: 22
- Failed refresh events in last 24h: 264
- Automatic agents that created verified new value in last 24h: 0
- Automatic agents that ran with no new value in last 24h: 11
- Automatic agents that failed in last 24h: 0

## Before / After Evidence

- New agent knowledge records in last 24h: 0
- New facility intelligence rows updated in last 24h: 0
- Net outcome of controlled run: successful execution state was restored, but no verified new knowledge/evidence objects were created during the run.

## Per-Agent Runtime State

```json
[
  {
    "agent_key": "activities_intelligence",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.311578",
    "next_refresh_at": "2026-07-20 19:40:34.311578"
  },
  {
    "agent_key": "clinical_knowledge",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.282956",
    "next_refresh_at": "2026-07-21 13:40:34.282956"
  },
  {
    "agent_key": "data_quality",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.350889",
    "next_refresh_at": "2026-07-20 13:45:34.350889"
  },
  {
    "agent_key": "family_experience",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.322398",
    "next_refresh_at": "2026-07-20 14:40:34.322398"
  },
  {
    "agent_key": "knowledge_graph",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.341250",
    "next_refresh_at": "2026-07-21 13:40:34.341250"
  },
  {
    "agent_key": "matching_improvement",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.334822",
    "next_refresh_at": "2026-07-20 13:45:34.334822"
  },
  {
    "agent_key": "nutrition_intelligence",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.317235",
    "next_refresh_at": "2026-07-21 13:40:34.317235"
  },
  {
    "agent_key": "outcome_learning",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.329840",
    "next_refresh_at": "2026-07-21 13:40:34.329840"
  },
  {
    "agent_key": "provider_intelligence",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.304410",
    "next_refresh_at": "2026-07-21 01:40:34.304410"
  },
  {
    "agent_key": "resident_needs",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.299254",
    "next_refresh_at": "2026-07-20 19:40:34.299254"
  },
  {
    "agent_key": "senior_living_research",
    "refresh_status": "READY",
    "freshness_status": "FRESH",
    "failed_refresh_count": 0,
    "refresh_error": null,
    "last_successful_refresh": "2026-07-20 13:40:34.291846",
    "next_refresh_at": "2026-07-20 14:40:34.291846"
  }
]
```

## Organic / AI Authority Real Status

- Status: PARTIAL
- Automated: NO
- Last verified work: UNVERIFIED_EXTERNAL
- What it actually does today: Strategy docs and multi-AI benchmark scaffolding exist, but automated organic/citation monitoring is not configured.
- New measurable result created: No verified external search or citation result was collected automatically.
- Google visibility: UNVERIFIED_EXTERNAL
- AI citation monitoring: NOT_CONFIGURED

This remains strategy/scaffolding plus benchmark support, not a verified automatic monitoring agent.

## Daily Report Integration

- The existing canonical daily executive report now includes:
  - Agent Activity summary
  - Agent Activity table
  - What OPTIME Achieved Today
  - Agents Requiring Attention
  - Organic / AI Authority system row
  - Authority lifecycle stages
- Same-day idempotency verified: canonical report count for today remained 1 before and after regeneration.

## Admin UI Verification

- Backend live endpoint verified: `GET /executive-report/latest/full` returned HTTP 200.
- Frontend live admin route verified: `GET /admin/executive-intelligence` returned HTTP 200 after restarting only the stale local backend/frontend processes.
- The rendered page exposes Executive Intelligence title, Agent Activity, Daily Report History, Attention, and authority-related content.

## Scheduler Verification

- Automatic scheduler entry still exists in backend startup via `start_background_refresh_loop()` and `start_executive_report_scheduler()`.
- Canonical one-report-per-day behavior remains in the existing archive/report writer path.
- SMTP remains unconfigured, so report generation succeeds but email delivery is blocked without affecting archive/admin visibility.

## Email Status

- NOT_CONFIGURED
- Latest controlled report generation returned: `SMTP host is not configured (OPTIME_SMTP_HOST)`

## Remaining Blockers

- The automatic agents now run successfully, but they still produce no verified new value because their current refresh logic only rebuilds prepared snapshots from existing data and did not create new `agent_knowledge_records` in the controlled run.
- Organic/AI authority monitoring is still not an automated measurable agent.

## Generated At

- 2026-07-20T13:42:18.423853+00:00
