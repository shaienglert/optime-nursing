# Provider Portal Schema

## Scope
Implemented Provider Portal schema in [backend/app/models/facility.py](backend/app/models/facility.py) using SQLAlchemy models.

Existing table reused:
- facilities

New tables added:
- facility_users
- facility_capabilities
- facility_photos
- facility_activity_categories
- facility_verification_memory
- facility_verification_requests
- facility_verification_responses
- facility_profile_completeness

## Table Definitions

### facilities (existing)
Primary key:
- id

Used as parent for all provider-portal entities.

### facility_users
Purpose:
- Facility-scoped users and role-based access.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- email (not null)
- password_hash (not null)
- full_name (nullable)
- role (not null): admin, marketing, admissions, activities_coordinator
- is_active (not null, default true)
- last_login_at (nullable)
- created_at
- updated_at

Constraints and indexes:
- UNIQUE (facility_id, email)
- INDEX (facility_id, role)
- INDEX on id, facility_id

### facility_capabilities
Purpose:
- Provider-maintained capability values and freshness.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- capability (not null)
- value (not null): YES | NO | LIMITED | UNKNOWN
- source (not null, default provider_portal)
- verified_at (nullable)
- expires_at (nullable)
- confidence (not null, default 0)
- verification_count (not null, default 0)
- last_updated_by_user_id FK -> facility_users.id (nullable)
- notes (nullable)
- created_at
- updated_at

Constraints and indexes:
- UNIQUE (facility_id, capability)
- INDEX (facility_id, value)
- INDEX on id, facility_id

### facility_photos
Purpose:
- Categorized media assets for profile enrichment.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- category (not null)
- url (not null)
- caption (nullable)
- source (not null, default provider_portal)
- uploaded_by_user_id FK -> facility_users.id (nullable)
- uploaded_at
- is_active (not null, default true)

Indexes:
- INDEX (facility_id, category)
- INDEX on id, facility_id

### facility_activity_categories
Purpose:
- Category-level activity intelligence (no public exact schedules).

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- category (not null): movie | music | lecture | gardening | exercise | religious | social
- availability (not null): YES | NO | LIMITED | UNKNOWN
- confidence (not null, default 0)
- import_source (nullable)
- last_imported_at (nullable)
- updated_by_user_id FK -> facility_users.id (nullable)
- updated_at

Constraints and indexes:
- UNIQUE (facility_id, category)
- INDEX (facility_id, availability)
- INDEX on id, facility_id

### facility_verification_memory
Purpose:
- Canonical per-facility capability memory state.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- capability (not null)
- value (not null): YES | NO | LIMITED | UNKNOWN
- verification_source (not null)
- verified_at (not null)
- expires_at (not null)
- confidence (not null, default 0)
- verification_count (not null, default 1)
- conflict_count (not null, default 0)
- last_request_id FK -> facility_verification_requests.id (nullable)
- last_response_id FK -> facility_verification_responses.id (nullable)
- created_at
- updated_at

Constraints and indexes:
- UNIQUE (facility_id, capability)
- INDEX (facility_id, confidence)
- INDEX (expires_at)
- INDEX on id, facility_id

### facility_verification_requests
Purpose:
- Outbound verification request records.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- requested_by_user_id FK -> facility_users.id (nullable)
- channel (not null, default provider_portal)
- subject (nullable)
- body (nullable)
- status (not null, default sent)
- sent_at
- created_at

Indexes:
- INDEX (facility_id, status)
- INDEX (sent_at)
- INDEX on id, facility_id

### facility_verification_responses
Purpose:
- Incoming verification responses per capability.

Columns:
- id PK
- request_id FK -> facility_verification_requests.id (not null)
- facility_id FK -> facilities.id (not null)
- responded_by_user_id FK -> facility_users.id (nullable)
- capability (not null)
- value (not null): YES | NO | LIMITED | UNKNOWN
- source (not null, default provider_portal)
- verified_at (not null)
- expires_at (not null)
- confidence (not null, default 0)
- notes (nullable)
- created_at

Indexes:
- INDEX (request_id)
- INDEX (facility_id, capability)
- INDEX (verified_at)
- INDEX on id, facility_id

### facility_profile_completeness
Purpose:
- Profile-completeness metrics used as tie-breakers only.

Columns:
- id PK
- facility_id FK -> facilities.id (not null)
- medical_completeness (not null, default 0)
- lifestyle_completeness (not null, default 0)
- dining_completeness (not null, default 0)
- photos_completeness (not null, default 0)
- activity_completeness (not null, default 0)
- overall_score (not null, default 0)
- calculated_at
- updated_at

Constraints and indexes:
- UNIQUE (facility_id)
- INDEX (overall_score)
- INDEX on id, facility_id

## Foreign Keys Summary
- facility_users.facility_id -> facilities.id
- facility_capabilities.facility_id -> facilities.id
- facility_capabilities.last_updated_by_user_id -> facility_users.id
- facility_photos.facility_id -> facilities.id
- facility_photos.uploaded_by_user_id -> facility_users.id
- facility_activity_categories.facility_id -> facilities.id
- facility_activity_categories.updated_by_user_id -> facility_users.id
- facility_verification_memory.facility_id -> facilities.id
- facility_verification_memory.last_request_id -> facility_verification_requests.id
- facility_verification_memory.last_response_id -> facility_verification_responses.id
- facility_verification_requests.facility_id -> facilities.id
- facility_verification_requests.requested_by_user_id -> facility_users.id
- facility_verification_responses.request_id -> facility_verification_requests.id
- facility_verification_responses.facility_id -> facilities.id
- facility_verification_responses.responded_by_user_id -> facility_users.id
- facility_profile_completeness.facility_id -> facilities.id

## Migration Plan

### Current Behavior Note
The backend currently recreates schema on startup via `Base.metadata.drop_all()` + `create_all()` in [backend/app/main.py](backend/app/main.py), which is destructive.

### Recommended Plan
1. Introduce Alembic and create baseline revision for current schema.
2. Remove destructive startup reset from [backend/app/main.py](backend/app/main.py) for non-dev environments.
3. Add revision creating the new provider-portal tables and indexes.
4. Backfill:
- create one admin user per facility (optional bootstrap)
- initialize facility_profile_completeness rows with zeros
5. Deploy with dual-read safety:
- keep existing resident search paths unchanged
- start writing provider-portal data after migration success
6. Add verification jobs:
- periodic expiration sweep for facility_verification_memory
- recompute profile completeness after capability/photo/activity updates
7. Add rollback plan:
- drop provider-portal tables only (leave facilities and scoring tables untouched)

## Implementation Location
- Models implemented in [backend/app/models/facility.py](backend/app/models/facility.py)
