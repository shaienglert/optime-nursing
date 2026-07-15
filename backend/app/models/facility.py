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
	medical_quality_score = Column(Float, nullable=True)
	staffing_score = Column(Float, nullable=True)
	safety_score = Column(Float, nullable=True)
	overall_optime_score = Column(Float, nullable=True)
	medical_quality_confidence = Column(String(30), nullable=True)
	staffing_confidence = Column(String(30), nullable=True)
	safety_confidence = Column(String(30), nullable=True)
	overall_confidence = Column(String(30), nullable=True)
	source_name = Column(String(100), nullable=True)
	source_date = Column(String(30), nullable=True)
	import_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
	confidence_level = Column(String(30), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	staffing_records = relationship("Staffing", back_populates="facility", cascade="all, delete-orphan")
	inspections = relationship("Inspection", back_populates="facility", cascade="all, delete-orphan")
	quality_measures = relationship("QualityMeasure", back_populates="facility", cascade="all, delete-orphan")
	reviews = relationship(
		"FacilityReview", back_populates="facility", cascade="all, delete-orphan"
	)
	scores = relationship(
		"OptimeScore", back_populates="facility", cascade="all, delete-orphan"
	)


class Staffing(Base):
	__tablename__ = "staffing"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	period_label = Column(String(50), nullable=False)
	staffing_rating = Column(Integer, nullable=True)
	rn_hours_per_resident_day = Column(Float, nullable=True)
	total_nurse_hours_per_resident_day = Column(Float, nullable=True)
	weekend_total_nurse_hours_per_resident_day = Column(Float, nullable=True)
	source_name = Column(String(100), nullable=True)
	source_date = Column(String(30), nullable=True)
	import_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
	confidence_level = Column(String(30), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="staffing_records")


class Inspection(Base):
	__tablename__ = "inspections"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	inspection_date = Column(String(20), nullable=False)
	inspection_rating = Column(Integer, nullable=True)
	deficiency_count = Column(Integer, nullable=True)
	severe_deficiency_count = Column(Integer, nullable=True)
	fine_amount = Column(Numeric(12, 2), nullable=True)
	payment_denials_count = Column(Integer, nullable=True)
	source_name = Column(String(100), nullable=True)
	source_date = Column(String(30), nullable=True)
	import_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
	confidence_level = Column(String(30), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="inspections")


class QualityMeasure(Base):
	__tablename__ = "quality_measures"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	measure_code = Column(String(50), nullable=False)
	measure_name = Column(String(255), nullable=False)
	measure_value = Column(Float, nullable=True)
	quality_rating = Column(Integer, nullable=True)
	period_label = Column(String(50), nullable=False)
	source_name = Column(String(100), nullable=True)
	source_date = Column(String(30), nullable=True)
	import_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
	confidence_level = Column(String(30), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="quality_measures")


# Backward-compatible aliases for existing imports.
FacilityStaffing = Staffing
FacilityInspection = Inspection
FacilityQualityMeasure = QualityMeasure
Inspections = Inspection
QualityMeasures = QualityMeasure


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


class HumanIntelligenceScore(Base):
	__tablename__ = "human_intelligence_scores"

	id = Column(Integer, primary_key=True, index=True)
	resident_key = Column(String(120), index=True, nullable=False)
	relationship = Column(String(40), nullable=True)
	age_group = Column(String(20), nullable=True)
	social_profile_score = Column(Float, nullable=False)
	family_support_score = Column(Float, nullable=False)
	cultural_match_score = Column(Float, nullable=False)
	loneliness_risk_score = Column(Float, nullable=False)
	transition_risk_score = Column(Float, nullable=False)
	future_care_score = Column(Float, nullable=False)
	social_fit_score = Column(Float, nullable=True)
	family_fit_score = Column(Float, nullable=True)
	language_match_score = Column(Float, nullable=True)
	religious_fit_score = Column(Float, nullable=True)
	language_fit_score = Column(Float, nullable=True)
	cultural_fit_score = Column(Float, nullable=True)
	food_fit_score = Column(Float, nullable=True)
	family_engagement_score = Column(Float, nullable=True)
	community_style_score = Column(Float, nullable=True)
	independence_fit_score = Column(Float, nullable=True)
	transition_success_probability = Column(Float, nullable=True)
	metadata_json = Column(Text, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveQuestionResponse(Base):
	__tablename__ = "adaptive_question_responses"

	id = Column(Integer, primary_key=True, index=True)
	resident_key = Column(String(120), index=True, nullable=False)
	question_key = Column(String(120), index=True, nullable=False)
	answer = Column(Text, nullable=False)
	signal_type = Column(String(120), nullable=False)
	signal_json = Column(Text, nullable=True)
	weights_json = Column(Text, nullable=True)
	impact_explanation = Column(Text, nullable=False)
	info_gain_score = Column(Float, nullable=False, default=0.0)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ResidentOutcome(Base):
	__tablename__ = "resident_outcomes"

	id = Column(Integer, primary_key=True, index=True)
	resident_key = Column(String(120), index=True, nullable=False)
	human_intelligence_score_id = Column(Integer, ForeignKey("human_intelligence_scores.id"), index=True, nullable=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=True)
	successful_adjustment = Column(Integer, nullable=False, default=0)
	loneliness_event = Column(Integer, nullable=False, default=0)
	relocated_within_24m = Column(Integer, nullable=False, default=0)
	notes = Column(Text, nullable=True)
	recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
