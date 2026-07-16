# Dynamic Persona Simulation Audit V1

Dynamic Persona Engine Status: **FAIL**

## Failing Dimensions

- Social weighting is not materially elevating more social communities for Persona A.
- Cultural and language weighting is not materially elevating culturally aligned communities for Persona D.

## Summary Checks

- Different personas generate different weights: **PASS**
- Different personas generate different rankings: **PASS**
- Social persona ranks higher-social communities higher: **FAIL**
- Clinical persona ranks higher-clinical communities higher: **PASS**
- Cultural persona ranks culturally aligned communities higher: **FAIL**

## Persona A

Generated Persona Type: **Independent Social Senior**

### Dynamic Weights

| Dimension | Weight |
| --- | --- |
| Luxury Amenities | 26% |
| Social Fit | 22% |
| Lifestyle Fit | 12% |
| Care Fit | 10% |
| Family Fit | 10% |
| Financial Fit | 10% |
| Cultural Fit | 5% |
| Clinical Quality | 5% |

### Top 10 Recommendations

| Dynamic Rank | Community | Dynamic Score | Static Rank | Rank Change |
| --- | --- | --- | --- | --- |
| 1 | COMMUNITY CONVALESCENT CENTER | 55.55 | 1 | 0 |
| 2 | W FRANK WELLS NURSING HOME | 42.95 | 5 | 3 |
| 3 | AVIATA AT THE SEA - PASADENA | 42.45 | 16 | 13 |
| 4 | SOUTH HERITAGE HEALTH & REHABILITATION CENTER | 42.45 | 17 | 13 |
| 5 | CORAL GABLES NURSING AND REHABILITATION CENTER | 42.20 | 24 | 19 |
| 6 | BISCAYNE HEALTH AND REHABILITATION CENTER | 41.95 | 26 | 20 |
| 7 | EAGLE LAKE NURSING AND REHAB CARE CENTER | 41.70 | 22 | 15 |
| 8 | JOHN KNOX VILLAGE OF POMPANO BEACH | 41.60 | 2 | -6 |
| 9 | TERRACES OF LAKE WORTH CARE CENTER AND REHAB | 41.45 | 38 | 29 |
| 10 | BEACH STREET HEALTH AND REHABILITATION CENTER | 41.45 | 39 | 29 |

### Weight Contribution Table

| Dimension | Weight | Top Rank Raw Score | Top Rank Contribution |
| --- | --- | --- | --- |
| Social Fit | 22% | 100.00 | 22.00 |
| Lifestyle Fit | 12% | 35.00 | 4.20 |
| Medical Fit | 10% | 0.00 | 0.00 |
| Family Proximity | 10% | 65.00 | 6.50 |
| Cultural Fit | 5% | 45.00 | 2.25 |
| Clinical Quality | 5% | 40.00 | 2.00 |

### Ranking Explanation

Ranked #1 because it has the highest weighted fit score and the strongest top-two contributor balance. We prioritized this community because parent has fully independent needs and prefers daily social interaction. COMMUNITY CONVALESCENT CENTER scored well on the strongest weighted fit dimensions, which kept it near the top of the ranking. The community's lifestyle cues were compared against movies. The distance signal is 30.

### Comparison Against Static Engine

| Community | Static Rank | Dynamic Rank | Rank Change | Reason |
| --- | --- | --- | --- | --- |
| COMMUNITY CONVALESCENT CENTER | 1 | 1 | 0 | Luxury Amenities increased relative influence. |
| W FRANK WELLS NURSING HOME | 5 | 2 | 3 | Luxury Amenities increased relative influence. |
| AVIATA AT THE SEA - PASADENA | 16 | 3 | 13 | Luxury Amenities increased relative influence. |
| SOUTH HERITAGE HEALTH & REHABILITATION CENTER | 17 | 4 | 13 | Luxury Amenities increased relative influence. |
| CORAL GABLES NURSING AND REHABILITATION CENTER | 24 | 5 | 19 | Luxury Amenities increased relative influence. |
| BISCAYNE HEALTH AND REHABILITATION CENTER | 26 | 6 | 20 | Luxury Amenities increased relative influence. |
| EAGLE LAKE NURSING AND REHAB CARE CENTER | 22 | 7 | 15 | Luxury Amenities increased relative influence. |
| JOHN KNOX VILLAGE OF POMPANO BEACH | 2 | 8 | -6 | Luxury Amenities increased relative influence. |
| TERRACES OF LAKE WORTH CARE CENTER AND REHAB | 38 | 9 | 29 | Luxury Amenities increased relative influence. |
| BEACH STREET HEALTH AND REHABILITATION CENTER | 39 | 10 | 29 | Luxury Amenities increased relative influence. |

## Persona B

Generated Persona Type: **Early Memory Support**

### Dynamic Weights

| Dimension | Weight |
| --- | --- |
| Care Fit | 22% |
| Clinical Quality | 22% |
| Luxury Amenities | 16% |
| Family Fit | 10% |
| Lifestyle Fit | 9% |
| Social Fit | 8% |
| Financial Fit | 8% |
| Cultural Fit | 5% |

### Top 10 Recommendations

| Dynamic Rank | Community | Dynamic Score | Static Rank | Rank Change |
| --- | --- | --- | --- | --- |
| 1 | CORAL GABLES NURSING AND REHABILITATION CENTER | 68.35 | 9 | 8 |
| 2 | TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 67.85 | 10 | 8 |
| 3 | BISCAYNE HEALTH AND REHABILITATION CENTER | 67.25 | 14 | 11 |
| 4 | CRESTVIEW REHABILITATION CENTER, LLC | 66.75 | 15 | 11 |
| 5 | RIVER GARDEN HEBREW HOME FOR THE AGED | 66.75 | 16 | 11 |
| 6 | MORTON PLANT REHABILITATION CENTER | 65.65 | 27 | 21 |
| 7 | FORT WALTON REHABILITATION CENTER, LLC | 65.65 | 28 | 21 |
| 8 | BROWARD NURSING & REHABILITATION CENTER | 65.65 | 29 | 21 |
| 9 | LIFE CARE CENTER OF MELBOURNE | 65.65 | 30 | 21 |
| 10 | SANDS AT SOUTH BEACH CARE CENTER, THE | 65.65 | 31 | 21 |

### Weight Contribution Table

| Dimension | Weight | Top Rank Raw Score | Top Rank Contribution |
| --- | --- | --- | --- |
| Medical Fit | 22% | 65.00 | 14.30 |
| Clinical Quality | 22% | 95.00 | 20.90 |
| Family Proximity | 10% | 80.00 | 8.00 |
| Lifestyle Fit | 9% | 50.00 | 4.50 |
| Social Fit | 8% | 45.00 | 3.60 |
| Cultural Fit | 5% | 45.00 | 2.25 |

### Ranking Explanation

Ranked #1 because it has the highest weighted fit score and the strongest top-two contributor balance. We prioritized this community because parent has some daily support needs and prefers a specific social rhythm social interaction. CORAL GABLES NURSING AND REHABILITATION CENTER scored well on the strongest weighted fit dimensions, which kept it near the top of the ranking. No single activity preference dominated the score. The distance signal is 15.

### Comparison Against Static Engine

| Community | Static Rank | Dynamic Rank | Rank Change | Reason |
| --- | --- | --- | --- | --- |
| CORAL GABLES NURSING AND REHABILITATION CENTER | 9 | 1 | 8 | Clinical Quality increased relative influence. |
| TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 10 | 2 | 8 | Clinical Quality increased relative influence. |
| BISCAYNE HEALTH AND REHABILITATION CENTER | 14 | 3 | 11 | Clinical Quality increased relative influence. |
| CRESTVIEW REHABILITATION CENTER, LLC | 15 | 4 | 11 | Clinical Quality increased relative influence. |
| RIVER GARDEN HEBREW HOME FOR THE AGED | 16 | 5 | 11 | Clinical Quality increased relative influence. |
| MORTON PLANT REHABILITATION CENTER | 27 | 6 | 21 | Clinical Quality increased relative influence. |
| FORT WALTON REHABILITATION CENTER, LLC | 28 | 7 | 21 | Clinical Quality increased relative influence. |
| BROWARD NURSING & REHABILITATION CENTER | 29 | 8 | 21 | Clinical Quality increased relative influence. |
| LIFE CARE CENTER OF MELBOURNE | 30 | 9 | 21 | Clinical Quality increased relative influence. |
| SANDS AT SOUTH BEACH CARE CENTER, THE | 31 | 10 | 21 | Clinical Quality increased relative influence. |

## Persona C

Generated Persona Type: **Rehabilitation**

### Dynamic Weights

| Dimension | Weight |
| --- | --- |
| Clinical Quality | 32% |
| Care Fit | 28% |
| Family Fit | 10% |
| Luxury Amenities | 10% |
| Lifestyle Fit | 5% |
| Social Fit | 5% |
| Cultural Fit | 5% |
| Financial Fit | 5% |

### Top 10 Recommendations

| Dynamic Rank | Community | Dynamic Score | Static Rank | Rank Change |
| --- | --- | --- | --- | --- |
| 1 | TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 80.95 | 2 | 1 |
| 2 | CORAL GABLES NURSING AND REHABILITATION CENTER | 80.35 | 1 | -1 |
| 3 | CRESTVIEW REHABILITATION CENTER, LLC | 79.35 | 4 | 1 |
| 4 | RIVER GARDEN HEBREW HOME FOR THE AGED | 79.35 | 5 | 1 |
| 5 | BISCAYNE HEALTH AND REHABILITATION CENTER | 78.75 | 3 | -2 |
| 6 | FORT WALTON REHABILITATION CENTER, LLC | 77.75 | 6 | 0 |
| 7 | BROWARD NURSING & REHABILITATION CENTER | 77.75 | 7 | 0 |
| 8 | LIFE CARE CENTER OF MELBOURNE | 77.75 | 8 | 0 |
| 9 | SANDS AT SOUTH BEACH CARE CENTER, THE | 77.75 | 9 | 0 |
| 10 | PINES OF SARASOTA | 77.75 | 10 | 0 |

### Weight Contribution Table

| Dimension | Weight | Top Rank Raw Score | Top Rank Contribution |
| --- | --- | --- | --- |
| Clinical Quality | 32% | 100.00 | 32.00 |
| Medical Fit | 28% | 95.00 | 26.60 |
| Family Proximity | 10% | 71.00 | 7.10 |
| Lifestyle Fit | 5% | 50.00 | 2.50 |
| Social Fit | 5% | 45.00 | 2.25 |
| Cultural Fit | 5% | 45.00 | 2.25 |

### Ranking Explanation

Ranked #1 because it has the highest weighted fit score and the strongest top-two contributor balance. We prioritized this community because parent has skilled nursing care needs and prefers a specific social rhythm social interaction. TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE scored well on the strongest weighted fit dimensions, which kept it near the top of the ranking. No single activity preference dominated the score. The distance signal is 20.

### Comparison Against Static Engine

| Community | Static Rank | Dynamic Rank | Rank Change | Reason |
| --- | --- | --- | --- | --- |
| TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 2 | 1 | 1 | Clinical Quality increased relative influence. |
| CORAL GABLES NURSING AND REHABILITATION CENTER | 1 | 2 | -1 | Clinical Quality increased relative influence. |
| CRESTVIEW REHABILITATION CENTER, LLC | 4 | 3 | 1 | Clinical Quality increased relative influence. |
| RIVER GARDEN HEBREW HOME FOR THE AGED | 5 | 4 | 1 | Clinical Quality increased relative influence. |
| BISCAYNE HEALTH AND REHABILITATION CENTER | 3 | 5 | -2 | Clinical Quality increased relative influence. |
| FORT WALTON REHABILITATION CENTER, LLC | 6 | 6 | 0 | Clinical Quality increased relative influence. |
| BROWARD NURSING & REHABILITATION CENTER | 7 | 7 | 0 | Clinical Quality increased relative influence. |
| LIFE CARE CENTER OF MELBOURNE | 8 | 8 | 0 | Clinical Quality increased relative influence. |
| SANDS AT SOUTH BEACH CARE CENTER, THE | 9 | 9 | 0 | Clinical Quality increased relative influence. |
| PINES OF SARASOTA | 10 | 10 | 0 | Clinical Quality increased relative influence. |

## Persona D

Generated Persona Type: **Independent Active Senior**

### Dynamic Weights

| Dimension | Weight |
| --- | --- |
| Care Fit | 18% |
| Lifestyle Fit | 16% |
| Luxury Amenities | 16% |
| Social Fit | 14% |
| Financial Fit | 12% |
| Clinical Quality | 10% |
| Family Fit | 8% |
| Cultural Fit | 6% |

### Top 10 Recommendations

| Dynamic Rank | Community | Dynamic Score | Static Rank | Rank Change |
| --- | --- | --- | --- | --- |
| 1 | W FRANK WELLS NURSING HOME | 47.90 | 2 | 1 |
| 2 | SHORE ACRES CARE CENTER AND REHAB | 47.30 | 1 | -1 |
| 3 | CORAL GABLES NURSING AND REHABILITATION CENTER | 47.00 | 23 | 20 |
| 4 | AVIATA AT THE SEA - PASADENA | 46.90 | 9 | 5 |
| 5 | SOUTH HERITAGE HEALTH & REHABILITATION CENTER | 46.90 | 10 | 5 |
| 6 | BISCAYNE HEALTH AND REHABILITATION CENTER | 46.50 | 25 | 19 |
| 7 | JOHN KNOX VILLAGE OF POMPANO BEACH | 46.40 | 3 | -4 |
| 8 | GROVES CENTER | 46.10 | 4 | -4 |
| 9 | TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 45.90 | 24 | 15 |
| 10 | AVANTE AT LEESBURG, INC | 45.80 | 5 | -5 |

### Weight Contribution Table

| Dimension | Weight | Top Rank Raw Score | Top Rank Contribution |
| --- | --- | --- | --- |
| Medical Fit | 18% | 30.00 | 5.40 |
| Lifestyle Fit | 16% | 35.00 | 5.60 |
| Social Fit | 14% | 45.00 | 6.30 |
| Clinical Quality | 10% | 50.00 | 5.00 |
| Family Proximity | 8% | 65.00 | 5.20 |
| Cultural Fit | 6% | 30.00 | 1.80 |

### Ranking Explanation

Ranked #1 because it has the highest weighted fit score and the strongest top-two contributor balance. We prioritized this community because parent has fully independent needs and prefers a specific social rhythm social interaction. W FRANK WELLS NURSING HOME scored well on the strongest weighted fit dimensions, which kept it near the top of the ranking. The community's lifestyle cues were compared against religious activities. The distance signal is 25.

### Comparison Against Static Engine

| Community | Static Rank | Dynamic Rank | Rank Change | Reason |
| --- | --- | --- | --- | --- |
| W FRANK WELLS NURSING HOME | 2 | 1 | 1 | Luxury Amenities increased relative influence. |
| SHORE ACRES CARE CENTER AND REHAB | 1 | 2 | -1 | Luxury Amenities increased relative influence. |
| CORAL GABLES NURSING AND REHABILITATION CENTER | 23 | 3 | 20 | Luxury Amenities increased relative influence. |
| AVIATA AT THE SEA - PASADENA | 9 | 4 | 5 | Luxury Amenities increased relative influence. |
| SOUTH HERITAGE HEALTH & REHABILITATION CENTER | 10 | 5 | 5 | Luxury Amenities increased relative influence. |
| BISCAYNE HEALTH AND REHABILITATION CENTER | 25 | 6 | 19 | Luxury Amenities increased relative influence. |
| JOHN KNOX VILLAGE OF POMPANO BEACH | 3 | 7 | -4 | Luxury Amenities increased relative influence. |
| GROVES CENTER | 4 | 8 | -4 | Luxury Amenities increased relative influence. |
| TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | 24 | 9 | 15 | Luxury Amenities increased relative influence. |
| AVANTE AT LEESBURG, INC | 5 | 10 | -5 | Luxury Amenities increased relative influence. |

## Quality Gate Investigation

1. Care Fit threshold value: **30**

2. Top 10 facilities

| Dynamic Rank | Community | Care Fit Score | Care Fit Threshold | Pass/Fail | Reason |
| --- | --- | --- | --- | --- | --- |
| 1 | JOHN KNOX VILLAGE OF POMPANO BEACH | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 2 | SERENITY BAY NURSING AND REHABILITATION CENTER | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 3 | W FRANK WELLS NURSING HOME | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 4 | SHORE ACRES CARE CENTER AND REHAB | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 5 | CORAL GABLES NURSING AND REHABILITATION CENTER | 0 | 30 | Fail | Fails quality gate because the top-result care fit is below threshold. |
| 6 | AVIATA AT THE SEA - PASADENA | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 7 | SOUTH HERITAGE HEALTH & REHABILITATION CENTER | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 8 | BISCAYNE HEALTH AND REHABILITATION CENTER | 0 | 30 | Fail | Fails quality gate because the top-result care fit is below threshold. |
| 9 | WINTER HAVEN HEALTH AND REHABILITATION CENTER | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |
| 10 | RIVERWOOD CENTER | 30 | 30 | Pass | Passes threshold only because assisted living bottoms out at 30 for fully independent users. |

3. Exact rule triggered: **Not triggered**

4. Classification: **Quality gate**

5. Recommended fix:
- Add an explicit Independent Living or Active Adult care type in the facility mapping instead of defaulting every community to Assisted Living.
- For fully independent profiles, reduce or remove the hard negative from the default Assisted Living label when no true independence-oriented care type is available.
- Sort or filter fully independent rankings with a minimum care-fit floor before the top-result quality gate is evaluated, so a low-care-fit skilled nursing or memory care result cannot become the lead recommendation.
