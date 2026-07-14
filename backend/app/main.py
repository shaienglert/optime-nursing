from fastapi import FastAPI

from app.models.facility import Facility

app = FastAPI(
	title="OPTIME Nursing API",
	version="0.1.0",
	description="Decision Intelligence for Senior Living"
)

sample_facility = Facility(
	cms_id="123456",
	name="Sunrise Senior Care Center",
	address="123 Main St",
	city="Dallas",
	state="TX",
	zip_code="75201",
	phone="(214) 555-0100",
	overall_rating=4,
	staffing_rating=3,
	quality_rating=5,
	inspection_rating=4,
	beds=120,
	latitude=32.7767,
	longitude=-96.7970,
)


@app.get("/")
async def root():
	return {
		"project": "OPTIME Nursing",
		"status": "running",
		"version": "0.1.0"
	}


@app.get("/health")
async def health():
	return {
		"status": "healthy"
	}


@app.get("/facility", response_model=Facility)
async def get_facility():
	return sample_facility
