# Extraction, prior answers and clarification contract

Classification B: completion of PR-002, PR-003, PR-005 and PR-008. No new
profile fields, care policy, scoring, question authority or finality authority.

The family record includes questionnaire button selections, original narrative
and prior adaptive answers. A missing material client-owned fact requires one
AI-authored question. A resolved fact must not be asked again. An ambiguous or
contradictory record still needs clarification; mere field presence is not proof
that an ambiguity is resolved. Broad assistance answers do not establish exact
ADL tasks. A different partner or a different care fact must remain distinct.

Missing facility capability, price or availability evidence remains downstream
research. The family is not asked to prove a facility service. UNKNOWN remains
UNKNOWN, and research does not manufacture eligibility or scores.
An exact quote does not turn UNKNOWN into EXPLICIT. Quoted unknown AI fields
remain UNKNOWN and are not materialized as decision facts. They cannot contest
an explicit button answer; source-backed ambiguity remains a separate state.

## General live transport boundary

`semantic_packet_wire.py` derives a strict provider JSON schema from the existing
interpreter field declarations. Both Chat Completions and Responses transports
request this format; the same Pydantic model validates it locally. Extraction is
a sparse list of full canonical path/value/quote entries, grouped in the provider
schema by the existing value representations. Unused fields are omitted, and
duplicate paths fail closed. Opaque aliases and mandatory empty slots are removed
after live diagnostics showed correct statement paths with missing or misplaced
extractions. Normalization reconstructs nested profile fields without inference.
A KNOWN/USED statement mapped to a client field must reach the profile unless
the questionnaire already supplies that field. Facility research remains separate.
The provider grammar constrains legal field paths and JSON value kinds;
local validation checks the existing scalar/list representation. Advisory prompt
enum descriptions do not acquire new canonical value authority. It avoids a
large union of one object per profile field at constrained-decoding time.
Live extraction quotes select unchanged source sentences or the full narrative
from a provider enum. Splitting source spans performs no semantic interpretation;
the existing exact-source validator still applies after normalization. A quoted
week duration cannot establish `temporarySupportMonths`; an absent month unit
requires AI repair rather than a numeric conversion or a guessed duration.
Normalization only reconstructs the existing nested patch and quote index.
Duplicate JSON members and blank quotes fail. The existing canonical exact-quote,
schema and conflict validators remain authoritative: schema conformity alone
does not prove the truth or semantic support of a value.

The interview is either READY/NEEDS_RESEARCH with no client question, or
NEEDS_CLARIFICATION with a question and an unresolved MUST/UNKNOWN trace. The
normalizer copies the model's question into the existing ASKED trace; it never
authors a fallback question or invents a fact to obtain READY. Canonical gap
policy continues to own blocking classification and final readiness.

Malformed wire output receives the existing one final packet repair. A second
failure raises an error; network/configuration errors are not schema repairs.
Direct manual answers are checked using the question's exact mapped field paths.
Known button answers trigger repair of a redundant question. Unresolved values,
broad assistance answers and explicit ambiguity do not trigger that shortcut.
Multiple ADL choices travel as one existing questionnaire string or one wire
array, joined into the existing comma-separated representation without inference.
Explicit integer months may be encoded as the existing string field; weeks are
never converted to months by the transport.

Medical detail fields must retain the existing clinical need they describe:
dialysis frequency/center, oxygen use and wound-care frequency require the
corresponding selected or explicitly extracted medical need. An omission asks
the AI to repair the packet; the validator does not add clinical facts. Existing
button selections already satisfy the dependency and need not be re-extracted.

Transient connection/read timeouts get at most two transport attempts by
default. Timeout allocations and backoff share the existing 45-second deadline;
an exhausted deadline prevents another attempt. These are transport retries,
not semantic repair or guessed fallback data. Configuration still controls the
attempt cap. HTTP errors are not converted into successful semantic packets.

## Regression evidence and limits

The executable field contract is `semantic_field_contract.py`. Every declared
extraction leaf is compiled against the approved canonical allowlist. Its
representation, source owner, unit, positive-value constraint and dependencies
are shared by provider schema generation, wire normalization and final server
acceptance. Field rules are data, not repair-specific conditional branches.
The prompt includes the same compiled contract for explanation.

Generation offers only genuine narrative spans as quotes and removes unit-bound
fields when no eligible source exists. The server independently validates
quotes, types and units even if the provider ignores its grammar. It also checks
the complete candidate patch before resolving conflicts with questionnaire
buttons, so a button cannot hide an invalid AI value. Unknown and ambiguous
facts retain their canonical states; existing questionnaire answers remain
authoritative inputs. Medical dependencies and known-field accounting are
checked before any AI candidate can enter matching.

Schema compliance does not prove that every interpretation is semantically
correct. Exact source presence is necessary evidence, not proof that a quote
entails an arbitrary value. Model readiness is advisory; existing deterministic
clarification and facility-evidence policy still decide what is usable. Failed
acceptance never authorizes guessed facts. The existing structured-only fallback
may use completed button answers with the narrative marked UNPROCESSED.

Tests cover couple fact preservation, missing question/trace, invalid patch
metadata, invalid types/enums, missing/forged quotes, duplicate paths, multiple
ADL selections, answered buttons versus a different missing transfer need,
ambiguity, facility research and bounded unsuccessful repair. Existing persona
expectations, fixture evidence and ranking oracles are unchanged.

The captured I09 was a direct interpreter test, not a questionnaire journey.
Its initial input did not prove a loss of button answers. The prior prompt-only
follow-up passed I09 but failed I02 and I07 in the live interpreter gate; its
browser workflow passed 9/10 with a loading timeout on pilot-004. This broader
contract must therefore be verified separately by live interpreter, structured
profile shadow and branch browser workflows. These are branch CI runs, not
interactive journeys on Production. PR #424 remains Draft and pre-cutover.
# Client evidence in generation and repair

Principle impact check: relevant PR-002, PR-003 and PR-005; existing single
canonical authority and explicit client evidence. Classification B
(implementation completion). DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.

Every provider request and repair receives a caller-derived view of resolved
questionnaire fields and minimum-dimension status, using the existing server
predicates. Values are not extracted again or assigned fabricated narrative
quotes. Unknown selections and broad assistance answers remain unresolved.
The original questionnaire and family text remain available for genuine
contradictions or more specific questions. Acceptance still blocks repeat
questions and unsupported facts independently of model instructions.

Provider requests carry one response grammar, existing questionnaire value
hints and the shared field contract, without a duplicate legacy packet shape or
unrelated trace examples. Blocking question traces belong only in the wire
interview. The transport deadline, evidence gates and live fixture expectations
are unchanged. Reduced prompt duplication is not proof of a resolved timeout;
live interpreter and launch-gate checks must pass on the resulting commit.
