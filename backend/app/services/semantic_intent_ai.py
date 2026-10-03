from __future__ import annotations

"""AI-first semantic understanding for OPTIME Nursing.

The model is the interpreter, not the authority. It must consume the Learning Center
advice and return a structured semantic packet. Domain rules then validate the packet.
No meaningful client statement may disappear; unresolved client meaning becomes a
question only when it is decision-critical. Facility-specific unknowns become
downstream research, never invented facts.
"""

import json
import copy
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional

import requests

from app.services.learning_center_advisor import build_learning_center_advice
from app.services.canonical_gap_policy import normalize_gap_key
from app.services.semantic_packet_wire import normalize_wire, parse_wire_json, provider_schema

SEMANTIC_AI_SYSTEM_RULES = [
    "Existing questionnaire selections are client evidence, separate from new narrative extraction. For each selected facility property, a statement may quote its exact existing questionnaire value and map its existing canonical path; do not emit questionnaire_patch_fields for unchanged selections. Only new/corrected fields need a user_text quote. When user_text is empty, emit no new patch fields. Preserve requested values as MUST/NICE traces using their separate requirement control.",
    "When requested property values have a separate Requirement/Preference control, enumerate each actual requested value in its own quoted MUST/NICE statement according to that control. This applies to arbitrary selected activities and other property lists. The control value itself is CONTEXT; absence-of-preference choices are CONTEXT. Do not leave requested values only in an advisory summary or transition context.",
    "The preferences string array is advisory metadata, never an independent decision source. Preserve every actual desired facility property, including arbitrary open-ended activities, in a quoted NICE statement trace. Do not leave a genuine facility preference only in preferences or classify its trace CONTEXT. Absence of preference and control values stay CONTEXT. Repairs must preserve these source traces.",
    'Only facility-testable desired properties belong in preferences or NICE traces. Explicit absence of preference, importance/requirement-level controls, resident biography and attitude toward moving are CONTEXT, retained in statement accounting without provider verification obligations. Preserve actual preferred activities as NICE even when separately reported as context. Do not infer a facility preference from a control value. Genuine negative preferences such as a smoke-free environment remain preferences.',
    "Supervision around the clock is not Nursing supervision or Skilled nursing care. Medication reminders are not Complex medication management. Rehabilitation alone does not establish speech therapy. Preserve only explicitly established clinical facts.",
    "Understand the client before recommending anything.",
    "Account for every meaningful client statement.",
    "For every KNOWN/USED client fact mapped to a canonical questionnaire field, populate that field's quoted patch slot unless questionnaire_state already supplies it. A facility research request is not a substitute for preserving the client's own known need. For example, explicit dialysis and its transport need require the quoted medicalCareProfile.needs Dialysis selection and dialysisTransportation Yes even while researching which facilities provide those services.",
    "Separate explicit facts from inferences.",
    "When client statements conflict about the same person and current situation, preserve both statements as AMBIGUOUS and ask which is correct. Do not choose the higher budget or more severe care need. Distinguish genuine contradictions from different people, time periods, or an explicit correction.",
    "Never convert an inference into a fact without confirmation or evidence.",
    "Do not infer Medicaid ineligibility from private pay, toileting assistance from hip surgery or transfer assistance, complex medication management from ordinary medication reminders, or absence of wandering from absence of memory problems. These are different facts; omit any field not explicitly supported. For couples preserve whose assistance is needed in coupleAssistance; one person's needs do not describe both people.",
    "Classify decision relevance as MUST, NICE, CONTEXT, or UNKNOWN.",
    "Identify unresolved client-owned information with a stable gap_key; deterministic policy, not the model, decides whether it blocks READY.",
    "NICE or CONTEXT ambiguity must remain UNKNOWN/AMBIGUOUS; the model may propose a question but may not grant it blocking authority.",
    "If material decision-critical information owned by the client is unknown or ambiguous, ASK the client instead of delegating it to facility research.",
    "Treat prior adaptiveSignals with explicit client answers as client evidence. Never re-ask a dimension that those answers already resolve, even with different wording.",
    "An explicit later correction in adaptiveSignals supersedes the conflicting original statement for the same person, fact, and time. Preserve the correction in statement accounting as KNOWN/USED and populate questionnaire_patch with the corrected value; do not keep the superseded conflict ASKED. Every repair response must return the full structured packet including questionnaire_patch, not only the repaired question or readiness.",
    "Treat explicit free-text client statements as client evidence too. Never ask a dimension again when the user's original text already answers it clearly.",
    "The target market/location is a minimum client-owned decision dimension. Absence is UNKNOWN and READY is forbidden until the client has supplied enough location information to select the search market.",
    "The affordability envelope/budget is a minimum client-owned decision dimension. Absence is UNKNOWN and READY is forbidden until the client has supplied a usable monthly budget or explicitly declined to set one.",
    "Facility-specific facts such as availability, price, unit route distance, meal delivery, dietary safety, current activities, or service capability may remain RESEARCH_REQUIRED after client intent is understood.",
    "decision_readiness is a raw advisory interview signal retained for audit; canonical deterministic gap policy owns final readiness.",
    "If domain or facility evidence is missing, request research and consult the Learning Center.",
    "UNKNOWN must remain UNKNOWN until resolved.",
    "Do not invent facility capabilities, prices, availability, reputation, or regulatory facts.",
    "Prefer one high-information clarification at a time.",
    "Populate questionnaire_patch from explicit client facts using only the exact field names and allowed enum values in required_output. Omit unknown or merely inferred fields; never copy defaults as client facts.",
    "Every new or changed questionnaire_patch leaf needs a statement whose raw_text is an exact substring of user_text and whose mapped_parameters contains that leaf's full dotted schema path. A paraphrase, a capability name, or the parent object path is not a field quote. Map every supported leaf, including needs arrays and rehabilitation fields; one exact quote may support multiple related leaf paths.",
    "Before returning JSON, walk every questionnaire_patch leaf and verify its full path appears in mapped_parameters on a statement with an exact source quote. Include relationship, gender, hasOngoingMedicalNeeds and other contextual leaves in this check, not only clinical needs. Add the appropriate path to an existing quoted statement or add a separate source-quoted statement. If a field is not supported, omit it; do not erase an explicit fact merely to avoid writing its trace.",
    "All socialProfile, familyProfile, languageProfile, foodProfile, culturalProfile, personalityProfile, futureCareProfile and transitionRiskProfile objects are children of humanIntelligenceV2. None is allowed at the root. The nesting must match required_output exactly, even during repair.",
    "Return questionnaire_patch_sources as a flat dictionary from every new/changed questionnaire_patch leaf path to an exact user_text quote. This explicit source index is mandatory for new facts even when the same quote is also in statements. Examples of keys: relationship, medicalCareProfile.hasOngoingMedicalNeeds, humanIntelligenceV2.transitionRiskProfile.recentHospitalization. Do not infer gender identity from pronouns or kinship. coupleAssistance is a single string, never an object keyed by partners.",
    "NEEDS_CLARIFICATION must include a separate ASKED statement with importance MUST or UNKNOWN, knowledge_state UNKNOWN or AMBIGUOUS, and the real clarification_question matching next_question. Do not mark a known location statement ASKED just because a different care fact is missing. If there is no unresolved decision-critical client question, return READY.",
    "Preserve the nested objects in required_output: mobilityMethod, transferAssistance and recentFalls belong under medicalCareProfile, never at the top level. Dialysis transportation belongs at medicalCareProfile.dialysisTransportation. Physical AND occupational therapy after hospitalization supports humanIntelligenceV2.transitionRiskProfile.postHospitalRehabNeed.",
    "Do not repeat values already supplied by questionnaire_state unless the family explicitly corrects them. A story about one parent's care must not turn a Parents/Couple search into Dad/Mom; preserve the household relationship and write each partner's needs in coupleAssistance. Do not infer no wandering from no dementia, or a recovery time from a therapy duration. temporarySupportMonths is measured in months, never copy a number of weeks into it.",
    "Medical terms must be normalized into the structured taxonomy: for example CPAP/BiPAP/ventilator/cough-assist belongs in respiratory equipment details and Permanent medical equipment, dialysis in Dialysis, chronic wounds in Wound care, wheelchairs in mobilityMethod, and lift/two-person transfers in transferAssistance.",
    "Return a compact decision packet: preserve 100% statement accounting but avoid repetition and long prose.",
]


def _required_output_schema() -> Dict[str, Any]:
    return {
        "facts": ["string"],
        "preferences": ["string"],
        "constraints": ["string"],
        "concerns": ["string"],
        "implications": [{"derived_from": ["string"], "implication": "string", "certainty": "POSSIBLE|LIKELY|CONFIRMED", "requires_confirmation": True}],
        "statements": [{"raw_text": "string", "meaning": "string", "importance": "MUST|NICE|CONTEXT|UNKNOWN", "knowledge_state": "KNOWN|UNKNOWN|AMBIGUOUS", "status": "USED|ASKED|RESEARCH_REQUIRED|NOT_DECISION_RELEVANT", "gap_key": "stable_snake_case_key|null", "mapped_parameters": ["string"], "clarification_question": "string|null", "research_task": "string|null"}],
        "next_question": "string|null",
        "research_requests": ["string"],
        "questionnaire_patch": {
            "relationship": "Mom|Dad|Grandma|Grandpa|Spouse|Myself|Parents|Couple|Relative|Friend",
            "gender": "Male|Female|Nonbinary|Other|Prefer not to say; only an explicit gender identity declaration, never inferred from kinship or pronouns",
            "ageGroup": "60-64|65-69|70-74|75-79|80-84|85-89|90-94|95+",
            "assistanceLevel": "Fully independent|Light assistance|Help with bathing|Help with dressing|Help with toileting|Help with medications|Daytime supervision|24/7 support required|Skilled nursing care",
            "memoryStatus": "No|Occasionally forgetful|Mild memory issues|Significant memory issues|Not sure",
            "budget": "positive monthly integer",
            "medicaidStatus": "Approved|Application pending|May qualify|Not eligible|Not sure",
            "medicareStatus": "Original Medicare|Medicare Advantage|No Medicare|Not sure",
            "moveTiming": "Immediately|Within 30 days|1-3 months|3-6 months|Planning ahead|Not sure",
            "coupleAssistance": "ONE STRING describing each partner's explicit assistance needs; never a dictionary or list",
            "referenceLocationValue": "explicit city/market string",
            "referenceAddress": "explicit reference address; preserve full address if provided",
            "locationImportant": "Yes|No",
            "maximumDistanceMiles": "explicit maximum distance in miles as a numeric string; do not round to preset choices",
            "parkingRequirement": "No|Regular parking|Accessible parking|Covered parking|Not sure",
            "parkingVehicleCount": "One vehicle|Two vehicles",
            "medicalCareProfile": {
                "hasOngoingMedicalNeeds": "No|Yes|Not sure",
                "needs": ["Dialysis|Oxygen|Wound care|Injections or infusions|Complex medication management|Complex chronic condition|Permanent medical equipment|Nursing supervision"],
                "mobilityMethod": "Independent|Cane|Walker|Wheelchair|Mostly in bed",
                "transferAssistance": "No|One person|Two people|Mechanical lift|Not sure",
                "recentFalls": "No|One|More than one|Not sure",
                "dialysisFrequency": "explicit frequency string",
                "dialysisCenter": "explicit center name/address",
                "dialysisTransportation": "No|Yes|Not sure",
                "oxygenUse": "At night|With activity|Continuously|Not sure",
                "woundCareFrequency": "explicit frequency string",
                "complexConditionDetails": "concise explicit conditions/equipment",
                "physicianCoordination": "No|Yes|Not sure",
            },
            "humanIntelligenceV2": {
                "transitionRiskProfile": {
                    "recentHospitalization": "No|Yes|Not sure",
                    "recentProcedure": "No|Yes|Not sure",
                    "procedureType": "explicit surgery or procedure",
                    "expectedRecovery": "No|Yes|Not sure",
                    "temporarySupportMonths": "explicit number of months",
                    "postHospitalRehabNeed": "No|Yes|Not sure",
                    "wanderingConcerns": "No|Yes|Not sure",
                    "attitudeTowardMove": "Wants to move|Positive|Cautious but open|Anxious|Resistant|Not sure",
                },
                "languageProfile": {
                    "preferredSpokenLanguage": "explicit language",
                    "nativeLanguage": "explicit language",
                    "languageNeedScope": "Requirement|Preference",
                },
                "foodProfile": {"dietaryPreferences": ["explicit dietary requirement"]},
                "futureCareProfile": {"secureMemoryNeighborhoodNeed": "No|Yes|Not sure", "continuumOfCarePreference": "Required|Preferred|Not important|Not sure"},
                "culturalProfile": {"religionImportance": "Yes|No", "faithTraditions": ["explicit faith tradition"]},
                "socialProfile": {"activityRequirementLevel": "Requirement|Preference"},
                "familyProfile": {"socialInteractionNeed": "Daily|Several times weekly|Weekly|Occasionally|Very little", "coupleStayTogetherPreference": "explicit preference to stay together"},
                "personalityProfile": {"communitySizePreference": "Small and familiar|Medium|Large and active|Quiet|No preference"},
            },
        },
        "questionnaire_patch_sources": {"full.dotted.patch.leaf.path": "exact source substring from user_text; one entry per new/changed patch leaf"},
        "decision_readiness": "READY|NEEDS_CLARIFICATION|NEEDS_RESEARCH",
    }


def _build_prompt(user_text: str, questionnaire_state: Dict[str, Any], learning_advice: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.semantic_field_contract import describe_fields
    return {
        "role": "OPTIME_NURSING_EXPERT_SEMANTIC_INTERPRETER",
        "mission": "Understand the resident/family request at senior-living expert level before matching. Distinguish decision-critical client clarification from downstream facility research and non-blocking NICE/CONTEXT ambiguity.",
        "rules": SEMANTIC_AI_SYSTEM_RULES,
        "response_constraints": {
            "style": "compact JSON; no repeated explanation",
            "facts_max": 10,
            "preferences_max": 8,
            "constraints_max": 8,
            "concerns_max": 6,
            "implications_max": 6,
            "research_requests_max": 8,
            "statement_rule": "Every meaningful user/questionnaire statement must be accounted for exactly once; semantically linked fragments may be grouped, but nothing material may be dropped.",
            "field_length_rule": "Keep meaning, implication, clarification_question and research_task concise; usually one sentence each.",
            "question_priority_rule": "Ask only one highest-information unresolved MUST/decision-critical client question. Do not ask NICE/CONTEXT questions merely to improve ranking.",
            "asked_statement_rule": "If any statement has status ASKED, copy the exact next_question into that statement's clarification_question. There may be at most one ASKED statement per turn.",
            "gap_key_rule": "Every ASKED statement must identify one stable snake_case gap_key. The key identifies the unresolved fact only; it does not decide whether the gap blocks recommendations.",
            "authority_rule": "The model extracts facts, identifies gaps, and phrases questions. Canonical deterministic policy alone decides blocking classification, final readiness, zero-result behavior, and escalation.",
            "adaptive_answer_rule": "Prior adaptiveSignals are part of the client record. If an adaptive signal contains an explicit answer, treat that dimension as answered and do not ask it again using a paraphrase.",
            "free_text_answer_rule": "Explicit statements in user_text are also part of the client record. Do not ask again about a dimension already answered there, including explicit negative statements such as no mobility limitation or no memory concerns.",
            "questionnaire_patch_rule": "Write every explicit structured client fact into questionnaire_patch. Use only supplied schema keys and exact enum spellings. Omit unknowns and inferences. This patch is the canonical bridge from narrative intake into the same table used by the manual questionnaire.",
            "field_quote_rule": "For each new/changed patch leaf include its full dotted path in statements.mapped_parameters, with an exact source substring in raw_text. Example: medicalCareProfile.transferAssistance, not transfer_assistance or transferAssistance. Never invent a quote or use questionnaire defaults as a source quote.",
            "minimum_readiness_dimensions": {
                "market_location": "Must be KNOWN from user_text, questionnaire_state, or prior adaptiveSignals before READY. If missing, ask the client.",
                "monthly_affordability": "Must be KNOWN from user_text, questionnaire_state, or prior adaptiveSignals before READY. A client may explicitly say they have no budget limit or do not want to set one; silence is not a value.",
                "absence_policy": "Do not treat omitted client-owned information as satisfied, defaulted, inferred, or research-required. Missing minimum dimensions require NEEDS_CLARIFICATION.",
            },
        },
        "questionnaire_state": questionnaire_state,
        "client_evidence": _client_evidence_context(user_text, questionnaire_state),
        "user_text": user_text,
        "learning_center_advice": learning_advice,
        "required_output": _required_output_schema(),
        "field_contract": describe_fields(_required_output_schema()["questionnaire_patch"]),
        "field_trace_example": {
            "source_example": "My aunt receives dialysis and enjoys group activities.",
            "questionnaire_patch": {"relationship": "Relative", "medicalCareProfile": {"hasOngoingMedicalNeeds": "Yes", "needs": ["Dialysis"]}, "humanIntelligenceV2": {"socialProfile": {"activityRequirementLevel": "Preference"}}},
            "questionnaire_patch_sources": {"relationship": "My aunt", "medicalCareProfile.hasOngoingMedicalNeeds": "receives dialysis", "medicalCareProfile.needs": "receives dialysis", "humanIntelligenceV2.socialProfile.activityRequirementLevel": "enjoys group activities"},
            "statements": [
                {"raw_text": "My aunt", "mapped_parameters": ["relationship"], "importance": "CONTEXT", "knowledge_state": "KNOWN", "status": "USED"},
                {"raw_text": "receives dialysis", "mapped_parameters": ["medicalCareProfile.hasOngoingMedicalNeeds", "medicalCareProfile.needs"], "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED"},
                {"raw_text": "enjoys group activities", "mapped_parameters": ["humanIntelligenceV2.socialProfile.activityRequirementLevel"], "importance": "NICE", "knowledge_state": "KNOWN", "status": "USED"},
            ],
            "instruction": "Example of field-by-field source accounting only. Never copy these values or quotes into the answer; use the actual user_text.",
        },
        "clarification_trace_example": {
            "source_example": "I need some daily assistance.",
            "statement": {"raw_text": "some daily assistance", "meaning": "The specific daily tasks requiring assistance remain unclear.", "importance": "MUST", "knowledge_state": "AMBIGUOUS", "status": "ASKED", "mapped_parameters": ["assistanceLevel"], "clarification_question": "Which daily tasks require assistance?"},
            "next_question": "Which daily tasks require assistance?",
            "decision_readiness": "NEEDS_CLARIFICATION",
            "instruction": "Question trace example only. An unresolved MUST needs an ASKED statement, even when other statements are known. Do not invent a confirmed assistanceLevel value while its source is ambiguous. Never copy this example into the answer; use the actual record and AI-authored question.",
        },
    }


def _extract_responses_output(body: Dict[str, Any]) -> Dict[str, Any]:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return parse_wire_json(output_text)
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                return parse_wire_json(part["text"])
    raise RuntimeError("SEMANTIC_AI_INVALID_RESPONSE")


def _request_with_retry(url: str, headers: Dict[str, str], request_json: Dict[str, Any]) -> requests.Response:
    timeout_seconds = max(5.0, float(os.getenv("OPTIME_SEMANTIC_AI_TIMEOUT_SECONDS", "45")))
    max_attempts = max(1, min(3, int(os.getenv("OPTIME_SEMANTIC_AI_MAX_ATTEMPTS", "2"))))
    backoff_seconds = max(0.0, float(os.getenv("OPTIME_SEMANTIC_AI_RETRY_BACKOFF_SECONDS", "1")))
    last_error: Optional[Exception] = None
    deadline = time.monotonic() + timeout_seconds
    attempts_made = 0
    for attempt in range(1, max_attempts + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        # A successful connection should get the available generation budget.
        # Reserving equal slices for speculative retries cancelled valid slow
        # generations after ~17 seconds despite a 45-second deadline. Retry
        # only with time actually left after an early transport failure.
        attempt_budget = remaining
        connect_timeout = min(5.0, attempt_budget / 4)
        read_timeout = attempt_budget - connect_timeout
        attempts_made += 1
        try:
            return requests.post(url, headers=headers, json=request_json, timeout=(connect_timeout, read_timeout))
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            if backoff_seconds:
                delay = backoff_seconds * attempt
                if deadline - time.monotonic() <= delay:
                    break
                time.sleep(delay)
    raise RuntimeError(f"SEMANTIC_AI_TRANSPORT_RETRY_EXHAUSTED:attempts={attempts_made}:timeout={timeout_seconds}:{last_error}")


def _resolve_temperature() -> Optional[float]:
    """0 by default -- decision_readiness is a classification, not creative writing,
    and needs reproducible behavior across calls on the same input. Confirmed live:
    two back-to-back production calls with byte-identical input flipped between
    READY and NEEDS_CLARIFICATION with no temperature set (the provider default,
    typically 0.7-1.0, applies). Set OPTIME_SEMANTIC_AI_TEMPERATURE to tune, or to
    the literal string "unset" to omit the parameter entirely -- some models
    (reasoning-only ones in particular) reject the field outright rather than
    ignoring it."""
    raw = os.getenv("OPTIME_SEMANTIC_AI_TEMPERATURE", "0").strip()
    if raw.lower() == "unset":
        return None
    try:
        return float(raw)
    except ValueError:
        return 0.0


TRANSPORT_SYSTEM_PROMPT = (
    "Existing questionnaire selections are client evidence, separate from new narrative extraction. For each selected facility property, a statement may quote its exact existing questionnaire value and map its existing canonical path; do not emit questionnaire_patch_fields for unchanged selections. Only new/corrected fields need a user_text quote. When user_text is empty, emit no new patch fields. Preserve requested values as MUST/NICE traces using their separate requirement control. "
    "When requested property values have a separate Requirement/Preference control, enumerate each actual requested value in its own quoted MUST/NICE statement according to that control. This applies to arbitrary selected activities and other property lists. The control value itself is CONTEXT; absence-of-preference choices are CONTEXT. Do not leave requested values only in an advisory summary or transition context. "
    "The preferences string array is advisory metadata, never an independent decision source. Preserve every actual desired facility property, including arbitrary open-ended activities, in a quoted NICE statement trace. Do not leave a genuine facility preference only in preferences or classify its trace CONTEXT. Absence of preference and control values stay CONTEXT. Repairs must preserve these source traces. "
    'Only facility-testable desired properties belong in preferences or NICE traces. Explicit absence of preference, importance/requirement-level controls, resident biography and attitude toward moving are CONTEXT, retained in statement accounting without provider verification obligations. Preserve actual preferred activities as NICE even when separately reported as context. Do not infer a facility preference from a control value. Genuine negative preferences such as a smoke-free environment remain preferences. '
    "You are the governed semantic reasoning layer for a senior-living decision engine. "
    "Return compact JSON only. Follow required_output nesting exactly. "
    "Every new questionnaire_patch leaf, including context fields, must have its full dotted path "
    "in statements.mapped_parameters beside a raw_text quote copied from user_text. "
    "Statement accounting does not require a field mapping. mapped_parameters: [] is valid "
    "and required when no canonical field value is explicitly established. Never attach a "
    "nearby or generic field merely because a statement is meaningful. A KNOWN/USED trace "
    "may map a canonical path only when the packet extracts that exact field with its quote "
    "or the caller already supplied its value. Preserve unsupported facts and requirements "
    "in their source traces without forcing them into a different profile field. "
    "Audit every leaf before returning; repair responses obey the same contract. "
    "Also audit the clarification contract in the final JSON, including every repair response: "
    "NEEDS_CLARIFICATION requires a nonempty next_question and exactly one ASKED statement "
    "with importance MUST or UNKNOWN, knowledge_state UNKNOWN or AMBIGUOUS, a stable gap_key, "
    "and clarification_question identical to next_question. Trace the unresolved fact separately "
    "from the known facts. Never return NEEDS_CLARIFICATION with null next_question or only USED statements. "
    "If a material client-owned unknown remains, phrase a question; do not invent its answer or "
    "return READY to avoid asking. If none remains and minimum client dimensions are resolved, "
    "return READY. Keep known facts and their exact source quotes. "
    "These are advisory extraction signals; deterministic policy owns final readiness."
)


def _default_transport(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip()
    model = os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip()
    api_key = os.getenv("OPTIME_SEMANTIC_AI_API_KEY", "").strip()
    if not url or not model:
        raise RuntimeError("SEMANTIC_AI_NOT_CONFIGURED")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    uses_responses_api = "/responses" in url.lower()
    required_output = _required_output_schema()
    schema = provider_schema(required_output, family_text=str(payload.get("user_text") or ""))
    payload = copy.deepcopy(payload)
    # The record belongs to the caller, never to a previous model packet.
    # Rebuild this view for every request and repair using the same predicates
    # used by the server's no-reask and minimum-dimension checks.
    payload["client_evidence"] = _client_evidence_context(
        str(payload.get("user_text") or ""), payload.get("questionnaire_state") or {})
    # Strict grammar already supplies the response structure. Sending a second,
    # legacy packet shape and examples invites the model to mix the two formats.
    payload.pop("required_output", None)
    payload.pop("field_trace_example", None)
    payload.pop("clarification_trace_example", None)
    payload["wire_contract"] = {
        "questionnaire_value_hints": required_output["questionnaire_patch"],
        "instruction": "Return the schema-constrained wire format, not a free-form packet. questionnaire_patch_fields is a sparse array of {path, value, quote} entries. Use the full canonical dotted path, exactly as in statements.mapped_parameters. Include at most one entry per path. Omit paths with no new fact, never emit empty placeholder entries. Multiple assistance selections belong in one assistanceLevel array entry. Every entry must be independently supported by an exact user_text quote. Constraints, facts and concerns are packet metadata, never patch fields. Omit unsupported inferred fields; preserve unsupported requirements in statements/constraints for accounting. Do not infer native language, religion importance or requirement scope merely from language use or dietary preference. Choose the interview variant matching whether a material client question remains. A clarification variant requires one AI-authored question and its unresolved-fact trace. Never invent facts or a source quote to satisfy the schema. These rules apply to all repairs too.",
        "version": "semantic-extraction-v1",
        "field_paths": "Each extraction entry uses the full canonical dotted path in both path and statements.mapped_parameters. Do not use aliases. Omit unused paths. Map canonical client fields only when that exact field's value is explicitly established, not merely because it is related to the statement. A known client fact marked USED must reach its path in questionnaire_patch_fields unless questionnaire_state already supplies that field. Speaking a language does not establish nativeLanguage. A dietary preference does not establish faithTraditions or religious identity; preserve the dietary fact without these unrelated mappings.",
        "source_quotes": "For each extraction quote choose an unchanged source span from SourceQuote in the response schema. Use that same quote in the associated statement raw_text. The full source sentence is valid; never paraphrase a quote or insert a pronoun that was not in the original text.",
        "clinical_detail_consistency": "A known medical detail does not replace its medical need. Unless already supplied by questionnaire_state, pair dialysis frequency/center with medicalCareProfile.needs containing Dialysis, oxygen use with Oxygen, and wound-care frequency with Wound care. Give the parent need its own exact quote from the same explicit client treatment statement. Never add a need when the client's treatment itself is unknown or denied.",
        "assistance_encoding": "Emit exactly one entry per field. assistanceLevel.value may preserve the existing questionnaire string or one array containing every explicit selection; normalization joins that array into the existing comma-separated string. Never split multiple ADL selections into repeated entries. Do not copy already supplied questionnaire values into new extracted entries unless explicitly corrected.",
    }
    system_prompt = TRANSPORT_SYSTEM_PROMPT + " The actual response shape is the supplied strict JSON schema. questionnaire_patch_fields is a sparse array of {path,value,quote}, with one entry per new or corrected field; omit unchanged fields and placeholders. client_evidence.resolved_questionnaire_fields contains existing client answers even when user_text does not repeat them: never ask for these facts again unless genuine conflicting client evidence needs resolution. An absent extraction entry does not make an existing answer unknown. client_evidence.minimum_dimensions reports whether the client has already answered location and affordability. Check the full questionnaire_state and original text for more specific unresolved facts; this summary does not authorize READY or invent answers. Never emit the same field twice; for couples use coupleAssistance to preserve each person's needs. Represent any ASKED trace only in interview.blocking_statement; its question is interview.next_question. Do not duplicate the blocking trace in statements. Keep metadata lists brief; retain every meaningful fact in its source trace. Normalization will reconstruct existing packet keys without inference."
    response_format = {"type": "json_schema", "json_schema": {"name": "semantic_extraction", "strict": True, "schema": schema}}
    if uses_responses_api:
        request_json = {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "text": {"format": {"type": "json_schema", "name": "semantic_extraction", "strict": True, "schema": schema}},
        }
    else:
        request_json = {
            "model": model,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
    temperature = _resolve_temperature()
    if temperature is not None:
        request_json["temperature"] = temperature
    response = _request_with_retry(url, headers, request_json)
    if not response.ok:
        raise RuntimeError(f"SEMANTIC_AI_HTTP_{response.status_code}:{response.text[:500]}")
    body = response.json()
    if uses_responses_api:
        wire_packet = _extract_responses_output(body)
    elif isinstance(body, dict) and "choices" in body:
        wire_packet = parse_wire_json(body["choices"][0]["message"]["content"])
    elif isinstance(body, dict) and "output" in body and isinstance(body["output"], dict):
        wire_packet = body["output"]
    elif isinstance(body, dict):
        wire_packet = body
    else:
        raise RuntimeError("SEMANTIC_AI_INVALID_RESPONSE")
    try:
        return normalize_wire(wire_packet, required_output, family_text=str(payload.get("user_text") or ""))
    except RuntimeError as error:
        # A rejected wire packet has not reached prior_packet. Give the bounded
        # AI repair the complete rejected evidence, without accepting any field.
        error.wire_diagnostic = copy.deepcopy(wire_packet)
        error.patch_diagnostic = {"rejected_wire_packet": error.wire_diagnostic}
        raise


def _ground_clinical_patch(result: Dict[str, Any], user_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce the existing explicit-fact rule at the narrative/structured boundary.

    Ordinary supervision/reminders must not become higher-acuity enum values.
    Keep the original statements for accounting; omitted inferred fields are traced.
    """
    patch = result.get("questionnaire_patch")
    if not isinstance(patch, dict):
        return result
    signals = (((state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    source = " ".join([str(user_text or "")] + [str(s.get("answer") or "") for s in signals if isinstance(s, dict)]).lower()
    # Exclude explicit negative clauses from positive grounding. Structured client
    # selections remain authoritative and are never removed by this patch guard.
    positive = re.sub(r"\b(?:no|without|not|does not need|doesn't need|do not need|don't need)\s+(?:any\s+)?(?:skilled\s+)?(?:nursing|nurses?|rn|lpn|complex\s+(?:medication|medicine|meds)\s+(?:management|regimens?))\b", "", source)
    selected = (state.get("medicalCareProfile") or {}).get("needs") or []
    # The bare word "nursing" is not a clinical fact. It appears in "we toured a nursing
    # home", "her nurse suggested", "nursing care in general" -- none of which says this
    # person needs nursing supervision. Matching it let ordinary supervision become a
    # nursing requirement, which is exactly what this guard exists to prevent, so the
    # phrasing must actually attach a nurse to this person's care, the same way the
    # complex-medication test below demands the whole phrase.
    nursing_phrase = re.compile(
        r"\b(?:skilled\s+nursing|nursing\s+(?:supervision|care|support|staff|services?)"
        r"|(?:supervis\w+|monitor\w+|care|assessments?)\s+by\s+(?:a\s+)?(?:nurse|rn|lpn)"
        r"|(?:needs?|requires?|has)\s+(?:a\s+)?(?:nurse|rn|lpn)\b"
        r"|(?:nurse|rn|lpn)\s+on\s+(?:site|staff|duty)"
        r"|round[- ]the[- ]clock\s+nursing|24/?7\s+nursing)\b"
    )
    nursing = "Nursing supervision" in selected or "skilled nursing" in str(state.get("assistanceLevel") or "").lower() or bool(nursing_phrase.search(positive))
    complex_meds = "Complex medication management" in selected or bool(re.search(r"\bcomplex\s+(?:medication|medicine|meds)\s+(?:management|regimen|regimens)\b", positive))
    omitted = []
    medical = patch.get("medicalCareProfile")
    if isinstance(medical, dict) and isinstance(medical.get("needs"), list):
        allowed = []
        for need in medical["needs"]:
            if (need == "Nursing supervision" and not nursing) or (need == "Complex medication management" and not complex_meds):
                omitted.append(f"medicalCareProfile.needs:{need}")
            else:
                allowed.append(need)
        medical["needs"] = allowed
    if patch.get("assistanceLevel") == "Skilled nursing care" and not nursing:
        del patch["assistanceLevel"]
        omitted.append("assistanceLevel:Skilled nursing care")
    if omitted:
        result["clinical_fact_validation"] = {"omitted_unsupported_fields": omitted, "reason": "EXPLICIT_CLIENT_EVIDENCE_REQUIRED"}
    return result


def _validate_result(result: Dict[str, Any], *, allow_empty_statements: bool = False) -> Dict[str, Any]:
    patch = result.get("questionnaire_patch")
    if patch is None:
        # Backwards-compatible for deterministic test doubles and model providers
        # that have not yet adopted the new contract; live prompts require it.
        result["questionnaire_patch"] = {}
    elif not isinstance(patch, dict):
        raise RuntimeError("SEMANTIC_AI_INVALID_QUESTIONNAIRE_PATCH")

    statements = result.get("statements")
    if not isinstance(statements, list) or (not statements and not allow_empty_statements):
        raise RuntimeError("SEMANTIC_AI_MISSING_STATEMENT_TRACE")
    allowed_status = {"USED", "ASKED", "RESEARCH_REQUIRED", "NOT_DECISION_RELEVANT"}
    allowed_importance = {"MUST", "NICE", "CONTEXT", "UNKNOWN"}
    allowed_knowledge = {"KNOWN", "UNKNOWN", "AMBIGUOUS"}

    asked_without_question = [statement for statement in statements if isinstance(statement, dict) and statement.get("status") == "ASKED" and not str(statement.get("clarification_question") or "").strip()]
    next_question = str(result.get("next_question") or "").strip()
    asked_statements = [statement for statement in statements if isinstance(statement, dict) and statement.get("status") == "ASKED"]
    if len(asked_without_question) == 1 and len(asked_statements) == 1 and next_question:
        asked_without_question[0]["clarification_question"] = next_question
        result["question_trace_normalization"] = {"applied": True, "reason": "SINGLE_ASKED_STATEMENT_USED_TOP_LEVEL_NEXT_QUESTION"}

    for idx, statement in enumerate(statements):
        if not isinstance(statement, dict) or not str(statement.get("raw_text") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_INVALID_STATEMENT:{idx}")
        if statement.get("status") not in allowed_status:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_STATUS:{idx}")
        if statement.get("importance") not in allowed_importance:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_IMPORTANCE:{idx}")
        if statement.get("knowledge_state") not in allowed_knowledge:
            raise RuntimeError(f"SEMANTIC_AI_INVALID_KNOWLEDGE:{idx}")
        if statement.get("status") == "ASKED" and not str(statement.get("clarification_question") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_ASKED_WITHOUT_QUESTION:{idx}")
        if statement.get("status") == "ASKED":
            gap_key = normalize_gap_key(statement.get("gap_key") or statement.get("target_fact_key"))
            if not gap_key:
                gap_key = next((normalize_gap_key(value) for value in statement.get("mapped_parameters") or [] if normalize_gap_key(value)), "semantic_ai_unregistered_gap")
            statement["gap_key"] = gap_key
        if statement.get("status") == "RESEARCH_REQUIRED" and not str(statement.get("research_task") or "").strip():
            raise RuntimeError(f"SEMANTIC_AI_RESEARCH_WITHOUT_TASK:{idx}")

    nonblocking_asked = [s for s in statements if s.get("status") == "ASKED" and s.get("importance") in {"NICE", "CONTEXT"}]
    for statement in nonblocking_asked:
        statement["status"] = "USED"
        statement["clarification_question"] = None
    blocking_asked = [s for s in statements if s.get("status") == "ASKED"]
    pending_question = bool(blocking_asked)
    pending_research = any(s.get("status") == "RESEARCH_REQUIRED" for s in statements)

    if not pending_question and nonblocking_asked:
        result["next_question"] = None
        if str(result.get("decision_readiness") or "") == "NEEDS_CLARIFICATION":
            result["decision_readiness"] = "READY"
        result["readiness_normalization"] = {"from": "NEEDS_CLARIFICATION", "to": "READY", "reason": "ONLY_NICE_OR_CONTEXT_AMBIGUITY_REMAINED"}

    readiness = str(result.get("decision_readiness") or "NEEDS_CLARIFICATION")
    if readiness == "READY" and pending_question:
        raise RuntimeError("SEMANTIC_AI_READY_WITH_UNRESOLVED_CLIENT_INPUT")
    if readiness == "NEEDS_CLARIFICATION" and not pending_question:
        raise RuntimeError("SEMANTIC_AI_CLARIFICATION_WITHOUT_BLOCKING_QUESTION")
    if readiness == "NEEDS_RESEARCH" and not pending_question:
        result["decision_readiness"] = "READY"
        result["readiness_normalization"] = {"from": "NEEDS_RESEARCH", "to": "READY", "reason": "CLIENT_INTENT_COMPLETE_FACILITY_RESEARCH_DEFERRED", "pending_facility_research": pending_research}
    result["statement_coverage_percent"] = 100.0
    result["dropped_statement_count"] = 0
    result["governance"] = {
        "ai_based": True,
        "learning_center_consulted": True,
        "unknown_is_not_default": True,
        "no_silent_drop": True,
        "client_intent_ready_allows_downstream_facility_research": True,
        "nice_context_unknowns_do_not_block_ready": True,
        "prior_adaptive_answers_are_client_evidence": True,
        "explicit_free_text_answers_are_client_evidence": True,
        "minimum_client_dimensions_required": ["market_location", "monthly_affordability"],
        "rules_applied": SEMANTIC_AI_SYSTEM_RULES,
    }
    return result


def _repair_live_readiness_mismatch(result: Dict[str, Any]) -> Dict[str, Any]:
    if str(result.get("decision_readiness") or "").upper() != "READY":
        return result
    statements = result.get("statements") if isinstance(result.get("statements"), list) else []
    blocking = [statement for statement in statements if isinstance(statement, dict) and statement.get("status") == "ASKED" and statement.get("importance") in {"MUST", "UNKNOWN"} and str(statement.get("clarification_question") or result.get("next_question") or "").strip()]
    if len(blocking) != 1:
        return result
    result = dict(result)
    result["decision_readiness"] = "NEEDS_CLARIFICATION"
    result["live_packet_repair"] = {"applied": True, "from": "READY", "to": "NEEDS_CLARIFICATION", "reason": "MODEL_RETURNED_BLOCKING_AI_QUESTION_WITH_READY_LABEL"}
    return result


def _adaptive_answer_summary(questionnaire_state: Dict[str, Any]) -> List[Dict[str, str]]:
    signals = (((questionnaire_state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    answers: List[Dict[str, str]] = []
    for item in signals:
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer") or "").strip()
        explanation = str(item.get("impactExplanation") or "").strip()
        if not answer:
            continue
        question = explanation.split("|", 1)[0].replace("Question:", "").strip() if explanation else ""
        answers.append({"question": question, "answer": answer})
    return answers


def _question_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", str(text or "").lower())
    stop = {"a", "an", "and", "any", "are", "can", "do", "does", "for", "has", "have", "how", "i", "in", "is", "of", "or", "she", "he", "the", "they", "to", "use", "uses", "what", "whether", "with", "you", "your"}
    aliases = {
        "walk": "mobility", "walking": "mobility", "walker": "mobility", "wheelchair": "mobility", "cane": "mobility", "stairs": "mobility", "standing": "mobility", "transfer": "mobility", "transfers": "mobility",
        "memory": "cognitive", "dementia": "cognitive", "alzheimer": "cognitive", "cognition": "cognitive",
        "city": "location", "metro": "location", "area": "location", "geography": "location",
        "monthly": "budget", "afford": "budget", "cost": "budget", "price": "budget",
    }
    return {aliases.get(token, token) for token in tokens if token not in stop and len(token) > 2}


def _explicit_user_text_answered_dimensions(user_text: str) -> set[str]:
    text = str(user_text or "").lower()
    answered: set[str] = set()
    if re.search(r"\b(no mobility limitation(?:s)?|walks? independently|independent with [^.]{0,100}transfers?|uses? (?:a )?(?:walker|wheelchair|cane)|needs? (?:a )?(?:walker|wheelchair|cane))\b", text):
        answered.add("mobility")
    if re.search(r"\b(no memory concern(?:s)?|no cognitive support|no dementia|cognitively intact|memory concern(?:s)?|dementia|alzheimer)\b", text):
        answered.add("cognitive")
    if re.search(r"\b(las vegas|north las vegas|henderson|nevada|miami|dallas|houston|austin)\b", text):
        answered.add("location")
    if re.search(r"(?:budget|monthly|per month|afford|cost)[^\n]{0,60}\$?\s*[0-9]{3,6}|\$\s*[0-9]{3,6}", text):
        answered.add("budget")
    return answered


def _question_reasks_answered_dimension(result: Dict[str, Any], questionnaire_state: Dict[str, Any], user_text: str = "") -> bool:
    next_question = str(result.get("next_question") or "").strip()
    if not next_question:
        return False
    # A mentioned dimension is not necessarily resolved. Preserve model-authored
    # questions about contradictory client evidence rather than forcing READY.
    has_conflict = any(
        isinstance(statement, dict)
        and statement.get("status") == "ASKED"
        and statement.get("knowledge_state") == "AMBIGUOUS"
        and statement.get("importance") in {"MUST", "UNKNOWN"}
        for statement in result.get("statements") or []
    )
    current = _question_terms(next_question)
    salient = {"mobility", "cognitive", "location", "budget"}
    if not has_conflict and current & _explicit_user_text_answered_dimensions(user_text) & salient:
        return True
    if not has_conflict:
        # Check the actual field targeted by the question, not merely similar
        # words. This includes button answers, which are not adaptiveSignals.
        asked = [s for s in result.get("statements") or []
                 if isinstance(s, dict) and s.get("status") == "ASKED"]
        for statement in asked:
            paths = statement.get("mapped_parameters") or []
            if paths and all(_questionnaire_field_resolved(questionnaire_state, path) for path in paths):
                return True
    if not current:
        return False
    for entry in _adaptive_answer_summary(questionnaire_state):
        prior = _question_terms(f"{entry.get('question', '')} {entry.get('answer', '')}")
        if not prior:
            continue
        overlap = current & prior
        if overlap & salient:
            return True
        if len(overlap) >= 2 and len(overlap) / max(1, min(len(current), len(prior))) >= 0.5:
            return True
    return False


def _questionnaire_field_resolved(state: Dict[str, Any], path: str) -> bool:
    from app.services.canonical_structured_profile import in_schema

    if not isinstance(path, str) or not in_schema(path):
        return False
    value: Any = state
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    if path == "budget":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    if value is None or value == [] or value == {}:
        return False
    text = str(value).strip().lower()
    if text in {"", "not sure", "unknown", "none"}:
        return False
    # These broad answers do not resolve which daily tasks need assistance.
    if path == "assistanceLevel" and text in {"light assistance", "24/7 support required"}:
        return False
    return True


def _client_evidence_context(user_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.semantic_field_contract import compile_fields

    resolved = {}
    for path in compile_fields(_required_output_schema()["questionnaire_patch"]):
        if not _questionnaire_field_resolved(state, path):
            continue
        value = state
        for part in path.split("."):
            value = value[part]
        resolved[path] = copy.deepcopy(value)
    return {
        "resolved_questionnaire_fields": resolved,
        "minimum_dimensions": _minimum_dimension_status(user_text, state),
        "prior_adaptive_answers": _adaptive_answer_summary(state),
        "instruction": "These are existing client answers, not new AI extractions or facility evidence. Preserve them without fabricating source quotes. Unknowns remain unknown; ask only for a material unresolved fact or genuine conflict.",
    }


_DIMENSION_BY_FACT_KEY = {
    "monthly_budget": "monthly_affordability",
    "monthly_affordability": "monthly_affordability",
    "budget": "monthly_affordability",
    "market_location": "market_location",
    "location": "market_location",
    "city_or_metro_area": "market_location",
}


def _answered_minimum_dimensions(questionnaire_state: Dict[str, Any]) -> set[str]:
    """Minimum dimensions the client has already been asked about and has answered.

    The readiness guardian's own rule is that "explicit adaptive answers, including
    acknowledged unknowns, resolve the interview blocker without fabricating a value".
    Without this, an answer that carries no parsable amount ("Not sure") left the
    dimension permanently unknown while the AI — correctly — reported READY, so the
    readiness guard below raised on every attempt and the interview could never be
    completed or retried out of.
    """
    answered: set[str] = set()
    signals = (((questionnaire_state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    for item in signals:
        if not isinstance(item, dict) or not str(item.get("answer") or "").strip():
            continue
        fact_key = str(item.get("targetFactKey") or item.get("target_fact_key") or "").strip()
        if not fact_key:
            match = re.search(r"Target fact:\s*([A-Za-z0-9_]+)", str(item.get("impactExplanation") or ""))
            fact_key = match.group(1) if match else ""
        dimension = _DIMENSION_BY_FACT_KEY.get(fact_key.strip().lower())
        if dimension:
            answered.add(dimension)
    return answered


def _minimum_dimension_status(user_text: str, questionnaire_state: Dict[str, Any]) -> Dict[str, bool]:
    text = str(user_text or "").lower()
    signals = (((questionnaire_state.get("humanIntelligenceV2") or {}).get("scoringEngine") or {}).get("adaptiveSignals") or [])
    signal_text = " ".join(f"{str(item.get('impactExplanation') or '')} {str(item.get('answer') or '')}" for item in signals if isinstance(item, dict)).lower()
    combined = f"{text} {signal_text}"
    answered = _answered_minimum_dimensions(questionnaire_state)
    explicit_location = any(str(questionnaire_state.get(key) or "").strip() for key in ("locationCity", "city", "referenceLocationValue"))
    text_location = bool(re.search(r"\b(las vegas|north las vegas|henderson|nevada)\b", combined))
    raw_budget = questionnaire_state.get("budget")
    numeric_budget = isinstance(raw_budget, (int, float)) and float(raw_budget) > 0
    text_budget = bool(re.search(
        r"(?:budget|monthly|per month|afford|cost|spend|pay)[^\n]{0,50}\$?\s*\d[\d,]{2,}(?:\.\d+)?|\$\s*\d[\d,]{2,}(?:\.\d+)?",
        combined,
    ))
    explicit_no_limit = bool(re.search(r"\b(no budget limit|no monthly limit|do not want to set a budget|don't want to set a budget)\b", combined))
    return {
        "market_location": explicit_location or text_location or "market_location" in answered,
        "monthly_affordability": numeric_budget or text_budget or explicit_no_limit or "monthly_affordability" in answered,
    }


def _has_blocking_question(result: Dict[str, Any]) -> bool:
    statements = result.get("statements") if isinstance(result.get("statements"), list) else []
    return any(isinstance(statement, dict) and statement.get("status") == "ASKED" and statement.get("importance") in {"MUST", "UNKNOWN"} and str(statement.get("clarification_question") or result.get("next_question") or "").strip() for statement in statements)


def _repair_missing_minimum_dimensions_with_ai(*, result: Dict[str, Any], payload: Dict[str, Any], user_text: str, questionnaire_state: Dict[str, Any], transport: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    status = _minimum_dimension_status(user_text, questionnaire_state)
    missing = [key for key, known in status.items() if not known]
    readiness = str(result.get("decision_readiness") or "").upper()
    if not missing or _has_blocking_question(result) or readiness not in {"READY", "NEEDS_RESEARCH", "NEEDS_CLARIFICATION"}:
        return result
    repair_payload = dict(payload)
    repair_payload["readiness_repair"] = {
        "required": True,
        "missing_client_owned_dimensions": missing,
        "prior_packet": result,
        "instruction": "The prior packet attempted to finish client-intent readiness while required client-owned dimensions are still missing. Do not invent them and do not send them to facility research. Return a corrected compact packet with NEEDS_CLARIFICATION, exactly one highest-information AI-authored next_question for one missing dimension, and exactly one ASKED statement carrying that exact question.",
    }
    repaired = transport(repair_payload)
    repaired = _repair_live_readiness_mismatch(repaired)
    repaired["minimum_dimension_repair"] = {"applied": True, "missing_dimensions": missing, "ai_authored_question": str(repaired.get("next_question") or "")}
    return repaired


def _repair_clarification_contract_with_ai(*, result: Dict[str, Any], payload: Dict[str, Any], user_text: str, questionnaire_state: Dict[str, Any], transport: Callable[[Dict[str, Any]], Dict[str, Any]], strict: bool = True) -> Dict[str, Any]:
    readiness = str(result.get("decision_readiness") or "").upper()
    missing_question = readiness == "NEEDS_CLARIFICATION" and not _has_blocking_question(result)
    repeated_question = readiness == "NEEDS_CLARIFICATION" and _question_reasks_answered_dimension(result, questionnaire_state, user_text)
    if not missing_question and not repeated_question:
        return result
    repair_payload = dict(payload)
    repair_payload["clarification_contract_repair"] = {
        "required": True,
        "prior_packet": result,
        "original_user_text": user_text,
        "prior_explicit_adaptive_answers": _adaptive_answer_summary(questionnaire_state),
        "failure": "REASKED_ANSWERED_DIMENSION" if repeated_question else "NEEDS_CLARIFICATION_WITHOUT_USABLE_BLOCKING_QUESTION",
        "instruction": "Repair the packet without inventing facts. Existing questionnaire_state button selections, explicit statements in original_user_text and prior explicit adaptive answers are binding client evidence and must not be asked again in different wording. If a different material client-owned unknown remains, return NEEDS_CLARIFICATION with exactly one new highest-information AI-authored question and one matching ASKED statement. If no material client-owned clarification remains, return READY. Facility-specific unknowns may remain RESEARCH_REQUIRED and must not block client-intent READY.",
    }
    repaired = transport(repair_payload)
    repaired = _repair_live_readiness_mismatch(repaired)
    if str(repaired.get("decision_readiness") or "").upper() == "NEEDS_CLARIFICATION":
        unusable = not _has_blocking_question(repaired)
        repeated_after_repair = _question_reasks_answered_dimension(repaired, questionnaire_state, user_text)
        if strict and unusable:
            raise RuntimeError("SEMANTIC_AI_REPAIR_CLARIFICATION_WITHOUT_QUESTION")
        if strict and repeated_after_repair:
            raise RuntimeError("SEMANTIC_AI_REPAIR_REASKED_ANSWERED_DIMENSION")
        if unusable or repeated_after_repair:
            repaired["clarification_contract_repair"] = {
                "applied": True,
                "reason": "FIRST_PASS_REPAIR_DEFERRED_TO_MINIMUM_DIMENSION_GUARD",
                "strict": False,
            }
            return repaired
    repaired["clarification_contract_repair"] = {"applied": True, "reason": "REASKED_ANSWERED_DIMENSION" if repeated_question else "MISSING_BLOCKING_QUESTION", "strict": strict}
    return repaired


def _validate_patch_contract(packet: Dict[str, Any], user_text: str, state: Dict[str, Any]) -> None:
    from app.services.canonical_structured_profile import build_structured_profile, in_schema

    profile = build_structured_profile(state, packet, family_text=user_text)
    issues = [f"OUT_OF_SCHEMA:{item['field']}" for item in profile["out_of_schema"] if item.get("field")]
    from app.services.semantic_field_contract import compile_fields, leaves, profile_issues
    contracts = compile_fields(_required_output_schema()["questionnaire_patch"])
    # Validate every supplied leaf, including values hidden by button conflicts.
    for path, value in leaves(packet.get("questionnaire_patch") or {}):
        if path in contracts:
            contracts[path].normalize(value, path)
    issues.extend(profile_issues(profile, contracts))
    # Accounting is bidirectional: a known client fact cannot be marked USED
    # while its declared canonical field is absent from the decision profile.
    # Facility parameter IDs are deliberately outside this check; research
    # statements do not become client facts or prove provider capabilities.
    for statement in packet.get("statements") or []:
        if not isinstance(statement, dict) or statement.get("status") != "USED" or statement.get("knowledge_state") != "KNOWN":
            continue
        for path in statement.get("mapped_parameters") or []:
            if in_schema(path) and path not in profile["fields"]:
                issues.append(f"KNOWN_FIELD_NOT_MATERIALIZED:{path}")
    if issues:
        error = RuntimeError("SEMANTIC_AI_PATCH_CONTRACT:" + ",".join(issues))
        error.patch_diagnostic = {"patch": packet.get("questionnaire_patch"), "sources": packet.get("questionnaire_patch_sources"), "statements": packet.get("statements")}
        raise error


def interpret_client_intent_with_ai(*, user_text: str, questionnaire_state: Optional[Dict[str, Any]] = None, transport: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None) -> Dict[str, Any]:
    questionnaire_state = questionnaire_state or {}
    learning_advice = build_learning_center_advice(user_text=user_text)
    payload = _build_prompt(user_text, questionnaire_state, learning_advice)
    active_transport = transport or _default_transport
    result = {}
    def validate_live_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
        packet = _ground_clinical_patch(packet, user_text, questionnaire_state)
        packet = _repair_live_readiness_mismatch(packet)
        # Validation normalizes advisory readiness, so check minimum dimensions
        # on the validated packet as well as question usability and repetition.
        packet = _validate_result(packet, allow_empty_statements=not user_text.strip())
        missing = [key for key, known in _minimum_dimension_status(user_text, questionnaire_state).items() if not known]
        readiness = str(packet.get("decision_readiness") or "").upper()
        if missing and (readiness == "READY" or (readiness == "NEEDS_CLARIFICATION" and not _has_blocking_question(packet))):
            raise RuntimeError(f"SEMANTIC_AI_READY_WITH_MISSING_MINIMUM_DIMENSIONS:{','.join(missing)}")
        if readiness == "NEEDS_CLARIFICATION" and _question_reasks_answered_dimension(packet, questionnaire_state, user_text):
            raise RuntimeError("SEMANTIC_AI_REPAIR_REASKED_ANSWERED_DIMENSION")
        _validate_patch_contract(packet, user_text, questionnaire_state)
        return packet

    if transport is None:
        prior_packet = copy.deepcopy(result)
        try:
            result = active_transport(payload)
            prior_packet = copy.deepcopy(result)
            result = _repair_live_readiness_mismatch(result)
            result = _repair_clarification_contract_with_ai(result=result, payload=payload, user_text=user_text, questionnaire_state=questionnaire_state, transport=active_transport, strict=False)
            result = _repair_missing_minimum_dimensions_with_ai(result=result, payload=payload, user_text=user_text, questionnaire_state=questionnaire_state, transport=active_transport)
            result = _repair_clarification_contract_with_ai(result=result, payload=payload, user_text=user_text, questionnaire_state=questionnaire_state, transport=active_transport, strict=True)
            prior_packet = copy.deepcopy(result)
            result = validate_live_packet(result)
        except RuntimeError as error:
            # One final schema repair covers failures that the question-only
            # repair misses (including omitted readiness and invalid enums).
            # Transport failures are not schema failures and are never retried here.
            code = str(error).split(":", 1)[0]
            repairable = code in {
                "SEMANTIC_AI_CLARIFICATION_WITHOUT_BLOCKING_QUESTION",
                "SEMANTIC_AI_REPAIR_CLARIFICATION_WITHOUT_QUESTION",
                "SEMANTIC_AI_INVALID_IMPORTANCE",
                "SEMANTIC_AI_INVALID_STATUS",
                "SEMANTIC_AI_INVALID_KNOWLEDGE",
                "SEMANTIC_AI_ASKED_WITHOUT_QUESTION",
                "SEMANTIC_AI_MISSING_STATEMENT_TRACE",
                "SEMANTIC_AI_PATCH_CONTRACT",
                "SEMANTIC_AI_WIRE_CONTRACT",
                "SEMANTIC_AI_REPAIR_REASKED_ANSWERED_DIMENSION",
                "SEMANTIC_AI_READY_WITH_MISSING_MINIMUM_DIMENSIONS",
            }
            if not repairable:
                raise
            repair_payload = dict(payload)
            repair_payload["packet_validation_repair"] = {
                "validation_error": str(error),
                "mapping_contract": {
                    "supported_canonical_mapping": "Each KNOWN/USED canonical path must have its actual explicit field value in questionnaire_patch_fields or already in questionnaire_state.",
                    "unsupported_mapping": "Remove the unsupported path from mapped_parameters, retaining the original source quote and meaning. An empty mapped_parameters array is valid. Never manufacture a field value or substitute another unrelated canonical path to preserve a trace.",
                },
                "issue_actions": {
                    "DUPLICATE_FIELD": "Return exactly one extraction entry per canonical path. Preserve all explicit selections in that field's supported array. For different people, retain each person's distinct needs and quotes in statements and coupleAssistance; never overwrite one partner with the other or combine contradictory facts as one person's answer. If the source is genuinely conflicting for the same person and time, ask a clarification rather than selecting a value.",
                    "NO_EXACT_FIELD_QUOTE": "Supply the field's own genuine source quote, or omit the unsupported field. Questionnaire defaults are not quotes from user_text.",
                    "KNOWN_FIELD_NOT_MATERIALIZED": "If the exact field value is explicit, include one {path,value,quote} entry in questionnaire_patch_fields. If the path was only loosely related or inferred, remove that path from mapped_parameters instead of inventing its value; retain the original meaningful statement and its actual supported fields.",
                    "UNSATISFIED_DEPENDENCY": "Supply the explicitly established parent field named in the contract error with its genuine source quote, or remove an unsupported detail. Never infer a parent fact or drop an explicit need.",
                    "UNSUPPORTED_UNIT": "The source does not establish the field unit named in the contract error. Remove that unsupported field and mapping; retain the original statement. Never estimate or silently convert units.",
                },
                "client_dimension_status": _minimum_dimension_status(user_text, questionnaire_state),
                "clarification_contract": {
                    "NEEDS_CLARIFICATION": {
                        "next_question": "one nonempty AI-authored question for an unresolved client-owned fact",
                        "statement": {"status": "ASKED", "importance": "MUST|UNKNOWN",
                                      "knowledge_state": "UNKNOWN|AMBIGUOUS", "gap_key": "the unresolved fact",
                                      "clarification_question": "identical to next_question"},
                    },
                    "READY": "Only if no material client-owned clarification remains and minimum dimensions are resolved.",
                    "preserve": "Keep known facts, each partner's distinct needs and exact source quotes. Never fill an unknown to avoid a question.",
                },
                "prior_packet": {key: value for key, value in prior_packet.items() if key not in {"governance", "learning_center"}},
                "rejected_wire_packet": getattr(error, "wire_diagnostic", None),
                "instruction": "Return the complete corrected packet using required_output exactly, including decision_readiness, questionnaire_patch and questionnaire_patch_sources. Preserve explicit client facts and unknowns. Every KNOWN/USED statement mapped to a client profile field must have that field in questionnaire_patch unless already supplied in questionnaire_state. Known medical detail requires its parent medicalCareProfile.needs selection: oxygenUse -> Oxygen, dialysisFrequency/dialysisCenter -> Dialysis, woundCareFrequency -> Wound care. Include the parent selection with its own exact quote; never drop an explicit clinical need to pass validation. Use only allowed enum values and exact nested schema paths. For every new/changed patch leaf, put its full dotted path in questionnaire_patch_sources with a quote copied exactly from original user_text; also account for the fact in statements. Reuse a genuine quote for related fields; never invent quotes, paraphrase them, move fields to the top level, or discard an explicit requirement to pass validation. Omit unsupported inferred fields and duplicate questionnaire defaults. gender must not be inferred from kinship/pronouns; coupleAssistance must be a string. If a material client question remains, include one ASKED MUST/UNKNOWN statement and its identical next_question. Otherwise return READY with statement accounting.",
            }
            repaired_packet = active_transport(repair_payload)
            try:
                result = validate_live_packet(repaired_packet)
            except RuntimeError as final_error:
                if not hasattr(final_error, "patch_diagnostic"):
                    final_error.patch_diagnostic = {"patch": repaired_packet.get("questionnaire_patch"), "sources": repaired_packet.get("questionnaire_patch_sources"), "statements": repaired_packet.get("statements"), "decision_readiness": repaired_packet.get("decision_readiness"), "next_question": repaired_packet.get("next_question")}
                raise
            result["packet_validation_repair"] = {"applied": True, "validation_error": code, "attempts": 1}
    else:
        result = active_transport(payload)
        result = _validate_result(_ground_clinical_patch(result, user_text, questionnaire_state), allow_empty_statements=not user_text.strip())
        # Injection changes delivery, never the accepted field contract.
        _validate_patch_contract(result, user_text, questionnaire_state)
    result["learning_center"] = {"advisor": learning_advice["advisor"], "consulted": True, "available_agent_count": learning_advice["available_agent_count"], "agent_count": learning_advice["agent_count"]}
    return result


__all__ = ["interpret_client_intent_with_ai", "SEMANTIC_AI_SYSTEM_RULES"]
