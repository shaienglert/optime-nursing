"""Validate provider-supplied details without promoting claims to verified facts."""
import json
import math
from datetime import date
from urllib.parse import urlparse

DETAIL_FIELDS = {"value", "conditions", "scope", "delivery", "evidence_url", "observed_on"}
SCOPES = {"FACILITY", "UNIT", "PROGRAM", "SERVICE"}
DELIVERIES = {"ON_SITE", "THIRD_PARTY", "TRANSPORT", "UNKNOWN"}

def normalize_details(question, answer, raw):
    if not isinstance(raw, dict) or set(raw) - DETAIL_FIELDS:
        raise ValueError("Unsupported questionnaire detail fields.")
    result = {}
    for key, value in raw.items():
        if key == "value":
            kind = question.get("response_kind", "state")
            if kind == "state":
                if value not in (None, ""):
                    raise ValueError("A capability answer cannot contain a separate numeric or text value.")
                continue
            if value in (None, ""):
                continue
            if kind == "number":
                if isinstance(value, bool):
                    raise ValueError("Numeric questionnaire values must be finite nonnegative numbers.")
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    raise ValueError("Numeric questionnaire values must be finite nonnegative numbers.")
                if not math.isfinite(number) or number < 0 or number > 1_000_000_000:
                    raise ValueError("Numeric questionnaire value is outside the supported range.")
                if question.get("key") in {"social_resident_count", "autonomy_parking_spaces"} and not number.is_integer():
                    raise ValueError("Counts must be whole numbers.")
                result[key] = number
            else:
                if not isinstance(value, str) or len(value) > 4000:
                    raise ValueError("Questionnaire text is limited to 4000 characters.")
                result[key] = value.strip()
                if kind == "date":
                    try:
                        date.fromisoformat(result[key])
                    except ValueError:
                        raise ValueError("Dates must use YYYY-MM-DD.")
        else:
            if not isinstance(value, str) or len(value) > 4000:
                raise ValueError("Questionnaire details must be text of at most 4000 characters.")
            clean = value.strip()
            if not clean:
                continue
            if key == "scope" and clean not in SCOPES:
                raise ValueError("Unsupported capability scope.")
            if key == "delivery" and clean not in DELIVERIES:
                raise ValueError("Unsupported service delivery.")
            if key == "evidence_url":
                url = urlparse(clean)
                if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                    raise ValueError("Evidence URL must be an absolute HTTP(S) URL without credentials.")
            if key == "observed_on":
                try:
                    observed = date.fromisoformat(clean)
                except ValueError:
                    raise ValueError("Observed date must use YYYY-MM-DD.")
                if observed > date.today():
                    raise ValueError("Observed date cannot be in the future.")
            result[key] = clean
    kind = question.get("response_kind", "state")
    if answer in {"YES", "LIMITED"} and kind != "state" and "value" not in result:
        raise ValueError("Provide the requested value or choose Not sure.")
    if answer == "LIMITED" and not result.get("conditions"):
        raise ValueError("Explain the limitation or condition.")
    if answer in {"NO", "UNKNOWN"}:
        result.pop("value", None)
    return result

def encode_details(details):
    return json.dumps({"provider_questionnaire_v2": details}, sort_keys=True, ensure_ascii=False)

def decode_details(notes):
    try:
        payload = json.loads(notes or "")
        value = payload.get("provider_questionnaire_v2") if isinstance(payload, dict) else None
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}
