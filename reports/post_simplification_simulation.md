# Post-Simplification Simulation Report

## Scenario

- Resident: Male, age 80 (age group 80-84)
- Requires 24/7 nursing support
- Uses walker with significant mobility limitations
- History of stroke with speech difficulty
- Dietary requirement: gluten-free meals
- Budget: $12,000/month
- Preferred location: Miami-Dade County
- Future care preference: Full continuum of care on one campus

## Top 5 Communities

| Rank | Community | Match Score | Verified Capabilities | Unknown Capabilities | Rejected Capabilities | Verification Readiness |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BISCAYNE HEALTH AND REHABILITATION CENTER | 100 | Skilled nursing capability; Neurological rehabilitation; Physical therapy | Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance; Gluten-free meal capability; Dietitian support; Movie programming; Music activities; Future care pathway: Full continuum of care on one campus | None | 20 |
| 2 | CORAL GABLES NURSING AND REHABILITATION CENTER | 100 | Skilled nursing capability; Neurological rehabilitation; Physical therapy | Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance; Gluten-free meal capability; Dietitian support; Movie programming; Music activities; Future care pathway: Full continuum of care on one campus | None | 20 |
| 3 | Pinecrest Center for Rehabilitation and Healing | 100 | Skilled nursing capability; Neurological rehabilitation; Physical therapy | Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance; Gluten-free meal capability; Dietitian support; Movie programming; Music activities; Future care pathway: Full continuum of care on one campus | None | 20 |
| 4 | FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | 100 | Skilled nursing capability; Neurological rehabilitation; Physical therapy | Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance; Gluten-free meal capability; Dietitian support; Movie programming; Music activities; Future care pathway: Full continuum of care on one campus | None | 20 |
| 5 | SERENITY BAY NURSING AND REHABILITATION CENTER | 100 | Skilled nursing capability; Neurological rehabilitation; Physical therapy | Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance; Gluten-free meal capability; Dietitian support; Movie programming; Music activities; Future care pathway: Full continuum of care on one campus | None | 20 |

## Deterministic Formula Validation (Rank #1)

- verified_yes: 3
- verified_no: 0
- unknown: 10
- computed score: 100
- reported score: 100
- formula check: **PASS**
- unknown excluded from score: **PASS**

## Rank #1 Full Narrative

```text
Why OPTIME selected this community
After reviewing the resident's medical, functional, social and lifestyle needs, OPTIME identified BISCAYNE HEALTH AND REHABILITATION CENTER as one of the strongest matches. The recommendation is based primarily on the community's ability to support current care needs while maintaining quality of life.

Medical Match
Because the resident profile requires licensed nurses 24/7, skilled nursing capability, neurological rehabilitation, speech therapy, occupational therapy, physical therapy, swallowing assessment support, walker accessibility, fall prevention protocol, mobility and transfer assistance, we prioritized communities experienced in complex clinical support. Confirmed in this community: Skilled nursing capability, Neurological rehabilitation, Physical therapy.

Lifestyle Match
Maintaining quality of life remains important. Confirmed lifestyle alignment currently includes: none yet.

Dietary Match
Dietary flexibility was reviewed because of stated restrictions. Confirmed dietary capability: none yet.

Social Match
No specific social-program requirements were identified.

Future Care Match
Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: none yet.

Verification Needed
Additional clarification is recommended regarding: Licensed nurses 24/7, Speech therapy, Occupational therapy, Swallowing assessment support, Walker accessibility, Fall prevention protocol, Mobility and transfer assistance, Gluten-free meal capability, Dietitian support, Movie programming, Music activities, Future care pathway: Full continuum of care on one campus.
```

## Rank #1 Anonymous Verification Request

Subject: Prospective Resident Match Verification Request

```text
Dear Admissions Team,

OPTIME matched your community (BISCAYNE HEALTH AND REHABILITATION CENTER) to an anonymous prospective resident profile and would appreciate clarification regarding several items before recommending an in-person visit.

Before scheduling a visit, please help verify the following open items:

Anonymous resident profile summary:

- Age: 80-84
- Gender: Male
- Current care level: Skilled nursing care
- Budget: $12,000/month
- Medical needs: Licensed nurses 24/7, Skilled nursing capability, Neurological rehabilitation, Speech therapy, Occupational therapy, Physical therapy, Swallowing assessment support, Walker accessibility, Fall prevention protocol, Mobility and transfer assistance
- Functional limitations: Mobility limitation / walker use
- Dietary requirements: Gluten-free
- Lifestyle interests: Movies, Music activities
- Geographic preference: Miami-Dade County

Please confirm availability of:

□ Licensed nurses 24/7
□ Speech therapy
□ Occupational therapy
□ Swallowing assessment support
□ Walker accessibility
□ Fall prevention protocol
□ Mobility and transfer assistance
□ Gluten-free meal capability
□ Dietitian support
□ Movie programming
□ Music activities
□ Future care pathway: Full continuum of care on one campus

For each item please indicate:

✅ Available
❌ Not available
⚠ Available with limitations

Optional comments:
______________________

No resident or family contact information has been shared.
If the family chooses to proceed later, OPTIME will request consent before releasing contact details.

Thank you.
```

## Questions Sent To Facility

- Does the community provide licensed nursing coverage 24/7?
- Is speech therapy available onsite for post-stroke recovery?
- Is occupational therapy available for post-stroke functional recovery?
- Can the community perform or coordinate swallowing assessments?
- Is the environment consistently walker-accessible across daily pathways?
- What fall prevention protocols are used for residents with walker dependence?
- Can staff provide transfer and mobility assistance as needed throughout the day?
- Can the community support consistent gluten-free meals with safe kitchen protocols?
- Is dietitian support available for special dietary plans such as gluten-free needs?
- Are movie activities or screenings offered regularly?
- Are music activities or music therapy sessions available?
- How does the community support the requested future care pathway (Full continuum of care on one campus)?

## Acceptance and Rejection Summary

- Accepted facility count: 10
- Rejected facility count: 90
- Top facility hard-rejection reasons: None

## Validation Status

- BUILD: **PASS** (validated separately via `npm run build`)
- SIMULATION: **PASS**
- NARRATIVE: **PASS**
- PRIVACY: **PASS**