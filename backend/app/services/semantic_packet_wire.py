"""One schema-constrained wire format for extraction and every repair.

Values, paths, quotes and questions are AI-authored. Normalization only reconstructs
existing packet keys; it does not infer facts, invent questions or decide finality.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, TypeAdapter, ValidationError, create_model

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


def _leaves(obj, prefix=""):
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from _leaves(value, path)
        else:
            yield path, value


@lru_cache(maxsize=1)
def _model(declarations_json):
    declarations = json.loads(declarations_json)
    # One structural slot per existing field prevents competing entries from
    # overwriting each other. Null means no new extraction, never a default fact.
    entries = {}
    slots = {}
    for n, (path, declaration) in enumerate(_leaves(declarations)):
        # Constrain representation at generation time instead of letting the
        # provider choose an invalid value kind and spending another live call
        # on repair. These are existing encodings, not new enum authority.
        kind = "Selections" if path == "assistanceLevel" else "List" if isinstance(declaration, list) else "Integer" if declaration == "positive monthly integer" else "Months" if declaration == "explicit number of months" else "Text"
        types = {"Selections": Union[StrictStr, list[StrictStr]], "List": list[StrictStr],
                 "Integer": StrictInt, "Months": Union[StrictStr, StrictInt], "Text": StrictStr}
        if kind not in entries:
            entries[kind] = create_model("Quoted" + kind, __config__=CONFIG,
                value=(types[kind], ...), quote=(StrictStr, ...))
        slots[path] = (Union[entries[kind], None], Field(..., alias=f"f{n}", description=path))
    fields = create_model("PatchFields", __config__=CONFIG,
        **slots)
    return create_model("SemanticExtraction", __config__=CONFIG,
        wire_version=(Literal[WIRE_VERSION], ...),
        facts=(list[StrictStr], ...), preferences=(list[StrictStr], ...),
        constraints=(list[StrictStr], ...), concerns=(list[StrictStr], ...),
        implications=(list[Implication], ...), statements=(list[Trace], ...),
        research_requests=(list[StrictStr], ...),
        questionnaire_patch_fields=(fields, ...),
        interview=(Union[NoClientQuestion, ClientQuestion], ...))


def _key(required_output):
    return json.dumps(required_output["questionnaire_patch"], sort_keys=True)


def provider_schema(required_output):
    schema = _model(_key(required_output)).model_json_schema()

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
    return schema


def normalize_wire(packet: Any, required_output: dict) -> dict:
    try:
        wire = _model(_key(required_output)).model_validate(packet)
    except ValidationError as exc:
        raise RuntimeError("SEMANTIC_AI_WIRE_CONTRACT:" + json.dumps(exc.errors(include_input=False), default=str)[:1000]) from exc
    result = wire.model_dump(exclude={"wire_version", "questionnaire_patch_fields", "interview"})
    patch, sources = {}, {}
    declarations = dict(_leaves(required_output["questionnaire_patch"]))
    for path, entry in wire.questionnaire_patch_fields.model_dump().items():
        if entry is None:
            continue
        value, quote = entry["value"], entry["quote"]
        if not quote.strip():
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:EMPTY_QUOTE:{path}")
        declaration = declarations[path]
        # Prompt enum examples are advisory, not the canonical schema's value
        # authority. Preserve established manual encodings instead of inventing
        # a stricter value vocabulary at the transport boundary.
        if path == "assistanceLevel":
            value_type = Union[StrictStr, list[StrictStr]]
        elif isinstance(declaration, list):
            value_type = list[StrictStr]
        elif declaration == "positive monthly integer":
            value_type = StrictInt
        else:
            value_type = StrictStr
            if declaration == "explicit number of months" and isinstance(value, int):
                value = str(value)  # Encoding only; no conversion of weeks to months.
        try:
            value = TypeAdapter(value_type).validate_python(value, strict=True)
        except ValidationError as exc:
            raise RuntimeError(f"SEMANTIC_AI_WIRE_CONTRACT:INVALID_FIELD_VALUE:{path}") from exc
        if path == "assistanceLevel" and isinstance(value, list):
            if not value:
                raise RuntimeError("SEMANTIC_AI_WIRE_CONTRACT:EMPTY_ASSISTANCE_SELECTIONS")
            value = ", ".join(value)
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
