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

## Review of the attached 4 October mapping document

The attached DOCX reports 217 labels against a single persona-10 baseline on an
unspecified #439 head with semantic AI disabled. Its original harness, raw
outputs and exact commit were not supplied. Do not treat its counts as independently
reproduced runs. The actual question inventory at the tested follow-up tree has
61 questions, 46 closed-option questions, 237 options and 237 distinct question/
option pairs. No duplicate-pair explanation accounts for the 20-option difference.
The missing options remain unidentified until the original run manifest is provided.

### Independently verified mutation semantics

Eleven added regression cases distinguish addition from replacement and actual
MUST evaluation from ordering. Added bathing, dressing, toileting, daytime
supervision or 24/7 assistance preserves an existing medication need and MUST.
Replacing a medication answer with one of those selections removes medication
support and retains ADL. This is expected withdrawal behavior, not lost input.
Two candidates both proven to support ADL remain tied on that criterion while
both pass ADL_SUPPORT_AVAILABLE; removing facility evidence produces must_unknown.
Unchanged order is not evidence that the family answer was unused.
All 21 assistance/shared-authority tests passed. These are deterministic local
checks, not persona-10 end-to-end reproduction or live production journeys.

### Corrected policy classification and decision requests

P1: preserving UNKNOWN without treating it as positive or negative evidence is
implementation of existing principles (B). The separate unresolved clinical
placement policy belongs to P5. UNKNOWN must not be reported as confirmed safe.

P2: normalizing a numeric budget string is A. Proposed funding policy (C): check
recurring monthly obligations against a monthly budget and a one-time entrance
fee against explicitly available capital, including payment timing. Do not add
the fee to monthly rent or assume missing capital is zero. Ask for available
capital only when a relevant otherwise-suitable option requires it. Impact: such
options remain funding-pending until capital is known. Risk: a premature fail
would exclude an affordable option; a premature pass would conceal an entrance
obligation. Alternative: omit entrance-fee options entirely, which is not
recommended. Owner approval requested for this separate-capital funding policy.

P3: the ADL propagation inconsistency is A and already repaired using unchanged
mappings. Proposed clarification policy (C): Light assistance, Daytime supervision,
24/7 support and Skilled nursing must not silently establish transfer assistance,
medication management or specialist nursing beyond what was explicitly stated.
Ask about a materially needed support method when still unknown; retain all
separately selected requirements. 24/7 support alone is not 24/7 skilled nursing.
Impact: remove only unsupported inferred needs after explicit mapping approval;
concrete selected support requirements remain. Risk: removing a real but unstated
need without clarification; avoid by asking before a safety-relevant decision.
Alternative: continue broad inferred requirements; not recommended.

P4: explicit One person/Two people/Mechanical lift is a requirement for that
exact transfer method; a fall count is context for focused clarification. Neither
establishes PT/OT or continuous nursing. New exact-method service mapping is D
until approved; propagation of an existing proven transfer requirement is B.
Approval requested: enforce the selected method and clarify missing supporting
facts, without deriving other services. Impact: providers without method proof
remain pending, not a verified negative. Risk: a generic transfer YES cannot
prove two-person/lift staffing. Alternative: generic transfer matching, weaker
than the stated need and not recommended.

P5: proposed memory policy (C): No, Occasionally forgetful and Not sure never
constitute consent to a memory-only/locked placement. Mild or Significant memory
labels require evaluation of actual assistance/supervision needs. A secured unit
becomes MUST from an explicit security requirement or a confirmed applicable
wandering/safety need, not severity wording alone. Assess the offered unit and
pathway, not the presence of an optional memory service at the community.
Unresolved safety needs trigger clarification; no confirmed-safe claim is made.
Impact: remove unsupported type-based inference only after approval; preserve
explicit secured-unit MUSTs. Risk: missing a material safety requirement; mitigate
with clarification before recommendation. Alternative: blanket locked-unit
requirement from severity labels; not recommended. Owner decision requested.

P6: separate Approved, Application pending, May qualify and Not sure in the
funding explanation (B). Proposed eligibility handling (C): only verified applicable
approval establishes coverage; pending/possible/unknown remain distinct funding
states and are clarified or researched when funding determines affordability.
They are not equivalent to approval or ineligibility. Impact: funding-pending
options are transparently distinguished. Risk: mistaken blanket exclusion or
implied benefit guarantee. Alternative: treating all non-negative responses as
one Medicaid need; not recommended. Owner decision requested for gate changes.

P7: show unverified preferences as UNKNOWN without score is B. Quiet/social
frequency as new case-relevant NICE criteria requires approved mappings (D).
Proposed policy: evaluate the stated frequency/environment only from relevant
provider evidence; do not assume larger/more social is universally better.
No evidence means visibly unverified preference, not negative fit.

P8: LIMITED requires capability-specific scope/limits. A limited capability may
pass only when governed evidence proves it meets the exact requirement. Otherwise
it remains pending clarification/research. Never globally convert LIMITED to YES
or NO. This is B when enforcing existing requirement semantics; interpreting
specific previously undefined limitation thresholds is C and must be presented
with its concrete evidence and requirement before approval.

P9: add a backend matching benchmark is B. Retain frontend tests for UI behavior.
Replacing deployed architecture or removing frontend safety coverage would be a
separate E proposal; this patch proposes neither.

No new policy above is activated. These are concrete decision proposals;
implementation fixes, inventory and source-integrity checks remain independent.
