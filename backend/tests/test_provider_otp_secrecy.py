from pathlib import Path


def test_provider_otp_is_not_exposed_by_default():
    text = Path("backend/app/services/provider_identity.py").read_text(encoding="utf-8")
    assert 'OOMNIK_EXPOSE_DEBUG_VERIFICATION_CODE' in text
    assert 'result["debug_verification_code"] = code' in text
    assert '"debug_verification_code": code' not in text
