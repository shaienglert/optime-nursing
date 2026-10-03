import os
from unittest.mock import patch

import pytest

from app.main import validate_ai_authority_configuration


def test_required_ai_component_cannot_run_with_semantic_ai_disabled():
    with patch.dict(os.environ, {
        "OPTIME_SEMANTIC_AI_ENABLED": "0",
        "OPTIME_AI_PROCESS_OWNER_REQUIRED": "1",
    }, clear=False):
        with pytest.raises(RuntimeError, match="AI_PROCESS_OWNER_REQUIRED"):
            validate_ai_authority_configuration()


def test_optional_ai_configuration_may_remain_disabled():
    with patch.dict(os.environ, {
        "OPTIME_SEMANTIC_AI_ENABLED": "0",
        "OPTIME_SEMANTIC_AI_REQUIRED": "0",
        "OPTIME_AI_PROCESS_OWNER_REQUIRED": "0",
        "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
        "OPTIME_AI_PREFERENCE_VERIFICATION_REQUIRED": "0",
    }, clear=False):
        validate_ai_authority_configuration()
