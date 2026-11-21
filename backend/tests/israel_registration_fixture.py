"""A complete, valid Israeli registration for tests."""

REQUIRED_QUESTIONNAIRE = {
    "street_address": "הרצל 1, חיפה",
    "contact_name": "דנה",
    "contact_phone": "04-1234567",
    "payment_tracks": ["MOH_CODE", "PRIVATE"],
    "staff_languages": ["HE", "RU"],
}


def registration(**overrides):
    base = {
        "functional_levels_served": ["NURSING"],
        "moh_code_agreement": "YES",
        "license_id": "X1",
        "license_authority": "MINISTRY_OF_HEALTH",
        "license_expiration_date": "2099-12-31",
        "questionnaire": dict(REQUIRED_QUESTIONNAIRE),
    }
    base.update(overrides)
    return base
