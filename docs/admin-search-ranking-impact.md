# Admin search ranking audit

RELEVANT EXISTING PRINCIPLES: parameter-first matching; evidence traceability; unknown is not negative evidence; no commercial ranking; true ties share rank.

DOES THIS CHANGE ALTER ANY PRINCIPLE? NO

OWNER APPROVAL REQUIRED? NO

Classification: B — implementation completion. The admin view records the final comparator and final returned order without re-ranking, new evidence collection or inferred numerical weights. Ranking uses ordered criteria, not a weighted composite. Original comparator values and evidence sources remain distinguishable from explanations and missing snapshots.

Completed recommendation requests get a durable audit in the same database transaction as their existing decision artifact. Audit retention is independent of the two-hour family artifact expiry. No raw questionnaire, contact details or search narrative is copied. History starts on deployment; old searches cannot be reconstructed. Access uses the existing fail-closed admin token. Failed/aborted searches are not completed decision records.
