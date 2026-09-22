# Live ten-case completion: Principle Impact Check

RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-008.

DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.

OWNER APPROVAL REQUIRED? NO.

Classification: A — Implementation Bug. A published-rates boolean currently bypasses
the existing numeric affordability comparison. Remove that bypass; retain the
existing pending/unknown treatment, numeric comparison, ranking weights, tie-breakers,
and source architecture. A disclosed rate is not proof of affordability.

Regression cases cover both provider and agent disclosure records with missing and
over-budget prices, plus a within-budget control. This is not a claim that ten live
journeys passed or that missing current facility prices have been obtained.

## Evidence gaps found during live acceptance

The research worker's semantic capability schema currently has no pricing,
dialysis, wound-care, or general clinical-acuity output. Requests for those
dimensions therefore cannot be satisfied by this interpreter merely by retrying.
The worker may also reuse a provider registry record instead of fetching the
source, even when that registry record lacks the requested dimension.

Published starting rent is not necessarily the total cost of the required care.
On 2026-09-22, Atria Seville's official page showed a studio starting at $4,450
per month, but explicitly excluded care and medication-management services from
its independent/assisted rental rates. This source cannot establish affordability
for the medication, ADL, or dialysis cases without additional cost evidence.

Source: https://www.atriaseniorliving.com/retirement-communities/atria-seville-las-vegas-nv

No starting rates, clinical claims, or synthetic test prices were added to
production evidence by this change. The existing starting-price comparator itself
is unchanged; case-specific total-cost coverage remains an open acceptance gap.

## Browser observation

A fresh production tab accepted the initial relationship choice. Subsequent
story submission and ordinary button actions had no visible effect across the
documented browser interaction methods; browser-extension metadata errors were
logged. This is not enough to attribute the problem to application code. No
additional speculative navigation patch was made. No ten-case live pass is claimed.
