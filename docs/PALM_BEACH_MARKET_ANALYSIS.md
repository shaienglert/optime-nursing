# Palm Beach County Market Intelligence (Verified Sources Only)

## Scope and Source Controls
- Geography: Palm Beach County, Florida
- Facility class: CMS Nursing Home Provider Information records (skilled nursing facilities)
- Estimates: none used; all values are direct source fields or deterministic calculations
- Source dataset: Provider Information (4pq5-n9py)
- Source metadata endpoint: https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/4pq5-n9py
- Source CSV endpoint: https://data.cms.gov/provider-data/sites/default/files/resources/bc7015f6a981fa7e209809e021f8f0cc_1781194538/NH_ProviderInfo_Jun2026.csv
- Report generated (UTC): 2026-07-15T07:00:07+00:00
- CMS metadata modified timestamp: 2026-06-01
- Most common provider Processing Date in county rows: 2026-06-01

## market_communities Table Spec
```sql
CREATE TABLE market_communities (
  community_id TEXT PRIMARY KEY,
  community_name TEXT NOT NULL,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  zip_code TEXT NOT NULL,
  phone TEXT,
  county TEXT NOT NULL,
  provider_type TEXT,
  ownership_type TEXT,
  legal_business_name TEXT,
  operator_name TEXT NOT NULL,
  chain_id TEXT,
  chain_name TEXT,
  facilities_in_chain INTEGER,
  is_national_chain BOOLEAN NOT NULL,
  is_independent BOOLEAN NOT NULL,
  certified_beds INTEGER,
  overall_rating INTEGER,
  staffing_rating INTEGER,
  quality_rating INTEGER,
  inspection_rating INTEGER,
  special_focus_status TEXT,
  changed_ownership_last_12m BOOLEAN NOT NULL,
  source_processing_date TEXT,
  source_dataset_id TEXT NOT NULL,
  source_download_url TEXT NOT NULL,
  generated_at_utc TEXT NOT NULL
);
```

Definition note: `is_national_chain` is true when CMS `Chain ID` is present and `Number of Facilities in Chain >= 25`.

## Market Metrics
- Total communities: 54
- National chain communities: 24
- Independent communities: 12
- Total certified beds: 6163

## Top 10 Operators by Market Share
| Rank | Operator | Communities | Facility Share | Beds | Bed Share |
|---|---|---:|---:|---:|---:|
| 1 | EXCELSIOR CARE GROUP | 7 | 13.0% | 960 | 15.6% |
| 2 | SOVEREIGN HEALTHCARE HOLDINGS | 4 | 7.4% | 571 | 9.3% |
| 3 | LIFESPACE COMMUNITIES | 4 | 7.4% | 304 | 4.9% |
| 4 | LIFE CARE CENTERS OF AMERICA | 3 | 5.6% | 447 | 7.3% |
| 5 | AVIATA HEALTH GROUP | 3 | 5.6% | 360 | 5.8% |
| 6 | CARERITE CENTERS | 2 | 3.7% | 334 | 5.4% |
| 7 | AVANTE CENTERS | 2 | 3.7% | 282 | 4.6% |
| 8 | ONYX HEALTH | 2 | 3.7% | 240 | 3.9% |
| 9 | SIMCHA HYMAN & NAFTALI ZANZIPER | 2 | 3.7% | 219 | 3.6% |
| 10 | FLORIDA INSTITUTE FOR LONG-TERM CARE | 2 | 3.7% | 205 | 3.3% |

## Recommended First 20 Communities for Outreach
| Rank | Community | City | Operator | Beds | Overall | Chain ID | Reason |
|---|---|---|---|---:|---:|---|---|
| 1 | GARDENS COURT | PALM BEACH GARDENS | LIFE CARE CENTERS OF AMERICA | 120 | 5 | 311 | large capacity (120 beds); strong overall rating (5/5); large chain footprint (194 facilities) |
| 2 | DARCY HALL OF LIFE CARE | WEST PALM BEACH | LIFE CARE CENTERS OF AMERICA | 220 | 2 | 311 | large capacity (220 beds); large chain footprint (194 facilities) |
| 3 | JOSEPH L MORSE HEALTH CENTER INC THE | WEST PALM BEACH | JOSEPH L MORSE HEALTH CENTER, INC | 230 | 5 |  | large capacity (230 beds); strong overall rating (5/5) |
| 4 | ISLES OF BOYNTON NURSING AND REHAB CENTER | BOYNTON BEACH | EXCELSIOR CARE GROUP | 180 | 4 | 217 | large capacity (180 beds); strong overall rating (4/5); large chain footprint (33 facilities) |
| 5 | LAKESIDE HEALTH CENTER | WEST PALM BEACH | LIFE CARE CENTERS OF AMERICA | 107 | 4 | 311 | strong overall rating (4/5); large chain footprint (194 facilities) |
| 6 | LEGACY AT BOCA RATON REHABILITATION AND NURSING CE | BOCA RATON | CARERITE CENTERS | 180 | 4 | 110 | large capacity (180 beds); strong overall rating (4/5); large chain footprint (34 facilities) |
| 7 | BOYNTON BEACH REHABILITATION CENTER | BOYNTON BEACH | SOVEREIGN HEALTHCARE HOLDINGS | 168 | 4 | 482 | large capacity (168 beds); strong overall rating (4/5); large chain footprint (43 facilities) |
| 8 | BOULEVARD REHABILITATION CENTER | BOYNTON BEACH | SOVEREIGN HEALTHCARE HOLDINGS | 167 | 4 | 482 | large capacity (167 beds); strong overall rating (4/5); large chain footprint (43 facilities) |
| 9 | HEARTLAND NURSING & REHAB CENTER | BOYNTON BEACH | EXCELSIOR CARE GROUP | 120 | 4 | 217 | large capacity (120 beds); strong overall rating (4/5); large chain footprint (33 facilities) |
| 10 | EDWARD J HEALEY REHABILITATION AND NURSING CENTER | RIVIERA BEACH | HEALTH CARE DISTRICT OF PALM BEACH COUNTY | 120 | 5 |  | large capacity (120 beds); strong overall rating (5/5) |
| 11 | YAMATO NURSING AND REHABILITATION CENTER | BOCA RATON | EXCELSIOR CARE GROUP | 180 | 2 | 217 | large capacity (180 beds); large chain footprint (33 facilities) |
| 12 | LOURDES-NOREEN MCKEEN RESIDENCE FOR GERIATRIC CARE | WEST PALM BEACH | CARMELITE SISTERS FOR THE AGED & INFIRM | 132 | 4 | 802 | large capacity (132 beds); strong overall rating (4/5); chain-affiliated operator |
| 13 | ROYAL PALM BEACH HEALTH AND REHABILITATION CENTER | ROYAL PALM BEACH | SIMCHA HYMAN & NAFTALI ZANZIPER | 120 | 3 | 580 | large capacity (120 beds); large chain footprint (85 facilities) |
| 14 | VENTURA HEALTH AND REHABILITATION CENTER | BOYNTON BEACH | SIMCHA HYMAN & NAFTALI ZANZIPER | 99 | 3 | 580 | large chain footprint (85 facilities) |
| 15 | WILLOWBROOKE COURT SKILLED CARE CENTER - EDGEWATER | BOCA RATON | ACTS RETIREMENT-LIFE COMMUNITIES | 60 | 5 | 9 | strong overall rating (5/5); large chain footprint (27 facilities) |
| 16 | PALM GARDEN OF WEST PALM BEACH | WEST PALM BEACH | PALM GARDEN HEALTH AND REHABILITATION | 176 | 3 | 394 | large capacity (176 beds); chain-affiliated operator |
| 17 | ENCORE AT BOCA RATON REHABILITATION AND NURSING CE | BOCA RATON | CARERITE CENTERS | 154 | 3 | 110 | large capacity (154 beds); large chain footprint (34 facilities) |
| 18 | THE TERRACE OF DELRAY BEACH NURSING AND REHABILITA | DELRAY BEACH | TD SNF OPCO LLC | 120 | 4 |  | large capacity (120 beds); strong overall rating (4/5) |
| 19 | AVIATA AT GREENACRES | GREEN ACRES | AVIATA HEALTH GROUP | 120 | 2 | 745 | large capacity (120 beds); large chain footprint (52 facilities) |
| 20 | AVIATA AT CORAL BAY | WEST PALM BEACH | AVIATA HEALTH GROUP | 120 | 3 | 745 | large capacity (120 beds); large chain footprint (52 facilities) |

## Reproducibility
Run the command below from the repository root to regenerate this report:
```bash
python scripts/build_palm_beach_market.py
```
