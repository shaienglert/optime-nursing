from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Facility(Base):
	__tablename__ = "facilities"

	id = Column(Integer, primary_key=True, index=True)
	cms_id = Column(String(20), unique=True, index=True, nullable=False)
	name = Column(String(255), nullable=False)
	address = Column(String(255), nullable=False)
	city = Column(String(100), index=True, nullable=False)
	state = Column(String(2), index=True, nullable=False)
	zip_code = Column(String(10), nullable=False)
	phone = Column(String(20), nullable=True)
	overall_rating = Column(Integer, nullable=True)
	staffing_rating = Column(Integer, nullable=True)
	quality_rating = Column(Integer, nullable=True)
	inspection_rating = Column(Integer, nullable=True)
	beds = Column(Integer, nullable=True)
	latitude = Column(Float, nullable=True)
	longitude = Column(Float, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	staffing_records = relationship(
		"FacilityStaffing", back_populates="facility", cascade="all, delete-orphan"
	)
	inspections = relationship(
		"FacilityInspection", back_populates="facility", cascade="all, delete-orphan"
	)
	quality_measures = relationship(
		"FacilityQualityMeasure", back_populates="facility", cascade="all, delete-orphan"
	)
	reviews = relationship(
		"FacilityReview", back_populates="facility", cascade="all, delete-orphan"
	)
	scores = relationship(
		"OptimeScore", back_populates="facility", cascade="all, delete-orphan"
	)


class FacilityStaffing(Base):
	__tablename__ = "facility_staffing"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	period_label = Column(String(50), nullable=False)
	staffing_rating = Column(Integer, nullable=True)
	rn_hours_per_resident_day = Column(Float, nullable=True)
	total_nurse_hours_per_resident_day = Column(Float, nullable=True)
	weekend_total_nurse_hours_per_resident_day = Column(Float, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="staffing_records")


class FacilityInspection(Base):
	__tablename__ = "facility_inspections"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	inspection_date = Column(String(20), nullable=False)
	inspection_rating = Column(Integer, nullable=True)
	deficiency_count = Column(Integer, nullable=True)
	severe_deficiency_count = Column(Integer, nullable=True)
	fine_amount = Column(Numeric(12, 2), nullable=True)
	payment_denials_count = Column(Integer, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="inspections")


class FacilityQualityMeasure(Base):
	__tablename__ = "facility_quality_measures"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	measure_code = Column(String(50), nullable=False)
	measure_name = Column(String(255), nullable=False)
	measure_value = Column(Float, nullable=True)
	quality_rating = Column(Integer, nullable=True)
	period_label = Column(String(50), nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="quality_measures")


class FacilityReview(Base):
	__tablename__ = "facility_reviews"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	source = Column(String(50), nullable=False)
	reviewer_hash = Column(String(100), nullable=False)
	rating = Column(Integer, nullable=False)
	review_text = Column(Text, nullable=True)
	sentiment_score = Column(Float, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="reviews")


class OptimeScore(Base):
	__tablename__ = "optime_scores"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	score_version = Column(String(20), nullable=False)
	overall_score = Column(Float, nullable=False)
	fit_score = Column(Float, nullable=True)
	quality_component = Column(Float, nullable=False)
	staffing_component = Column(Float, nullable=False)
	safety_component = Column(Float, nullable=False)
	reviews_component = Column(Float, nullable=False)
	value_component = Column(Float, nullable=False)
	metadata_json = Column(Text, nullable=True)
	computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="scores")
