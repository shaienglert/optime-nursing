from pydantic import BaseModel


class Facility(BaseModel):
	cms_id: str
	name: str
	address: str
	city: str
	state: str
	zip_code: str
	phone: str
	overall_rating: int
	staffing_rating: int
	quality_rating: int
	inspection_rating: int
	beds: int
	latitude: float
	longitude: float
