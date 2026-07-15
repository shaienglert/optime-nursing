# South Florida Market Intelligence (Verified Sources Only)

## Scope and Source Controls
- Geography: Palm Beach, Broward, and Miami-Dade counties (Florida)
- Facility class: CMS Nursing Home Provider Information records (skilled nursing facilities)
- Estimates: none used; all values are direct source fields or deterministic calculations
- Source dataset: Provider Information (4pq5-n9py)
- Source metadata endpoint: https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/4pq5-n9py
- Source CSV endpoint: https://data.cms.gov/provider-data/sites/default/files/resources/bc7015f6a981fa7e209809e021f8f0cc_1781194538/NH_ProviderInfo_Jun2026.csv
- Report generated (UTC): 2026-07-15T07:04:41+00:00
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
  chain_tier TEXT,
  is_national_chain BOOLEAN NOT NULL,
  is_regional_chain BOOLEAN NOT NULL,
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

Definition notes:
- `chain_tier = national` when chain identifier exists and `Number of Facilities in Chain >= 25`.
- `chain_tier = regional` when chain identifier exists and `Number of Facilities in Chain < 25`.
- `chain_tier = null` when chain affiliation exists but chain-size is unavailable in source.

## County Metrics
| County | Total Communities | Total Beds | National Chain | Regional Chain | Independent |
|---|---:|---:|---:|---:|---:|
| Palm Beach | 54 | 6163 | 24 | 18 | 12 |
| Broward | 33 | 4314 | 7 | 18 | 8 |
| Miami-Dade | 54 | 8281 | 10 | 24 | 20 |

Combined communities across target counties: 141

## Top Operators Per County

### Palm Beach
| Rank | Operator | Communities | Beds |
|---|---|---:|---:|
| 1 | EXCELSIOR CARE GROUP | 7 | 960 |
| 2 | SOVEREIGN HEALTHCARE HOLDINGS | 4 | 571 |
| 3 | LIFESPACE COMMUNITIES | 4 | 304 |
| 4 | LIFE CARE CENTERS OF AMERICA | 3 | 447 |
| 5 | AVIATA HEALTH GROUP | 3 | 360 |
| 6 | CARERITE CENTERS | 2 | 334 |
| 7 | AVANTE CENTERS | 2 | 282 |
| 8 | ONYX HEALTH | 2 | 240 |
| 9 | SIMCHA HYMAN & NAFTALI ZANZIPER | 2 | 219 |
| 10 | FLORIDA INSTITUTE FOR LONG-TERM CARE | 2 | 205 |

### Broward
| Rank | Operator | Communities | Beds |
|---|---|---:|---:|
| 1 | MILLENNIUM HEALTH SYSTEMS | 3 | 460 |
| 2 | CONSULATE HEALTH CARE/INDEPENDENCE LIVING CENTERS/NSPIRE HEALTHCARE/RAYDIANT HEALTH CARE | 3 | 370 |
| 3 | CARERITE CENTERS | 2 | 322 |
| 4 | FLORIDA INSTITUTE FOR LONG-TERM CARE | 2 | 321 |
| 5 | Legal Business Name Not Available | 2 | 156 |
| 6 | AVIATA HEALTH GROUP | 2 | 142 |
| 7 | VENTURA SERVICES | 1 | 240 |
| 8 | MICHAEL FEIST | 1 | 237 |
| 9 | JOHN KNOX VILLAGE OF FLORIDA, INC. | 1 | 194 |
| 10 | ST JOHNS REHABILITATION HOSPITAL AND NURSING CENTER INC | 1 | 181 |

### Miami-Dade
| Rank | Operator | Communities | Beds |
|---|---|---:|---:|
| 1 | ONYX HEALTH | 8 | 1069 |
| 2 | VENTURA SERVICES | 7 | 1508 |
| 3 | GOLD FL TRUST II | 3 | 543 |
| 4 | BENJAMIN LANDA | 2 | 383 |
| 5 | PUBLIC HEALTH TRUST OF MIAMI DADE COUNTY FLORIDA | 2 | 343 |
| 6 | CARERITE CENTERS | 2 | 275 |
| 7 | CONSULATE HEALTH CARE/INDEPENDENCE LIVING CENTERS/NSPIRE HEALTHCARE/RAYDIANT HEALTH CARE | 2 | 240 |
| 8 | VILLA MARIA NURSING & REHABILITATION CENTER | 2 | 239 |
| 9 | MIAMI JEWISH HEALTH SYSTEMS INC | 1 | 393 |
| 10 | ELEVATE CARE | 1 | 276 |

## Recommended First 30 Communities for Outreach
| Rank | County | Community | City | Operator | Beds | Overall | Chain ID | Reason |
|---|---|---|---|---:|---:|---|---|
| 1 | Palm Beach | GARDENS COURT | PALM BEACH GARDENS | LIFE CARE CENTERS OF AMERICA | 120 | 5 | 311 | large capacity (120 beds); strong overall rating (5/5); large chain footprint (194 facilities) |
| 2 | Palm Beach | DARCY HALL OF LIFE CARE | WEST PALM BEACH | LIFE CARE CENTERS OF AMERICA | 220 | 2 | 311 | large capacity (220 beds); large chain footprint (194 facilities) |
| 3 | Miami-Dade | UNITY HEALTHCARE AND REHABILITATION CENTER | MIAMI | GOLD FL TRUST II | 294 | 5 | 594 | large capacity (294 beds); strong overall rating (5/5); large chain footprint (36 facilities) |
| 4 | Miami-Dade | VICTORIA NURSING & REHABILITATION CENTER, INC. | MIAMI | VICTORIA NURSING & REHABILITATION CENTER, INC | 264 | 5 |  | large capacity (264 beds); strong overall rating (5/5) |
| 5 | Palm Beach | JOSEPH L MORSE HEALTH CENTER INC THE | WEST PALM BEACH | JOSEPH L MORSE HEALTH CENTER, INC | 230 | 5 |  | large capacity (230 beds); strong overall rating (5/5) |
| 6 | Miami-Dade | RIVIERA HEALTH RESORT | CORAL GABLES | NEW RIVIERA NURSING & REHABILITATION CENTER, LLC | 223 | 5 |  | large capacity (223 beds); strong overall rating (5/5) |
| 7 | Broward | BROWARD NURSING & REHABILITATION CENTER | FORT LAUDERDALE | MILLENNIUM HEALTH SYSTEMS | 198 | 5 | 351 | large capacity (198 beds); strong overall rating (5/5); chain-affiliated operator |
| 8 | Miami-Dade | WEST GABLES HEALTH CARE CENTER | MIAMI | MARQUIS HEALTH SERVICES | 120 | 5 | 336 | large capacity (120 beds); strong overall rating (5/5); large chain footprint (88 facilities) |
| 9 | Broward | LIFE CARE CENTER AT INVERRARY | LAUDERHILL | LIFE CARE CENTERS OF AMERICA | 120 | 4 | 311 | large capacity (120 beds); strong overall rating (4/5); large chain footprint (194 facilities) |
| 10 | Miami-Dade | MIAMI JEWISH HEALTH SYSTEMS, INC | MIAMI | MIAMI JEWISH HEALTH SYSTEMS INC | 393 | 4 |  | large capacity (393 beds); strong overall rating (4/5) |
| 11 | Miami-Dade | SANDS AT SOUTH BEACH CARE CENTER, THE | MIAMI BEACH | ONYX HEALTH | 230 | 5 | 385 | large capacity (230 beds); strong overall rating (5/5); chain-affiliated operator |
| 12 | Miami-Dade | ST ANNES NURSING CENTER, ST ANNES RESIDENCE INC | MIAMI | ST. ANNE'S NURSING CENTER, ST ANNE'S RESIDENCE INC | 213 | 4 |  | large capacity (213 beds); strong overall rating (4/5) |
| 13 | Miami-Dade | HARMONY HEALTH CENTER | MIAMI | BENJAMIN LANDA | 203 | 5 | 646 | large capacity (203 beds); strong overall rating (5/5); large chain footprint (49 facilities) |
| 14 | Broward | JOHN KNOX VILLAGE OF POMPANO BEACH | POMPANO BEACH | JOHN KNOX VILLAGE OF FLORIDA, INC. | 194 | 4 |  | large capacity (194 beds); strong overall rating (4/5) |
| 15 | Miami-Dade | SOUTH DADE NURSING AND REHABILITATION CENTER | MIAMI | VENTURA SERVICES | 180 | 5 | 860 | large capacity (180 beds); strong overall rating (5/5); chain-affiliated operator |
| 16 | Miami-Dade | SIERRA LAKES NURSING & REHABILITATION CENTER | MIAMI | VENTURA SERVICES | 180 | 4 | 860 | large capacity (180 beds); strong overall rating (4/5); chain-affiliated operator |
| 17 | Miami-Dade | PALACE AT KENDALL NURSING AND REHABILITATION CENTE | MIAMI | KENDALL HEALTHCARE PROPERTIES III | 180 | 5 |  | large capacity (180 beds); strong overall rating (5/5) |
| 18 | Palm Beach | ISLES OF BOYNTON NURSING AND REHAB CENTER | BOYNTON BEACH | EXCELSIOR CARE GROUP | 180 | 4 | 217 | large capacity (180 beds); strong overall rating (4/5); large chain footprint (33 facilities) |
| 19 | Miami-Dade | JACKSON MEMORIAL PERDUE MEDICAL CENTER | CUTLER BAY | PUBLIC HEALTH TRUST OF MIAMI DADE COUNTY FLORIDA | 163 | 5 |  | large capacity (163 beds); strong overall rating (5/5) |
| 20 | Palm Beach | LAKESIDE HEALTH CENTER | WEST PALM BEACH | LIFE CARE CENTERS OF AMERICA | 107 | 4 | 311 | strong overall rating (4/5); large chain footprint (194 facilities) |
| 21 | Broward | SUNRISE HEALTH & REHABILITATION CENTER | SUNRISE | MICHAEL FEIST | 237 | 4 | 769 | large capacity (237 beds); strong overall rating (4/5); chain-affiliated operator |
| 22 | Palm Beach | LEGACY AT BOCA RATON REHABILITATION AND NURSING CE | BOCA RATON | CARERITE CENTERS | 180 | 4 | 110 | large capacity (180 beds); strong overall rating (4/5); large chain footprint (34 facilities) |
| 23 | Miami-Dade | JACKSON MEMORIAL LONG TERM CARE CENTER | MIAMI | PUBLIC HEALTH TRUST OF MIAMI DADE COUNTY FLORIDA | 180 | 4 |  | large capacity (180 beds); strong overall rating (4/5) |
| 24 | Miami-Dade | CORAL REEF SUBACUTE CARE CENTER LLC | MIAMI | CARERITE CENTERS | 180 | 3 | 110 | large capacity (180 beds); large chain footprint (34 facilities) |
| 25 | Broward | MARGATE HEALTH AND REHABILITATION CENTER | MARGATE | ONYX HEALTH | 170 | 5 | 385 | large capacity (170 beds); strong overall rating (5/5); chain-affiliated operator |
| 26 | Palm Beach | BOYNTON BEACH REHABILITATION CENTER | BOYNTON BEACH | SOVEREIGN HEALTHCARE HOLDINGS | 168 | 4 | 482 | large capacity (168 beds); strong overall rating (4/5); large chain footprint (43 facilities) |
| 27 | Palm Beach | BOULEVARD REHABILITATION CENTER | BOYNTON BEACH | SOVEREIGN HEALTHCARE HOLDINGS | 167 | 4 | 482 | large capacity (167 beds); strong overall rating (4/5); large chain footprint (43 facilities) |
| 28 | Miami-Dade | SHORESIDE HEALTH AND REHABILITATION CENTER | MIAMI | ONYX HEALTH | 150 | 5 | 385 | large capacity (150 beds); strong overall rating (5/5); chain-affiliated operator |
| 29 | Miami-Dade | RIVERSIDE CARE CENTER | MIAMI | STACEY HEALTH CARE CENTERS INC RIVERSIDE CARE CENTER | 120 | 5 |  | large capacity (120 beds); strong overall rating (5/5) |
| 30 | Miami-Dade | NSPIRE HEALTHCARE KENDALL | KENDALL | CONSULATE HEALTH CARE/INDEPENDENCE LIVING CENTERS/NSPIRE HEALTHCARE/RAYDIANT HEALTH CARE | 120 | 5 | 158 | large capacity (120 beds); strong overall rating (5/5); chain-affiliated operator |

## Reproducibility
Run the command below from the repository root to regenerate this report:
```bash
python scripts/build_palm_beach_market.py
```
