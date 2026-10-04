"""Observe original questionnaire answers without interpreting or ranking them.

A canonical copy proves preservation, not decision use. A quoted semantic trace
proves interpretation, not a ranking effect. Only an explicit downstream source
reference proves a link to a deterministic need. Keep these claims separate.
"""
from collections import Counter
from typing import Any


# Transport/interview bookkeeping is not a family answer. Unknown new fields are
# intentionally included so a new question cannot disappear from this contract.
_METADATA_ROOTS = {"questionnaireCompletion"}


def _answers(value: dict, prefix: str = ""):
    for key, child in value.items():
        if not prefix and key in _METADATA_ROOTS:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            yield from _answers(child, path)
        elif isinstance(child, list):
            # Keep source identity for each selection; matching the parent path
            # alone cannot prove that every activity/clinical answer was handled.
            for index, selected in enumerate(child):
                if isinstance(selected, dict):
                    yield from _answers(selected, f"{path}[{index}]")
                elif selected is not None and selected != "":
                    yield path, index, selected
        elif child is not None and child != "":
            yield path, None, child


def _at(value: dict, path: str):
    import re
    current: Any = value
    for token in re.findall(r"[^.\[\]]+", path):
        if isinstance(current, dict):
            current = current.get(token)
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return None
    return current


def _source_path(value: Any) -> str:
    path = str(value or "")
    return path.removeprefix("questionnaire.")


def build_questionnaire_answer_accounting(questionnaire: dict, result: dict) -> dict:
    decision = result.get("decision_intelligence") or {}
    human = decision.get("human_intelligence") or {}
    profile = result.get("patient_needs_profile") or {}
    canonical = profile.get("canonical_decision_questionnaire") or human.get("canonical_decision_questionnaire") or {}
    semantic = (human.get("semantic_ai") or {}).get("result") or {}
    strict = (semantic.get("wire_contract") or {}).get("schema_constrained") is True
    statements = semantic.get("statements") or [] if strict else []
    rows = []
    # Only a decisive final-comparator explanation establishes a ranking effect.
    # Source records are created where the actual questionnaire inputs are read.
    from app.services.regulatory_quality_layer import explain_ranked_pair
    ranked = result.get("results") or []
    ranking_sources = []
    for higher, lower in zip(ranked, ranked[1:]):
        snapshot = higher.get("__rank_comparison_trace") or {}
        dimensions = snapshot.get("base_dimensions")
        comparison = explain_ranked_pair(higher, lower, dimensions) if dimensions else None
        if not comparison:
            continue
        dimension = comparison["decision_dimension"]
        for candidate in (higher, lower):
            fit = candidate.get("nearby_place_fit") or {}
            if fit.get("status") != "KNOWN":
                continue
            for source in candidate.get("__ranking_answer_sources") or []:
                if dimension in source.get("dimensions", []):
                    ranking_sources.append({**source, "decision_dimension": dimension})
    for path, selection_index, answer in _answers(questionnaire):
        canonical_value = _at(canonical, path)
        # bool/int equality in Python is unsuitable for evidence identity.
        def same(left, right):
            return type(left) is type(right) and left == right
        preserved = (
            any(same(answer, item) for item in canonical_value)
            if selection_index is not None and isinstance(canonical_value, list)
            else same(answer, canonical_value)
        )
        traces = []
        for index, statement in enumerate(statements):
            if not isinstance(statement, dict):
                continue
            mapped = [_source_path(p) for p in statement.get("mapped_parameters") or []]
            if path not in mapped or str(statement.get("raw_text") or "").strip() != str(answer).strip():
                continue
            traces.append({"statement_index": index, "status": statement.get("status"),
                           "role": statement.get("importance"), "knowledge_state": statement.get("knowledge_state")})
        # A grouped list source cannot prove which selection produced a need.
        # Preserve that uncertainty instead of crediting every item in the list.
        needs = [str(need.get("parameter_id")) for need in profile.get("needs") or []
                 if selection_index is None and preserved and isinstance(need, dict)
                 and _source_path(need.get("user_evidence_source")) == path]
        effects = sorted({source["decision_dimension"] for source in ranking_sources
                          if source.get("answer_path") == path
                          and source.get("selection_index") == selection_index
                          and same(source.get("answer"), answer)}) if preserved else []
        control_diagnostics = [item["status"] for item in (decision.get("client_intent") or {}).get("unrecognized_controls", [])
                               if item.get("answer_path") == path and same(item.get("answer"), answer)]
        intent = decision.get("client_intent") or {}
        active_keys = {item.get("key") for item in (intent.get("must_haves") or []) + (intent.get("nice_to_haves") or [])}
        intent_keys = sorted({source["intent_key"] for source in intent.get("answer_source_links") or []
                             if source.get("intent_key") in active_keys and source.get("answer_path") == path
                             and source.get("selection_index") == selection_index
                             and same(source.get("answer"), answer)}) if preserved else []
        status = "RANKING_EFFECT_TRACED" if effects else "NEED_LINKED" if needs else "INTENT_LINKED" if intent_keys else "SOURCE_TRACED" if traces else "PRESERVED_NOT_TRACED" if preserved else "UNACCOUNTED"
        rows.append({"answer_path": path, "selection_index": selection_index, "answer": answer,
                     "canonical_preserved": preserved, "semantic_traces": traces,
                     "need_parameter_ids": needs, "ranking_effect_dimensions": effects,
                     "intent_keys": intent_keys,
                     "control_diagnostics": control_diagnostics, "status": status})
    counts = Counter(row["status"] for row in rows)
    return {"version": "questionnaire-answer-accounting-v1", "answers": rows,
            "answer_count": len(rows), "status_counts": dict(sorted(counts.items())),
            "canonical_preserved_count": sum(row["canonical_preserved"] for row in rows),
            "unaccounted_count": counts["UNACCOUNTED"],
            "untraced_count": counts["UNACCOUNTED"] + counts["PRESERVED_NOT_TRACED"],
            "strict_semantic_trace_authority": strict,
            "contract": "PRESERVATION_IS_NOT_USE;QUOTED_INTERPRETATION_IS_NOT_RANK_EFFECT;NO_SOURCE_LINK_NO_USAGE_CLAIM",
            "effect": "OBSERVATION_ONLY_NO_RANKING_READINESS_OR_ELIGIBILITY_CHANGE"}


def attach_questionnaire_answer_accounting(result: dict, questionnaire: dict) -> dict:
    accounting = build_questionnaire_answer_accounting(questionnaire, result)
    result["questionnaire_answer_accounting"] = accounting
    result.setdefault("recommendation_audit_trace", {})["questionnaire_answer_accounting"] = accounting
    return result
