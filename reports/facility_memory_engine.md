# Facility Memory Engine V1

## Overview
Facility Memory Engine V1 is implemented in [frontend/src/lib/optime-v2-engine.ts](frontend/src/lib/optime-v2-engine.ts).

It stores capability-level verification memory per facility and applies it automatically in future recommendation runs.

## Stored Record Fields
Each stored capability record includes:
- facility_id (memory scope)
- capability_key
- value
- source
- verified_at
- expires_at
- confidence_level
- verification_count

Current in-memory representation:
- facility memory object is keyed by facility id
- capability entries are keyed by capability key
- each entry stores both canonical and API-friendly aliases:
  - key and capability
  - state and value
  - source and verification_source
  - verifiedAt and verified_at
  - expiresAt and expires_at
  - confidenceLevel and confidence_level
  - verificationCount and verification_count

## Rule Enforcement

### 1. Newer data overrides older data
Implemented in apply path:
- Incoming records older than current record are rejected.
- Exception: if current value is UNKNOWN and incoming value is known, incoming value is accepted.

### 2. Provider answers override UNKNOWN
Implemented via two mechanisms:
- Verification update flow updates UNKNOWN checklist items.
- Memory precedence allows known incoming values to replace existing UNKNOWN even when incoming timestamp is older.
- Source set supports PROVIDER_PORTAL.

### 3. Expired data lowers confidence
Implemented in confidence logic:
- Expired capability entries receive LOW confidence behavior.
- Facility-level confidence score calculation penalizes expired/unknown coverage.

### 4. Conflicts trigger review
Implemented by conflict tracking:
- Any active non-UNKNOWN value conflict creates a conflict record.
- Conflict records are marked:
  - requiresReview = true
  - reviewStatus = OPEN
- Review queue export is available through:
  - getFacilityKnowledgeReviewQueue()

## Public Engine Functions
Implemented exports:
- getFacilityKnowledgeMemory(facilityId)
- resetFacilityKnowledgeMemory()
- getFacilityKnowledgeMemoryStats()
- getFacilityKnowledgeReviewQueue()

## Automatic Recommendation Impact
- Capability assessment reads active (non-expired) memory first.
- Verified memory state directly affects clinical capability assessments.
- Future recommendations improve automatically as memory accumulates.

## Notes
- Storage is currently in-process memory map (runtime-scoped).
- For production persistence, map this structure to facility_verification_memory and related tables in the backend schema.
