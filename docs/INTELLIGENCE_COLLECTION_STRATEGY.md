# OPTIME Intelligence Collection Strategy

## Objective
Design a collection architecture that produces decision-grade community intelligence for placement outcomes, not just high-volume data.

Primary optimization target: decision quality for family placement fit and placement success.

## Decision Outcomes To Predict
- Placement acceptance likelihood
- 90-day stability (no early move-out)
- Family satisfaction after move-in
- Clinical appropriateness (care level fit)
- Safety risk during first 6 months
- Budget sustainability for 12 months

## Scoring Framework
- Reliability Score: 1 (low) to 5 (high)
- Predictive Value Score: 1 (low) to 5 (high)
- Collection Cost: 1 (low) to 5 (high)

Tier rules:
- Tier 1: Predictive >= 4 and Reliability >= 4
- Tier 2: Predictive >= 3 and Reliability >= 3
- Tier 3: Everything else (context/noise unless corroborated)

## Collection Architecture

### Layer 1: Source Registry
- Maintain per-source metadata: category coverage, legal basis, rate limits, crawl policy, freshness SLA, expected schema.
- Track source status: active, degraded, blocked, retired.

### Layer 2: Acquisition Connectors
- Official datasets: scheduled pull (API/CSV where available).
- Public pages: policy-compliant crawler honoring robots, rate limits, and terms.
- Third-party review platforms: partner/API feeds where allowed, otherwise public metadata only.
- Legal/news: licensed feeds or public docket/news endpoints.

### Layer 3: Normalization And Entity Resolution
- Canonical community key with source-specific aliases.
- Deterministic resolution first (license ID, CMS ID, exact address), fuzzy resolution only as provisional.
- Keep unresolved entities separate; never force-match.

### Layer 4: Signal Extraction
- Extract only defined signals in this strategy.
- Store raw evidence pointers and extraction timestamps for every signal.

### Layer 5: Quality And Trust Controls
- Provenance required for every non-null value.
- Confidence rules by signal type and source count.
- Contradiction handling: retain both claims and mark status as verified, unverified, disputed.

### Layer 6: Intelligence Serving
- Community profile view (latest snapshot).
- Trend view (30, 90, 180, 365 days).
- Alerting for material negative changes (regulatory, staffing, legal, ownership).

## Legal And Technical Collection Policy
- Use only publicly accessible data with permitted collection terms.
- Respect robots.txt and platform terms for crawlable sources.
- Prefer official APIs/downloads over HTML scraping.
- Store only necessary public facts for decision support.
- Keep allegation and verified finding as separate fields.
- Maintain per-source attribution URL and collection timestamp.

## Signal Catalog (Top 28)

| Signal Name | Category | Primary Source | Collection Method | Update Frequency | Reliability | Predictive Value | Cost | Legal/Technical Method | Tier |
|---|---|---|---|---|---:|---:|---:|---|---|
| CMS Overall Rating | Regulatory quality | CMS Care Compare / Provider datasets | Official dataset ingest | Monthly | 5 | 5 | 1 | Public federal dataset pull | Tier 1 |
| CMS Staffing Rating | Regulatory quality, Medical capability | CMS | Official dataset ingest | Monthly | 5 | 5 | 1 | Public federal dataset pull | Tier 1 |
| CMS Health Inspection Rating | Safety, Regulatory quality | CMS | Official dataset ingest | Monthly | 5 | 5 | 1 | Public federal dataset pull | Tier 1 |
| Deficiency Severity Count | Safety, Regulatory quality | CMS/state inspection records | Official dataset ingest | Monthly | 5 | 5 | 2 | Public regulator records | Tier 1 |
| Civil Monetary Penalties (Fines) | Safety, Regulatory quality | CMS/state enforcement | Official dataset ingest | Monthly | 5 | 4 | 2 | Public regulator records | Tier 1 |
| Infection Control Citations | Safety, Medical capability | CMS inspection data | Official dataset ingest | Monthly | 5 | 4 | 2 | Public regulator records | Tier 1 |
| License Status | Regulatory quality | State licensing registry | Registry ingest | Daily | 5 | 5 | 2 | Public state registry query | Tier 1 |
| License Action Events | Litigation risk, Regulatory quality | State licensing registry | Registry ingest + event diff | Daily | 5 | 5 | 2 | Public enforcement records | Tier 1 |
| Ownership Change Flag | Ownership stability | CMS + state filings | Official dataset ingest + diff | Monthly | 4 | 4 | 2 | Public filing comparison | Tier 1 |
| Nurse Hours Per Resident Day | Medical capability | CMS staffing dataset | Official dataset ingest | Quarterly/Monthly | 5 | 5 | 1 | Public federal dataset pull | Tier 1 |
| Complaint Investigation Volume | Safety, Family experience | State survey/complaint records | Official ingest | Monthly | 4 | 4 | 3 | Public complaint dispositions | Tier 1 |
| Substantiated Abuse/Neglect Findings | Safety | State enforcement summaries | Official ingest | Monthly | 5 | 5 | 3 | Public enforcement summaries | Tier 1 |
| Hospital Transfer Rate Proxy | Medical capability | CMS quality measures | Official dataset ingest | Quarterly | 4 | 4 | 2 | Public quality measure pull | Tier 1 |
| Rehospitalization Measure | Medical capability | CMS quality measures | Official dataset ingest | Quarterly | 4 | 4 | 2 | Public quality measure pull | Tier 1 |
| Family Review Volume (All Platforms) | Family experience, Reputation | Google/Caring/APFM/SeniorAdvisor/Seniorly/Yelp | API/metadata aggregation | Weekly | 3 | 4 | 4 | Public metadata/partner APIs where allowed | Tier 2 |
| Family Rating Trend (90-day) | Family experience | Review platforms | API/metadata aggregation | Weekly | 3 | 4 | 4 | Platform-compliant collection | Tier 2 |
| Negative Review Ratio (90-day) | Family experience, Reputation | Review platforms | NLP over review text/labels | Weekly | 3 | 4 | 4 | Terms-compliant review processing | Tier 2 |
| Employee Review Volume | Employee experience | Indeed/Glassdoor | API/metadata aggregation | Weekly | 3 | 3 | 4 | Public metadata/partner routes | Tier 2 |
| Employee Sentiment Trend | Employee experience | Indeed/Glassdoor | NLP trend extraction | Weekly | 3 | 4 | 4 | Terms-compliant aggregation | Tier 2 |
| Staff Turnover Proxy | Employee experience, Medical capability | CMS + employee sources | Derived metric from official + public signals | Monthly | 4 | 4 | 3 | Deterministic derived metric | Tier 2 |
| Activities Program Breadth | Activities and social life | Official community site, brochures, event calendars | Structured extraction | Monthly | 3 | 3 | 3 | Public site crawl with attribution | Tier 2 |
| Dining Program Signals | Dining quality | Official site + family reviews | Structured extraction + sentiment themes | Monthly | 3 | 3 | 3 | Public pages + review metadata | Tier 2 |
| Memory Care Program Specificity | Medical capability, Community culture | Official site, care program pages | Structured extraction | Monthly | 4 | 4 | 3 | Public pages with evidence links | Tier 2 |
| Language Support Availability | Community culture | Official site | Structured extraction | Quarterly | 4 | 3 | 2 | Public site extraction | Tier 2 |
| Faith/Cultural Affiliation Disclosure | Community culture | Official site, parent org pages | Structured extraction | Quarterly | 4 | 3 | 2 | Public disclosure only | Tier 2 |
| Litigation Event Count (12m) | Litigation risk | Public court records | Docket query + entity resolution | Weekly | 4 | 4 | 4 | Public docket search/compliant feeds | Tier 2 |
| Material News Event Count (12m) | Reputation, Stability | Local news and press releases | News feed ingestion | Daily | 3 | 3 | 3 | Licensed/public news feeds | Tier 2 |
| Financial Distress Indicators | Financial stability | Public filings, liens, closure notices | Filing/event ingestion | Monthly | 4 | 4 | 4 | Public filings and notices | Tier 2 |

## Tier 3 (Context / Noise Unless Corroborated)
- Social follower counts
- Generic marketing claims without third-party evidence
- One-off testimonial quotes
- Unverified forum posts
- Single-article reputation spikes
- Non-attributed award badges on marketing pages

These can be collected for context but should not materially affect placement recommendations without corroboration.

## Category Coverage Matrix

| Category | Coverage Status | Best Current Public Sources | Recommended Cadence |
|---|---|---|---|
| Regulatory quality | Strong | CMS, state license and inspection records | Daily to Monthly |
| Family experience | Moderate | Review platforms | Weekly |
| Employee experience | Moderate | Indeed, Glassdoor | Weekly |
| Community culture | Moderate | Official websites, program pages | Monthly/Quarterly |
| Medical capability | Strong | CMS quality and staffing | Monthly/Quarterly |
| Activities and social life | Moderate | Official calendars, reviews | Monthly |
| Dining quality | Moderate | Official dining pages, reviews | Monthly |
| Safety | Strong | Inspections, deficiency severity, complaints | Weekly/Monthly |
| Financial stability | Limited to Moderate | Public filings and distress signals | Monthly |
| Ownership stability | Strong | CMS ownership change + state filings | Monthly |
| Litigation risk | Moderate | Public dockets and regulatory actions | Weekly |
| Reputation | Moderate | Multi-platform review aggregates + news | Weekly |
| Improvement/decline trends | Strong where history exists | Time-series across Tier 1 and Tier 2 signals | Weekly/Monthly |

## Update Frequency Policy
- Daily: license status/actions, high-priority news and legal alerts.
- Weekly: review and employee signal refresh, litigation checks.
- Monthly: CMS/provider/regulatory batch updates and trend recomputation.
- Quarterly: lower-volatility profile attributes (languages, affiliations, amenities).

## Reliability Governance
- Require source URL and timestamp for all non-null values.
- Keep raw evidence snippets for auditability.
- Mark every signal as verified, unverified, or disputed.
- Preserve history; never overwrite prior regulatory events.

## Predictive Core (Recommended 20-30 Signals)
Priority shortlist for placement outcomes is the Tier 1 set plus highest-value Tier 2 signals:
- All 14 Tier 1 signals
- Tier 2: family review volume, family rating trend, negative review ratio, employee sentiment trend, staff turnover proxy, memory care specificity, litigation count, financial distress indicators, material news count, activities breadth

Total recommended predictive set: 24 signals.

## Operational Recommendations
- Start with Tier 1 ingestion and trending before expanding breadth.
- Add Tier 2 in waves based on legal access and extraction quality.
- Exclude Tier 3 from ranking inputs.
- Revalidate predictive weights quarterly using placement outcomes.

## What Not To Do
- Do not rank by raw mention volume alone.
- Do not merge uncertain entities into a single community record.
- Do not treat allegations as confirmed findings.
- Do not display recurring themes below 5 independent mentions.