from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.semantic_intent_ai import _default_transport, _resolve_temperature

_BASE_ENV = {
    "OPTIME_SEMANTIC_AI_URL": "https://example.test/v1/chat/completions",
    "OPTIME_SEMANTIC_AI_MODEL": "test-model",
}


def _mock_response(body: dict):
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
    def test_chat_completions_request_includes_temperature_zero_by_default(self) -> None:
        with patch.dict(os.environ, _BASE_ENV, clear=False):
            os.environ.pop("OPTIME_SEMANTIC_AI_TEMPERATURE", None)
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"choices": [{"message": {"content": "{}"}}]})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_json["temperature"], 0.0)

    def test_responses_api_request_also_includes_temperature(self) -> None:
        env = dict(_BASE_ENV, OPTIME_SEMANTIC_AI_URL="https://example.test/v1/responses")
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("OPTIME_SEMANTIC_AI_TEMPERATURE", None)
            with patch("app.services.semantic_intent_ai.requests.post") as mock_post:
                mock_post.return_value = _mock_response({"output_text": "{}"})
                _default_transport({"user_text": "hello"})
        sent_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_json["temperature"], 0.0)

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
