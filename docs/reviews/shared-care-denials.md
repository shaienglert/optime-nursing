# Shared care-denial authority

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: A — a downstream parser reintroduces an explicitly denied need.

Reproductions on main:
- Fully independent, explicitly denies medication and bathing/dressing help:
  core and strategy require neither; combined care requires both.
- Parents moving together; "Neither has dementia": core has no memory-care need;
  strategy still creates SECURE_MEMORY_CARE_CONFIRMED.

Use the existing core denial rules as a shared authority, passed once through
production intake composition. Preserve positive needs, existing attribution
behavior and all evidence/ranking rules. No synonym expansion or clinical-severity
reclassification is included. Reminder vs administration remains a separate semantic
question; this change does not claim that every intake interpretation is unified.

## Integration failure: durable writes blocked by discovery

The first branch browser run exposed SQLite lock contention after PR #358:
all ten intake requests failed with 503 while the background discovery transaction
held a write lock across network requests. Preserve RUNNING job/snapshot state in
short committed transactions, and commit each independently verified source result
before contacting the next source. Evidence acceptance and ranking rules do not
change. Include artifact and discovery files in the real pilot workflow trigger;
the prior trigger omitted the artifact-store change.
