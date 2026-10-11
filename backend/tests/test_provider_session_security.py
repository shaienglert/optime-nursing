import os
from unittest.mock import patch

import pytest

from app.services.provider_identity import issue_provider_access_token, provider_session_user_id, verify_provider_access_token


def test_provider_session_is_bound_to_facility_and_user():
    with patch.dict(os.environ, {"OOMNIK_PROVIDER_SESSION_SECRET": "test-secret-only"}, clear=False):
        token = issue_provider_access_token(12, 34)
        assert provider_session_user_id(token, 12) == 34
        verify_provider_access_token(token, 12, 34)
        with pytest.raises(PermissionError):
            verify_provider_access_token(token, 12, 35)
        with pytest.raises(PermissionError):
            provider_session_user_id(token, 13)


def test_provider_session_rejects_tampering():
    with patch.dict(os.environ, {"OOMNIK_PROVIDER_SESSION_SECRET": "test-secret-only"}, clear=False):
        token = issue_provider_access_token(12, 34)
        body, signature = token.split(".", 1)
        with pytest.raises(PermissionError):
            provider_session_user_id(body + "." + ("0" * len(signature)), 12)
