# Facility Questionnaire Definition V1

## Answer State Standard
Every questionnaire answer must be stored as one of:
- YES
- NO
- UNKNOWN
- LIMITED

Implementation notes:
- Enforced at model layer via shared enum in [backend/app/models/facility.py](backend/app/models/facility.py).
- Applied to:
  - facility_capabilities.value
  - facility_activity_categories.availability
  - facility_verification_memory.value
  - facility_verification_responses.value

## Sections

### 1. Medical
- medical_24_7_nursing: 24/7 nursing
- medical_physician_availability: Physician availability
- medical_memory_care: Memory care

### 2. Rehabilitation
- rehab_speech_therapy: Speech therapy
- rehab_physical_therapy: Physical therapy
- rehab_occupational_therapy: Occupational therapy
- rehab_stroke_support: Stroke rehabilitation
- rehab_parkinson_support: Parkinson support

### 3. Dining
- dining_gluten_free: Gluten free
- dining_kosher: Kosher
- dining_vegetarian: Vegetarian
- dining_diabetic_meals: Diabetic meals

### 4. Lifestyle
- lifestyle_movies: Movies
- lifestyle_music: Music
- lifestyle_gardening: Gardening
- lifestyle_pool: Pool
- lifestyle_fitness_center: Fitness center
- lifestyle_religious_services: Religious services
- lifestyle_transportation: Transportation

### 5. Housing
- housing_kitchenette: Kitchenette
- housing_balcony: Balcony
- housing_studio: Studio
- housing_one_bedroom: One bedroom
- housing_pets_allowed: Pets allowed

### 6. Accessibility
- accessibility_walker_support: Walker support
- accessibility_wheelchair_access: Wheelchair accessibility
- accessibility_fall_prevention: Fall prevention
- accessibility_transfer_assistance: Transfer assistance

### 7. Future Care Continuum
- continuum_assisted_living: Assisted living available
- continuum_memory_care: Memory care available
- continuum_skilled_nursing: Skilled nursing available
- continuum_rehabilitation: Rehabilitation available
- continuum_on_campus_progression: On-campus progression across care levels

## Source of Truth Module
The canonical questionnaire definition is implemented in:
- [backend/app/models/facility_questionnaire.py](backend/app/models/facility_questionnaire.py)

Exports:
- ANSWER_STATES
- FACILITY_QUESTIONNAIRE_V1
- facility_questionnaire_v1_flat()
