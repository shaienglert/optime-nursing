# Durable intake authority

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: B, completion of the approved shared, server-held profile.

Replace the process-local artifact cache with the existing application database.
Keep opaque handles, input binding, independent copies and the two-hour lifetime.
Do not fall back to a new interpretation when confirmed intake cannot be resolved.
The database must be shared and persistent in production; local SQLite only shares
artifacts between processes using the same file. Database failures must surface
without issuing a handle that was not saved.

This persistence change does not resolve conflicting intake interpretations or
change care requirements, facility eligibility, evidence or ranking rules.
