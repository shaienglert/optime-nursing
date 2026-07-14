import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.facility import (
	Facility,
	FacilityInspection,
	FacilityQualityMeasure,
	FacilityReview,
	FacilityStaffing,
	OptimeScore,
)

app = FastAPI(
	title="OPTIME Nursing API",
	version="0.2.0",
	description="Decision Intelligence for Senior Living with normalized data model",
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


class FacilityOut(BaseModel):
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
	latitude: Optional[float] = None
	longitude: Optional[float] = None

	model_config = ConfigDict(from_attributes=True)


class FacilityStaffingOut(BaseModel):
	id: int
	facility_id: int
	period_label: str
	staffing_rating: Optional[int] = None
	rn_hours_per_resident_day: Optional[float] = None
	total_nurse_hours_per_resident_day: Optional[float] = None
	weekend_total_nurse_hours_per_resident_day: Optional[float] = None

	model_config = ConfigDict(from_attributes=True)


class FacilityInspectionOut(BaseModel):
	id: int
	facility_id: int
	inspection_date: str
	inspection_rating: Optional[int] = None
	deficiency_count: Optional[int] = None
	severe_deficiency_count: Optional[int] = None
	fine_amount: Optional[float] = None
	payment_denials_count: Optional[int] = None

	model_config = ConfigDict(from_attributes=True)


class FacilityQualityMeasureOut(BaseModel):
	id: int
	facility_id: int
	measure_code: str
	measure_name: str
	measure_value: Optional[float] = None
	quality_rating: Optional[int] = None
	period_label: str

	model_config = ConfigDict(from_attributes=True)


class OptimeScoreOut(BaseModel):
	id: int
	facility_id: int
	score_version: str
	overall_score: float
	fit_score: Optional[float] = None
	quality_component: float
	staffing_component: float
	safety_component: float
	reviews_component: float
	value_component: float
	metadata_json: Optional[str] = None

	model_config = ConfigDict(from_attributes=True)


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


def seed_sample_data(db: Session) -> None:
	if db.query(Facility).count() > 0:
		return

	facilities = [
		Facility(
			cms_id="105001",
			name="Sunrise Senior Living Miami",
			address="123 Biscayne Blvd",
			city="Miami",
			state="FL",
			zip_code="33132",
			phone="3055550101",
			overall_rating=4,
			staffing_rating=3,
			quality_rating=4,
			inspection_rating=4,
			beds=140,
			latitude=25.7617,
			longitude=-80.1918,
		),
		Facility(
			cms_id="105002",
			name="Brookdale Boca Raton",
			address="456 Glades Rd",
			city="Boca Raton",
			state="FL",
			zip_code="33431",
			phone="5615550110",
			overall_rating=5,
			staffing_rating=4,
			quality_rating=5,
			inspection_rating=4,
			beds=120,
			latitude=26.3683,
			longitude=-80.1289,
		),
		Facility(
			cms_id="105003",
			name="The Palace Coral Gables",
			address="789 Ponce de Leon Blvd",
			city="Coral Gables",
			state="FL",
			zip_code="33134",
			phone="3055550199",
			overall_rating=4,
			staffing_rating=4,
			quality_rating=4,
			inspection_rating=5,
			beds=98,
			latitude=25.7215,
			longitude=-80.2684,
		),
	]
	db.add_all(facilities)
	db.commit()

	persisted = db.query(Facility).all()
	for facility in persisted:
		db.add(
			FacilityStaffing(
				facility_id=facility.id,
				period_label="2026-Q2",
				staffing_rating=facility.staffing_rating,
				rn_hours_per_resident_day=0.75,
				total_nurse_hours_per_resident_day=3.8,
				weekend_total_nurse_hours_per_resident_day=3.4,
			)
		)
		db.add(
			FacilityInspection(
				facility_id=facility.id,
				inspection_date="2026-05-15",
				inspection_rating=facility.inspection_rating,
				deficiency_count=2,
				severe_deficiency_count=0,
				fine_amount=0,
				payment_denials_count=0,
			)
		)
		db.add(
			FacilityQualityMeasure(
				facility_id=facility.id,
				measure_code="QM_REHOSP",
				measure_name="Short-stay rehospitalization",
				measure_value=83.5,
				quality_rating=facility.quality_rating,
				period_label="2026-Q2",
			)
		)
		db.add(
			FacilityReview(
				facility_id=facility.id,
				source="family_portal",
				reviewer_hash=f"sample-reviewer-{facility.id}",
				rating=4,
				review_text="Caring staff and clean environment.",
				sentiment_score=0.84,
			)
		)
		db.add(
			OptimeScore(
				facility_id=facility.id,
				score_version="v1",
				overall_score=84.0,
				fit_score=81.0,
				quality_component=29.4,
				staffing_component=20.0,
				safety_component=16.8,
				reviews_component=8.0,
				value_component=9.8,
				metadata_json='{"source":"sample_seed"}',
			)
		)

	db.commit()


@app.on_event("startup")
def startup() -> None:
	Base.metadata.create_all(bind=engine)
	db = SessionLocal()
	try:
		seed_sample_data(db)
	finally:
		db.close()


@app.get("/")
async def root():
	return {
		"project": "OPTIME Nursing",
		"status": "running",
		"version": "0.2.0",
	}


@app.get("/health")
async def health():
	return {"status": "healthy"}


@app.get(
	"/facilities",
	response_model=List[FacilityOut],
	summary="List facilities",
	description="Returns all nursing facilities from the normalized Facility table.",
)
async def get_facilities(db: Session = Depends(get_db)):
	return db.query(Facility).order_by(Facility.id.asc()).all()


@app.get(
	"/facilities/{id}",
	response_model=FacilityOut,
	summary="Get a facility",
	description="Returns one facility by numeric id.",
)
async def get_facility(id: int, db: Session = Depends(get_db)):
	facility = db.query(Facility).filter(Facility.id == id).first()
	if not facility:
		raise HTTPException(status_code=404, detail="Facility not found")
	return facility


@app.get(
	"/facilities/{id}/staffing",
	response_model=List[FacilityStaffingOut],
	summary="Get facility staffing history",
	description="Returns staffing records for a facility.",
)
async def get_facility_staffing(id: int, db: Session = Depends(get_db)):
	return (
		db.query(FacilityStaffing)
		.filter(FacilityStaffing.facility_id == id)
		.order_by(FacilityStaffing.id.asc())
		.all()
	)


@app.get(
	"/facilities/{id}/inspections",
	response_model=List[FacilityInspectionOut],
	summary="Get facility inspections",
	description="Returns inspection and enforcement records for a facility.",
)
async def get_facility_inspections(id: int, db: Session = Depends(get_db)):
	return (
		db.query(FacilityInspection)
		.filter(FacilityInspection.facility_id == id)
		.order_by(FacilityInspection.id.asc())
		.all()
	)


@app.get(
	"/facilities/{id}/quality",
	response_model=List[FacilityQualityMeasureOut],
	summary="Get facility quality measures",
	description="Returns quality measure rows for a facility.",
)
async def get_facility_quality(id: int, db: Session = Depends(get_db)):
	return (
		db.query(FacilityQualityMeasure)
		.filter(FacilityQualityMeasure.facility_id == id)
		.order_by(FacilityQualityMeasure.id.asc())
		.all()
	)


@app.get(
	"/facilities/{id}/score",
	response_model=OptimeScoreOut,
	summary="Get latest OPTIME score",
	description="Returns the latest score snapshot for a facility.",
)
async def get_facility_score(id: int, db: Session = Depends(get_db)):
	score = (
		db.query(OptimeScore)
		.filter(OptimeScore.facility_id == id)
		.order_by(OptimeScore.computed_at.desc(), OptimeScore.id.desc())
		.first()
	)
	if not score:
		raise HTTPException(status_code=404, detail="Score not found")
	return score
