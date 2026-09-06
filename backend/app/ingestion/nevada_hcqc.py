"""Nevada state licence registry (DPBH / Health Care Quality and Compliance).

CMS certifies skilled nursing and nothing else. Every assisted living community, memory
care home and residential group home in Nevada is licensed by the state instead, which is
why they were entirely absent from a facility table keyed on CCN -- Atria Seville,
Brookdale Las Vegas, Legacy House, Merrill Gardens, MorningStar, Silverado and Oakmont all
exist, and none of them had a row.

That gap matters beyond coverage. Clark County has roughly 51 assisted living communities
against 40 certified nursing facilities, so a product that only knows the CMS half knows
the smaller half, and the wrong one for a family that is not yet looking at skilled care.

Two joins, in this order:

  federal_provider_no present  -> the state row describes a facility CMS already gave us;
                                  attach the licence, never create a second row for it
  otherwise                    -> a state-only community; create it with a synthetic
                                  identifier so nothing pretends it has a CCN

Rows that are not senior housing are skipped by care type. The registry's own
serves_elderly flag cannot carry that decision on its own: it tracks a single endorsement,
and reads N on dedicated Alzheimer homes and on every skilled nursing facility.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityLicenseRecord

SOURCE_NAME = "NV DPBH HCQC"
REGISTRY_PATH = (
    Path(__file__).resolve().parents[3]
    / "data" / "nevada" / "verified" / "nv_hcqc_clark_registry.json"
)
DETAIL_BASE = "https://hcqc.nv.gov"

# Eligibility is an exclusion list, not an inclusion list, and that is a deliberate
# correction. An inclusion list has to enumerate every care type Nevada might license, and
# the first attempt at one silently dropped all forty skilled nursing facilities and every
# GROUP_HOME_WITH_MEMORY_CARE, because they were absent from a hand-written set. Naming
# what is *not* somewhere a senior lives is a much shorter and much more stable list.
EXCLUDED_CARE_TYPES = {
    "NON_SENIOR_GROUP_HOME",   # licensed for a different population
    "ADULT_DAY",               # a day programme; nobody lives there
    "REFERRAL_AGENCY",         # a placement broker, not a facility
    "HOSPICE",                 # a service, generally delivered elsewhere
}

# Community-Based Living Arrangements are Nevada's behavioural-health housing category and
# are mostly not senior housing, so this one type has to earn its place with an endorsement
# that names older adults. Every other residential type is admitted on its care type alone.
CONDITIONAL_CARE_TYPES = {"COMMUNITY_BASED_LIVING"}

SENIOR_ENDORSEMENTS = {
    "RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS",
    "ALZHEIMER DISEASE",
    "ASSISTED LIVING SERVICES",
}


# Values the state uses to mean "we do not have this". Passed through untouched, "UNKNOWN"
# reads as data: it once became a facility identifier, and 291 separate assisted living
# communities collapsed onto a single row that answered to it.
NULL_SENTINELS = {"", "UNKNOWN", "N/A", "NA", "NONE", "NULL", "-"}


def _clean(value: Optional[str]) -> str:
    return str(value or "").strip()


def _clean_optional(value: Optional[str]) -> str:
    """Empty string for anything the source used to mean absence."""
    text = _clean(value)
    return "" if text.upper() in NULL_SENTINELS else text


def federal_provider_number(row: Dict[str, str]) -> str:
    """A CCN is six digits. Anything else is not an identity, whatever the column says.

    This is the guard rather than the sentinel list above: a new sentinel spelled some other
    way still fails the shape test, so identity can only ever be taken from something that
    actually looks like a certification number.
    """
    candidate = _clean_optional(row.get("federal_provider_no"))
    return candidate if candidate.isdigit() else ""


def _to_int(value: Optional[str]) -> Optional[int]:
    text = _clean(value)
    try:
        return int(float(text)) if text else None
    except ValueError:
        return None


def endorsements_of(row: Dict[str, str]) -> List[str]:
    raw = _clean(row.get("endorsement"))
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return [part for part in parts if part.upper() != "N/A"]


def _has_senior_signal(row: Dict[str, str]) -> bool:
    if _clean(row.get("serves_elderly")).upper() == "Y":
        return True
    if any(item.upper() in SENIOR_ENDORSEMENTS for item in endorsements_of(row)):
        return True
    # A dedicated Alzheimer bed is senior housing whatever the flags say.
    return (_to_int(row.get("beds_alzheimer")) or 0) > 0


def serves_seniors(row: Dict[str, str]) -> bool:
    care_type = _clean(row.get("derived_care_type")).upper()
    if not care_type or care_type in EXCLUDED_CARE_TYPES:
        return False
    if care_type in CONDITIONAL_CARE_TYPES:
        return _has_senior_signal(row)
    return True


def synthetic_id(credential_number: str) -> str:
    """Identifier for a state-only community.

    Prefixed so it can never be mistaken for a CCN, and derived from the credential so a
    re-run updates the same row instead of duplicating it.
    """
    return f"NV-{_clean(credential_number)}"[:20]


# Short tokens that are genuinely initialisms in this registry and should not be softened
# into words. Kept as an explicit list because guessing from length alone turns LAS VEGAS
# into "LAS Vegas" -- the registry is full of three-letter words that are not acronyms.
KNOWN_INITIALISMS = {"ASI", "LLC", "INC", "LP", "LLP", "CO", "II", "III", "IV", "NV", "US"}


def _title_case(value: str) -> str:
    """The registry shouts. Families read the name, so it is cased for them."""
    text = _clean(value)
    if not text or text != text.upper():
        return text
    small = {"of", "at", "the", "and", "on", "in", "for", "an", "a"}
    words = []
    for index, word in enumerate(text.split()):
        stripped = word.strip(".,")
        if stripped in KNOWN_INITIALISMS:
            words.append(word)
            continue
        lower = word.lower()
        words.append(lower if index and lower in small else lower.capitalize())
    return " ".join(words)


def read_rows(registry_path: Path | str | None = None) -> List[Dict[str, str]]:
    path = Path(registry_path) if registry_path else REGISTRY_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(record) for record in payload.get("records", [])]


def _detail_url(row: Dict[str, str]) -> Optional[str]:
    path = _clean(row.get("detail_url"))
    if not path:
        return None
    if path.startswith("http"):
        return path[:500]
    return f"{DETAIL_BASE}{path}"[:500]


def _upsert_license(db: Session, facility: Facility, row: Dict[str, str]) -> None:
    credential = _clean(row.get("credential_number"))
    record = (
        db.query(FacilityLicenseRecord)
        .filter(
            FacilityLicenseRecord.facility_id == facility.id,
            FacilityLicenseRecord.state_license_number == credential,
        )
        .one_or_none()
    )
    if record is None:
        record = FacilityLicenseRecord(facility_id=facility.id)
        db.add(record)

    record.state_license_number = credential
    record.state_license_type = _clean(row.get("credential_type_code")) or None
    record.state_care_type = _clean(row.get("derived_care_type")) or None
    record.state_endorsements = ", ".join(endorsements_of(row)) or None
    record.state_source_url = _detail_url(row)
    record.legal_name = _clean(row.get("name")) or None
    record.legal_address = _clean(row.get("address")) or None
    record.status = "VERIFIED"
    record.medicare_provider_number = federal_provider_number(row) or None
    record.verification_notes = (
        f"{SOURCE_NAME} active credential {credential}; "
        f"expires {_clean(row.get('expiration_date')) or 'unknown'}."
    )


def import_nevada_registry(
    db: Session,
    registry_path: Path | str | None = None,
    rows: Optional[Iterable[Dict[str, str]]] = None,
) -> Dict[str, int]:
    """Idempotent: safe to re-run when the state republishes its list."""
    source_rows = list(rows) if rows is not None else read_rows(registry_path)

    created = 0
    enriched = 0
    updated = 0
    skipped_not_senior = 0
    skipped_inactive = 0

    for row in source_rows:
        if _clean(row.get("status")).lower() != "active":
            skipped_inactive += 1
            continue
        if not serves_seniors(row):
            skipped_not_senior += 1
            continue

        credential = _clean(row.get("credential_number"))
        if not credential:
            continue

        ccn = federal_provider_number(row)
        facility: Optional[Facility] = None
        if ccn:
            facility = db.query(Facility).filter(Facility.cms_id == ccn).one_or_none()
            if facility is not None:
                enriched += 1

        if facility is None:
            key = ccn or synthetic_id(credential)
            facility = db.query(Facility).filter(Facility.cms_id == key).one_or_none()
            if facility is None:
                facility = Facility(
                    cms_id=key,
                    name=_title_case(row.get("name", "")),
                    address=_title_case(row.get("address", "")),
                    city=_title_case(row.get("city", "")),
                    state=_clean(row.get("state")).upper()[:2] or "NV",
                    zip_code=_clean(row.get("zip")),
                )
                db.add(facility)
                created += 1
            else:
                updated += 1

        # Bed count is the state's licensed capacity. It is only written where CMS left a
        # blank: a CCN row already carries certified beds, which is a different, federally
        # audited number and must not be silently replaced by a licence figure.
        beds = _to_int(row.get("bed_count"))
        if beds and not facility.beds:
            facility.beds = beds
        phone = _clean_optional(row.get("phone"))
        if phone and not facility.phone:
            facility.phone = phone
        if not facility.source_name:
            facility.source_name = SOURCE_NAME

        db.flush()
        _upsert_license(db, facility, row)

    db.commit()
    return {
        "rows_read": len(source_rows),
        "facilities_created": created,
        "cms_facilities_enriched": enriched,
        "existing_state_rows_updated": updated,
        "skipped_not_senior_housing": skipped_not_senior,
        "skipped_inactive": skipped_inactive,
    }
