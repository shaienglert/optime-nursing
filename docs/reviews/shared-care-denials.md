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
