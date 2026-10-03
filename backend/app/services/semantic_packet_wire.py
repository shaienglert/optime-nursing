"""One schema-constrained wire format for extraction and every repair.

Values, paths, quotes and questions are AI-authored. Normalization only reconstructs
existing packet keys; it does not infer facts, invent questions or decide finality.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, StrictStr, ValidationError, create_model

from app.services.semantic_field_contract import compile_fields, leaves as _leaves

WIRE_VERSION = "semantic-extraction-v1"
CONFIG = ConfigDict(extra="forbid", strict=True)


class Trace(BaseModel):
    model_config = CONFIG
    raw_text: StrictStr
    meaning: StrictStr
    importance: Literal["MUST", "NICE", "CONTEXT", "UNKNOWN"]
    knowledge_state: Literal["KNOWN", "UNKNOWN", "AMBIGUOUS"]
    status: Literal["USED", "RESEARCH_REQUIRED", "NOT_DECISION_RELEVANT"]
    gap_key: StrictStr | None
    mapped_parameters: list[StrictStr]
    research_task: StrictStr | None


class QuestionTrace(BaseModel):
    model_config = CONFIG
    raw_text: StrictStr
    meaning: StrictStr
    importance: Literal["MUST", "UNKNOWN"]
    knowledge_state: Literal["UNKNOWN", "AMBIGUOUS"]
    gap_key: StrictStr
    mapped_parameters: list[StrictStr]


class NoClientQuestion(BaseModel):
    model_config = CONFIG
    readiness: Literal["READY", "NEEDS_RESEARCH"]
    next_question: None
    blocking_statement: None


class ClientQuestion(BaseModel):
    model_config = CONFIG
    readiness: Literal["NEEDS_CLARIFICATION"]
    next_question: StrictStr
    blocking_statement: QuestionTrace


class Implication(BaseModel):
    model_config = CONFIG
    derived_from: list[StrictStr]
    implication: StrictStr
    certainty: Literal["POSSIBLE", "LIKELY", "CONFIRMED"]
    requires_confirmation: bool


def _model(declarations_json):
    declarations = json.loads(declarations_json)
    # Sparse, full canonical paths avoid opaque aliases and mandatory empty
    # slots. Group by existing representation, not by clinical interpretation.
    groups = {}
    contracts = compile_fields(declarations)
    for path, contract in contracts.items():
        groups.setdefault((contract.kind, contract.unit, contract.positive), []).append(path)
    entries = [create_model("Quoted" + kind + (unit or "") + ("Positive" if positive else ""), __config__=CONFIG,
        path=(Literal[tuple(paths)], ...), value=(contracts[paths[0]].value_type, ...), quote=(StrictStr, ...))
        for (kind, unit, positive), paths in groups.items()]
    return create_model("SemanticExtraction", __config__=CONFIG,
        wire_version=(Literal[WIRE_VERSION], ...),
        facts=(list[StrictStr], ...), preferences=(list[StrictStr], ...),
        constraints=(list[StrictStr], ...), concerns=(list[StrictStr], ...),
        implications=(list[Implication], ...), statements=(list[Trace], ...),
        research_requests=(list[StrictStr], ...),
        questionnaire_patch_fields=(list[Union[tuple(entries)]], ...),
        interview=(Union[NoClientQuestion, ClientQuestion], ...))


def _key(required_output):
    return json.dumps(required_output["questionnaire_patch"], sort_keys=True)


def provider_schema(required_output, *, family_text: str | None = None):
    schema = _model(_key(required_output)).model_json_schema()

    # Without narrative there is no legal exact source quote for a new field.
    # Existing buttons remain in the caller's profile and statement accounting;
    # do not invite the provider to copy them into ungrounded extraction entries.
    if family_text is not None and not family_text.strip():
        schema["properties"]["questionnaire_patch_fields"]["maxItems"] = 0

    def portable(value):
        if isinstance(value, dict):
            value.pop("title", None)
            if "const" in value:
                value["enum"] = [value.pop("const")]
            for child in value.values():
                portable(child)
        elif isinstance(value, list):
            for child in value:
                portable(child)
    portable(schema)
    contracts = compile_fields(required_output["questionnaire_patch"])
    for definition in schema["$defs"].values():
        properties = definition.get("properties", {})
        if "quote" in properties and contracts[properties["path"]["enum"][0]].positive:
            properties["value"]["minimum"] = 1
    if family_text and family_text.strip():
        # Grammar chooses source spans; it does not interpret their meaning.
        # The complete narrative remains available when a fact spans sentences.
        quotes = list(dict.fromkeys([family_text.strip(), *[
            part.strip() for part in re.split(r"[\n;]|(?<=[.!?])\s+", family_text)
            if part.strip()]]))
        schema["$defs"]["SourceQuote"] = {"type": "string", "enum": quotes}
        excluded = set()
        for name, definition in list(schema["$defs"].items()):
            properties = definition.get("properties", {})
            if "quote" not in properties:
                continue
            paths = properties["path"]["enum"]
            contract = contracts[paths[0]]
            eligible = [quote for quote in quotes if contract.accepts_quote(quote)]
            if not eligible:
                excluded.add("#/$defs/" + name)
                del schema["$defs"][name]
                continue
            properties["quote"] = {"type": "string", "enum": eligible} if contract.unit else {"$ref": "#/$defs/SourceQuote"}
        alternatives = schema["properties"]["questionnaire_patch_fields"]["items"]["anyOf"]
        alternatives[:] = [item for item in alternatives if item.get("$ref") not in excluded]
    return schema


def normalize_wire(packet: Any, required_output: dict, *, family_text: str | None = None) -> dict:
    try:
        wire = _model(_key(required_output)).model_validate(packet)
    except ValidationError as exc:
        raise RuntimeError("SEMANTIC_AI_WIRE_CONTRACT:" + json.dumps(exc.errors(include_input=False), default=str)[:1000]) from exc
    result = wire.model_dump(exclude={"wire_version", "questionnaire_patch_fields", "interview"})
    patch, sources = {}, {}
    contracts = compile_fields(required_output["questionnaire_patch"])
    for field in wire.questionnaire_patch_fields:
        entry = field.model_dump()
        path = entry["path"]
        if path in sources:
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:DUPLICATE_FIELD:{path}")
        value, quote = entry["value"], entry["quote"]
        if not quote.strip():
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:EMPTY_QUOTE:{path}")
        value = contracts[path].normalize(value, path)
        if family_text is not None:
            if quote not in family_text:
                raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:NO_EXACT_FIELD_QUOTE:{path}")
            if not contracts[path].accepts_quote(quote):
                raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:UNSUPPORTED_UNIT:{path}:{contracts[path].unit}")
        sources[path] = quote  # Copy the model's mandatory source; never manufacture it.
        target = patch
        parts = path.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    result["questionnaire_patch"] = patch
    result["questionnaire_patch_sources"] = sources
    result["decision_readiness"] = wire.interview.readiness
    result["next_question"] = wire.interview.next_question
    if isinstance(wire.interview, ClientQuestion):
        if not wire.interview.next_question.strip() or not wire.interview.blocking_statement.gap_key.strip():
            raise RuntimeError("SEMANTIC_AI_WIRE_CONTRACT:EMPTY_CLIENT_QUESTION")
        trace = wire.interview.blocking_statement.model_dump()
        trace.update(status="ASKED", clarification_question=wire.interview.next_question, research_task=None)
        result["statements"].append(trace)
    result["wire_contract"] = {"version": WIRE_VERSION, "schema_constrained": True}
    return result


def parse_wire_json(content: str) -> dict:
    def unique_members(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:DUPLICATE_MEMBER:{key}")
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=unique_members)
