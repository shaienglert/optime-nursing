from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AnswerState(str, PyEnum):
	YES = "YES"
	NO = "NO"
	UNKNOWN = "UNKNOWN"
	LIMITED = "LIMITED"


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
	intelligence_profile = relationship(
		"FacilityIntelligenceProfile", back_populates="facility", uselist=False, cascade="all, delete-orphan"
	)
	portal_users = relationship("FacilityUser", back_populates="facility", cascade="all, delete-orphan")
	portal_capabilities = relationship("FacilityCapability", back_populates="facility", cascade="all, delete-orphan")
	portal_photos = relationship("FacilityPhoto", back_populates="facility", cascade="all, delete-orphan")
	portal_activity_categories = relationship("FacilityActivityCategory", back_populates="facility", cascade="all, delete-orphan")
	verification_memory_records = relationship("FacilityVerificationMemory", back_populates="facility", cascade="all, delete-orphan")
	verification_requests = relationship("FacilityVerificationRequest", back_populates="facility", cascade="all, delete-orphan")
	verification_responses = relationship("FacilityVerificationResponse", back_populates="facility", cascade="all, delete-orphan")
	profile_completeness = relationship("FacilityProfileCompleteness", back_populates="facility", uselist=False, cascade="all, delete-orphan")
	domain_allowlist = relationship("FacilityDomainAllowlist", back_populates="facility", cascade="all, delete-orphan")
	identity_challenges = relationship("ProviderIdentityChallenge", back_populates="facility", cascade="all, delete-orphan")
	license_records = relationship("FacilityLicenseRecord", back_populates="facility", cascade="all, delete-orphan")
	audit_logs = relationship("FacilityAuditLog", back_populates="facility", cascade="all, delete-orphan")


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


class FacilityIntelligenceProfile(Base):
	__tablename__ = "facility_intelligence_profiles"

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), unique=True, index=True, nullable=False)
	last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
	sources_used = Column(Text, nullable=False, default="[]")
	clinical_score = Column(Float, nullable=False, default=0.0)
	family_score = Column(Float, nullable=False, default=0.0)
	employee_score = Column(Float, nullable=False, default=0.0)
	social_score = Column(Float, nullable=False, default=0.0)
	reputation_score = Column(Float, nullable=False, default=0.0)
	legal_risk_score = Column(Float, nullable=False, default=0.0)
	regulatory_risk_score = Column(Float, nullable=False, default=0.0)
	social_energy_index = Column(Float, nullable=False, default=0.0)
	family_satisfaction_index = Column(Float, nullable=False, default=0.0)
	staff_stability_index = Column(Float, nullable=False, default=0.0)
	regulatory_risk_index = Column(Float, nullable=False, default=0.0)
	litigation_risk_index = Column(Float, nullable=False, default=0.0)
	cultural_match_signals = Column(Float, nullable=False, default=0.0)
	activity_density_index = Column(Float, nullable=False, default=0.0)
	community_engagement_index = Column(Float, nullable=False, default=0.0)
	clinical_quality_index = Column(Float, nullable=False, default=0.0)
	reputation_index = Column(Float, nullable=False, default=0.0)
	intelligence_confidence = Column(Float, nullable=False, default=0.0)
	verified_facts = Column(Text, nullable=False, default="[]")
	public_allegations = Column(Text, nullable=False, default="[]")
	public_opinions = Column(Text, nullable=False, default="[]")
	missing_information = Column(Text, nullable=False, default="[]")
	positive_signals = Column(Text, nullable=False, default="[]")
	negative_signals = Column(Text, nullable=False, default="[]")
	signal_details = Column(Text, nullable=False, default="[]")
	unresolved_risks = Column(Text, nullable=False, default="[]")
	visual_hero_image = Column(Text, nullable=False, default="{}")
	visual_gallery_images = Column(Text, nullable=False, default="[]")
	visual_lifestyle_tags = Column(Text, nullable=False, default="[]")
	visual_confidence_score = Column(Float, nullable=False, default=0.0)
	visual_coverage_score = Column(Float, nullable=False, default=0.0)
	intelligence_summary = Column(Text, nullable=False, default="")
	update_frequency = Column(Text, nullable=False, default="{}")
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="intelligence_profile")


class FacilityUser(Base):
	__tablename__ = "facility_users"
	__table_args__ = (
		UniqueConstraint("facility_id", "email", name="uq_facility_users_facility_email"),
		Index("ix_facility_users_facility_role", "facility_id", "role"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	email = Column(String(255), nullable=False)
	password_hash = Column(String(255), nullable=False)
	full_name = Column(String(255), nullable=True)
	role = Column(String(40), nullable=False)  # admin, marketing, admissions, activities_coordinator
	is_active = Column(Boolean, nullable=False, default=True)
	is_verified = Column(Boolean, nullable=False, default=False)
	verification_sent_at = Column(DateTime(timezone=True), nullable=True)
	verification_completed_at = Column(DateTime(timezone=True), nullable=True)
	verification_method = Column(String(40), nullable=True)
	verified_badge = Column(Boolean, nullable=False, default=False)
	next_reverification_due_at = Column(DateTime(timezone=True), nullable=True)
	last_login_at = Column(DateTime(timezone=True), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="portal_users")


class FacilityDomainAllowlist(Base):
	__tablename__ = "facility_domain_allowlist"
	__table_args__ = (
		UniqueConstraint("facility_id", "domain", name="uq_facility_domain_allowlist_facility_domain"),
		Index("ix_facility_domain_allowlist_facility_active", "facility_id", "is_active"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	domain = Column(String(255), nullable=False)
	is_parent_org = Column(Boolean, nullable=False, default=False)
	is_active = Column(Boolean, nullable=False, default=True)
	manual_approval_required = Column(Boolean, nullable=False, default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="domain_allowlist")


class ProviderIdentityChallenge(Base):
	__tablename__ = "provider_identity_challenges"
	__table_args__ = (
		Index("ix_provider_identity_challenges_user_status", "user_id", "status"),
		Index("ix_provider_identity_challenges_expires_at", "expires_at"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	user_id = Column(Integer, ForeignKey("facility_users.id"), index=True, nullable=False)
	email = Column(String(255), nullable=False)
	code_hash = Column(String(255), nullable=False)
	verification_method = Column(String(40), nullable=False, default="EMAIL_OTP")
	verification_sent_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
	verification_completed_at = Column(DateTime(timezone=True), nullable=True)
	expires_at = Column(DateTime(timezone=True), nullable=False)
	status = Column(String(30), nullable=False, default="PENDING")
	attempt_count = Column(Integer, nullable=False, default=0)
	ip_address = Column(String(120), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="identity_challenges")


class FacilityLicenseRecord(Base):
	__tablename__ = "facility_license_records"
	__table_args__ = (
		Index("ix_facility_license_records_facility_status", "facility_id", "status"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	cms_provider_id = Column(String(40), nullable=True)
	ahca_license_number = Column(String(80), nullable=True)
	medicare_provider_number = Column(String(80), nullable=True)
	legal_name = Column(String(255), nullable=True)
	legal_address = Column(String(255), nullable=True)
	domain = Column(String(255), nullable=True)
	status = Column(String(40), nullable=False, default="PENDING")
	verified_at = Column(DateTime(timezone=True), nullable=True)
	verification_notes = Column(Text, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="license_records")


class FacilityAuditLog(Base):
	__tablename__ = "facility_audit_logs"
	__table_args__ = (
		Index("ix_facility_audit_logs_facility_timestamp", "facility_id", "timestamp"),
		Index("ix_facility_audit_logs_reverted", "is_reverted"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	user_id = Column(Integer, ForeignKey("facility_users.id"), index=True, nullable=False)
	field_name = Column(String(120), nullable=False)
	old_value = Column(Text, nullable=True)
	new_value = Column(Text, nullable=True)
	timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	ip_address = Column(String(120), nullable=True)
	user_role = Column(String(40), nullable=False)
	is_reverted = Column(Boolean, nullable=False, default=False)
	reverted_at = Column(DateTime(timezone=True), nullable=True)
	reverted_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)

	facility = relationship("Facility", back_populates="audit_logs")


class FacilityCapability(Base):
	__tablename__ = "facility_capabilities"
	__table_args__ = (
		UniqueConstraint("facility_id", "capability", name="uq_facility_capabilities_facility_capability"),
		Index("ix_facility_capabilities_facility_value", "facility_id", "value"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	capability = Column(String(120), nullable=False)
	value = Column(SAEnum(AnswerState, name="answer_state_enum", native_enum=False), nullable=False, default=AnswerState.UNKNOWN)
	source = Column(String(60), nullable=False, default="provider_portal")
	verified_at = Column(DateTime(timezone=True), nullable=True)
	expires_at = Column(DateTime(timezone=True), nullable=True)
	confidence = Column(Float, nullable=False, default=0.0)
	verification_count = Column(Integer, nullable=False, default=0)
	last_updated_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)
	notes = Column(Text, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="portal_capabilities")


class FacilityPhoto(Base):
	__tablename__ = "facility_photos"
	__table_args__ = (
		Index("ix_facility_photos_facility_category", "facility_id", "category"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	category = Column(String(60), nullable=False)
	url = Column(String(1000), nullable=False)
	caption = Column(String(255), nullable=True)
	source = Column(String(60), nullable=False, default="provider_portal")
	uploaded_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)
	uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	is_active = Column(Boolean, nullable=False, default=True)

	facility = relationship("Facility", back_populates="portal_photos")


class FacilityActivityCategory(Base):
	__tablename__ = "facility_activity_categories"
	__table_args__ = (
		UniqueConstraint("facility_id", "category", name="uq_facility_activity_categories_facility_category"),
		Index("ix_facility_activity_categories_facility_availability", "facility_id", "availability"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	category = Column(String(40), nullable=False)  # movie, music, lecture, gardening, exercise, religious, social
	availability = Column(SAEnum(AnswerState, name="answer_state_enum", native_enum=False), nullable=False, default=AnswerState.UNKNOWN)
	confidence = Column(Float, nullable=False, default=0.0)
	import_source = Column(String(60), nullable=True)
	last_imported_at = Column(DateTime(timezone=True), nullable=True)
	updated_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="portal_activity_categories")


class FacilityVerificationMemory(Base):
	__tablename__ = "facility_verification_memory"
	__table_args__ = (
		UniqueConstraint("facility_id", "capability", name="uq_facility_verification_memory_facility_capability"),
		Index("ix_facility_verification_memory_facility_confidence", "facility_id", "confidence"),
		Index("ix_facility_verification_memory_expires_at", "expires_at"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	capability = Column(String(120), nullable=False)
	value = Column(SAEnum(AnswerState, name="answer_state_enum", native_enum=False), nullable=False)
	verification_source = Column(String(60), nullable=False)
	verified_at = Column(DateTime(timezone=True), nullable=False)
	expires_at = Column(DateTime(timezone=True), nullable=False)
	confidence = Column(Float, nullable=False, default=0.0)
	verification_count = Column(Integer, nullable=False, default=1)
	conflict_count = Column(Integer, nullable=False, default=0)
	last_request_id = Column(Integer, ForeignKey("facility_verification_requests.id"), nullable=True)
	last_response_id = Column(Integer, ForeignKey("facility_verification_responses.id"), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="verification_memory_records")


class FacilityVerificationRequest(Base):
	__tablename__ = "facility_verification_requests"
	__table_args__ = (
		Index("ix_facility_verification_requests_facility_status", "facility_id", "status"),
		Index("ix_facility_verification_requests_sent_at", "sent_at"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	requested_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)
	channel = Column(String(40), nullable=False, default="provider_portal")
	subject = Column(String(255), nullable=True)
	body = Column(Text, nullable=True)
	status = Column(String(30), nullable=False, default="sent")
	sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="verification_requests")


class FacilityVerificationResponse(Base):
	__tablename__ = "facility_verification_responses"
	__table_args__ = (
		Index("ix_facility_verification_responses_request", "request_id"),
		Index("ix_facility_verification_responses_facility_capability", "facility_id", "capability"),
		Index("ix_facility_verification_responses_verified_at", "verified_at"),
	)

	id = Column(Integer, primary_key=True, index=True)
	request_id = Column(Integer, ForeignKey("facility_verification_requests.id"), index=True, nullable=False)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	responded_by_user_id = Column(Integer, ForeignKey("facility_users.id"), nullable=True)
	capability = Column(String(120), nullable=False)
	value = Column(SAEnum(AnswerState, name="answer_state_enum", native_enum=False), nullable=False)
	source = Column(String(60), nullable=False, default="provider_portal")
	verified_at = Column(DateTime(timezone=True), nullable=False)
	expires_at = Column(DateTime(timezone=True), nullable=False)
	confidence = Column(Float, nullable=False, default=0.0)
	notes = Column(Text, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	facility = relationship("Facility", back_populates="verification_responses")


class FacilityProfileCompleteness(Base):
	__tablename__ = "facility_profile_completeness"
	__table_args__ = (
		UniqueConstraint("facility_id", name="uq_facility_profile_completeness_facility"),
		Index("ix_facility_profile_completeness_overall", "overall_score"),
	)

	id = Column(Integer, primary_key=True, index=True)
	facility_id = Column(Integer, ForeignKey("facilities.id"), index=True, nullable=False)
	medical_completeness = Column(Float, nullable=False, default=0.0)
	lifestyle_completeness = Column(Float, nullable=False, default=0.0)
	dining_completeness = Column(Float, nullable=False, default=0.0)
	photos_completeness = Column(Float, nullable=False, default=0.0)
	activity_completeness = Column(Float, nullable=False, default=0.0)
	overall_score = Column(Float, nullable=False, default=0.0)
	calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at = Column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	facility = relationship("Facility", back_populates="profile_completeness")
