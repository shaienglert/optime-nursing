import os
import json
from statistics import mean
from typing import Dict, List, Optional

from sqlalchemy import func, or_

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.facility import AdaptiveQuestionResponse, Facility, FacilityIntelligenceProfile, HumanIntelligenceScore, Inspection, QualityMeasure, ResidentOutcome, Staffing
from app.services.cms_inspection_import import import_inspection_data
from app.services.cms_provider_import import import_provider_information
from app.services.cms_quality_import import import_quality_data
from app.services.cms_staffing_import import import_staffing_data
from app.services.intelligence_agent import UPDATE_FREQUENCY, run_intelligence_collection
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    clean_state,
    clip_0_100,
    download_dataset,
    env_int,
    inverse_count,
    invert_percent,
    iter_csv_rows,
    normalize_hours,
    stars_to_score,
    to_float,
)

app = FastAPI(
    title="OPTIME Nursing API",
    version="0.3.0",
    description="OPTIME Phase 1 CMS ingestion pipeline for Florida nursing homes",
)

frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FacilityListOut(BaseModel):
    id: int
    cms_id: str
    name: str
    city: str
    state: str
    address: str
    zip_code: str
    phone: Optional[str] = None
    overall_rating: Optional[int] = None
    staffing_rating: Optional[int] = None
    quality_rating: Optional[int] = None
    inspection_rating: Optional[int] = None
    beds: Optional[int] = None
    medical_quality_score: Optional[float] = None
    staffing_score: Optional[float] = None
    safety_score: Optional[float] = None
    overall_optime_score: Optional[float] = None
    confidence_level: Optional[str] = None
    intelligence_confidence: Optional[float] = None
    intelligence_sources_used: List[str] = Field(default_factory=list)
    intelligence_positive_signals: List[str] = Field(default_factory=list)
    intelligence_negative_signals: List[str] = Field(default_factory=list)
    family_satisfaction_index: Optional[float] = None
    staff_stability_index: Optional[float] = None
    regulatory_risk_index: Optional[float] = None
    litigation_risk_index: Optional[float] = None
    social_energy_index: Optional[float] = None
    community_engagement_index: Optional[float] = None
    reputation_index: Optional[float] = None
    cultural_match_signals: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ScoreBreakdownOut(BaseModel):
    medical_quality_score: float
    staffing_score: float
    safety_score: float
    overall_optime_score: float
    medical_components: Dict[str, float]
    staffing_components: Dict[str, float]
    safety_components: Dict[str, float]


class FacilityDetailsOut(BaseModel):
    id: int
    cms_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None
    overall_rating: Optional[int] = None
    staffing_rating: Optional[int] = None
    quality_rating: Optional[int] = None
    inspection_rating: Optional[int] = None
    beds: Optional[int] = None
    confidence_level: Optional[str] = None
    score_breakdown: ScoreBreakdownOut


class ImportSummaryOut(BaseModel):
    facilities_imported: int
    missing_records: int
    failed_mappings: int
    score_distributions: Dict[str, Dict[str, float]]


class HumanIntelligenceIn(BaseModel):
    resident_key: str
    relationship: Optional[str] = None
    age_group: Optional[str] = None
    social_profile_score: float
    family_support_score: float
    cultural_match_score: float
    loneliness_risk_score: float
    transition_risk_score: float
    future_care_score: float
    social_fit_score: Optional[float] = None
    family_fit_score: Optional[float] = None
    language_match_score: Optional[float] = None
    religious_fit_score: Optional[float] = None
    language_fit_score: Optional[float] = None
    cultural_fit_score: Optional[float] = None
    food_fit_score: Optional[float] = None
    family_engagement_score: Optional[float] = None
    community_style_score: Optional[float] = None
    independence_fit_score: Optional[float] = None
    transition_success_probability: Optional[float] = None
    metadata_json: Optional[str] = None


class HumanIntelligenceOut(HumanIntelligenceIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ResidentOutcomeIn(BaseModel):
    resident_key: str
    human_intelligence_score_id: Optional[int] = None
    facility_id: Optional[int] = None
    successful_adjustment: bool
    loneliness_event: bool
    relocated_within_24m: bool
    notes: Optional[str] = None


class AdaptiveQuestionResponseIn(BaseModel):
    resident_key: str
    question_key: str
    answer: str
    signal_type: str
    signal_json: Optional[str] = None
    weights_json: Optional[str] = None
    impact_explanation: str
    info_gain_score: float = 0.0


class AdaptiveQuestionResponseOut(AdaptiveQuestionResponseIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ResidentOutcomeOut(BaseModel):
    id: int
    resident_key: str
    human_intelligence_score_id: Optional[int] = None
    facility_id: Optional[int] = None
    successful_adjustment: bool
    loneliness_event: bool
    relocated_within_24m: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValidationFeedbackOut(BaseModel):
    outcomes_count: int
    adjustment_success_rate: float
    loneliness_event_rate: float
    relocation_rate_24m: float
    average_scores_for_successful_adjustment: Dict[str, float]
    average_scores_for_unsuccessful_adjustment: Dict[str, float]


class FacilityIntelligenceProfileOut(BaseModel):
    facility_id: int
    last_updated: str
    sources_used: List[str]
    clinical_score: float
    family_score: float
    employee_score: float
    social_score: float
    reputation_score: float
    legal_risk_score: float
    regulatory_risk_score: float
    intelligence_confidence: float
    verified_facts: List[str]
    public_allegations: List[str]
    public_opinions: List[str]
    missing_information: List[str]
    positive_signals: List[str]
    negative_signals: List[str]
    unresolved_risks: List[str]
    intelligence_summary: str
    social_energy_index: float
    family_satisfaction_index: float
    staff_stability_index: float
    regulatory_risk_index: float
    litigation_risk_index: float
    cultural_match_signals: float
    activity_density_index: float
    community_engagement_index: float
    clinical_quality_index: float
    reputation_index: float


class IntelligenceRunSummaryOut(BaseModel):
    processed: int
    facility_ids: List[int]
    update_frequency: Dict[str, str]



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_measure_score(measures: List[QualityMeasure], keywords: List[str]) -> Optional[float]:
    values: List[float] = []
    for measure in measures:
        name = (measure.measure_name or "").lower()
        if any(keyword in name for keyword in keywords) and measure.measure_value is not None:
            values.append(float(measure.measure_value))
    if not values:
        return None
    return mean(values)


def _build_provider_row_map(facilities: List[Facility], state: str) -> Dict[str, dict]:
    ccn_set = {facility.cms_id for facility in facilities}
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")
    row_map: Dict[str, dict] = {}
    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue
        ccn = row.get("CMS Certification Number (CCN)") or ""
        if ccn in ccn_set:
            row_map[ccn] = row
    return row_map


def _calculate_scores(db: Session, state: str = "FL") -> dict:
    facilities = db.query(Facility).filter(Facility.state == state).order_by(Facility.id.asc()).all()
    provider_rows = _build_provider_row_map(facilities, state)

    medical_values: List[float] = []
    staffing_values: List[float] = []
    safety_values: List[float] = []
    overall_values: List[float] = []

    for facility in facilities:
        quality_rows = db.query(QualityMeasure).filter(QualityMeasure.facility_id == facility.id).all()
        staffing_row = (
            db.query(Staffing)
            .filter(Staffing.facility_id == facility.id)
            .order_by(Staffing.id.desc())
            .first()
        )
        inspection_rows = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()
        provider_row = provider_rows.get(facility.cms_id, {})

        # Medical Quality Score components (0-100)
        cms_rating = stars_to_score(facility.quality_rating or facility.overall_rating)
        hospitalization = invert_percent(_get_measure_score(quality_rows, ["hospital", "rehospital"]))
        er_visits = invert_percent(_get_measure_score(quality_rows, ["emergency", "er visit"]))
        falls = invert_percent(_get_measure_score(quality_rows, ["fall"]))
        pressure_ulcers = invert_percent(_get_measure_score(quality_rows, ["pressure ulcer", "pressure"]))
        weight_loss = invert_percent(_get_measure_score(quality_rows, ["weight loss"]))

        medical_quality_score = clip_0_100(
            0.25 * cms_rating
            + 0.25 * hospitalization
            + 0.15 * er_visits
            + 0.15 * falls
            + 0.10 * pressure_ulcers
            + 0.10 * weight_loss
        )

        # Staffing Score components (0-100)
        rn_hours = staffing_row.rn_hours_per_resident_day if staffing_row else None
        total_staffing_hours = staffing_row.total_nurse_hours_per_resident_day if staffing_row else None
        rn_score = normalize_hours(rn_hours, benchmark=0.75)
        total_staffing_score = normalize_hours(total_staffing_hours, benchmark=3.5)

        agency_staff_raw = to_float(provider_row.get("Agency staff") if provider_row else None)
        agency_staff_score = invert_percent(agency_staff_raw) if agency_staff_raw is not None else 50.0

        turnover_rate = to_float(provider_row.get("Total nursing staff turnover") if provider_row else None)
        turnover_score = invert_percent(turnover_rate)

        staffing_score = clip_0_100(
            0.35 * rn_score
            + 0.25 * total_staffing_score
            + 0.20 * agency_staff_score
            + 0.20 * turnover_score
        )

        # Safety Score components (0-100)
        serious_deficiencies = float(sum(item.severe_deficiency_count or 0 for item in inspection_rows))
        complaints = float(sum(item.payment_denials_count or 0 for item in inspection_rows))
        fines = to_float(provider_row.get("Total Amount of Fines in Dollars") if provider_row else None)
        infection_control = to_float(provider_row.get("Number of Citations from Infection Control Inspections") if provider_row else None)

        serious_score = inverse_count(serious_deficiencies, max_bad=10)
        complaint_score = inverse_count(complaints, max_bad=25)
        fine_score = inverse_count(fines, max_bad=500000)
        infection_score = inverse_count(infection_control, max_bad=10)

        safety_score = clip_0_100(
            0.35 * serious_score
            + 0.25 * complaint_score
            + 0.20 * fine_score
            + 0.20 * infection_score
        )

        overall_optime_score = clip_0_100(
            0.4 * medical_quality_score + 0.35 * staffing_score + 0.25 * safety_score
        )

        facility.medical_quality_score = round(medical_quality_score, 2)
        facility.staffing_score = round(staffing_score, 2)
        facility.safety_score = round(safety_score, 2)
        facility.overall_optime_score = round(overall_optime_score, 2)

        medical_values.append(facility.medical_quality_score)
        staffing_values.append(facility.staffing_score)
        safety_values.append(facility.safety_score)
        overall_values.append(facility.overall_optime_score)

    db.commit()

    def summarize(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {"min": min(values), "max": max(values), "avg": round(mean(values), 2)}

    return {
        "medical_quality_score": summarize(medical_values),
        "staffing_score": summarize(staffing_values),
        "safety_score": summarize(safety_values),
        "overall_optime_score": summarize(overall_values),
    }


def run_phase1_ingestion(db: Session, state: str = "FL", limit: int = 100) -> dict:
    ccn_to_facility_id, provider_summary = import_provider_information(db, state=state, limit=limit)
    staffing_summary = import_staffing_data(db, ccn_to_facility_id, state=state)
    quality_summary = import_quality_data(db, ccn_to_facility_id, state=state)
    inspection_summary = import_inspection_data(db, ccn_to_facility_id, state=state)
    distributions = _calculate_scores(db, state=state)

    return {
        "facilities_imported": provider_summary["facilities_imported"],
        "missing_records": provider_summary["missing_records"]
        + staffing_summary["missing_records"]
        + quality_summary["missing_records"]
        + inspection_summary["missing_records"],
        "failed_mappings": provider_summary["failed_mappings"]
        + staffing_summary["failed_mappings"]
        + quality_summary["failed_mappings"]
        + inspection_summary["failed_mappings"],
        "score_distributions": distributions,
    }


def _avg_or_zero(value: Optional[float]) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _group_average_scores(db: Session, success_value: int) -> Dict[str, float]:
    row = (
        db.query(
            func.avg(HumanIntelligenceScore.social_profile_score),
            func.avg(HumanIntelligenceScore.family_support_score),
            func.avg(HumanIntelligenceScore.cultural_match_score),
            func.avg(HumanIntelligenceScore.loneliness_risk_score),
            func.avg(HumanIntelligenceScore.transition_risk_score),
            func.avg(HumanIntelligenceScore.future_care_score),
        )
        .join(ResidentOutcome, ResidentOutcome.human_intelligence_score_id == HumanIntelligenceScore.id)
        .filter(ResidentOutcome.successful_adjustment == success_value)
        .one()
    )

    return {
        "social_profile_score": _avg_or_zero(row[0]),
        "family_support_score": _avg_or_zero(row[1]),
        "cultural_match_score": _avg_or_zero(row[2]),
        "loneliness_risk_score": _avg_or_zero(row[3]),
        "transition_risk_score": _avg_or_zero(row[4]),
        "future_care_score": _avg_or_zero(row[5]),
    }


def _parse_json_array(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _to_intelligence_profile_out(profile: FacilityIntelligenceProfile) -> FacilityIntelligenceProfileOut:
    return FacilityIntelligenceProfileOut(
        facility_id=profile.facility_id,
        last_updated=(profile.last_updated.isoformat() if profile.last_updated else ""),
        sources_used=_parse_json_array(profile.sources_used),
        clinical_score=profile.clinical_score,
        family_score=profile.family_score,
        employee_score=profile.employee_score,
        social_score=profile.social_score,
        reputation_score=profile.reputation_score,
        legal_risk_score=profile.legal_risk_score,
        regulatory_risk_score=profile.regulatory_risk_score,
        intelligence_confidence=profile.intelligence_confidence,
        verified_facts=_parse_json_array(profile.verified_facts),
        public_allegations=_parse_json_array(profile.public_allegations),
        public_opinions=_parse_json_array(profile.public_opinions),
        missing_information=_parse_json_array(profile.missing_information),
        positive_signals=_parse_json_array(profile.positive_signals),
        negative_signals=_parse_json_array(profile.negative_signals),
        unresolved_risks=_parse_json_array(profile.unresolved_risks),
        intelligence_summary=profile.intelligence_summary,
        social_energy_index=profile.social_energy_index,
        family_satisfaction_index=profile.family_satisfaction_index,
        staff_stability_index=profile.staff_stability_index,
        regulatory_risk_index=profile.regulatory_risk_index,
        litigation_risk_index=profile.litigation_risk_index,
        cultural_match_signals=profile.cultural_match_signals,
        activity_density_index=profile.activity_density_index,
        community_engagement_index=profile.community_engagement_index,
        clinical_quality_index=profile.clinical_quality_index,
        reputation_index=profile.reputation_index,
    )


@app.on_event("startup")
def startup() -> None:
    # Phase 1 MVP re-initializes schema to guarantee model/table parity.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        state = os.getenv("OPTIME_IMPORT_STATE", "FL")
        limit = env_int("OPTIME_IMPORT_LIMIT", 100)
        app.state.import_summary = run_phase1_ingestion(db, state=state, limit=limit)
    finally:
        db.close()


@app.get("/")
async def root():
    return {
        "project": "OPTIME Nursing",
        "status": "running",
        "version": "0.3.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/import-summary", response_model=ImportSummaryOut)
async def import_summary():
    summary = getattr(app.state, "import_summary", None)
    if not summary:
        raise HTTPException(status_code=404, detail="Import summary not found")
    return summary


@app.get("/facilities", response_model=List[FacilityListOut])
async def get_facilities(q: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Facility).filter(Facility.state == "FL")

    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Facility.name.ilike(like),
                Facility.city.ilike(like),
                Facility.address.ilike(like),
                Facility.zip_code.ilike(like),
                Facility.cms_id.ilike(like),
            )
        )

    facilities = query.order_by(Facility.overall_optime_score.desc().nullslast(), Facility.id.asc()).all()

    if facilities and db.query(FacilityIntelligenceProfile).count() == 0:
        run_intelligence_collection(db)

    intelligence_profiles = {
        profile.facility_id: profile
        for profile in db.query(FacilityIntelligenceProfile).filter(
            FacilityIntelligenceProfile.facility_id.in_([facility.id for facility in facilities])
        ).all()
    }

    payload: List[FacilityListOut] = []
    for facility in facilities:
        profile = intelligence_profiles.get(facility.id)
        payload.append(
            FacilityListOut(
                id=facility.id,
                cms_id=facility.cms_id,
                name=facility.name,
                city=facility.city,
                state=facility.state,
                address=facility.address,
                zip_code=facility.zip_code,
                phone=facility.phone,
                overall_rating=facility.overall_rating,
                staffing_rating=facility.staffing_rating,
                quality_rating=facility.quality_rating,
                inspection_rating=facility.inspection_rating,
                beds=facility.beds,
                medical_quality_score=facility.medical_quality_score,
                staffing_score=facility.staffing_score,
                safety_score=facility.safety_score,
                overall_optime_score=facility.overall_optime_score,
                confidence_level=facility.confidence_level,
                intelligence_confidence=profile.intelligence_confidence if profile else None,
                intelligence_sources_used=_parse_json_array(profile.sources_used) if profile else [],
                intelligence_positive_signals=_parse_json_array(profile.positive_signals) if profile else [],
                intelligence_negative_signals=_parse_json_array(profile.negative_signals) if profile else [],
                family_satisfaction_index=profile.family_satisfaction_index if profile else None,
                staff_stability_index=profile.staff_stability_index if profile else None,
                regulatory_risk_index=profile.regulatory_risk_index if profile else None,
                litigation_risk_index=profile.litigation_risk_index if profile else None,
                social_energy_index=profile.social_energy_index if profile else None,
                community_engagement_index=profile.community_engagement_index if profile else None,
                reputation_index=profile.reputation_index if profile else None,
                cultural_match_signals=profile.cultural_match_signals if profile else None,
            )
        )

    return payload


@app.get("/facilities/{id}", response_model=FacilityDetailsOut)
async def get_facility(id: int, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == id, Facility.state == "FL").first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    quality_rows = db.query(QualityMeasure).filter(QualityMeasure.facility_id == facility.id).all()
    staffing_row = (
        db.query(Staffing)
        .filter(Staffing.facility_id == facility.id)
        .order_by(Staffing.id.desc())
        .first()
    )
    inspection_rows = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()

    medical_components = {
        "cms_rating": round(stars_to_score(facility.quality_rating or facility.overall_rating), 2),
        "hospitalizations": round(invert_percent(_get_measure_score(quality_rows, ["hospital", "rehospital"])), 2),
        "er_visits": round(invert_percent(_get_measure_score(quality_rows, ["emergency", "er visit"])), 2),
        "falls": round(invert_percent(_get_measure_score(quality_rows, ["fall"])), 2),
        "pressure_ulcers": round(invert_percent(_get_measure_score(quality_rows, ["pressure ulcer", "pressure"])), 2),
        "weight_loss": round(invert_percent(_get_measure_score(quality_rows, ["weight loss"])), 2),
    }

    staffing_components = {
        "rn_hours": round(normalize_hours(staffing_row.rn_hours_per_resident_day if staffing_row else None, 0.75), 2),
        "total_staffing": round(normalize_hours(staffing_row.total_nurse_hours_per_resident_day if staffing_row else None, 3.5), 2),
        "agency_staff": 50.0,
        "turnover": 50.0,
    }

    safety_components = {
        "serious_deficiencies": round(inverse_count(sum(item.severe_deficiency_count or 0 for item in inspection_rows), 10), 2),
        "complaints": round(inverse_count(sum(item.payment_denials_count or 0 for item in inspection_rows), 25), 2),
        "fines": 50.0,
        "infection_control": 50.0,
    }

    return FacilityDetailsOut(
        id=facility.id,
        cms_id=facility.cms_id,
        name=facility.name,
        address=facility.address,
        city=facility.city,
        state=facility.state,
        zip_code=facility.zip_code,
        phone=facility.phone,
        overall_rating=facility.overall_rating,
        staffing_rating=facility.staffing_rating,
        quality_rating=facility.quality_rating,
        inspection_rating=facility.inspection_rating,
        beds=facility.beds,
        confidence_level=facility.confidence_level,
        score_breakdown=ScoreBreakdownOut(
            medical_quality_score=facility.medical_quality_score or 0.0,
            staffing_score=facility.staffing_score or 0.0,
            safety_score=facility.safety_score or 0.0,
            overall_optime_score=facility.overall_optime_score or 0.0,
            medical_components=medical_components,
            staffing_components=staffing_components,
            safety_components=safety_components,
        ),
    )


@app.post("/intelligence/run", response_model=IntelligenceRunSummaryOut)
async def run_intelligence(facility_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)):
    if facility_id is not None:
        facility = db.query(Facility).filter(Facility.id == facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

    result = run_intelligence_collection(db, facility_id=facility_id)
    return IntelligenceRunSummaryOut(
        processed=int(result["processed"]),
        facility_ids=[int(value) for value in result["facility_ids"]],
        update_frequency={str(key): str(value) for key, value in result["update_frequency"].items()},
    )


@app.get("/intelligence/facilities/{id}", response_model=FacilityIntelligenceProfileOut)
async def get_facility_intelligence_profile(id: int, db: Session = Depends(get_db)):
    profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == id).first()
    if not profile:
        facility = db.query(Facility).filter(Facility.id == id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        run_intelligence_collection(db, facility_id=id)
        profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == id).first()

    if not profile:
        raise HTTPException(status_code=500, detail="Intelligence profile generation failed")

    return _to_intelligence_profile_out(profile)


@app.get("/intelligence/schedule")
async def intelligence_schedule():
    return {
        "update_frequency": UPDATE_FREQUENCY,
        "policy": "Only publicly available information is used.",
    }


@app.post("/human-intelligence", response_model=HumanIntelligenceOut)
async def create_human_intelligence(payload: HumanIntelligenceIn, db: Session = Depends(get_db)):
    def clip_optional(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return clip_0_100(value)

    record = HumanIntelligenceScore(
        resident_key=payload.resident_key,
        relationship=payload.relationship,
        age_group=payload.age_group,
        social_profile_score=clip_0_100(payload.social_profile_score),
        family_support_score=clip_0_100(payload.family_support_score),
        cultural_match_score=clip_0_100(payload.cultural_match_score),
        loneliness_risk_score=clip_0_100(payload.loneliness_risk_score),
        transition_risk_score=clip_0_100(payload.transition_risk_score),
        future_care_score=clip_0_100(payload.future_care_score),
        social_fit_score=clip_optional(payload.social_fit_score),
        family_fit_score=clip_optional(payload.family_fit_score),
        language_match_score=clip_optional(payload.language_match_score),
        religious_fit_score=clip_optional(payload.religious_fit_score),
        language_fit_score=clip_optional(payload.language_fit_score),
        cultural_fit_score=clip_optional(payload.cultural_fit_score),
        food_fit_score=clip_optional(payload.food_fit_score),
        family_engagement_score=clip_optional(payload.family_engagement_score),
        community_style_score=clip_optional(payload.community_style_score),
        independence_fit_score=clip_optional(payload.independence_fit_score),
        transition_success_probability=clip_optional(payload.transition_success_probability),
        metadata_json=payload.metadata_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return HumanIntelligenceOut.model_validate(record)


@app.post("/human-intelligence/adaptive-response", response_model=AdaptiveQuestionResponseOut)
async def create_adaptive_response(payload: AdaptiveQuestionResponseIn, db: Session = Depends(get_db)):
    record = AdaptiveQuestionResponse(
        resident_key=payload.resident_key,
        question_key=payload.question_key,
        answer=payload.answer,
        signal_type=payload.signal_type,
        signal_json=payload.signal_json,
        weights_json=payload.weights_json,
        impact_explanation=payload.impact_explanation,
        info_gain_score=max(0.0, min(100.0, payload.info_gain_score)),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return AdaptiveQuestionResponseOut.model_validate(record)


@app.post("/resident-outcomes", response_model=ResidentOutcomeOut)
async def create_resident_outcome(payload: ResidentOutcomeIn, db: Session = Depends(get_db)):
    if payload.human_intelligence_score_id is not None:
        score_record = db.query(HumanIntelligenceScore).filter(HumanIntelligenceScore.id == payload.human_intelligence_score_id).first()
        if not score_record:
            raise HTTPException(status_code=404, detail="Human intelligence score not found")

    if payload.facility_id is not None:
        facility = db.query(Facility).filter(Facility.id == payload.facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

    record = ResidentOutcome(
        resident_key=payload.resident_key,
        human_intelligence_score_id=payload.human_intelligence_score_id,
        facility_id=payload.facility_id,
        successful_adjustment=1 if payload.successful_adjustment else 0,
        loneliness_event=1 if payload.loneliness_event else 0,
        relocated_within_24m=1 if payload.relocated_within_24m else 0,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ResidentOutcomeOut(
        id=record.id,
        resident_key=record.resident_key,
        human_intelligence_score_id=record.human_intelligence_score_id,
        facility_id=record.facility_id,
        successful_adjustment=bool(record.successful_adjustment),
        loneliness_event=bool(record.loneliness_event),
        relocated_within_24m=bool(record.relocated_within_24m),
        notes=record.notes,
    )


@app.get("/validation-feedback", response_model=ValidationFeedbackOut)
async def get_validation_feedback(db: Session = Depends(get_db)):
    outcomes_count = db.query(func.count(ResidentOutcome.id)).scalar() or 0
    if outcomes_count == 0:
        return ValidationFeedbackOut(
            outcomes_count=0,
            adjustment_success_rate=0.0,
            loneliness_event_rate=0.0,
            relocation_rate_24m=0.0,
            average_scores_for_successful_adjustment={
                "social_profile_score": 0.0,
                "family_support_score": 0.0,
                "cultural_match_score": 0.0,
                "loneliness_risk_score": 0.0,
                "transition_risk_score": 0.0,
                "future_care_score": 0.0,
            },
            average_scores_for_unsuccessful_adjustment={
                "social_profile_score": 0.0,
                "family_support_score": 0.0,
                "cultural_match_score": 0.0,
                "loneliness_risk_score": 0.0,
                "transition_risk_score": 0.0,
                "future_care_score": 0.0,
            },
        )

    success_count = db.query(func.sum(ResidentOutcome.successful_adjustment)).scalar() or 0
    loneliness_count = db.query(func.sum(ResidentOutcome.loneliness_event)).scalar() or 0
    relocation_count = db.query(func.sum(ResidentOutcome.relocated_within_24m)).scalar() or 0

    return ValidationFeedbackOut(
        outcomes_count=int(outcomes_count),
        adjustment_success_rate=round((float(success_count) / float(outcomes_count)) * 100, 2),
        loneliness_event_rate=round((float(loneliness_count) / float(outcomes_count)) * 100, 2),
        relocation_rate_24m=round((float(relocation_count) / float(outcomes_count)) * 100, 2),
        average_scores_for_successful_adjustment=_group_average_scores(db, 1),
        average_scores_for_unsuccessful_adjustment=_group_average_scores(db, 0),
    )
