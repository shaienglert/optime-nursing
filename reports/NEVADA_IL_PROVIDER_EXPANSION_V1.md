# Nevada Independent Living Provider Expansion v1

Scope: Las Vegas Valley Independent Living / unlicensed senior housing discovery beyond business names containing `senior`.

## Evidence policy

- Nevada HCQC / ALiS remains the licensing source of truth for RFG/Assisted Living, Memory Care endorsements, and Skilled Nursing.
- Provider/operator primary evidence may confirm unlicensed senior housing / Independent Living identity.
- Provider-only IL records are explicitly marked `PRIMARY_PROVIDER_IDENTITY_NO_CARE_LICENSE_INFERRED`.
- Active-adult apartment housing is distinguished with `ACTIVE_ADULT_55_PLUS_APARTMENTS` where applicable.
- Active-adult ownership/master-planned communities such as Sun City / Del Webb are not automatically included as Independent Living facilities.
- Missing care evidence remains `UNKNOWN`.

## Newly verified provider IL records

1. Vista Park Retirement Community — North Las Vegas — all-inclusive Independent Living; primary provider explicitly allows third-party in-home health providers.
2. Country Club at The Meadows — Las Vegas — 55+ active-adult apartments.
3. Country Club at Valley View — Las Vegas — 55+ active-adult apartments.
4. Destinations Pebble — Paradise / Las Vegas Valley — 55+ active-adult apartments.
5. Destinations Pueblo — Las Vegas — 55+ senior apartments.
6. Carefree Senior Living at The Willows — Las Vegas — senior apartments / active retirement community.
7. Album Union Village — Henderson — 55+ active-adult apartments.

## Runtime guardrails

Deterministic tests assert that all seven records:

- enter the runtime universe as `INDEPENDENT_LIVING`;
- remain `UNREGULATED_SENIOR_HOUSING_PROVIDER_VERIFIED`, never HCQC-licensed by inference;
- carry primary-source URLs;
- do not infer Assisted Living / Memory Care;
- preserve care evidence as `UNKNOWN` except where a provider explicitly verifies an outside-care model.
