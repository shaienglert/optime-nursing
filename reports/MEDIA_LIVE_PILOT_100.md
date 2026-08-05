# MEDIA LIVE PILOT 100

Generated at: `2026-08-04T17:29:55Z`
Active market: **Las Vegas, Nevada** (Las Vegas Valley)
Configured region key: `las-vegas`

## Step 1 - Selection

- Target facilities: **100**
- Selected facilities: **42**
- Priority 1 (current recommendation result): **0**
- Priority 2 (active launch market): **42**
- Priority 3 (complete identity + missing verified image): **0**
- Data limitation: **only 42 eligible facilities available** under governed selection constraints.

| canonical facility ID | facility name | city | state | authoritative identity source | selection priority |
| --- | --- | --- | --- | --- | --- |
| CMS-295006 | LAS VEGAS POST ACUTE & REHABILITATION | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295008 | EL JEN SKILLED CARE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295017 | HORIZON HEALTH AND REHABILITATION CENTER | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295021 | PREMIER HEALTH & REHABILITATION CENTER OF LV, LP | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295036 | NORTH LAS VEGAS CARE CENTER | NORTH LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295037 | HENDERSON HEALTH AND REHABILITATION | HENDERSON | NV | CMS Provider Information | 2 |
| CMS-295040 | SAINT JOSEPH TRANSITIONAL REHABILITATION CENTER | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295041 | OASIS NURSING & REHAB OF GREEN VALLEY | HENDERSON | NV | CMS Provider Information | 2 |
| CMS-295045 | TORREY PINES POST ACUTE AND REHABILITATION | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295046 | BOULDER CITY HOSPITAL SNF | BOULDER CITY | NV | CMS Provider Information | 2 |
| CMS-295048 | HARMON HOSPITAL - SNF | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295052 | LIFE CARE CENTER OF LAS VEGAS | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295055 | COLLEGE PARK REHABILITATION CENTER | NORTH LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295066 | SILVER HILLS HEALTH CARE CENTER | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295068 | HIGHLAND MANOR OF MESQUITE REHABILITATION LLC | MESQUITE | NV | CMS Provider Information | 2 |
| CMS-295070 | MARQUIS PLAZA REGENCY POST ACUTE REHAB | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295071 | TLC CARE CENTER | HENDERSON | NV | CMS Provider Information | 2 |
| CMS-295072 | SILVER RIDGE HEALTHCARE CENTER | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295073 | ROYAL SPRINGS HEALTHCARE AND REHAB | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295076 | LIFE CARE CENTER OF SOUTH LAS VEGAS | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295080 | MOUNTAIN VIEW CARE CENTER | BOULDER CITY | NV | CMS Provider Information | 2 |
| CMS-295081 | NEVADA STATE VETERANS HOME - BOULDER CITY | BOULDER CITY | NV | CMS Provider Information | 2 |
| CMS-295083 | THE HEIGHTS OF SUMMERLIN, LLC | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295084 | NEURORESTORATIVE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295086 | LAS VENTANAS RETIREMENT COMM SNF | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295089 | MARQUIS CARE AT CENTENNIAL HILLS | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295090 | ADVANCED HEALTH CARE OF LAS VEGAS | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295091 | NEURORESTORATIVE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295092 | ADVANCED HEALTH CARE OF SUMMERLIN | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295093 | CANYON VISTA POST ACUTE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295094 | SPANISH HILLS WELLNESS SUITES | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295095 | SANDSTONE SPRING VALLEY | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295097 | SKYE CANYON POST ACUTE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295098 | SAGE CREEK POST-ACUTE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295099 | CORONADO RIDGE SKILLED NURSING & REHABILITATION CE | HENDERSON | NV | CMS Provider Information | 2 |
| CMS-295102 | ADVANCED HEALTH CARE OF HENDERSON | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295106 | TRELLIS CENTENNIAL | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295107 | ADVANCED HEALTH CARE OF PARADISE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295108 | SILVER STATE PEDIATRIC SKILLED NURSING FACILITY | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295109 | TRELLIS PARADISE | LAS VEGAS | NV | CMS Provider Information | 2 |
| CMS-295110 | GREEN VALLEY HEALTH AND WELLNESS SUITES | HENDERSON | NV | CMS Provider Information | 2 |
| CMS-29E037 | MISSION PINES NURSING AND REHAB CENTER | NORTH LAS VEGAS | NV | CMS Provider Information | 2 |

## Step 2/3 - Live Dry-Run Discovery Summary

- Facilities processed: **42**
- Official domains found: **18**
- Exact facility pages verified: **18**
- Operator-only pages found: **0**
- Candidate images found: **18**
- Images accepted as facility-specific: **0**
- Images rejected as stock/corporate/logo/staff/unrelated: **11**
- Images blocked by rights uncertainty: **6**
- Images missing: **36**
- Average processing time per facility (seconds): **58.92**

### Top 20 failure reasons
- MISSING_PRIMARY_IMAGE: 36
- IDENTITY:PARTIAL: 20
- IMAGE_REJECTION:INSUFFICIENT_FACILITY_SPECIFIC_EVIDENCE: 11
- IMAGE_REJECTION:DISPLAY_RIGHTS_UNCLEAR: 6
- IMAGE_PROBE:FETCH_FAILED: 4
- IDENTITY:NOT_VERIFIED: 3
- IDENTITY:AMBIGUOUS: 1

## Step 4 - Owner Gate

Owner gate status: **FAIL**
- no_directory_source_became_official: PASS
- no_operator_wide_image_became_facility_specific: PASS
- no_unclear_rights_image_became_displayable: PASS
- at_least_20pct_exact_facility_pages: PASS
- at_least_10_newly_displayable_images: FAIL
- Baseline displayable image count (selected set): **0**
- Final displayable image count (dry-run result): **0**
- Exact increase: **0**

Gate failed. Per governed instructions, registry write rerun and end-to-end publish validation were not executed.

## Processing time per facility

| canonical facility ID | facility name | seconds |
| --- | --- | --- |
| CMS-295083 | THE HEIGHTS OF SUMMERLIN, LLC | 75.964 |
| CMS-295080 | MOUNTAIN VIEW CARE CENTER | 74.496 |
| CMS-295021 | PREMIER HEALTH & REHABILITATION CENTER OF LV, LP | 71.067 |
| CMS-295017 | HORIZON HEALTH AND REHABILITATION CENTER | 68.776 |
| CMS-295040 | SAINT JOSEPH TRANSITIONAL REHABILITATION CENTER | 65.177 |
| CMS-295037 | HENDERSON HEALTH AND REHABILITATION | 64.217 |
| CMS-29E037 | MISSION PINES NURSING AND REHAB CENTER | 63.909 |
| CMS-295102 | ADVANCED HEALTH CARE OF HENDERSON | 63.425 |
| CMS-295048 | HARMON HOSPITAL - SNF | 63.083 |
| CMS-295045 | TORREY PINES POST ACUTE AND REHABILITATION | 61.714 |
| CMS-295089 | MARQUIS CARE AT CENTENNIAL HILLS | 60.236 |
| CMS-295073 | ROYAL SPRINGS HEALTHCARE AND REHAB | 58.801 |
| CMS-295108 | SILVER STATE PEDIATRIC SKILLED NURSING FACILITY | 58.627 |
| CMS-295097 | SKYE CANYON POST ACUTE | 58.360 |
| CMS-295098 | SAGE CREEK POST-ACUTE | 58.273 |
| CMS-295095 | SANDSTONE SPRING VALLEY | 58.124 |
| CMS-295090 | ADVANCED HEALTH CARE OF LAS VEGAS | 58.056 |
| CMS-295046 | BOULDER CITY HOSPITAL SNF | 58.010 |
| CMS-295006 | LAS VEGAS POST ACUTE & REHABILITATION | 57.978 |
| CMS-295094 | SPANISH HILLS WELLNESS SUITES | 57.739 |
| CMS-295041 | OASIS NURSING & REHAB OF GREEN VALLEY | 57.662 |
| CMS-295055 | COLLEGE PARK REHABILITATION CENTER | 57.642 |
| CMS-295093 | CANYON VISTA POST ACUTE | 57.458 |
| CMS-295036 | NORTH LAS VEGAS CARE CENTER | 57.093 |
| CMS-295081 | NEVADA STATE VETERANS HOME - BOULDER CITY | 56.916 |
| CMS-295070 | MARQUIS PLAZA REGENCY POST ACUTE REHAB | 56.731 |
| CMS-295052 | LIFE CARE CENTER OF LAS VEGAS | 56.495 |
| CMS-295072 | SILVER RIDGE HEALTHCARE CENTER | 56.173 |
| CMS-295092 | ADVANCED HEALTH CARE OF SUMMERLIN | 56.158 |
| CMS-295106 | TRELLIS CENTENNIAL | 55.742 |
| CMS-295076 | LIFE CARE CENTER OF SOUTH LAS VEGAS | 55.412 |
| CMS-295008 | EL JEN SKILLED CARE | 55.142 |
| CMS-295071 | TLC CARE CENTER | 55.020 |
| CMS-295091 | NEURORESTORATIVE | 54.693 |
| CMS-295084 | NEURORESTORATIVE | 54.587 |
| CMS-295066 | SILVER HILLS HEALTH CARE CENTER | 54.427 |
| CMS-295099 | CORONADO RIDGE SKILLED NURSING & REHABILITATION CE | 54.313 |
| CMS-295110 | GREEN VALLEY HEALTH AND WELLNESS SUITES | 53.822 |
| CMS-295107 | ADVANCED HEALTH CARE OF PARADISE | 53.705 |
| CMS-295109 | TRELLIS PARADISE | 53.494 |
| CMS-295068 | HIGHLAND MANOR OF MESQUITE REHABILITATION LLC | 53.436 |
| CMS-295086 | LAS VENTANAS RETIREMENT COMM SNF | 52.501 |

Total dry-run wall time (seconds): **1249.992**
