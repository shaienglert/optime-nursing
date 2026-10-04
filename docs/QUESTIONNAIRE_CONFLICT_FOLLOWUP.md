# Questionnaire conflict follow-up

Classification A/B for this patch. Relevant principles: PR-002, PR-003, PR-005,
PR-006, PR-009. Principle change: NO. Owner approval required: NO.

## Confirmed and repaired

- `frontend/src/app/results/simple-results-page-client.tsx` previously read
  “up to 10 miles” as a budget of 10. Numeric edits now require a money or budget
  dimension, and reject distance units as money. Both dimensions can coexist.
  Withdrawn radius clears all three radius fields and sets locationImportant=No.
- The same results editor could restore “Large” after first removing the large
  community preference. The affirmative branch now respects the existing removal.
- `living_strategy_runtime.py` missed structured toileting, daytime supervision
  and 24/7 ADL answers recognized by decision_engine_core. Both now consume the
  existing STRUCTURED_INTAKE_MAPPING_CONTRACT from structured_intake_mapping.py.
  The old public core symbol remains available; no parameter meaning is added.
  Every assistance option is tested through strategy and actual client-intent gate.

## Inventory and catalog

`docs/generated/intake-label-inventory.json` is generated from actual QUESTIONS:
61 questions and 237 option labels, with source lines, read/write accessors and
pending semantic review. It is an inventory, not approval of 237 meanings.
CI detects inventory drift. It does not pretend all options have semantics yet.

The structural catalog validator checked 500 facilities: IDs/names, record counts,
foreign references, price units, available-unit validity and contradictory claims
with identical source and scope. No failures were found. This does not prove
clinical consistency, ranking quality, licenses or real-world facts.

## Verified in code, still open

- client_intent_runtime AVAILABILITY_FIT reads current_availability from matched
  needs; confirm authoritative availability propagation before changing it.
- NO_FORCED_MEMORY_PLACEMENT checks memory-only type/archetype. A community with
  an optional memory unit must not be equated with forced memory placement.
- Independent clinical meaning review is needed for fall frequency, transfers,
  mobility, dietary restrictions and declined/unknown preferences. Do not infer
  PT/OT/nursing requirements merely from a fall or a wheelchair.
- Entrance fees must participate in funding analysis; an entrance fee and monthly
  rent are separate facts, not an invariant violation by themselves.
- Narrative must be derived from final decision facts; complete family-facing
  narrative, geographic resolution and backend benchmark migration remain open.

## Owner decisions needed before new mappings

For each presently unused label, approve its role (MUST/NICE/context/unknown),
its actual capability/evidence parameter and scope. Required capability that is
not evidenced remains pending verification; a missing family fact triggers a
focused question. A provider fact must never be completed by a family guess.
The complete generated inventory provides the review surface; these decisions
have not been assumed by this patch.

Local validation: 46 ADL/medical/intent tests and 12 numeric-edit tests passed;
frontend types passed; generated inventory and catalog checks passed. Expanded
ranking checks are recorded separately when complete. No production run claimed.

Final local checks: 174 ADL/medical/intent/oracle/Oomniker/accounting/neutral
backend tests plus four catalog corruption tests passed (178 total).

## Concrete semantic proposal for owner review (NOT IMPLEMENTED)

Current principle: client MUST is deterministic and cannot be relaxed by AI;
missing family facts require a focused clarification and missing provider facts
require provider/source verification. Unknown is never negative evidence.

Current behavior: some selected services and preferences are preserved without
an explicit deterministic intent/evidence mapping. The proposed roles below
are new mappings (D), not merely source-accounting labels. No change is active.

| Selected family answer | Proposed role and clarification | Required facility proof |
| --- | --- | --- |
| Cane / Walker / Wheelchair / Mostly in bed | Context; clarify actual layout/access/assistance requirements before creating MUST. Do not infer nursing/PT/OT. | Proof of the specific confirmed accessibility/support requirement at facility/unit level |
| One person / Two people / Mechanical lift | MUST for the explicitly selected transfer support; Not sure remains unknown and is clarified if material | Evidence of the exact staffing/transfer method, including scope and any delivery restrictions |
| One / More than one fall | Context and focused safety/support clarification; no automatic service inference | Evidence only for the subsequently confirmed requirement |
| Several times weekly / Weekly / Occasionally / Very little | NICE for the stated desired social frequency, with no automatic “more social is better” rule | Programming/delivery that matches that frequency; absence remains unknown |
| Quiet | NICE for a quiet environment; not a proxy for community size | Case-relevant quiet-environment evidence; no invented fit from size alone |
| Halal / Vegetarian / Vegan / Low sodium / Diabetic / Gluten free / Other | Clarify MUST vs preference and any medical/allergy severity once unless already stated in structured controls or narrative | Exact dietary capability, scope, limitations and safeguards for confirmed requirements |
| Regular / Accessible / Covered parking | Clarify MUST vs preference once unless explicit; accessible parking does not alone imply all accessibility needs | Exact parking type and, if material, capacity for the requested number of vehicles |
| Pet = Yes | Clarify whether bringing a pet is a MUST, and species/size restrictions if material | Pet policy for the selected unit and actual pet; no generic yes substitute |
| Religious community = Yes and selected religious services | Clarify MUST vs preference and exact service; do not infer faith from language/kosher | Proof for the selected service and denomination if explicitly required |
| Move-loss concerns and biggest fear | Dialogue/context by default; map to an existing confirmed intent or ask a focused question, without generating duplicate MUSTs | Evidence only for the clarified concrete requirement |
| Medicare | Funding context; do not treat insurance coverage as proof that long-term residential rent is covered | Case-specific covered service/eligibility and billing evidence |

User impact: confirmed requirements can move candidates into provider research
instead of recommendations when exact capability proof is missing. Preferences
can affect governed ranking only with relevant evidence. Context alone does not
raise/lower rank. These effects must be tested against actual pilot facts.

Risks: declaring ambiguous choices MUST without clarification can incorrectly
exclude communities; declaring them NICE can weaken true requirements. Generic
facility flags may not prove a specific service. Alternative: keep them context
and visibly pending until clarified (recommended for ambiguous answers).

Approval required under AGENTS.md: “Owner approval required before semantic
implementation: C, D, E”. The inventory contains every original option, so no
new option can be silently assigned a role after approval of this proposal.
