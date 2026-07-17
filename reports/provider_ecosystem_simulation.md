# Facility Memory Persistence Simulation

## Scenario

- Resident age: 80
- Clinical context: stroke history, walker, requires 24/7 support
- Lifestyle: movies, music
- Dietary: gluten free
- Budget: $12,000/month
- Location: Miami

## Top Recommendation

- Community: **BISCAYNE HEALTH AND REHABILITATION CENTER**
- Match score: **100**
- Verification readiness: **20**

## Verified Capabilities

- Skilled nursing capability
- Neurological rehabilitation
- Physical therapy

## Unknown Capabilities

- Licensed nurses 24/7
- Speech therapy
- Occupational therapy
- Swallowing assessment support
- Walker accessibility
- Fall prevention protocol
- Mobility and transfer assistance
- Gluten-free meal capability
- Dietitian support
- Movie programming
- Music activities
- Future care pathway: Full continuum of care on one campus

## Verification Questions

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

## Narrative Output

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

## Provider Portal Integration

- Inbox generation:
  - Total provider inbox items: **10**
  - Top facility inbox status: **OPEN**
  - Resident info shared: **false**

- Anonymous verification request payload (capability-only):

  - Subject: Prospective Resident Match Verification Request

```text
Dear Admissions Team,

OPTIME matched your community (BISCAYNE HEALTH AND REHABILITATION CENTER) to an anonymous prospective resident profile and would appreciate clarification regarding several items before recommending an in-person visit.

Before scheduling a visit, please help verify the following open items:

No resident demographic, contact, budget, or medical-history details are shared in this request.

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

- Provider answers applied through PROVIDER_PORTAL: **YES**
- Initial unknown count: **12**
- Final unknown count: **0**
- Initial confidence: **20**
- Final confidence: **100**
- Updated capabilities persisted: **12**
- Persisted answers: **12**
- Conflict records: **1**
- Conflict engine status: **PASS**

## Simulation Assertions

- UNKNOWN decreases after persistence: **PASS**
- Confidence increases after persistence: **PASS**
- Conflict detection rule enforced: **PASS**