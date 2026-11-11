"""Provider IDs and roles in a request body are attribution, never credentials."""
from unittest.mock import Mock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import main


PROTECTED_ROUTES = [
    (method, route.path)
    for route in main.app.routes
    if isinstance(route, APIRoute) and route.path.startswith("/provider/")
    for method in route.methods
    if (
        method in {"POST", "PUT", "PATCH", "DELETE"}
        and route.path != "/provider/identity/access-check"
    ) or route.path.endswith(("/profile", "/completeness"))
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPTIME_ADMIN_TOKEN", "provider-management-test-token")
    # No application lifespan: these tests must not start schedulers or imports.
    return TestClient(main.app)


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
@pytest.mark.parametrize("credential", [None, "wrong-token", "unconfigured"])
def test_every_provider_management_route_denies_before_database_access(
    client, monkeypatch, method, path, credential
):
    database = Mock(side_effect=AssertionError("unauthorized database access"))
    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[main.get_db] = database
    if credential == "unconfigured":
        monkeypatch.delenv("OPTIME_ADMIN_TOKEN")
        credential = "provider-management-test-token"
    try:
        path = path.format(facility_id=1, audit_id=1, photo_id=1)
        headers = {"X-Admin-Token": credential} if credential else {}
        response = client.request(method, path, json={"user_id": 1}, headers=headers)
        assert response.status_code == 401
        database.assert_not_called()
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)


def test_admin_can_reach_provider_service(client, monkeypatch):
    sentinel = object()
    service = Mock(side_effect=ValueError("authorized service reached"))
    monkeypatch.setattr(main, "apply_facility_field_update", service)
    previous = main.app.dependency_overrides.copy()
    main.app.dependency_overrides[main.get_db] = lambda: sentinel
    try:
        response = client.post(
            "/provider/facilities/1/identity/field-update",
            headers={"X-Admin-Token": "provider-management-test-token"},
            json={"user_id": 1, "field_name": "name", "new_value": "Example", "category": "ADMIN"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "authorized service reached"
        assert service.call_args.kwargs["db"] is sentinel
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)


def test_registration_and_invitation_response_never_serializes_otp():
    payload = main.IdentityRegistrationStartOut(
        facility_id=1, user_id=1, email="staff@example.org",
        verification_sent_at="2026-11-03T00:00:00", verification_method="EMAIL_OTP",
        debug_verification_code="123456",
    )
    assert "debug_verification_code" not in payload.model_dump()
    assert "123456" not in payload.model_dump_json()
    assert "debug_verification_code" not in main.IdentityRegistrationStartOut.model_json_schema()["properties"]


@pytest.mark.parametrize("action,service_name,extra", [
    ("register/start", "start_email_verification", {}),
    ("staff/invite", "invite_staff_member", {"inviter_user_id": 1}),
])
def test_identity_http_responses_strip_secret(client, monkeypatch, action, service_name, extra):
    monkeypatch.setattr(main, service_name, lambda **kwargs: {
        "facility_id": 1, "user_id": 1, "email": "staff@example.org",
        "verification_sent_at": "2026-11-03T00:00:00", "verification_method": "EMAIL_OTP",
        "debug_verification_code": "123456",
    })
    response = client.post(
        f"/provider/facilities/1/identity/{action}",
        headers={"X-Admin-Token": "provider-management-test-token"},
        json={"email": "staff@example.org", "role": "OWNER", **extra},
    )
    assert response.status_code == 200
    assert "debug_verification_code" not in response.json()
    assert "123456" not in response.text


def test_identity_service_retains_only_code_hash(monkeypatch):
    import hashlib
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database import Base
    from app.models.facility import Facility, ProviderIdentityChallenge
    from app.services import provider_identity

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(provider_identity.secrets, "randbelow", lambda limit: 123456)
    try:
        with Session(engine) as db:
            facility = Facility(
                cms_id="SECURITY-TEST", name="Example", address="1 Test Street",
                city="Las Vegas", state="NV", zip_code="89101",
            )
            db.add(facility)
            db.commit()
            result = provider_identity.start_email_verification(
                db, facility.id, "staff@example.org", None, "OWNER", None
            )
            assert "debug_verification_code" not in result
            assert "123456" not in str(result)
            challenge = db.query(ProviderIdentityChallenge).one()
            assert challenge.code_hash == hashlib.sha256(b"123456").hexdigest()
    finally:
        engine.dispose()


def test_public_provider_lookup_does_not_require_admin(client, monkeypatch):
    monkeypatch.setattr(main, "search_claimable_facilities", lambda *args: [])
    assert client.get("/provider/facilities/search", params={"q": "example"}).status_code == 200
