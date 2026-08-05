# MEDIA LIVE PILOT Failure Analysis (Las Vegas)

Analyzed inputs only:
- [reports/MEDIA_LIVE_PILOT_100.md](reports/MEDIA_LIVE_PILOT_100.md)
- [reports/MEDIA_LIVE_PILOT_100.json](reports/MEDIA_LIVE_PILOT_100.json)

No network rerun was executed. No registry writes were performed.

## Observed

- Processed facilities: **42**
- Owner gate status: **FAIL**
- Valid displayable images: **0**

### 1) Terminal outcomes (count + percentage)

| Outcome | Count | Percentage |
| --- | ---: | ---: |
| OFFICIAL_SITE_NOT_FOUND | 24 | 57.14% |
| EXACT_LOCATION_PAGE_NOT_FOUND | 0 | 0% |
| NO_IMAGE_CANDIDATE | 0 | 0% |
| CORPORATE_OR_SHARED_IMAGE | 0 | 0% |
| STOCK_OR_LIFESTYLE_IMAGE | 0 | 0% |
| LOGO_OR_NON_FACILITY_MEDIA | 0 | 0% |
| FACILITY_IDENTITY_UNCERTAIN | 11 | 26.19% |
| DISPLAY_RIGHTS_UNCLEAR | 6 | 14.29% |
| BROKEN_OR_UNREACHABLE_IMAGE | 0 | 0% |
| VALID_DISPLAYABLE_IMAGE | 0 | 0% |
| OTHER | 1 | 2.38% |

### 2) Exact number of valid displayable images

- **0** of 42 (**0%**) 

### 3) Top 10 failure causes

| Rank | Failure cause | Count |
| ---: | --- | ---: |
| 1 | No official facility website found | 24 |
| 2 | Identity status PARTIAL | 20 |
| 3 | Facility identity uncertain for candidate image | 11 |
| 4 | Display rights unclear | 6 |
| 5 | Image probe FETCH_FAILED | 4 |
| 6 | Identity status NOT_VERIFIED | 3 |
| 7 | Other | 1 |
| 8 | Identity status AMBIGUOUS | 1 |
| 9 | No image candidate on verified facility page | 0 |
| 10 | Exact location page not found | 0 |

### 4) Primary failure domain

| Domain | Count | Share of facilities |
| --- | ---: | ---: |
| data discovery | 24 | 57.14% |
| identity verification | 11 | 26.19% |
| image classification | 0 | 0% |
| rights policy | 6 | 14.29% |
| source-site quality | 0 | 0% |

- Failures are primarily **data discovery** based on facility-level terminal outcomes.

### 5) Per-failure-category handling assessment

| Failure category | Pipeline currently handles correctly? | Would code change help? | More authoritative data required? | Cannot be solved automatically? | Notes |
| --- | --- | --- | --- | --- | --- |
| OFFICIAL_SITE_NOT_FOUND | Yes (safe fail, no false promotion) | Limited | Yes | Partly | Core issue is missing authoritative domain mapping for many facilities. |
| EXACT_LOCATION_PAGE_NOT_FOUND | Yes (not observed in this run) | Possible | Sometimes | No | Would benefit from deeper location-page discovery on official domains. |
| NO_IMAGE_CANDIDATE | Yes | Limited | Sometimes | Sometimes | Some facility pages simply expose no usable images. |
| FACILITY_IDENTITY_UNCERTAIN | Yes | Yes | Sometimes | Partly | Better image-to-facility evidence extraction could convert a subset safely. |
| DISPLAY_RIGHTS_UNCLEAR | Yes | Yes | Yes | Partly | Rights metadata capture/normalization could unlock a subset without lowering bar. |
| BROKEN_OR_UNREACHABLE_IMAGE | Yes (not terminal in this run) | Yes | No | No | URL retry strategy and alternate asset fetch paths can help. |
| VALID_DISPLAYABLE_IMAGE | N/A | N/A | N/A | N/A | None achieved in this run. |
| OTHER | Yes | Unknown | Unknown | Unknown | No additional uncategorized terminal pattern observed. |

### 6) Per-facility terminal outcome classification

| canonical facility ID | facility name | city | state | terminal outcome |
| --- | --- | --- | --- | --- |
| CMS-295006 | LAS VEGAS POST ACUTE & REHABILITATION |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295008 | EL JEN SKILLED CARE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295017 | HORIZON HEALTH AND REHABILITATION CENTER |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295021 | PREMIER HEALTH & REHABILITATION CENTER OF LV, LP |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295036 | NORTH LAS VEGAS CARE CENTER |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295037 | HENDERSON HEALTH AND REHABILITATION |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295040 | SAINT JOSEPH TRANSITIONAL REHABILITATION CENTER |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295041 | OASIS NURSING & REHAB OF GREEN VALLEY |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295045 | TORREY PINES POST ACUTE AND REHABILITATION |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295046 | BOULDER CITY HOSPITAL SNF |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295048 | HARMON HOSPITAL - SNF |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295052 | LIFE CARE CENTER OF LAS VEGAS |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295055 | COLLEGE PARK REHABILITATION CENTER |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295066 | SILVER HILLS HEALTH CARE CENTER |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295068 | HIGHLAND MANOR OF MESQUITE REHABILITATION LLC |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295070 | MARQUIS PLAZA REGENCY POST ACUTE REHAB |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295071 | TLC CARE CENTER |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295072 | SILVER RIDGE HEALTHCARE CENTER |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295073 | ROYAL SPRINGS HEALTHCARE AND REHAB |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295076 | LIFE CARE CENTER OF SOUTH LAS VEGAS |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295080 | MOUNTAIN VIEW CARE CENTER |  |  | OTHER |
| CMS-295081 | NEVADA STATE VETERANS HOME - BOULDER CITY |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295083 | THE HEIGHTS OF SUMMERLIN, LLC |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295084 | NEURORESTORATIVE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295086 | LAS VENTANAS RETIREMENT COMM SNF |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295089 | MARQUIS CARE AT CENTENNIAL HILLS |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295090 | ADVANCED HEALTH CARE OF LAS VEGAS |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295091 | NEURORESTORATIVE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295092 | ADVANCED HEALTH CARE OF SUMMERLIN |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295093 | CANYON VISTA POST ACUTE |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295094 | SPANISH HILLS WELLNESS SUITES |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295095 | SANDSTONE SPRING VALLEY |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295097 | SKYE CANYON POST ACUTE |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295098 | SAGE CREEK POST-ACUTE |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295099 | CORONADO RIDGE SKILLED NURSING & REHABILITATION CE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295102 | ADVANCED HEALTH CARE OF HENDERSON |  |  | FACILITY_IDENTITY_UNCERTAIN |
| CMS-295106 | TRELLIS CENTENNIAL |  |  | DISPLAY_RIGHTS_UNCLEAR |
| CMS-295107 | ADVANCED HEALTH CARE OF PARADISE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295108 | SILVER STATE PEDIATRIC SKILLED NURSING FACILITY |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295109 | TRELLIS PARADISE |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-295110 | GREEN VALLEY HEALTH AND WELLNESS SUITES |  |  | OFFICIAL_SITE_NOT_FOUND |
| CMS-29E037 | MISSION PINES NURSING AND REHAB CENTER |  |  | FACILITY_IDENTITY_UNCERTAIN |

## Inference

- The dominant blocker is **upstream discovery coverage**: 24/42 facilities ended with no official site.
- The second blocker is **image-facility evidence sufficiency**: 11/42 facilities had candidates but not enough facility-specific proof.
- Rights policy is active and conservative: 6 provisional images were withheld instead of being promoted.
- The observed failure pattern indicates governance is being enforced correctly; the shortfall is evidence availability and rights certainty, not permissiveness.

## Recommendation

### 7) Smallest high-impact changes without weakening verification

1. Add authoritative domain seeding for Nevada SNFs (state/federal licensing crosswalk -> official facility domains where available).
   - Expected impact: reduce OFFICIAL_SITE_NOT_FOUND by ~6 to 10 facilities.
2. Add rights-evidence extraction on already facility-specific images (terms/license cues, explicit source-policy mapping).
   - Expected impact: convert ~2 to 4 of current DISPLAY_RIGHTS_UNCLEAR facilities to VERIFIED displayable.
3. Improve facility-specific evidence scoring on official pages (name/address/logo-nearby context, page-title/address match strictness) without lowering acceptance thresholds.
   - Expected impact: convert ~2 to 3 of current FACILITY_IDENTITY_UNCERTAIN facilities to VERIFIED displayable.
4. Add fallback official-page traversal for verified domains when initial page has no usable media.
   - Expected impact: convert ~1 to 2 facilities from NO_IMAGE_CANDIDATE or missing-image paths.

### 8) Estimated verified-image coverage progression

| Stage | Estimated verified displayable images | Estimated coverage |
| --- | ---: | ---: |
| Current observed baseline | 0 / 42 | 0.0% |
| After rights-evidence extraction | 2-4 / 42 | 4.8%-9.5% |
| After + facility-specific evidence improvements | 4-7 / 42 | 9.5%-16.7% |
| After + authoritative domain seeding + traversal improvements | 7-13 / 42 | 16.7%-31.0% |

These are bounded estimates derived from observed bucket sizes in this run; they are not guarantees.
