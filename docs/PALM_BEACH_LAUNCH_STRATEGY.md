# OPTIME Palm Beach County Launch Strategy

## Objective
Launch OPTIME in Palm Beach County with a structured provider acquisition plan that prioritizes high-fit communities and rapid go-live potential.

## 1. Market Mapping: Identify All Senior Living Communities

### Scope
- Geography: Palm Beach County, Florida
- Facility universe:
  - Independent Living
  - Assisted Living
  - Memory Care
  - Skilled Nursing

### Data Collection Sources
- Florida AHCA facility directories
- CMS Provider Information and Nursing Home datasets
- State licensing records (ALF / memory care where applicable)
- County and municipal business registries
- Operator websites and facility location pages
- Google Maps and major senior living aggregators (for cross-validation)

### Data Fields to Capture Per Community
- Facility name
- Address, city, zip
- Primary care type
- Secondary care types
- Licensed capacity (if available)
- Operator name
- Website
- Contact channels (phone, email, intake form)
- Source reliability (high/medium/low)

## 2. Classification Framework

### A. Care-Level Classification
Each community is assigned one or more labels:
- Independent
- Assisted Living
- Memory Care
- Skilled Nursing

### B. Operator-Type Classification
Each community is assigned one operator label:
- Chains
  - Multi-state or national operators with standardized brand and centralized intake
- Regional operators
  - Multi-facility operators concentrated in Florida/Southeast
- Independent operators
  - Single-site or small local ownership groups

### C. Decision Rules
- If ownership entity controls >= 10 facilities across multiple states: Chain
- If ownership entity controls 2-9 facilities in one region/state: Regional operator
- If ownership entity controls 1 facility (or only local footprint): Independent operator

## 3. Priority List for First Outreach

### Scoring Dimensions for Outreach Priority
- Coverage value:
  - Number of communities under same operator
  - Presence across key Palm Beach cities
- Care breadth:
  - Facilities offering multiple care levels
- Readiness signals:
  - Active digital intake process
  - Fast response channels
  - Public transparency of services/pricing
- Quality and fit signals:
  - Strong objective quality indicators
  - Stable staffing indicators
- Partnership velocity:
  - Ease of decision-maker access
  - Expected legal/procurement complexity

### Priority Tiers
- Tier 1: Fastest leverage and highest county impact
  - Large chains and strong regional operators with multiple facilities
- Tier 2: High-quality independents and specialized memory/skilled operators
- Tier 3: Long-tail independents with lower immediate impact but strategic geographic coverage

### Initial Outreach Targets (Wave Plan)
- Wave 1 (Weeks 1-2): Top Tier 1 operators
- Wave 2 (Weeks 3-4): Remaining Tier 1 + top Tier 2
- Wave 3 (Weeks 5-6): Tier 2 balance + selected Tier 3 gap-fillers

## 4. CRM Design for Launch Execution

### Required Lifecycle Fields
- contacted (boolean)
- interested (boolean)
- onboarded (boolean)
- active (boolean)
- paying (boolean)

### Recommended Supporting Fields
- operator_type (chain / regional / independent)
- care_types (multi-select)
- outreach_owner
- outreach_stage
- last_contact_date
- next_follow_up_date
- notes
- blocker_type
- blocker_notes
- contract_status
- technical_status
- launch_priority_tier (1/2/3)

### Stage Definitions
- contacted: First outbound touch completed
- interested: Verbal or written positive signal to evaluate partnership
- onboarded: Data/profile setup completed in OPTIME systems
- active: Facility listing live and operational in user-facing recommendations
- paying: Commercial agreement active and billing started

## 5. Execution Cadence
- Weekly:
  - New facilities mapped
  - Outreach attempts completed
  - Meetings booked
  - Stage conversions by operator type
- Bi-weekly:
  - Priority list recalibration based on conversion signals
- Monthly:
  - Coverage report by city and care type
  - Revenue pipeline and activation forecast

## 6. Success Metrics (Launch Phase)
- Market coverage:
  - % of Palm Beach communities mapped
  - % mapped by care level
- Outreach performance:
  - Contact rate
  - Interest rate
  - Onboarding conversion rate
- Activation performance:
  - Active facilities count
  - Time from first contact to active
- Commercial performance:
  - Paying facilities count
  - Paying conversion rate from onboarded

## 7. Immediate Next Steps
1. Build master facility list for Palm Beach County from AHCA + CMS + web validation.
2. Apply care-level and operator-type classifications to all facilities.
3. Score and tag each record with launch priority tier.
4. Load records into CRM with lifecycle fields and ownership assignments.
5. Start Wave 1 outreach with Tier 1 operators.
