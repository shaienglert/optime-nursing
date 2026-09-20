#!/usr/bin/env python3
"""Build the isolated 200-community Oomnik recommendation pilot.

Every identity, claim, price and availability value in this artifact is synthetic.
The output is deliberately kept outside the production Nevada universe and can only
be loaded when OPTIME_CANONICAL_MARKET=synthetic-pilot.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "database" / "synthetic_pilot"
DB_PATH = OUT / "oomnik_synthetic_pilot.db"
CANONICAL_PATH = OUT / "facility_universe.json"
EVIDENCE_PATH = OUT / "facility_parameter_evidence.json"
MEDIA_PATH = OUT / "facility_media_registry.json"

CITIES = [
    ("LAS VEGAS", "89101", 36.1716, -115.1391),
    ("LAS VEGAS", "89117", 36.1433, -115.2852),
    ("LAS VEGAS", "89123", 36.0355, -115.1537),
    ("HENDERSON", "89012", 36.0050, -115.0403),
    ("HENDERSON", "89052", 35.9875, -115.1034),
    ("NORTH LAS VEGAS", "89031", 36.2578, -115.1711),
]

ARCHETYPES = [
    ("INDEPENDENT_LIVING", "Independent Living", 3600, 5200),
    ("ACTIVE_ADULT_55_PLUS", "Active Adult 55+", 2500, 3900),
    ("ASSISTED_LIVING_RFG", "Assisted Living", 4400, 7200),
    ("MEMORY_CARE", "Memory Care", 6100, 9400),
    ("SKILLED_NURSING", "Skilled Nursing", 8900, 13800),
    ("REHABILITATION", "Short-term Rehabilitation", 7600, 12400),
    ("CONTINUING_CARE", "Continuing Care", 5600, 9800),
    ("SMALL_GROUP_HOME", "Small Residential Care Home", 4200, 6800),
]

PREFIXES = ["Desert", "Silver", "Sage", "Red Rock", "Sunrise", "Mojave", "Canyon", "Willow", "Harmony", "Mesa"]
SUFFIXES = ["Gardens", "Commons", "House", "Village", "Court"]


def _name_component_index(offset: int, salt: str, modulus: int) -> int:
    # `offset % len(PREFIXES)` used to pick the prefix -- since len(PREFIXES)=10 and
    # len(ARCHETYPES)=8 share a factor of 2, every archetype (offset % 8) always landed
    # on the same 1-2 prefixes across all 200 facilities (e.g. every Continuing Care
    # facility got "Canyon"/"Desert", every Memory Care facility got "Mesa"/"Mojave").
    # Facility names then sort alphabetically by canonical_type by construction, so any
    # tiebreak or shortlist cutoff by name (see must_ai_nice_pipeline.py's
    # rankable[:interactive_shortlist_limit]) always favors the same handful of
    # archetypes over others regardless of clinical fit. A hash-based index has no
    # relationship to offset % len(ARCHETYPES), breaking that correlation.
    digest = hashlib.sha256(f"{salt}-{offset}".encode("utf-8")).hexdigest()
    return int(digest, 16) % modulus

# backend/app/services/patient_decision_engine/__init__.py's _care_setting_fit() only
# recognizes these three canonical_type values (the ones the real Nevada regulatory data
# uses) -- a facility with any other canonical_type silently falls through to a generic
# "verification required" rank tier regardless of its actual capabilities. Collapse the
# richer archetype set onto this production-recognized taxonomy so ranking behaves the
# same way it does against real data; the original archetype is kept in
# `synthetic_archetype` for naming, pricing and capability variety.
PRODUCTION_CANONICAL_TYPE = {
    "INDEPENDENT_LIVING": "INDEPENDENT_LIVING",
    "ACTIVE_ADULT_55_PLUS": "INDEPENDENT_LIVING",
    "ASSISTED_LIVING_RFG": "ASSISTED_LIVING_RFG",
    "MEMORY_CARE": "ASSISTED_LIVING_RFG",
    "SKILLED_NURSING": "SKILLED_NURSING",
    "REHABILITATION": "SKILLED_NURSING",
    "CONTINUING_CARE": "ASSISTED_LIVING_RFG",
    "SMALL_GROUP_HOME": "ASSISTED_LIVING_RFG",
}

PARAMETERS = [
    "adl_support", "medication_support", "transfer_assistance", "memory_care",
    "dementia_alz_programs", "nursing_24_7", "skilled_nursing_capabilities",
    "pt", "ot", "speech_therapy", "post_stroke_neuro_evidence", "transportation", "published_rates",
    "current_availability", "languages", "kosher", "gluten_free",
    "religious_cultural_services", "activities", "accessibility",
    "dialysis_arrangements", "wound_care", "respiratory_trach_vent",
]

ILLUSTRATIONS = [
    ("exterior", "/pilot-media/community-exterior.svg"),
    ("room", "/pilot-media/private-room.svg"),
    ("garden", "/pilot-media/garden.svg"),
    ("dining", "/pilot-media/dining-room.svg"),
    ("lounge", "/pilot-media/community-lounge.svg"),
]

PORTAL_CAPABILITY_KEYS = [
    "medical_24_7_nursing", "medical_physician_availability", "medical_memory_care",
    "rehab_speech_therapy", "rehab_physical_therapy", "rehab_occupational_therapy",
    "rehab_stroke_support", "rehab_parkinson_support", "dining_gluten_free",
    "dining_kosher", "dining_vegetarian", "dining_diabetic_meals", "lifestyle_movies",
    "lifestyle_music", "lifestyle_gardening", "lifestyle_pool", "lifestyle_fitness_center",
    "lifestyle_religious_services", "lifestyle_transportation", "housing_kitchenette",
    "housing_balcony", "housing_studio", "housing_one_bedroom", "housing_pets_allowed",
    "accessibility_walker_support", "accessibility_wheelchair_access",
    "accessibility_fall_prevention", "accessibility_transfer_assistance",
    "continuum_assisted_living", "continuum_memory_care", "continuum_skilled_nursing",
    "continuum_rehabilitation", "continuum_on_campus_progression",
]


def yes_no(index: int, modulus: int, *, limited: bool = False) -> str:
    if limited and index % modulus == 0:
        return "LIMITED"
    return "YES" if index % modulus != 0 else "NO"


def capability_map(index: int, canonical_type: str) -> dict[str, object]:
    care = canonical_type in {"ASSISTED_LIVING_RFG", "MEMORY_CARE", "SKILLED_NURSING", "REHABILITATION", "CONTINUING_CARE", "SMALL_GROUP_HOME"}
    skilled = canonical_type in {"SKILLED_NURSING", "REHABILITATION", "CONTINUING_CARE"}
    memory = canonical_type in {"MEMORY_CARE", "CONTINUING_CARE"}
    return {
        "adl_support": "YES" if care else "NO",
        "medication_support": "YES" if care else "NO",
        "transfer_assistance": "YES" if skilled or index % 3 else "LIMITED",
        "memory_care": "YES" if memory else "NO",
        "dementia_alz_programs": "YES" if memory else ("LIMITED" if care and index % 4 == 0 else "NO"),
        "nursing_24_7": "YES" if skilled else ("LIMITED" if care and index % 5 == 0 else "NO"),
        "skilled_nursing_capabilities": "YES" if skilled else "NO",
        "pt": "YES" if skilled or index % 3 == 0 else "NO",
        "ot": "YES" if skilled or index % 4 == 0 else "NO",
        "speech_therapy": "YES" if skilled or index % 7 == 0 else "NO",
        "post_stroke_neuro_evidence": "YES" if canonical_type == "REHABILITATION" or (canonical_type == "SKILLED_NURSING" and index % 5 == 0) else "NO",
        "transportation": yes_no(index, 6, limited=True),
        "published_rates": "YES",
        "current_availability": ["YES", "YES", "LIMITED", "NO", "YES"][index % 5],
        "languages": ["English", "English, Spanish", "English, Hebrew", "English, Russian", "English, Mandarin"][index % 5],
        "kosher": "YES" if index % 9 == 0 else ("LIMITED" if index % 4 == 0 else "NO"),
        "gluten_free": "YES" if index % 3 else "LIMITED",
        "religious_cultural_services": yes_no(index, 5, limited=True),
        "activities": "YES",
        "accessibility": "YES" if care or skilled or index % 2 == 0 else "LIMITED",
        "dialysis_arrangements": "YES" if skilled and index % 3 != 0 else ("LIMITED" if care and index % 6 == 0 else "NO"),
        "wound_care": "YES" if skilled else ("LIMITED" if care and index % 5 == 0 else "NO"),
        # Some residential settings can manage stable oxygen, while all skilled
        # settings can; this gives oxygen-dependent personas a real parameter to
        # match without treating a category label as a capability proxy.
        "respiratory_trach_vent": "YES" if skilled or (care and index % 4 == 0) else "NO",
    }


def build() -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    facilities: list[dict] = []
    evidence: list[dict] = []
    rooms: list[dict] = []
    media: list[dict] = []
    portal_capabilities: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for offset in range(200):
        index = offset + 1
        archetype_id, care_label, low, high = ARCHETYPES[offset % len(ARCHETYPES)]
        canonical_type = PRODUCTION_CANONICAL_TYPE[archetype_id]
        city, zip_code, base_lat, base_lon = CITIES[offset % len(CITIES)]
        canonical_id = f"PILOT-NV-{index:03d}"
        name = f"{PREFIXES[_name_component_index(offset, 'prefix', len(PREFIXES))]} {SUFFIXES[_name_component_index(offset, 'suffix', len(SUFFIXES))]} {care_label}"
        address = f"{1100 + index * 37} Pilot Mesa Avenue"
        capacity = 12 + ((index * 17) % 170)
        capabilities = capability_map(index, archetype_id)
        facility = {
            "canonical_id": canonical_id,
            "facility_name": name,
            "address": address,
            "city": city,
            "state": "NV",
            "zip": zip_code,
            "latitude": round(base_lat + ((index % 7) - 3) * 0.006, 6),
            "longitude": round(base_lon + ((index % 9) - 4) * 0.006, 6),
            "canonical_type": canonical_type,
            "synthetic_archetype": archetype_id,
            "housing_modalities": [care_label.upper().replace("-", "_").replace(" ", "_")],
            "licensed_capacity": capacity,
            "license_status": "SYNTHETIC_PILOT_ACTIVE",
            "is_las_vegas_valley": True,
            "synthetic_pilot": True,
            "pilot_exposure_order": index,
            "truth_label": "FICTIONAL COMMUNITY — TEST DATA ONLY",
            "provider_reported_at": now,
            "description": f"Fictional {care_label.lower()} profile created to test Oomnik matching behavior.",
            "phone": f"+1-702-555-{100 + (index % 100):04d}",
            "admissions_email": f"admissions-{index:03d}@pilot.example.invalid",
            "website": f"https://pilot.example.invalid/communities/{canonical_id.lower()}",
            "entrance_fee": 75000 + index * 2500 if archetype_id == "CONTINUING_CARE" else 0,
            "community_size": "SMALL" if capacity < 45 else ("MEDIUM" if capacity < 100 else "LARGE"),
            "minimum_age": 55 if archetype_id == "ACTIVE_ADULT_55_PLUS" else 62,
            "accepts_couples": index % 6 != 0,
            "accepts_resident_caregiver": index % 7 == 0,
            "parking_spaces_available": index % 5 != 0,
            "languages": capabilities["languages"],
            "owner_profile_status": "COMPLETE_SYNTHETIC_PILOT",
            "source_identity_ids": {"synthetic_pilot_id": canonical_id},
        }
        if archetype_id in {"MEMORY_CARE", "CONTINUING_CARE"}:
            # Matches how real Nevada memory-care communities are recognized by
            # _care_setting_fit()/_memory_confirmed(): canonical_type ASSISTED_LIVING_RFG
            # plus this classification field, not a distinct canonical_type.
            facility["memory_care_classification"] = "CONFIRMED"
        facilities.append(facility)

        monthly_mid = low + ((index * 173) % max(1, high - low))
        room_names = ["Private studio", "One-bedroom suite"]
        if archetype_id in {"MEMORY_CARE", "SKILLED_NURSING", "REHABILITATION", "SMALL_GROUP_HOME"}:
            room_names = ["Private care room", "Shared companion room"]
        for room_offset, room_name in enumerate(room_names):
            rooms.append({
                "canonical_facility_id": canonical_id,
                "room_type_name": room_name,
                "description": f"Synthetic {room_name.lower()} used for controlled pilot testing.",
                "monthly_price_cents": (monthly_mid + room_offset * 900) * 100,
                "availability_status": ["AVAILABLE", "WAITLIST", "AVAILABLE", "UNAVAILABLE"][((index + room_offset) % 4)],
                "available_units": [3, 0, 1, 0][((index + room_offset) % 4)],
                "source": "SYNTHETIC_PROVIDER_PORTAL",
                "last_verified_at": now,
            })

        for parameter_id in PARAMETERS:
            value = capabilities[parameter_id]
            evidence.append({
                "canonical_facility_id": canonical_id,
                "parameter_id": parameter_id,
                "value": value,
                "source": "Synthetic owner-completed pilot profile",
                "scope": "FACILITY",
                "scope_name": name,
                "last_verified": now,
                "source_record_id": canonical_id,
                "evidence_text": f"Synthetic provider response for {parameter_id.replace('_', ' ')}",
                "evidence_value": value,
                "evidence_date": now,
                "confidence": "HIGH",
                "evidence_strength": "FACILITY_REPORTED",
                "verification_status": "VERIFIED",
                "conflict_status": "NONE",
                "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
            })
        evidence.append({
            "canonical_facility_id": canonical_id,
            "parameter_id": "current_price",
            "value": monthly_mid,
            "source": "Synthetic owner-completed pilot profile",
            "scope": "FACILITY",
            "scope_name": name,
            "last_verified": now,
            "source_record_id": canonical_id,
            "evidence_text": "Synthetic starting monthly price",
            "evidence_value": monthly_mid,
            "evidence_date": now,
            "confidence": "HIGH",
            "evidence_strength": "FACILITY_REPORTED",
            "verification_status": "VERIFIED",
            "conflict_status": "NONE",
            "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
        })
        for category, url in ILLUSTRATIONS:
            media.append({
                "canonical_facility_id": canonical_id,
                "category": category,
                "url": url,
                "caption": f"Synthetic illustration of {category}; not a photograph of a real facility",
                "source": "OOMNIK_SYNTHETIC_ILLUSTRATION",
                "display_rights_status": "OOMNIK_OWNED_SYNTHETIC",
            })
        for capability_offset, capability in enumerate(PORTAL_CAPABILITY_KEYS):
            if capability == "medical_24_7_nursing":
                value = capabilities["nursing_24_7"]
            elif capability == "medical_memory_care":
                value = capabilities["memory_care"]
            elif capability == "rehab_speech_therapy":
                value = capabilities["speech_therapy"]
            elif capability == "rehab_physical_therapy":
                value = capabilities["pt"]
            elif capability == "rehab_occupational_therapy":
                value = capabilities["ot"]
            elif capability == "dining_gluten_free":
                value = capabilities["gluten_free"]
            elif capability == "dining_kosher":
                value = capabilities["kosher"]
            elif capability == "lifestyle_transportation":
                value = capabilities["transportation"]
            elif capability == "accessibility_transfer_assistance":
                value = capabilities["transfer_assistance"]
            elif capability == "continuum_memory_care":
                value = "YES" if archetype_id in {"MEMORY_CARE", "CONTINUING_CARE"} else "NO"
            elif capability == "continuum_skilled_nursing":
                value = "YES" if archetype_id in {"SKILLED_NURSING", "CONTINUING_CARE"} else "NO"
            elif capability == "continuum_rehabilitation":
                value = "YES" if archetype_id in {"REHABILITATION", "SKILLED_NURSING", "CONTINUING_CARE"} else "NO"
            elif capability == "continuum_on_campus_progression":
                value = "YES" if archetype_id == "CONTINUING_CARE" else "NO"
            else:
                value = ["YES", "YES", "LIMITED", "NO"][(index + capability_offset) % 4]
            portal_capabilities.append({
                "canonical_facility_id": canonical_id,
                "capability": capability,
                "value": value,
                "source": "SYNTHETIC_OWNER_COMPLETED_PORTAL",
                "confidence": 1.0,
                "verification_status": "VERIFIED",
                "verified_at": now,
            })
    return facilities, evidence, rooms, media, portal_capabilities


def write_sqlite(facilities: list[dict], evidence: list[dict], rooms: list[dict], media: list[dict], portal_capabilities: list[dict]) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    connection.executescript("""
        CREATE TABLE pilot_facilities (canonical_id TEXT PRIMARY KEY, name TEXT NOT NULL, canonical_type TEXT NOT NULL, city TEXT NOT NULL, state TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE TABLE pilot_parameter_evidence (id INTEGER PRIMARY KEY, canonical_facility_id TEXT NOT NULL, parameter_id TEXT NOT NULL, value_json TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE TABLE pilot_rooms (id INTEGER PRIMARY KEY, canonical_facility_id TEXT NOT NULL, room_type_name TEXT NOT NULL, monthly_price_cents INTEGER, availability_status TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE TABLE pilot_media (id INTEGER PRIMARY KEY, canonical_facility_id TEXT NOT NULL, category TEXT NOT NULL, url TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE TABLE pilot_capabilities (id INTEGER PRIMARY KEY, canonical_facility_id TEXT NOT NULL, capability TEXT NOT NULL, value TEXT NOT NULL, payload_json TEXT NOT NULL);
        CREATE INDEX ix_pilot_evidence_facility_parameter ON pilot_parameter_evidence(canonical_facility_id, parameter_id);
        CREATE INDEX ix_pilot_rooms_facility ON pilot_rooms(canonical_facility_id);
        CREATE INDEX ix_pilot_media_facility ON pilot_media(canonical_facility_id);
        CREATE UNIQUE INDEX ux_pilot_capability ON pilot_capabilities(canonical_facility_id, capability);
    """)
    connection.executemany("INSERT INTO pilot_facilities VALUES (?, ?, ?, ?, ?, ?)", [(x["canonical_id"], x["facility_name"], x["canonical_type"], x["city"], x["state"], json.dumps(x)) for x in facilities])
    connection.executemany("INSERT INTO pilot_parameter_evidence(canonical_facility_id, parameter_id, value_json, payload_json) VALUES (?, ?, ?, ?)", [(x["canonical_facility_id"], x["parameter_id"], json.dumps(x["value"]), json.dumps(x)) for x in evidence])
    connection.executemany("INSERT INTO pilot_rooms(canonical_facility_id, room_type_name, monthly_price_cents, availability_status, payload_json) VALUES (?, ?, ?, ?, ?)", [(x["canonical_facility_id"], x["room_type_name"], x["monthly_price_cents"], x["availability_status"], json.dumps(x)) for x in rooms])
    connection.executemany("INSERT INTO pilot_media(canonical_facility_id, category, url, payload_json) VALUES (?, ?, ?, ?)", [(x["canonical_facility_id"], x["category"], x["url"], json.dumps(x)) for x in media])
    connection.executemany("INSERT INTO pilot_capabilities(canonical_facility_id, capability, value, payload_json) VALUES (?, ?, ?, ?)", [(x["canonical_facility_id"], x["capability"], x["value"], json.dumps(x)) for x in portal_capabilities])
    connection.commit()
    connection.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    facilities, evidence, rooms, media, portal_capabilities = build()
    generated_at = datetime.now(timezone.utc).isoformat()
    CANONICAL_PATH.write_text(json.dumps({"generated_at_utc": generated_at, "record_count": len(facilities), "dataset_mode": "SYNTHETIC_PILOT", "records": facilities}, indent=2), encoding="utf-8")
    EVIDENCE_PATH.write_text(json.dumps({"generated_at_utc": generated_at, "record_count": len(evidence), "dataset_mode": "SYNTHETIC_PILOT", "records": evidence}, indent=2), encoding="utf-8")
    grouped_media = []
    for facility in facilities:
        facility_media = [row for row in media if row["canonical_facility_id"] == facility["canonical_id"]]
        grouped_media.append({
            "canonical_facility_id": facility["canonical_id"],
            "verified_facility_specific": False,
            "synthetic_pilot": True,
            "image_status": "SYNTHETIC_PILOT",
            "display_rights_status": "OOMNIK_OWNED_SYNTHETIC",
            "primary_image_url": facility_media[0]["url"],
            "primary_image_category": facility_media[0]["category"],
            "image_source_type": "OOMNIK_SYNTHETIC_ILLUSTRATION",
            "verification_method": "Oomnik-owned synthetic illustration; no real facility depicted",
            "gallery_images": facility_media,
        })
    MEDIA_PATH.write_text(json.dumps({"generated_at_utc": generated_at, "record_count": len(grouped_media), "dataset_mode": "SYNTHETIC_PILOT", "records": grouped_media}, indent=2), encoding="utf-8")
    (OUT / "room_inventory.json").write_text(json.dumps({"generated_at_utc": generated_at, "record_count": len(rooms), "dataset_mode": "SYNTHETIC_PILOT", "records": rooms}, indent=2), encoding="utf-8")
    (OUT / "provider_capabilities.json").write_text(json.dumps({"generated_at_utc": generated_at, "record_count": len(portal_capabilities), "dataset_mode": "SYNTHETIC_PILOT", "records": portal_capabilities}, indent=2), encoding="utf-8")
    write_sqlite(facilities, evidence, rooms, media, portal_capabilities)
    for path in (CANONICAL_PATH, EVIDENCE_PATH, MEDIA_PATH, OUT / "room_inventory.json", OUT / "provider_capabilities.json"):
        encoded = base64.b64encode(gzip.compress(path.read_bytes(), compresslevel=9)).decode("ascii")
        path.with_suffix(path.suffix + ".gz.b64").write_text(encoded + "\n", encoding="ascii")
    print(json.dumps({"facilities": len(facilities), "evidence": len(evidence), "rooms": len(rooms), "media": len(media), "portal_capabilities": len(portal_capabilities), "database": str(DB_PATH)}, indent=2))


if __name__ == "__main__":
    main()
