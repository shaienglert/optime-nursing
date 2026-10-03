from __future__ import annotations

import os
import json
import unittest
from unittest.mock import MagicMock, patch

from app.services.semantic_intent_ai import _default_transport, _resolve_temperature, _required_output_schema
from app.services.semantic_packet_wire import provider_schema

_BASE_ENV = {
    "OPTIME_SEMANTIC_AI_URL": "https://example.test/v1/chat/completions",
    "OPTIME_SEMANTIC_AI_MODEL": "test-model",
}


def _mock_response(body: dict):
    wire = json.dumps({"wire_version": "semantic-extraction-v1", "facts": [],
        "preferences": [], "constraints": [], "concerns": [], "implications": [],
        "statements": [], "research_requests": [], "questionnaire_patch_fields": [],
        "interview": {"readiness": "READY", "next_question": None, "blocking_statement": None}})
    if "choices" in body:
        body["choices"][0]["message"]["content"] = wire
    elif "output_text" in body:
        body["output_text"] = wire
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = body
    return resp


class ResolveTemperatureTests(unittest.TestCase):
    def test_defaults_to_zero_when_unset(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPTIME_SEMANTIC_AI_TEMPERATURE", None)
            self.assertEqual(_resolve_temperature(), 0.0)

    def test_reads_a_configured_value(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_TEMPERATURE": "0.3"}, clear=False):
            self.assertEqual(_resolve_temperature(), 0.3)

    def test_literal_unset_omits_the_parameter(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_TEMPERATURE": "unset"}, clear=False):
            self.assertIsNone(_resolve_temperature())

    def test_literal_unset_is_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_TEMPERATURE": "UNSET"}, clear=False):
            self.assertIsNone(_resolve_temperature())

    def test_garbage_value_falls_back_to_zero_rather_than_crashing(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_TEMPERATURE": "not-a-number"}, clear=False):
            self.assertEqual(_resolve_temperature(), 0.0)


class DefaultTransportTemperatureTests(unittest.TestCase):
    def test_caller_answers_survive_wire_generation_without_narrative_repetition(self) -> None:
        with patch.dict(os.environ, _BASE_ENV, clear=False):
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"choices": [{"message": {"content": "{}"}}]})
                _default_transport({"user_text": "We are looking in Las Vegas, Nevada.",
                    "questionnaire_state": {"budget": 6000, "referenceLocationValue": "Las Vegas, Nevada",
                        "memoryStatus": "Not sure", "assistanceLevel": "Light assistance"},
                    "client_evidence": {"resolved_questionnaire_fields": {"budget": 9000}},
                    "required_output": _required_output_schema(),
                    "field_trace_example": {"budget": 4500},
                    "clarification_trace_example": {"next_question": "Example question"}})
        request = mock_post.call_args.kwargs["json"]
        payload = json.loads(request["messages"][1]["content"])
        evidence = payload["client_evidence"]
        self.assertEqual(evidence["resolved_questionnaire_fields"], {
            "budget": 6000, "referenceLocationValue": "Las Vegas, Nevada"})
        self.assertEqual(evidence["minimum_dimensions"], {
            "market_location": True, "monthly_affordability": True})
        self.assertNotIn("required_output", payload)
        self.assertNotIn("field_trace_example", payload)
        self.assertNotIn("clarification_trace_example", payload)
        self.assertEqual(request["response_format"]["json_schema"]["schema"],
            provider_schema(_required_output_schema(), family_text=payload["user_text"], questionnaire_state=payload["questionnaire_state"]))

    def test_existing_read_only_answers_have_their_own_source_paths(self) -> None:
        from app.services.semantic_intent_ai import _client_evidence_context
        state = {"distanceFromFamily": "Balanced location", "otherInterests": ["Star watching"],
                 "memoryStatus": "Not sure", "__guardian": {"instruction": "Not client evidence"}}
        evidence = _client_evidence_context("", state)["resolved_questionnaire_fields"]
        self.assertEqual(evidence, {"distanceFromFamily": "Balanced location", "otherInterests": ["Star watching"]})
        self.assertNotIn("locationImportant", evidence)
        self.assertNotIn("distanceFromFamily", _required_output_schema()["questionnaire_patch"])

    def test_chat_completions_request_includes_temperature_zero_by_default(self) -> None:
        with patch.dict(os.environ, _BASE_ENV, clear=False):
            os.environ.pop("OPTIME_SEMANTIC_AI_TEMPERATURE", None)
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"choices": [{"message": {"content": "{}"}}]})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_json["temperature"], 0.0)
        self.assertEqual(sent_json["response_format"]["type"], "json_schema")
        self.assertTrue(sent_json["response_format"]["json_schema"]["strict"])

    def test_responses_api_request_also_includes_temperature(self) -> None:
        env = dict(_BASE_ENV, OPTIME_SEMANTIC_AI_URL="https://example.test/v1/responses")
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("OPTIME_SEMANTIC_AI_TEMPERATURE", None)
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"output_text": "{}"})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_json["temperature"], 0.0)
        self.assertEqual(sent_json["text"]["format"]["type"], "json_schema")
        self.assertTrue(sent_json["text"]["format"]["strict"])

    def test_configured_temperature_is_forwarded(self) -> None:
        env = dict(_BASE_ENV, OPTIME_SEMANTIC_AI_TEMPERATURE="0.25")
        with patch.dict(os.environ, env, clear=False):
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"choices": [{"message": {"content": "{}"}}]})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_json["temperature"], 0.25)

    def test_unset_sentinel_omits_temperature_from_the_request(self) -> None:
        env = dict(_BASE_ENV, OPTIME_SEMANTIC_AI_TEMPERATURE="unset")
        with patch.dict(os.environ, env, clear=False):
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"choices": [{"message": {"content": "{}"}}]})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertNotIn("temperature", sent_json)


if __name__ == "__main__":
    unittest.main()
