# Intake queued-selection repair

RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-009; owner-approved removal of insurance from family intake.

DOES THIS CHANGE ALTER ANY PRINCIPLE? NO

OWNER APPROVAL REQUIRED? NO. Classification A: preserve every explicitly selected answer when React batches updates. Classification B: align guardian regression tests with the approved insurance-free questionnaire.

The current single-question intake no longer contains the older `MultiChoices` component, but its multi-choice handler still calculated replacements from captured answers. It now passes an answer updater into a functional context update, so each queued selection reads the preceding selection. Single-choice navigation and care requirements are unchanged.

The real-journey browser harness now dispatches multi-choice clicks in the same browser task and checks every selected button before advancing. This exercises the state batching case that sequential awaited clicks conceal. It is a simulated batched-event regression, not evidence that normal separate human clicks always lose selections.

Current production evidence differs from the pasted older/local report: all ten recorded production journeys reached results, including significant memory needs, post-hospital rehabilitation, and dialysis with daily wound care. Each returned ten backend rows, with five displayed recommendations. The independent audit found no care, price, radius, or duplicate-identity violations in 489 eligible identities across those cases. These findings apply to the synthetic pilot catalog, not verified real-world facilities.

The current catalog contains exactly one `Silver House Short-term Rehabilitation` identity, `PILOT-NV-006`, at 1322 Pilot Mesa Avenue. Its starting price is $8,638. The minimum pilot price among facilities with evidenced nursing and ADL support is $5,851: a $3,000 budget with the existing 10% tolerance cannot include those facilities. No care gate or affordability threshold was relaxed to generate results.

The removed insurance question cannot create an adaptive-interview blocker. Guardian tests now verify that stale AI Medicare wording is discarded and that an actually missing monthly budget still invokes the deterministic fallback.
