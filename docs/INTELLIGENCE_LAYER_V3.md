# OPTIME Deep Intelligence Layer V3

## Goal
Move beyond directory-style matching toward adjustment prediction.

V3 adds seven new intelligence layers focused on the first 12 months after move-in:
- Transition intelligence
- Friendship intelligence
- Family trust intelligence
- Dining intelligence
- Independence intelligence
- Visit intelligence
- Red flag intelligence

Primary success metric:
- Probability of successful adjustment after 12 months

## Source Policy
- Never invent information.
- Missing values remain null.
- Store source URLs.
- Store collection timestamps.
- Separate facts from opinions.
- Separate historical issues from current issues.
- Separate allegations from verified findings.

## Current Output
Generated file:
- `database/community_deep_intelligence_v3.json`

Each community record contains:
- `sources`
- `transition_intelligence`
- `friendship_intelligence`
- `family_trust_intelligence`
- `dining_intelligence`
- `independence_intelligence`
- `visit_intelligence`
- `red_flag_intelligence`
- `success_prediction`

## Layer Definitions

### 1. Transition Intelligence
Purpose:
- Estimate how well a resident may adjust during the move-in period.

Current collected fields:
- `move_in_transition_program`
- `clinical_transition_support`
- `care_levels_available`
- `regulatory_support_context`

Current derived field:
- `transition_readiness_score`

Current data reality:
- `care_levels_available` can be populated from inventory.
- CMS ratings can provide limited regulatory support context.
- Dedicated transition-program evidence is not available in current local datasets, so those fields remain null.

### 2. Friendship Intelligence
Purpose:
- Estimate whether the community can support peer connection and belonging.

Current collected fields:
- `resident_similarity_signals`
- `friendship_group_signals`
- `community_size_beds`
- `engagement_evidence`

Current derived field:
- `friendship_potential_score`

Current data reality:
- Community size can be populated from inventory.
- Direct friendship and social-circle evidence is not currently available, so those fields remain null.

### 3. Family Trust Intelligence
Purpose:
- Estimate how much verifiable information exists for a family to trust the placement process.

Current collected fields:
- `official_website_present`
- `state_license_profile_present`
- `cms_profile_present`
- `phone_present`

Current derived field:
- `family_trust_score`

Current data reality:
- This layer is partially supported today because verified URLs and contact presence exist for many communities.

### 4. Dining Intelligence
Purpose:
- Track food-related experience and dietary fit.

Current collected fields:
- `food_quality_signals`
- `dining_flexibility`
- `dietary_accommodations`
- `kosher_meals`
- `meal_service_details`

Current data reality:
- No verified dining-attribute dataset is currently available locally, so these fields remain null.

### 5. Independence Intelligence
Purpose:
- Estimate how well the community supports autonomy.

Current collected fields:
- `independent_living_available`
- `assisted_living_available`
- `memory_care_available`
- `transportation_services`
- `mobility_support_signals`

Current derived field:
- `independence_support_score`

Current data reality:
- Care type availability is supported by inventory.
- Transportation and mobility detail are not currently verified in the local source base.

### 6. Visit Intelligence
Purpose:
- Estimate how practical and supportive family visitation will be.

Current collected fields:
- `family_distance`
- `travel_time`
- `visit_flexibility_signals`
- `parking_access`
- `family_visit_support`

Current derived field:
- `visit_support_score`

Current data reality:
- This layer requires family reference-location data plus community visitation evidence. Neither exists for all communities in the current dataset, so these fields remain null.

### 7. Red Flag Intelligence
Purpose:
- Separate serious warning signs from general quality signals.

Current verified findings:
- `low_overall_rating`
- `low_staffing_rating`
- `low_inspection_rating`
- `ownership_change_last_12m`

Current derived field:
- `red_flag_level`

Current data reality:
- This is the strongest V3 layer today because it can use verified CMS ratings and ownership-change flags.

## 12-Month Adjustment Probability

Field:
- `success_prediction.twelve_month_success_adjustment_probability`

Current method:
- `baseline_proxy_v1`

Important limitation:
- This is a documented proxy, not an outcome-validated model.
- The field is null when verified inputs are insufficient.
- No resident outcome data is used yet.

Current proxy inputs:
- CMS ratings
- Verified source count
- Ownership change flag
- Care type availability

## What V3 Improves Over V2
- Shifts the model target from general intelligence coverage to adjustment success.
- Adds family-trust and red-flag framing, which are closer to placement outcomes.
- Creates a clean schema for future resident-level transition and outcome data.

## What Is Still Missing
The current local datasets do not yet provide verified evidence for most of the following:
- Move-in transition programs
- Friendship and resident similarity signals
- Dining quality details
- Family visit support details
- Transportation and mobility specifics
- Resident-level 6-month and 12-month outcomes

## Next Data Requirements
To make V3 operationally predictive instead of structurally prepared, OPTIME needs source-backed feeds for:
- Review text and theme extraction
- Workforce/job-board monitoring
- Activities and dining pages
- Leadership roster history
- Family tour and visit observations
- Resident outcome tracking

## Summary
V3 is now structurally ready for deeper adjustment prediction.

It does not fabricate missing fields.
It preserves provenance.
It exposes a 12-month adjustment probability field while clearly marking the current method as a baseline proxy until real outcome data is available.