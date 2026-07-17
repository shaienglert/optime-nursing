# Provider Portal V1 Design

## Objective
Enable each community to maintain and enrich its OPTIME profile through authenticated provider users while preserving resident-first ranking logic.

## Architecture Alignment
- Backend: FastAPI + SQLAlchemy + SQLite (current stack in backend/app)
- Frontend: Next.js + TypeScript (current stack in frontend/src)
- Scope: Provider-side authoring and verification ingestion; resident matching remains authoritative and clinically constrained.

---

## Section 1: Authentication and Roles

### User Types
- Community administrator account (required, one per facility at onboarding)
- Multiple staff users per facility

### Roles and Permissions
- Admin
  - Manage facility profile and all capability sections
  - Manage users and invitations
  - Manage media and activity imports
  - Publish verification records
- Marketing
  - Edit lifestyle, housing, dining, media sections
  - Cannot manage users
- Admissions
  - Edit medical, mobility, dining, housing sections
  - Publish provider verification responses
- Activities Coordinator
  - Manage activities imports and category mappings
  - Edit activity-related lifestyle fields only

### Auth Model
- Email + password with hashed passwords (bcrypt/argon2)
- JWT access token + refresh token
- Facility-scoped authorization for all portal resources
- Optional MFA-ready schema field for future Phase 4

---

## Section 2: Community Questionnaire

### Questionnaire Sections and Fields

#### Medical
- nursing_24_7
- physician_availability
- speech_therapy
- physical_therapy
- occupational_therapy
- stroke_rehabilitation
- parkinson_support
- memory_care

#### Mobility
- walker_support
- wheelchair_accessibility
- fall_prevention
- transfer_assistance

#### Dining
- gluten_free
- kosher
- vegetarian
- diabetic_meals

#### Lifestyle
- movies
- music
- gardening
- pool
- fitness_center
- religious_services
- transportation

#### Housing
- kitchenette
- balcony
- studio
- one_bedroom
- pets_allowed

### Answer States
- YES
- NO
- LIMITED
- UNKNOWN (system default until explicitly answered)

### Rule
- Provider-submitted answer overrides UNKNOWN in memory engine.

---

## Section 3: Media Management

### Upload Categories
- community_photos
- apartments
- dining_areas
- gardens
- activities
- pool
- fitness_center

### Media Requirements
- Store URL/path, category, source, uploaded_by, uploaded_at
- Optional caption + alt text
- File validation: extension/type/size checks
- Soft-delete support

### Completeness Inputs from Media
- Presence coverage by required category
- Recency score (updated in last N days)
- Quality score (minimum image count per category)

---

## Section 4: Activities Intelligence

### Supported Imports
- Google Calendar
- Outlook Calendar
- ICS
- CSV
- PDF

### Normalized Public Categories (only)
- movie
- music
- lecture
- gardening
- exercise
- religious
- social

### Privacy Rule
- Exact schedules are private/internal only.
- Public/resident-facing exposure uses category-level capability flags and aggregated density only.

### Import Pipeline
1. Ingest source file/feed
2. Normalize event titles/descriptions
3. Map to allowed categories
4. Store raw private payload internally
5. Publish category availability + confidence + last_updated only

---

## Section 5: Verification Memory (Provider Portal Source)

Every community answer creates a facility_verification_record.

### Required Record Fields
- facility_id
- capability
- value
- source = provider_portal
- verified_at
- expires_at
- confidence

### Additional Recommended Fields
- verified_by_user_id
- verification_count
- conflict_flag
- superseded_by_record_id
- notes

### Resolution Rules
- Provider response overrides UNKNOWN
- More recent verification overrides older verification
- Expired verification lowers confidence
- Conflicting non-UNKNOWN updates generate conflict events

---

## Section 6: Profile Completeness

### Component Scores (0-100)
- Medical completeness
- Lifestyle completeness
- Dining completeness
- Photos completeness
- Activity completeness

### Suggested Formula
- medical_completeness = answered_medical_fields / total_medical_fields
- lifestyle_completeness = answered_lifestyle_fields / total_lifestyle_fields
- dining_completeness = answered_dining_fields / total_dining_fields
- photos_completeness = covered_media_categories / required_media_categories
- activity_completeness = covered_activity_categories / allowed_activity_categories

Overall score:
- overall_profile_completeness = weighted average
- Suggested weights:
  - medical 30%
  - lifestyle 15%
  - dining 15%
  - photos 20%
  - activity 20%

---

## Section 7: Search Impact Rule

### Rule
Profile completeness never overrides clinical fit.

### Ranking Tie-Break
When two facilities have equivalent clinical fit/match score, rank by:
1. Higher profile completeness
2. Higher verification confidence
3. More recent verification freshness

### Engine Integration Point
- Add completeness and verification freshness as post-fit tie-breakers only
- Never alter hard filters or clinical fit acceptance path

---

## Section 8: Deliverables

## Database Schema

### New Tables

1. provider_accounts
- id PK
- email UNIQUE
- password_hash
- is_active
- mfa_enabled (future-ready)
- created_at
- updated_at

2. provider_facility_memberships
- id PK
- provider_account_id FK -> provider_accounts.id
- facility_id FK -> facilities.id
- role ENUM(admin, marketing, admissions, activities_coordinator)
- invited_by_user_id FK -> provider_accounts.id NULL
- created_at
- updated_at

3. facility_provider_profiles
- id PK
- facility_id FK UNIQUE -> facilities.id
- medical_json
- mobility_json
- dining_json
- lifestyle_json
- housing_json
- profile_completeness_score
- medical_completeness
- lifestyle_completeness
- dining_completeness
- photos_completeness
- activity_completeness
- published_at NULL
- created_at
- updated_at

4. facility_media_assets
- id PK
- facility_id FK -> facilities.id
- category ENUM(community_photos, apartments, dining_areas, gardens, activities, pool, fitness_center)
- storage_url
- mime_type
- file_size
- caption NULL
- alt_text NULL
- uploaded_by_user_id FK -> provider_accounts.id
- uploaded_at
- is_deleted

5. facility_activity_imports
- id PK
- facility_id FK -> facilities.id
- source_type ENUM(google_calendar, outlook_calendar, ics, csv, pdf)
- source_reference NULL
- imported_by_user_id FK -> provider_accounts.id
- imported_at
- status ENUM(pending, completed, failed)
- summary_json

6. facility_activity_categories
- id PK
- facility_id FK -> facilities.id
- category ENUM(movie, music, lecture, gardening, exercise, religious, social)
- availability ENUM(yes, no, limited, unknown)
- confidence
- last_imported_at NULL
- updated_by_user_id FK -> provider_accounts.id
- updated_at

7. facility_verification_records
- id PK
- facility_id FK -> facilities.id
- capability
- value ENUM(YES, NO, LIMITED, UNKNOWN)
- source ENUM(provider_portal, facility_response, phone_call, email, onsite_visit, document_review, other)
- verified_at
- expires_at
- confidence
- verification_count
- verified_by_user_id FK -> provider_accounts.id NULL
- conflict_flag
- superseded_by_record_id FK -> facility_verification_records.id NULL
- notes NULL
- created_at

8. facility_verification_conflicts
- id PK
- facility_id FK -> facilities.id
- capability
- previous_record_id FK -> facility_verification_records.id
- incoming_record_id FK -> facility_verification_records.id
- detected_at
- resolution_status ENUM(open, resolved)
- resolved_by_user_id FK -> provider_accounts.id NULL
- resolution_notes NULL

### Required Tables Summary
- provider_accounts
- provider_facility_memberships
- facility_provider_profiles
- facility_media_assets
- facility_activity_imports
- facility_activity_categories
- facility_verification_records
- facility_verification_conflicts

---

## API Endpoints

### Auth
- POST /provider/auth/login
- POST /provider/auth/refresh
- POST /provider/auth/logout
- GET /provider/auth/me

### User and Membership Management
- GET /provider/facilities/{facility_id}/users
- POST /provider/facilities/{facility_id}/users/invite
- PATCH /provider/facilities/{facility_id}/users/{user_id}/role
- DELETE /provider/facilities/{facility_id}/users/{user_id}

### Questionnaire/Profile
- GET /provider/facilities/{facility_id}/profile
- PUT /provider/facilities/{facility_id}/profile/medical
- PUT /provider/facilities/{facility_id}/profile/mobility
- PUT /provider/facilities/{facility_id}/profile/dining
- PUT /provider/facilities/{facility_id}/profile/lifestyle
- PUT /provider/facilities/{facility_id}/profile/housing
- POST /provider/facilities/{facility_id}/profile/publish

### Media
- GET /provider/facilities/{facility_id}/media
- POST /provider/facilities/{facility_id}/media/upload
- DELETE /provider/facilities/{facility_id}/media/{media_id}

### Activities Intelligence
- POST /provider/facilities/{facility_id}/activities/import/google
- POST /provider/facilities/{facility_id}/activities/import/outlook
- POST /provider/facilities/{facility_id}/activities/import/ics
- POST /provider/facilities/{facility_id}/activities/import/csv
- POST /provider/facilities/{facility_id}/activities/import/pdf
- GET /provider/facilities/{facility_id}/activities/categories
- PUT /provider/facilities/{facility_id}/activities/categories

### Verification Memory
- POST /provider/facilities/{facility_id}/verification-records
- GET /provider/facilities/{facility_id}/verification-records
- GET /provider/facilities/{facility_id}/verification-conflicts
- POST /provider/facilities/{facility_id}/verification-conflicts/{conflict_id}/resolve

### Completeness and Ranking Signals
- GET /provider/facilities/{facility_id}/completeness
- GET /provider/facilities/{facility_id}/ranking-impact-preview

---

## UI Screens

1. Provider Login
- Email/password auth

2. Facility Workspace Selector
- For users assigned to multiple facilities

3. Provider Dashboard
- Completeness widgets
- Verification freshness
- Conflict alerts
- Import status cards

4. Community Questionnaire
- Tabs: Medical, Mobility, Dining, Lifestyle, Housing
- Save draft / publish

5. Media Manager
- Category upload lanes
- Coverage/progress indicators

6. Activities Intelligence
- Import wizard for Google/Outlook/ICS/CSV/PDF
- Category mapping review

7. Verification Memory Center
- Capability records timeline
- Current value/confidence/expiry
- Conflict resolution workflow

8. Team & Permissions
- Invite/manage users and roles

9. Ranking Impact Preview
- Shows tie-break effect only (never clinical override)

---

## Migration Plan

### Important Current Constraint
Current backend startup recreates schema via drop_all/create_all in backend/app/main.py startup. This must be changed before introducing provider portal persistence.

### Plan
1. Freeze destructive startup behavior
- Replace drop_all/create_all with migration-managed startup
- Keep one-time bootstrap flag for local dev only

2. Add migration framework
- Introduce Alembic
- Baseline current schema revision

3. Add portal tables
- Create eight new tables listed above
- Add indexes:
  - provider_accounts.email
  - provider_facility_memberships (facility_id, provider_account_id)
  - facility_verification_records (facility_id, capability, verified_at)
  - facility_media_assets (facility_id, category)

4. Seed initial admin accounts
- Create bootstrap script for one admin per selected pilot facility

5. API rollout
- Add auth middleware + role guards
- Add profile/media/activity/verification endpoints

6. Completeness engine rollout
- Compute and persist section scores on every profile/media/activity update

7. Search tie-break integration
- In ranking path, apply completeness only when clinical fit equivalence threshold is met

8. Validation
- Unit tests for role permissions, recency precedence, expiration confidence decay
- Integration tests for end-to-end provider profile publish flow

---

## Acceptance Criteria V1
- Provider users can authenticate and manage only assigned facilities
- Questionnaire responses persist with role-based access
- Media upload + activity imports work and update completeness
- Provider answers generate facility_verification_records with source=provider_portal
- Recency and expiry rules applied to verification memory
- Ranking tie-break uses completeness only when fit-equivalent
- Provider portal design implemented with migration-safe backend plan
