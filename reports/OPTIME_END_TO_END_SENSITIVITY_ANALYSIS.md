# OPTIME End-to-End Sensitivity Analysis

Each test started independently from the same base case in a fresh process with the production result cache disabled. Changes were not combined. All runs used active runtime `0c81e52c7136390c` and all 11,090 candidates.

## Base reference

The base top five are 24/7 NURSING CARE INC, A TOUCH OF KINDNESS HOME CARE INC, ABACA NURSING CARE INC, ABSOLUTE HEALTH CARE NOW INC, and ADL FAMILYCARE SERVICES INC. All are Joint #1, `POTENTIALLY_ELIGIBLE`, score 60.0, with no CMS CCN and six unknown HIGH needs.

## Test A: Hebrew becomes mandatory

Run time: 4,021.79 ms.

### Result

The top five, order, eligibility, score, and confidence are unchanged. Eligibility counts remain 1,057 potentially eligible and 10,033 insufficient evidence. No candidate is marked ineligible or excluded.

### Why

The current parser does not preserve the requested change. Both “prefers Hebrew-speaking support” and “requires Hebrew-speaking support” map to `languages`, level MEDIUM, desired value `hebrew`, with `UNKNOWN` accepted. The test therefore did not create a REQUIRED condition.

Hebrew availability is UNKNOWN for all base top-five providers. UNKNOWN is neutral and creates neither exclusion nor a penalty. This run cannot establish what the requested mandatory-Hebrew scenario would do under genuinely required semantics.

### Top five

| Position | Provider | ID | Eligibility | Score |
| --- | --- | --- | --- | ---: |
| Joint #1 | 24/7 NURSING CARE INC | `NPI-1962821785` | POTENTIALLY_ELIGIBLE | 60.0 |
| Joint #1 | A TOUCH OF KINDNESS HOME CARE INC | `NPI-1205485182` | POTENTIALLY_ELIGIBLE | 60.0 |
| Joint #1 | ABACA NURSING CARE INC | `NPI-1932782919` | POTENTIALLY_ELIGIBLE | 60.0 |
| Joint #1 | ABSOLUTE HEALTH CARE NOW INC | `NPI-1316729890` | POTENTIALLY_ELIGIBLE | 60.0 |
| Joint #1 | ADL FAMILYCARE SERVICES INC. | `NPI-1487211645` | POTENTIALLY_ELIGIBLE | 60.0 |

Movement: none. Driver: no effective semantic change.

## Test B: budget becomes $8,000 per month

Run time: 3,952.71 ms.

### Result

The top five, order, eligibility, and score are unchanged. Confidence falls slightly from 19.78 to 19.50 because one more practical-fit field is unknown. Eligibility counts remain 1,057 potentially eligible and 10,033 insufficient evidence. No candidate is marked ineligible or excluded.

### Why

A nonzero budget adds `published_rates`, level PREFERENCE, desired value `KNOWN`. The numeric $8,000 maximum is not compared with a facility price and is not an affordability filter. All five prices remain UNKNOWN. UNKNOWN is neutral and does not remove or penalize a provider.

The current engine cannot make a defensible affordability recommendation for this test. Current rates and total care charges must be verified outside the ranking before claiming fit with $8,000.

### Top five

The same five remain Joint #1 at 60.0. Each has UNKNOWN pricing and no verified affordability. Movement: none. Driver: no known price and no numeric maximum-price rule.

## Test C: rehabilitation no longer required

Run time: 3,790.86 ms.

### Result

The top five, order, eligibility, and 60.0 score are unchanged. Confidence rises from 19.78 to 23.67 because fewer mapped critical needs are unknown. Eligibility counts become 1,034 potentially eligible and 10,056 insufficient evidence. No candidate is marked ineligible or excluded.

### Why

The independent input removes rehabilitation from the questionnaire and says therapies are unnecessary. PT, OT, and speech are absent from the effective need profile. Stroke/neuro support remains HIGH because “recent stroke” still triggers it. The three remaining unknown HIGH needs are medication support, stroke/neuro evidence, and transfer assistance.

No base provider improves relative to another: each loses the same three unknowns, retains the same taxonomy ADL match, and keeps the same Miami bonus. The changed universe counts reflect fewer critical requirements, but there is no top-five ordering effect.

### Top five

The same five remain Joint #1 at 60.0. Movement: none. Driver: symmetric removal of PT, OT, and speech with no differentiating known evidence.

## Test D: dementia support becomes required

Run time: 4,001.87 ms.

### Internal consistency

The input is logically contradictory: it retains “mentally alert and has no dementia” while changing questionnaire memory status to “Significant support needed” and adding that dementia/memory support is required. The final profile resolves this to `memory_care` REQUIRED YES and `dementia_alz_programs` HIGH YES, but the output does not expose a contradiction warning. That resolution must not be mistaken for family clarification.

### Result

Eligibility counts become 142 potentially eligible and 10,948 insufficient evidence. No candidate is marked ineligible or excluded because unknown required evidence is not treated as a negative or verified gap.

| Position | Provider | ID | CMS CCN | Eligibility | Score | Confidence |
| --- | --- | --- | --- | --- | ---: | ---: |
| #1 | BALDOMERO LOPEZ MEMORIAL VETERANS NURSING HOME | `CMS-106006` | 106006 | POTENTIALLY_ELIGIBLE | 60.0 | 50.59 |
| #2 | ALEXANDER "SANDY" NININGER STATE VETERANS NURSING | `CMS-106038` | 106038 | POTENTIALLY_ELIGIBLE | 60.0 | 50.59 |
| #3 | MIAMI BLUE HEALTH | `NPI-1225589849` | None | POTENTIALLY_ELIGIBLE | 60.0 | 28.47 |
| Joint #4 | 100 JOHN KNOX RD TENANT LLC | `NPI-1023846045` | None | POTENTIALLY_ELIGIBLE | 55.0 | 28.47 |
| Joint #4 | 1415 FORT CLARKE BLVD TENANT LLC | `NPI-1174351183` | None | POTENTIALLY_ELIGIBLE | 55.0 | 28.47 |

The entire base top five leaves the displayed top five. The movement is driven by known memory-care and dementia-program parameters, followed by governed tie-break dimensions; it is ranking-driven among potentially eligible candidates, not exclusion-driven. The two CMS-identified veterans homes rise to #1 and #2. Exact pairwise details are retained in the machine-readable artifact.

All five displayed providers have taxonomy-inferred matches for both memory care and dementia programming. The two CMS providers also have a facility-reported Medicare match. Seven other HIGH needs remain unknown for every displayed provider.

There is also an internal ordering-trace contradiction. The output displays Alexander Nininger at #2 and Miami Blue at #3, while their recorded pairwise decision says, “MIAMI BLUE HEALTH ranked above ALEXANDER ‘SANDY’ NININGER STATE VETERANS NURSING on verified capability depth evidence.” The comparator decision does not reorder the pre-sorted list. That trace cannot reproduce or justify the displayed #2/#3 order as written.

This test materially changes the recommendation, but it is not clinically interpretable until the family-input contradiction and ordering-trace contradiction are resolved.

## Sensitivity conclusion

- Hebrew mandatory: no effective semantic change; no movement.
- $8,000 budget: adds price transparency preference only; no movement and no affordability conclusion.
- Rehabilitation removed: fewer unknowns and higher confidence, but no movement.
- Dementia required: complete top-five replacement, driven by memory parameters, with unresolved contradictory family inputs.

The base ordering is insensitive to the first three requested changes because the parser/rules do not preserve all requested severity and numeric semantics and because evidence is sparse. It is highly sensitive to memory-care requirements where differentiated evidence exists.