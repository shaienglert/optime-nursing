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

## General live transport boundary

`semantic_packet_wire.py` derives a strict provider JSON schema from the existing
interpreter field declarations. Both Chat Completions and Responses transports
request this format; the same Pydantic model validates it locally. Each extracted
entry pairs an allowed path, its value and a mandatory AI-authored quote.
The compact provider grammar constrains legal paths and JSON value kinds;
local validation enforces each field's exact existing type and enum. It avoids a
large union of one object per profile field at constrained-decoding time.
Normalization only reconstructs the existing nested patch and quote index.
Duplicate paths and blank quotes fail. The existing canonical exact-quote,
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
Multiple ADL choices travel in one wire array and are joined into the
questionnaire's existing comma-separated representation without inference.

## Regression evidence and limits

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
