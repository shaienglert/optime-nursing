# Pilot care-path contract (owner approved 2026-10-02)

The owner selected option 2: `oracle.care` denotes an offered, independently verified
service/program path, not a building category. This completes PR009 without changing
its parameter-first principle. Classification B (implementation completion); approval
of the earlier ambiguity was explicitly supplied. Relevant principles: PR002, PR003,
PR005, PR006, PR007, PR009. No principle change.

The frozen persona expectations remain unchanged. An alternative listed in `care`
passes only when its entire evidence path passes. UNKNOWN/conflict/missing sources
cannot prove a match. Existing negative placement, licensing, radius, budget and
availability contracts remain separate.

| Path | Required frozen evidence |
| --- | --- |
| Independent living | Explicit independent/active-adult housing modality |
| Assisted living | Verified ADL parameter and identity-bound service evidence |
| Small group home | Same ADL proof and capacity 1–16 |
| Memory care | Memory and dementia program parameters; medical memory and continuum program records |
| Skilled nursing | Skilled capability and 24/7 nursing parameters; nursing and physician service proof; provider medical nursing |
| Rehabilitation | PT, OT, therapy staff and nursing parameters; nursing and physician coordination services; explicit provider rehabilitation program |
| Continuing care | Continuum service proof and on-campus progression program |

`care_oracle.py` reads frozen parameters, services and provider capability records,
never engine verdicts. Proof output includes evidence sources and verification dates.
These are synthetic tests, not clinical or real-world facility verification. Requested
wandering protection is separately checked against secured-unit evidence.

The post-hospital engine gate is separate from outpatient/external PT/OT access.
`POST_HOSPITAL_REHAB_PROGRAM` is created for an explicit post-hospital need and is
registered as a care MUST, including in the affordability floor. Category alone and
PT/OT flags cannot prove it. Verified incompatible pilot evidence fails; missing
program evidence remains pending. Real-world positive claims need a governed source
and the explicit full-program and clinical-support fields; absent evidence is pending.

The acceptance harness retains its ANY-of-positive-path quantifier for general
preferences; forbidden archetypes are enforced independently. For the explicitly
required memory and post-hospital programs, every recommendation must prove the
program. Wandering protection and post-hospital need are now explicit questionnaire
answers as well as narrative statements, so a mocked interpreter cannot silently
drop those requirements. This does not prove live narrative extraction.

A curated therapy URL (including Las Ventanas) proves the existing therapy-access
path, but cannot prove the new full clinical program. The regression test retains
all prior positive therapy/couple assertions and requires PENDING for that missing
program. This may leave real post-hospital cases pending until program evidence
is collected; no real evidence was invented to make the test pass.

PR #424 remains Draft and NO-GO until separately authorized readiness/cutover review.
