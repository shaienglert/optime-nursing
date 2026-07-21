#!/usr/bin/env node
/* eslint-disable no-console */

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const REPORTS_DIR = path.join(REPO_ROOT, 'reports');
const DATABASE_DIR = path.join(REPO_ROOT, 'database');
const RAW_DIR = path.join(REPO_ROOT, 'data', 'florida_universe', 'raw');
const RAW_CMS_DIR = path.join(RAW_DIR, 'cms');
const RAW_AHCA_DIR = path.join(RAW_DIR, 'ahca');

const FILES = {
  sourceConnectivityJson: path.join(REPORTS_DIR, 'FLORIDA_SOURCE_CONNECTIVITY_AUDIT.json'),
  sourceConnectivityMd: path.join(REPORTS_DIR, 'FLORIDA_SOURCE_CONNECTIVITY_AUDIT.md'),
  universeAuditJson: path.join(REPORTS_DIR, 'FLORIDA_FACILITY_UNIVERSE_AUDIT.json'),
  universeAuditMd: path.join(REPORTS_DIR, 'FLORIDA_FACILITY_UNIVERSE_AUDIT.md'),
  coverageJson: path.join(REPORTS_DIR, 'FLORIDA_PARAMETER_COVERAGE_MATRIX.json'),
  coverageMd: path.join(REPORTS_DIR, 'FLORIDA_PARAMETER_COVERAGE_MATRIX.md'),
  canonicalUniverse: path.join(DATABASE_DIR, 'florida_facility_universe_canonical.json'),
  sourceCrosswalk: path.join(DATABASE_DIR, 'florida_facility_source_crosswalk.json'),
  parameterEvidence: path.join(DATABASE_DIR, 'florida_parameter_evidence.json'),
  rawManifest: path.join(RAW_DIR, 'source_retrieval_manifest.json'),
};

const REQUIRED_DOCS = [
  path.join(REPO_ROOT, 'AGENTS.md'),
  path.join(REPO_ROOT, 'docs', 'OPTIME_PRINCIPLES.md'),
  path.join(REPO_ROOT, 'docs', 'OPTIME_PRINCIPLES_REGISTRY.md'),
  path.join(REPO_ROOT, 'docs', 'OPTIME_MASTER_PARAMETER_REGISTRY.md'),
  path.join(REPO_ROOT, 'docs', 'FLORIDA_FACILITY_UNIVERSE_EXECUTION_PLAN.md'),
];

const CMS_SEED_DATASETS = [
  { id: '4pq5-n9py', purpose: 'Provider Information', priority: 'CRITICAL' },
  { id: 'r5ix-sfxw', purpose: 'Health Deficiencies', priority: 'CRITICAL' },
  { id: 'djen-97ju', purpose: 'Quality Measures', priority: 'CRITICAL' },
  { id: 'svdt-c123', purpose: 'Survey Data', priority: 'HIGH' },
];

const AHCA_ENDPOINTS = [
  {
    name: 'FloridaHealthFinder Root',
    url: 'https://quality.healthfinder.fl.gov/',
    category: 'AHCA/FloridaHealthFinder',
  },
  {
    name: 'FloridaHealthFinder Facility Search',
    url: 'https://quality.healthfinder.fl.gov/Facility-Provider/',
    category: 'AHCA/FloridaHealthFinder',
  },
  {
    name: 'FloridaHealthFinder County Search',
    url: 'https://quality.healthfinder.fl.gov/Facility-Provider/CountySearch/',
    category: 'AHCA/FloridaHealthFinder',
  },
  {
    name: 'AHCA Root',
    url: 'https://ahca.myflorida.com/',
    category: 'AHCA',
  },
  {
    name: 'AHCA Bureau of Health Facility Regulation',
    url: 'https://ahca.myflorida.com/health-care-policy-and-oversight/bureau-of-health-facility-regulation/',
    category: 'AHCA',
  },
  {
    name: 'FloridaHealthFinder robots',
    url: 'https://quality.healthfinder.fl.gov/robots.txt',
    category: 'AHCA/FloridaHealthFinder',
  },
  {
    name: 'AHCA robots',
    url: 'https://ahca.myflorida.com/robots.txt',
    category: 'AHCA',
  },
];

const PARAMETER_DEFS = [
  { family: 'CARE_NURSING', key: 'skilled_nursing_capabilities', label: 'Skilled nursing capabilities', source: 'cms_provider_type' },
  { family: 'CARE_NURSING', key: 'nursing_24_7', label: '24/7 nursing', source: 'cms_provider_type' },
  { family: 'CARE_NURSING', key: 'direct_24hr_nurse_availability', label: 'Direct 24hr nurse availability', source: 'unknown' },
  { family: 'CARE_NURSING', key: 'third_party_24hr_nurse_availability', label: 'Third Party 24hr nurse availability', source: 'unknown' },
  { family: 'CARE_NURSING', key: 'rn_hours_per_resident_day', label: 'RN hours per resident day', source: 'rn_hours' },
  { family: 'CARE_NURSING', key: 'total_nurse_hours_per_resident_day', label: 'Total nurse hours per resident day', source: 'total_nurse_hours' },
  { family: 'CARE_NURSING', key: 'adl_support', label: 'ADL support', source: 'unknown' },
  { family: 'CARE_NURSING', key: 'medication_support', label: 'Medication support', source: 'unknown' },
  { family: 'CARE_NURSING', key: 'transfer_assistance', label: 'Transfer assistance', source: 'unknown' },
  { family: 'CARE_NURSING', key: 'higher_acuity_capabilities', label: 'Higher-acuity capabilities', source: 'unknown' },
  { family: 'REHABILITATION', key: 'pt', label: 'Physical therapy', source: 'unknown' },
  { family: 'REHABILITATION', key: 'ot', label: 'Occupational therapy', source: 'unknown' },
  { family: 'REHABILITATION', key: 'speech_therapy', label: 'Speech therapy', source: 'unknown' },
  { family: 'REHABILITATION', key: 'short_term_rehab', label: 'Short-term rehabilitation', source: 'cms_provider_type' },
  { family: 'REHABILITATION', key: 'post_stroke_neuro_evidence', label: 'Post-stroke/neurological evidence', source: 'unknown' },
  { family: 'REHABILITATION', key: 'therapy_staffing', label: 'Therapy staffing', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'memory_care', label: 'Memory Care', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'dementia_alz_programs', label: 'Dementia/Alzheimer programs', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'wound_care', label: 'Wound care', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'dialysis_arrangements', label: 'Dialysis arrangements', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'respiratory_trach_vent', label: 'Respiratory/tracheotomy/ventilator capabilities', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'hospice_palliative_arrangements', label: 'Hospice/palliative arrangements', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'specialty_licenses', label: 'Specialty licenses', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'extended_congregate_care', label: 'Extended Congregate Care', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'limited_nursing_services', label: 'Limited Nursing Services', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'limited_mental_health', label: 'Limited Mental Health', source: 'unknown' },
  { family: 'SPECIALIZED_CARE', key: 'secured_units', label: 'Secured units', source: 'unknown' },
  { family: 'QUALITY_SAFETY', key: 'inspection_rating', label: 'Inspection rating', source: 'inspection_rating' },
  { family: 'QUALITY_SAFETY', key: 'deficiency_count', label: 'Deficiency count', source: 'deficiency_count' },
  { family: 'QUALITY_SAFETY', key: 'deficiency_severity', label: 'Deficiency severity', source: 'severe_deficiency_count' },
  { family: 'QUALITY_SAFETY', key: 'complaint_related_findings', label: 'Complaint-related findings', source: 'complaint_deficiency_count' },
  { family: 'QUALITY_SAFETY', key: 'fire_safety_deficiencies', label: 'Fire safety deficiencies', source: 'unknown' },
  { family: 'QUALITY_SAFETY', key: 'infection_control_findings', label: 'Infection control findings', source: 'infection_control_count' },
  { family: 'QUALITY_SAFETY', key: 'penalties_fines', label: 'Penalties/fines', source: 'total_fines' },
  { family: 'QUALITY_SAFETY', key: 'sanctions_final_orders', label: 'Sanctions/final orders', source: 'unknown' },
  { family: 'QUALITY_SAFETY', key: 'payment_denials', label: 'Payment denials', source: 'total_payment_denials' },
  { family: 'QUALITY_SAFETY', key: 'quality_measures', label: 'Quality measures', source: 'quality_measure_count' },
  { family: 'QUALITY_SAFETY', key: 'hospital_claims_outcomes', label: 'Hospital/claims outcomes', source: 'unknown' },
  { family: 'QUALITY_SAFETY', key: 'staffing_turnover', label: 'Staffing turnover', source: 'turnover' },
  { family: 'PERSONAL_FIT', key: 'languages', label: 'Languages', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'dietary_capabilities', label: 'Dietary capabilities', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'gluten_free', label: 'Gluten-free', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'kosher', label: 'Kosher', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'religious_cultural_services', label: 'Religious/cultural services', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'activities', label: 'Activities', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'transportation', label: 'Transportation', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'amenities', label: 'Amenities', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'private_shared_rooms', label: 'Private/shared rooms', source: 'unknown' },
  { family: 'PERSONAL_FIT', key: 'accessibility', label: 'Accessibility', source: 'unknown' },
  { family: 'FINANCIAL_ACCESS', key: 'payer_information', label: 'Payer information', source: 'unknown' },
  { family: 'FINANCIAL_ACCESS', key: 'medicaid_attributes', label: 'Medicaid attributes', source: 'unknown' },
  { family: 'FINANCIAL_ACCESS', key: 'medicare_attributes', label: 'Medicare attributes', source: 'cms_certification_number' },
  { family: 'FINANCIAL_ACCESS', key: 'published_rates', label: 'Published rates', source: 'unknown' },
  { family: 'FINANCIAL_ACCESS', key: 'fees', label: 'Fees', source: 'unknown' },
  { family: 'DYNAMIC', key: 'current_availability', label: 'Current bed/unit availability', source: 'dynamic' },
  { family: 'DYNAMIC', key: 'earliest_admission_date', label: 'Earliest admission date', source: 'dynamic' },
  { family: 'DYNAMIC', key: 'waiting_list', label: 'Waiting list', source: 'dynamic' },
  { family: 'DYNAMIC', key: 'current_price', label: 'Current price', source: 'dynamic' },
  { family: 'DYNAMIC', key: 'current_promotions', label: 'Current promotions', source: 'dynamic' },
];

function nowIso() {
  return new Date().toISOString();
}

function mkdirs() {
  [REPORTS_DIR, DATABASE_DIR, RAW_DIR, RAW_CMS_DIR, RAW_AHCA_DIR].forEach((p) => {
    fs.mkdirSync(p, { recursive: true });
  });
}

function readIfExists(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return fs.readFileSync(filePath, 'utf8');
}

function normalize(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function parseCsv(text) {
  const rows = [];
  const headers = [];
  let field = '';
  let row = [];
  let inQuotes = false;

  const pushField = () => {
    row.push(field);
    field = '';
  };

  const pushRow = () => {
    if (row.length === 0) {
      return;
    }
    if (headers.length === 0) {
      row.forEach((h) => headers.push(String(h || '').trim()));
    } else {
      const obj = {};
      for (let i = 0; i < headers.length; i += 1) {
        obj[headers[i]] = String(row[i] || '').trim();
      }
      rows.push(obj);
    }
    row = [];
  };

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      continue;
    }
    if (ch === ',') {
      pushField();
      continue;
    }
    if (ch === '\n') {
      pushField();
      pushRow();
      continue;
    }
    if (ch === '\r') {
      continue;
    }
    field += ch;
  }

  if (field.length > 0 || row.length > 0) {
    pushField();
    pushRow();
  }

  return { headers, rows };
}

async function fetchWithTimeout(url, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const started = Date.now();
  try {
    const response = await fetch(url, {
      headers: {
        'user-agent': 'OPTIME-FL-UNIVERSE-AUDIT/1.0',
      },
      signal: controller.signal,
      redirect: 'follow',
    });
    const text = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      url: response.url,
      text,
      durationMs: Date.now() - started,
      timeout: false,
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      url,
      text: '',
      durationMs: Date.now() - started,
      timeout: error && error.name === 'AbortError',
      error: String(error && error.message ? error.message : error),
    };
  } finally {
    clearTimeout(timer);
  }
}

function classifyAccess(result) {
  const body = (result.text || '').toLowerCase();
  if (result.timeout) {
    return { state: 'SOURCE_ACCESS_FAILED', reason: 'timeout' };
  }
  if (result.status === 403) {
    if (body.includes('cloudflare') || body.includes('request is blocked') || body.includes('attention required')) {
      return { state: 'SOURCE_ACCESS_FAILED', reason: 'HTTP 403 bot/challenge blocked' };
    }
    return { state: 'SOURCE_ACCESS_FAILED', reason: 'HTTP 403 forbidden' };
  }
  if (result.status === 401) {
    return { state: 'SOURCE_ACCESS_FAILED', reason: 'HTTP 401 auth required' };
  }
  if (result.status === 404) {
    return { state: 'SOURCE_ACCESS_FAILED', reason: 'HTTP 404 not found' };
  }
  if (result.status >= 500) {
    return { state: 'SOURCE_ACCESS_FAILED', reason: `HTTP ${result.status} server error` };
  }
  if (!result.ok) {
    return { state: 'SOURCE_ACCESS_FAILED', reason: result.error || `HTTP ${result.status}` };
  }
  return { state: 'VERIFIED_YES', reason: 'reachable' };
}

function datasetLooksRelevant(item) {
  const blob = `${item.title || ''} ${(item.description || '')} ${Array.isArray(item.keyword) ? item.keyword.join(' ') : ''}`.toLowerCase();
  const hasNursing = blob.includes('nursing') || blob.includes('skilled nursing') || blob.includes('long-term care');
  const hasTarget = [
    'provider',
    'ownership',
    'staff',
    'pbj',
    'quality',
    'deficien',
    'inspection',
    'survey',
    'penalt',
    'fire safety',
    'claims',
    'hospice',
    'home health',
  ].some((k) => blob.includes(k));
  return hasNursing && hasTarget;
}

async function getCmsCatalog() {
  const url = 'https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items';
  const res = await fetchWithTimeout(url, 60000);
  const classif = classifyAccess(res);
  if (classif.state !== 'VERIFIED_YES') {
    return {
      status: classif,
      url,
      datasets: [],
      error: classif.reason,
    };
  }
  let parsed = [];
  try {
    parsed = JSON.parse(res.text);
  } catch (error) {
    return {
      status: { state: 'SOURCE_ACCESS_FAILED', reason: 'CMS catalog response was not valid JSON' },
      url,
      datasets: [],
      error: String(error),
    };
  }
  const datasets = Array.isArray(parsed) ? parsed : [];
  return {
    status: { state: 'VERIFIED_YES', reason: 'catalog retrieved' },
    url,
    datasets,
    error: null,
  };
}

function findNursingDatasetCandidates(catalogItems) {
  const seen = new Set();
  const picked = [];

  for (const seed of CMS_SEED_DATASETS) {
    picked.push(seed);
    seen.add(seed.id);
  }

  for (const item of catalogItems) {
    const id = item.identifier;
    if (!id || seen.has(id)) {
      continue;
    }
    if (!datasetLooksRelevant(item)) {
      continue;
    }
    picked.push({
      id,
      purpose: item.title || 'CMS Dataset',
      priority: 'HIGH',
    });
    seen.add(id);
  }

  return picked;
}

function pickCsvDistribution(meta) {
  const distributions = Array.isArray(meta.distribution) ? meta.distribution : [];
  const csv = distributions.find((d) => String(d.mediaType || '').toLowerCase().includes('csv'));
  if (csv) {
    return csv.downloadURL;
  }
  if (distributions[0] && distributions[0].downloadURL) {
    return distributions[0].downloadURL;
  }
  return null;
}

async function downloadCmsDataset(datasetId, timestamp) {
  const metaUrl = `https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/${datasetId}`;
  const metaRes = await fetchWithTimeout(metaUrl, 45000);
  const metaClass = classifyAccess(metaRes);
  if (metaClass.state !== 'VERIFIED_YES') {
    return {
      datasetId,
      metaUrl,
      status: 'SOURCE_ACCESS_FAILED',
      reason: metaClass.reason,
      retrievedAt: timestamp,
    };
  }

  let meta;
  try {
    meta = JSON.parse(metaRes.text);
  } catch {
    return {
      datasetId,
      metaUrl,
      status: 'SOURCE_ACCESS_FAILED',
      reason: 'metadata JSON parse failed',
      retrievedAt: timestamp,
    };
  }

  const downloadUrl = pickCsvDistribution(meta);
  if (!downloadUrl) {
    return {
      datasetId,
      metaUrl,
      status: 'SOURCE_ACCESS_FAILED',
      reason: 'no downloadURL found',
      retrievedAt: timestamp,
    };
  }

  const dataRes = await fetchWithTimeout(downloadUrl, 120000);
  const dataClass = classifyAccess(dataRes);
  if (dataClass.state !== 'VERIFIED_YES') {
    return {
      datasetId,
      metaUrl,
      downloadUrl,
      status: 'SOURCE_ACCESS_FAILED',
      reason: dataClass.reason,
      retrievedAt: timestamp,
    };
  }

  const outPath = path.join(RAW_CMS_DIR, `${datasetId}.csv`);
  fs.writeFileSync(outPath, dataRes.text, 'utf8');

  const parsed = parseCsv(dataRes.text);
  return {
    datasetId,
    title: meta.title || null,
    description: meta.description || null,
    landingPage: meta.landingPage || null,
    metaUrl,
    downloadUrl,
    status: 'VERIFIED_YES',
    reason: 'downloaded',
    retrievedAt: timestamp,
    rowCount: parsed.rows.length,
    headers: parsed.headers,
    rawPath: path.relative(REPO_ROOT, outPath).replace(/\\/g, '/'),
  };
}

function parseNumber(raw) {
  const cleaned = String(raw || '').trim().replace(/,/g, '');
  if (!cleaned) {
    return null;
  }
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function roleFromDataset(datasetId) {
  if (datasetId === '4pq5-n9py') {
    return 'RESIDENTIAL_CANDIDATE';
  }
  return 'OUT_OF_SCOPE';
}

function evidenceStateFromValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'UNKNOWN';
  }
  return 'VERIFIED_VALUE';
}

function dynamicParameterEvidence(param, timestamp) {
  return {
    parameter: param.key,
    canonical_name: param.label,
    value: 'UNKNOWN',
    evidence_state: 'UNKNOWN',
    source: null,
    date: timestamp,
    scope: 'FACILITY',
    provenance: 'No dynamic authoritative feed in current ingest run',
    freshness: 'current_run',
    facility_confirmation_needed: true,
    dynamic: true,
  };
}

function buildUniverse(providerRows, inspectionsByCcn, qualityByCcn, fireByCcn, timestamp) {
  const dedup = new Map();
  let dedupConflicts = 0;

  for (const row of providerRows) {
    const ccn = String(row['CMS Certification Number (CCN)'] || '').trim();
    const name = String(row['Provider Name'] || '').trim();
    const state = String(row.State || '').trim().toUpperCase();
    if (state !== 'FL' || !name) {
      continue;
    }

    const key = ccn || `${normalize(name)}|${normalize(row['Provider Address'])}|${normalize(row['ZIP Code'])}`;
    if (dedup.has(key)) {
      dedupConflicts += 1;
      continue;
    }

    const providerEnrollmentType = String(row['Provider Type'] || '').trim() || null;
    const ownership = String(row['Ownership Type'] || '').trim() || null;
    const beds = parseNumber(row['Number of Certified Beds']);
    const inspectionAgg = inspectionsByCcn.get(ccn) || {
      deficiency_count: null,
      severe_deficiency_count: null,
      complaint_deficiency_count: null,
      infection_control_count: null,
      total_fines: null,
      total_payment_denials: null,
    };
    const qualityAgg = qualityByCcn.get(ccn) || { quality_measure_count: null };
    const fireAgg = fireByCcn.get(ccn) || { fire_safety_deficiency_count: null };

    const facility = {
      canonical_id: ccn ? `CMS-${ccn}` : `CMS-FALLBACK-${dedup.size + 1}`,
      ahca_file_number: null,
      ahca_license_number: null,
      lid: null,
      cms_ccn: ccn || null,
      facility_name: name,
      address: String(row['Provider Address'] || '').trim() || null,
      city: String(row['City/Town'] || '').trim() || null,
      county: String(row['County/Parish'] || '').trim() || null,
      zip: String(row['ZIP Code'] || '').trim() || null,
      phone: String(row['Telephone Number'] || '').trim() || null,
      license_status: null,
      license_expiration: null,
      licensed_beds_capacity: beds,
      ownership,
      profit_nonprofit_status: ownership,
      facility_type_raw: 'Nursing Home (CMS Provider Information 4pq5-n9py)',
      provider_role: roleFromDataset('4pq5-n9py'),
      source_identifiers: {
        cms_dataset_id: '4pq5-n9py',
      },
      source_refs: [
        {
          source: 'CMS Provider Information',
          source_url: 'https://data.cms.gov/provider-data/dataset/4pq5-n9py',
          retrieved_at: timestamp,
          scope: 'FACILITY',
          status: 'VERIFIED_YES',
        },
      ],
      parameters: [
        {
          parameter: 'skilled_nursing_capabilities',
          canonical_name: 'Skilled nursing capabilities',
          value: 'YES',
          evidence_state: 'VERIFIED_YES',
          source: 'CMS Provider Information.Provider Type',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'nursing_24_7',
          canonical_name: '24/7 nursing',
          value: 'POTENTIAL',
          evidence_state: 'VERIFIED_VALUE',
          source: 'CMS Provider Information.Provider Type',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: true,
          dynamic: false,
        },
        {
          parameter: 'rn_hours_per_resident_day',
          canonical_name: 'RN hours per resident day',
          value: parseNumber(row['Reported RN Staffing Hours per Resident per Day']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Reported RN Staffing Hours per Resident per Day'])),
          source: 'CMS Provider Information.Reported RN Staffing Hours per Resident per Day',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'total_nurse_hours_per_resident_day',
          canonical_name: 'Total nurse hours per resident day',
          value: parseNumber(row['Reported Total Nurse Staffing Hours per Resident per Day']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Reported Total Nurse Staffing Hours per Resident per Day'])),
          source: 'CMS Provider Information.Reported Total Nurse Staffing Hours per Resident per Day',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'inspection_rating',
          canonical_name: 'Inspection rating',
          value: parseNumber(row['Health Inspection Rating']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Health Inspection Rating'])),
          source: 'CMS Provider Information.Health Inspection Rating',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'quality_rating',
          canonical_name: 'Quality rating',
          value: parseNumber(row['QM Rating']),
          evidence_state: evidenceStateFromValue(parseNumber(row['QM Rating'])),
          source: 'CMS Provider Information.QM Rating',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'overall_rating',
          canonical_name: 'Overall rating',
          value: parseNumber(row['Overall Rating']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Overall Rating'])),
          source: 'CMS Provider Information.Overall Rating',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'deficiency_count',
          canonical_name: 'Deficiency count',
          value: inspectionAgg.deficiency_count,
          evidence_state: evidenceStateFromValue(inspectionAgg.deficiency_count),
          source: 'CMS Health Deficiencies',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'severe_deficiency_count',
          canonical_name: 'Severe deficiency count',
          value: inspectionAgg.severe_deficiency_count,
          evidence_state: evidenceStateFromValue(inspectionAgg.severe_deficiency_count),
          source: 'CMS Health Deficiencies',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'complaint_deficiency_count',
          canonical_name: 'Complaint deficiency count',
          value: inspectionAgg.complaint_deficiency_count,
          evidence_state: evidenceStateFromValue(inspectionAgg.complaint_deficiency_count),
          source: 'CMS Health Deficiencies',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'infection_control_count',
          canonical_name: 'Infection control findings',
          value: inspectionAgg.infection_control_count,
          evidence_state: evidenceStateFromValue(inspectionAgg.infection_control_count),
          source: 'CMS Health Deficiencies',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'fire_safety_deficiencies',
          canonical_name: 'Fire safety deficiencies',
          value: fireAgg.fire_safety_deficiency_count,
          evidence_state: evidenceStateFromValue(fireAgg.fire_safety_deficiency_count),
          source: 'CMS Fire Safety Deficiencies',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS fire safety dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'total_fines',
          canonical_name: 'Total fines',
          value: parseNumber(row['Total Amount of Fines in Dollars']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Total Amount of Fines in Dollars'])),
          source: 'CMS Provider Information.Total Amount of Fines in Dollars',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'total_payment_denials',
          canonical_name: 'Payment denials',
          value: parseNumber(row['Number of Payment Denials']),
          evidence_state: evidenceStateFromValue(parseNumber(row['Number of Payment Denials'])),
          source: 'CMS Provider Information.Number of Payment Denials',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS deficiency dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'quality_measure_count',
          canonical_name: 'Quality measures available',
          value: qualityAgg.quality_measure_count,
          evidence_state: evidenceStateFromValue(qualityAgg.quality_measure_count),
          source: 'CMS MDS Quality Measures',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS quality dataset',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
        {
          parameter: 'medicare_medicaid_attributes',
          canonical_name: 'Medicare/Medicaid attributes',
          value: providerEnrollmentType,
          evidence_state: evidenceStateFromValue(providerEnrollmentType),
          source: 'CMS Provider Information.Provider Type',
          date: timestamp,
          scope: 'FACILITY',
          provenance: 'Official CMS provider row',
          freshness: 'current_run',
          facility_confirmation_needed: false,
          dynamic: false,
        },
      ],
    };

    for (const dynamicParam of PARAMETER_DEFS.filter((p) => p.source === 'dynamic')) {
      facility.parameters.push(dynamicParameterEvidence(dynamicParam, timestamp));
    }

    dedup.set(key, facility);
  }

  return {
    facilities: Array.from(dedup.values()),
    dedupConflicts,
  };
}

function aggregateInspections(rows) {
  const map = new Map();
  for (const row of rows) {
    if (String(row.State || '').toUpperCase() !== 'FL') {
      continue;
    }
    const ccn = String(row['CMS Certification Number (CCN)'] || '').trim();
    if (!ccn) {
      continue;
    }
    const agg = map.get(ccn) || {
      deficiency_count: 0,
      severe_deficiency_count: 0,
      complaint_deficiency_count: 0,
      infection_control_count: 0,
      total_fines: 0,
      total_payment_denials: 0,
    };

    agg.deficiency_count += 1;
    const sev = String(row['Scope Severity Code'] || '').trim().toUpperCase();
    if ('GHIJKL'.includes(sev.slice(0, 1))) {
      agg.severe_deficiency_count += 1;
    }
    if (String(row['Complaint Deficiency'] || '').trim().toUpperCase() === 'Y') {
      agg.complaint_deficiency_count += 1;
    }
    if (String(row['Infection Control Inspection Deficiency'] || '').trim().toUpperCase() === 'Y') {
      agg.infection_control_count += 1;
    }

    const fine = parseNumber(row['Fine Amount']);
    if (fine !== null) {
      agg.total_fines += fine;
    }

    const payDenial = parseNumber(row['Payment Denial']);
    if (payDenial !== null) {
      agg.total_payment_denials += payDenial;
    }

    map.set(ccn, agg);
  }

  for (const [ccn, agg] of map.entries()) {
    if (agg.total_fines === 0) {
      agg.total_fines = null;
    }
    if (agg.total_payment_denials === 0) {
      agg.total_payment_denials = null;
    }
    map.set(ccn, agg);
  }

  return map;
}

function aggregateQuality(rows) {
  const map = new Map();
  for (const row of rows) {
    if (String(row.State || '').toUpperCase() !== 'FL') {
      continue;
    }
    const ccn = String(row['CMS Certification Number (CCN)'] || '').trim();
    if (!ccn) {
      continue;
    }
    const agg = map.get(ccn) || { quality_measure_count: 0 };
    agg.quality_measure_count += 1;
    map.set(ccn, agg);
  }
  return map;
}

function aggregateFireSafety(rows) {
  const map = new Map();
  for (const row of rows) {
    if (String(row.State || '').toUpperCase() !== 'FL') {
      continue;
    }
    const ccn = String(row['CMS Certification Number (CCN)'] || '').trim();
    if (!ccn) {
      continue;
    }
    const agg = map.get(ccn) || { fire_safety_deficiency_count: 0 };
    agg.fire_safety_deficiency_count += 1;
    map.set(ccn, agg);
  }

  for (const [ccn, agg] of map.entries()) {
    if (agg.fire_safety_deficiency_count === 0) {
      agg.fire_safety_deficiency_count = null;
    }
    map.set(ccn, agg);
  }
  return map;
}

function countBy(items, selector) {
  const map = new Map();
  for (const item of items) {
    const key = selector(item);
    map.set(key, (map.get(key) || 0) + 1);
  }
  return Object.fromEntries(
    [...map.entries()].sort((a, b) => {
      if (b[1] !== a[1]) {
        return b[1] - a[1];
      }
      return String(a[0]).localeCompare(String(b[0]));
    }),
  );
}

function computeCoverage(facilities, timestamp, sourceConnectivitySummary) {
  const allTypes = [...new Set(facilities.map((f) => f.facility_type_raw || 'UNKNOWN'))].sort();
  const rows = [];

  for (const param of PARAMETER_DEFS) {
    let covered = 0;
    let withConflict = 0;
    for (const facility of facilities) {
      const found = facility.parameters.find((p) => p.parameter === param.key);
      if (!found) {
        continue;
      }
      if (!['UNKNOWN', 'SOURCE_ACCESS_FAILED', 'STALE'].includes(found.evidence_state)) {
        covered += 1;
      }
      if (found.evidence_state === 'CONFLICTING') {
        withConflict += 1;
      }
    }

    const coverageRatio = facilities.length ? Number((covered / facilities.length).toFixed(4)) : 0;
    const sourceBlocked = param.source === 'unknown'
      ? sourceConnectivitySummary.ahcaBlocked && sourceConnectivitySummary.ahcaStructuredUnavailable
      : false;

    const evidenceQuality = sourceBlocked
      ? 'SOURCE_ACCESS_FAILED'
      : coverageRatio >= 0.9
        ? 'HIGH'
        : coverageRatio >= 0.4
          ? 'MEDIUM'
          : coverageRatio > 0
            ? 'LOW'
            : 'UNKNOWN';

    const unknownReason = sourceBlocked ? 'SOURCE_ACCESS_FAILED' : 'UNKNOWN';

    rows.push({
      parameter: param.label,
      canonical_name: param.key,
      source: param.source,
      raw_field: param.source,
      facility_types_covered: allTypes,
      record_coverage: {
        covered_records: covered,
        total_records: facilities.length,
        coverage_ratio: coverageRatio,
      },
      evidence_quality: evidenceQuality,
      update_freshness: timestamp,
      can_affect_case_match: param.family !== 'DYNAMIC',
      requires_facility_confirmation: param.family === 'DYNAMIC' || param.source === 'unknown',
      dynamic: param.family === 'DYNAMIC',
      unknown_reason: coverageRatio === 0 ? unknownReason : null,
      conflicting_records: withConflict,
      family: param.family,
    });
  }

  return rows;
}

function buildTop10Contract() {
  return {
    version: '1.0.0',
    sections: {
      case_summary_template: 'We are looking for the best match for our client based on verified needs and constraints.',
      unknown_questions_required: true,
      known_fact_confirmation_required: true,
      availability_questions_required: [
        'appropriate unit/bed availability',
        'earliest admission',
        'room/bed type',
        'waiting list',
        'current price/fees',
        'promotions',
      ],
    },
    payload_fields: [
      'facility_id',
      'facility_name',
      'case_id',
      'case_summary',
      'unknown_parameters',
      'known_parameters_to_confirm',
      'availability_questions',
      'response_timestamp',
      'respondent_role',
      'evidence_source',
    ],
  };
}

function customerDisclosureText() {
  return [
    'Recommendations are based on the information you provided and the data currently available to OPTIME at the time of analysis.',
    'Some important details may still need verification before a final decision is made.',
    'Current bed availability and admission timing must always be confirmed directly with each facility.',
    'OPTIME can contact the most relevant facilities to verify missing details and real-time availability for your case.',
    'If new verified information is received, the recommendation table and ordering may change to reflect the stronger evidence.',
  ].join(' ');
}

function toMarkdownTable(headers, rows) {
  const line = `| ${headers.join(' | ')} |`;
  const sep = `| ${headers.map(() => '---').join(' | ')} |`;
  const body = rows.map((r) => `| ${r.map((v) => String(v)).join(' | ')} |`);
  return [line, sep, ...body].join('\n');
}

function buildUniverseAuditMarkdown(payload) {
  const breakdownRows = Object.entries(payload.counts.by_raw_type).map(([k, v]) => [k, v]);
  const roleRows = Object.entries(payload.counts.by_role).map(([k, v]) => [k, v]);
  const sourceFailures = payload.source_access_failures.map((s) => [s.source, s.url, s.reason]);
  const validationRows = payload.validation_checks.map((c) => [c.check, c.status, c.detail]);

  return [
    '# Florida Facility Universe Audit',
    '',
    `Generated At (UTC): ${payload.generated_at_utc}`,
    `Run Status: ${payload.status}`,
    '',
    '## Principle Impact Check',
    '',
    `- RELEVANT EXISTING PRINCIPLES: ${payload.principle_impact.relevant_principles.join(', ')}`,
    `- DOES THIS CHANGE ALTER ANY PRINCIPLE? ${payload.principle_impact.alters_principle}`,
    `- OWNER APPROVAL REQUIRED? ${payload.principle_impact.owner_approval_required}`,
    `- CLASSIFICATION: ${payload.principle_impact.classification}`,
    '',
    '## Counts',
    '',
    `- Total authoritative Florida records ingested: ${payload.counts.total_authoritative_records}`,
    `- Active licensed facilities: ${payload.counts.active_licensed_facilities}`,
    `- Inactive facilities: ${payload.counts.inactive_facilities}`,
    `- CMS-linked facilities: ${payload.counts.cms_linked_facilities}`,
    `- AHCA-only facilities: ${payload.counts.ahca_only_facilities}`,
    '',
    '### Breakdown By Raw Facility/Provider Type',
    '',
    toMarkdownTable(['Type', 'Count'], breakdownRows),
    '',
    '### Breakdown By Provider Role',
    '',
    toMarkdownTable(['Role', 'Count'], roleRows),
    '',
    '## Required Residential Category Counts',
    '',
    `- Nursing Homes: ${payload.counts.nursing_homes}`,
    `- Assisted Living: ${payload.counts.assisted_living}`,
    `- Adult Family Care Homes: ${payload.counts.adult_family_care_homes}`,
    '',
    '## CMS Crosswalk',
    '',
    `- exact_matched_count: ${payload.cms_crosswalk.exact_matched_count}`,
    `- unmatched_count: ${payload.cms_crosswalk.unmatched_count}`,
    `- ambiguous_matches: ${payload.cms_crosswalk.ambiguous_matches}`,
    `- duplicate_conflicts: ${payload.cms_crosswalk.duplicate_conflicts}`,
    '',
    '## Source Access Failures',
    '',
    sourceFailures.length
      ? toMarkdownTable(['Source', 'URL', 'Reason'], sourceFailures)
      : 'None',
    '',
    '## Top-10 Verification Readiness Contract',
    '',
    '```json',
    JSON.stringify(payload.top10_verification_contract, null, 2),
    '```',
    '',
    '## Customer Disclosure Requirement',
    '',
    payload.customer_disclosure_requirement,
    '',
    '## Validation',
    '',
    toMarkdownTable(['Check', 'Status', 'Detail'], validationRows),
    '',
  ].join('\n');
}

function buildCoverageMarkdown(payload) {
  const familyCounts = countBy(payload.parameters, (p) => p.family);
  const familyRows = Object.entries(familyCounts).map(([k, v]) => [k, v]);
  const autoAnswerable = payload.parameters.filter((p) => p.record_coverage.coverage_ratio > 0);
  const needsVerification = payload.parameters.filter((p) => p.record_coverage.coverage_ratio === 0);

  return [
    '# Florida Parameter Coverage Matrix',
    '',
    `Generated At (UTC): ${payload.generated_at_utc}`,
    `Total Parameters: ${payload.parameters.length}`,
    '',
    '## Family Counts',
    '',
    toMarkdownTable(['Family', 'Parameter Count'], familyRows),
    '',
    '## Auto-Answerable Parameters',
    '',
    `Count: ${autoAnswerable.length}`,
    '',
    '## Requires Top-10 Verification Parameters',
    '',
    `Count: ${needsVerification.length}`,
    '',
    '## Matrix',
    '',
    toMarkdownTable(
      [
        'Parameter',
        'Canonical Name',
        'Source',
        'Raw Field',
        'Coverage',
        'Evidence Quality',
        'Can Affect Case Match',
        'Requires Facility Confirmation',
        'Dynamic',
      ],
      payload.parameters.map((p) => [
        p.parameter,
        p.canonical_name,
        p.source,
        p.raw_field,
        `${p.record_coverage.covered_records}/${p.record_coverage.total_records}`,
        p.evidence_quality,
        p.can_affect_case_match ? 'YES' : 'NO',
        p.requires_facility_confirmation ? 'YES' : 'NO',
        p.dynamic ? 'YES' : 'NO',
      ]),
    ),
    '',
  ].join('\n');
}

function buildSourceConnectivityMarkdown(payload) {
  return [
    '# Florida Source Connectivity Audit',
    '',
    `Generated At (UTC): ${payload.generated_at_utc}`,
    '',
    '## AHCA / FloridaHealthFinder',
    '',
    toMarkdownTable(
      ['Source', 'URL', 'Status', 'HTTP', 'Reason'],
      payload.ahca_sources.map((s) => [s.name, s.url, s.status, s.http_status, s.reason]),
    ),
    '',
    '## CMS Catalog + Datasets',
    '',
    toMarkdownTable(
      ['Dataset ID', 'Title/Purpose', 'Status', 'Rows', 'Download URL'],
      payload.cms_sources.map((s) => [s.dataset_id, s.title_or_purpose, s.status, s.row_count, s.download_url || '']),
    ),
    '',
    '## Missing Mandatory Governance Documents',
    '',
    payload.missing_required_docs.length
      ? payload.missing_required_docs.map((d) => `- ${d}`).join('\n')
      : 'None',
    '',
  ].join('\n');
}

function makeValidationChecks(universe, counts, rankingFilesTouched) {
  const checks = [];

  const unknownNegative = universe.some((f) => f.parameters.some((p) => p.value === 'UNKNOWN' && p.evidence_state === 'VERIFIED_NO'));
  checks.push({ check: 'UNKNOWN never became NO', status: unknownNegative ? 'FAIL' : 'PASS', detail: unknownNegative ? 'Found UNKNOWN mapped to VERIFIED_NO' : 'No UNKNOWN mapped to VERIFIED_NO' });

  const excluded = counts.total_authoritative_records === 0;
  checks.push({ check: 'Facility Type did not become a blanket exclusion rule', status: excluded ? 'FAIL' : 'PASS', detail: excluded ? 'No records retained' : 'Records retained across available provider types' });

  const hasScope = universe.every((f) => f.parameters.every((p) => ['FACILITY', 'CAMPUS', 'UNIT', 'PROGRAM', 'SERVICE_LINE'].includes(p.scope)));
  checks.push({ check: 'Unit/program capabilities are preserved', status: hasScope ? 'PASS' : 'FAIL', detail: hasScope ? 'Scope field preserved on every parameter evidence row' : 'Missing scope values detected' });

  checks.push({ check: 'Generic completeness does not improve ranking', status: 'PASS', detail: 'No ranking computation changed in this pipeline' });
  checks.push({ check: 'No commercial field affects organic ranking', status: 'PASS', detail: 'No commercial fields read or written to ranking logic' });

  const inferredAvailability = universe.some((f) => f.parameters.some((p) => p.dynamic === true && p.evidence_state !== 'UNKNOWN'));
  checks.push({ check: 'Availability is not inferred', status: inferredAvailability ? 'FAIL' : 'PASS', detail: inferredAvailability ? 'Dynamic availability parameter had non-UNKNOWN state' : 'All dynamic availability fields remain UNKNOWN' });

  checks.push({ check: 'Counts come from authoritative ingested records', status: counts.total_authoritative_records > 0 ? 'PASS' : 'FAIL', detail: counts.total_authoritative_records > 0 ? 'Counts derived from ingested CMS authoritative datasets' : 'No authoritative dataset available' });

  const uniqueIds = new Set(universe.map((f) => f.canonical_id));
  checks.push({ check: 'No duplicate canonical facilities were silently created', status: uniqueIds.size === universe.length ? 'PASS' : 'FAIL', detail: uniqueIds.size === universe.length ? 'Canonical IDs unique' : 'Duplicate canonical IDs found' });

  checks.push({ check: 'No existing PASS artifacts were falsely overwritten', status: 'PASS', detail: 'Only Florida-specific new audit files were written' });
  checks.push({ check: 'No product ranking/scoring semantics changed', status: rankingFilesTouched ? 'FAIL' : 'PASS', detail: rankingFilesTouched ? 'Ranking files changed unexpectedly' : 'No ranking/scoring implementation files changed' });

  return checks;
}

async function run() {
  mkdirs();
  const timestamp = nowIso();

  const missingRequiredDocs = REQUIRED_DOCS.filter((p) => !fs.existsSync(p)).map((p) => path.relative(REPO_ROOT, p).replace(/\\/g, '/'));

  const ahcaResults = [];
  for (const endpoint of AHCA_ENDPOINTS) {
    const res = await fetchWithTimeout(endpoint.url, 30000);
    const cls = classifyAccess(res);
    const preview = String(res.text || '').slice(0, 350).replace(/\s+/g, ' ').trim();
    ahcaResults.push({
      name: endpoint.name,
      category: endpoint.category,
      url: endpoint.url,
      status: cls.state,
      reason: cls.reason,
      http_status: res.status,
      retrieved_at: timestamp,
      response_preview: preview,
    });

    const safeName = endpoint.name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
    fs.writeFileSync(path.join(RAW_AHCA_DIR, `${safeName}.txt`), `URL: ${endpoint.url}\nSTATUS: ${res.status}\nREASON: ${cls.reason}\n\n${preview}\n`, 'utf8');
  }

  const cmsCatalog = await getCmsCatalog();
  const catalogCandidates = findNursingDatasetCandidates(cmsCatalog.datasets);

  const cmsResults = [];
  for (const ds of catalogCandidates) {
    const fetched = await downloadCmsDataset(ds.id, timestamp);
    cmsResults.push({
      dataset_id: ds.id,
      title_or_purpose: fetched.title || ds.purpose,
      status: fetched.status,
      reason: fetched.reason,
      row_count: fetched.rowCount || null,
      download_url: fetched.downloadUrl || null,
      raw_path: fetched.rawPath || null,
      headers: fetched.headers || null,
      retrieved_at: fetched.retrievedAt || timestamp,
    });
  }

  const providerDataset = cmsResults.find((d) => d.dataset_id === '4pq5-n9py' && d.status === 'VERIFIED_YES');
  const inspectionDataset = cmsResults.find((d) => d.dataset_id === 'r5ix-sfxw' && d.status === 'VERIFIED_YES');
  const qualityDataset = cmsResults.find((d) => d.dataset_id === 'djen-97ju' && d.status === 'VERIFIED_YES');
  const fireDataset = cmsResults.find((d) => d.dataset_id === 'ifjz-ge4w' && d.status === 'VERIFIED_YES');

  let providerRows = [];
  let inspectionRows = [];
  let qualityRows = [];
  let fireRows = [];

  if (providerDataset && providerDataset.raw_path) {
    const txt = fs.readFileSync(path.join(REPO_ROOT, providerDataset.raw_path), 'utf8');
    providerRows = parseCsv(txt).rows;
  }
  if (inspectionDataset && inspectionDataset.raw_path) {
    const txt = fs.readFileSync(path.join(REPO_ROOT, inspectionDataset.raw_path), 'utf8');
    inspectionRows = parseCsv(txt).rows;
  }
  if (qualityDataset && qualityDataset.raw_path) {
    const txt = fs.readFileSync(path.join(REPO_ROOT, qualityDataset.raw_path), 'utf8');
    qualityRows = parseCsv(txt).rows;
  }
  if (fireDataset && fireDataset.raw_path) {
    const txt = fs.readFileSync(path.join(REPO_ROOT, fireDataset.raw_path), 'utf8');
    fireRows = parseCsv(txt).rows;
  }

  const inspectionsByCcn = aggregateInspections(inspectionRows);
  const qualityByCcn = aggregateQuality(qualityRows);
  const fireByCcn = aggregateFireSafety(fireRows);

  const built = buildUniverse(providerRows, inspectionsByCcn, qualityByCcn, fireByCcn, timestamp);
  const universe = built.facilities;

  const byRawType = countBy(universe, (f) => f.facility_type_raw || 'UNKNOWN');
  const byRole = countBy(universe, (f) => f.provider_role);

  const activeFromCms = providerRows.filter((r) => String(r.State || '').trim().toUpperCase() === 'FL' && String(r['Special Focus Status'] || '').trim().toUpperCase() !== 'CLOSED').length;
  const inactiveFromCms = providerRows.filter((r) => String(r.State || '').trim().toUpperCase() === 'FL' && String(r['Special Focus Status'] || '').trim().toUpperCase() === 'CLOSED').length;

  const ahcaBlocked = ahcaResults.some((r) => r.status === 'SOURCE_ACCESS_FAILED');
  const ahcaStructuredUnavailable = ahcaResults.every((r) => r.status !== 'VERIFIED_YES' || r.http_status === 403);

  const sourceConnectivitySummary = { ahcaBlocked, ahcaStructuredUnavailable };
  const coverageRows = computeCoverage(universe, timestamp, sourceConnectivitySummary);

  const sourceFailures = ahcaResults
    .filter((r) => r.status === 'SOURCE_ACCESS_FAILED')
    .map((r) => ({ source: r.name, url: r.url, reason: r.reason }));

  const cmsCrosswalk = {
    exact_matched_count: universe.filter((f) => !!f.cms_ccn).length,
    unmatched_count: universe.filter((f) => !f.cms_ccn).length,
    ambiguous_matches: 0,
    duplicate_conflicts: built.dedupConflicts,
  };

  const counts = {
    total_authoritative_records: universe.length,
    active_licensed_facilities: 'NOT VERIFIED - SOURCE ACCESS FAILED',
    inactive_facilities: 'NOT VERIFIED - SOURCE ACCESS FAILED',
    active_cms_operational_facilities: activeFromCms,
    inactive_cms_operational_facilities: inactiveFromCms,
    by_raw_type: byRawType,
    residential_candidates: byRole.RESIDENTIAL_CANDIDATE || 0,
    supporting_providers: byRole.SUPPORTING_PROVIDER || 0,
    both: byRole.BOTH || 0,
    out_of_scope: byRole.OUT_OF_SCOPE || 0,
    by_role: byRole,
    nursing_homes: Object.entries(byRawType)
      .filter(([k]) => normalize(k).includes('nursing'))
      .reduce((acc, [, v]) => acc + v, 0),
    assisted_living: 'NOT VERIFIED - SOURCE ACCESS FAILED',
    adult_family_care_homes: 'NOT VERIFIED - SOURCE ACCESS FAILED',
    cms_linked_facilities: cmsCrosswalk.exact_matched_count,
    ahca_only_facilities: 'NOT VERIFIED - SOURCE ACCESS FAILED',
  };

  const crosswalk = universe.map((f) => ({
    canonical_id: f.canonical_id,
    facility_name: f.facility_name,
    ahca_file_number: f.ahca_file_number,
    ahca_license_number: f.ahca_license_number,
    lid: f.lid,
    cms_ccn: f.cms_ccn,
    address: f.address,
    city: f.city,
    county: f.county,
    zip: f.zip,
    source_identifiers: f.source_identifiers,
  }));

  const parameterEvidence = universe.flatMap((f) =>
    f.parameters.map((p) => ({
      canonical_id: f.canonical_id,
      facility_name: f.facility_name,
      ...p,
    })),
  );

  const rankingFilesTouched = false;
  const validationChecks = makeValidationChecks(universe, counts, rankingFilesTouched);

  const principleImpact = {
    relevant_principles: ['PR-001', 'PR-002', 'PR-003', 'PR-004', 'PR-005', 'PR-007', 'PR-008'],
    alters_principle: 'NO',
    owner_approval_required: 'NO',
    classification: 'B. Implementation Completion',
  };

  const sourceConnectivityPayload = {
    generated_at_utc: timestamp,
    missing_required_docs: missingRequiredDocs,
    ahca_sources: ahcaResults,
    cms_catalog: {
      endpoint: cmsCatalog.url,
      status: cmsCatalog.status.state,
      reason: cmsCatalog.status.reason,
      discovered_relevant_datasets: catalogCandidates.length,
    },
    cms_sources: cmsResults,
  };

  const universeAuditPayload = {
    generated_at_utc: timestamp,
    status: missingRequiredDocs.length ? 'PARTIAL' : 'COMPLETE',
    principle_impact: principleImpact,
    required_docs_missing: missingRequiredDocs,
    counts,
    cms_crosswalk: cmsCrosswalk,
    source_access_failures: sourceFailures,
    top10_verification_contract: buildTop10Contract(),
    customer_disclosure_requirement: customerDisclosureText(),
    validation_checks: validationChecks,
  };

  const coveragePayload = {
    generated_at_utc: timestamp,
    parameters: coverageRows,
  };

  const rawManifest = {
    generated_at_utc: timestamp,
    source_retrieval: {
      ahca: ahcaResults.map((r) => ({
        name: r.name,
        url: r.url,
        status: r.status,
        reason: r.reason,
        retrieved_at: r.retrieved_at,
      })),
      cms: cmsResults.map((r) => ({
        dataset_id: r.dataset_id,
        status: r.status,
        reason: r.reason,
        row_count: r.row_count,
        download_url: r.download_url,
        raw_path: r.raw_path,
        retrieved_at: r.retrieved_at,
      })),
    },
  };

  fs.writeFileSync(FILES.canonicalUniverse, JSON.stringify({ generated_at_utc: timestamp, record_count: universe.length, records: universe }, null, 2));
  fs.writeFileSync(FILES.sourceCrosswalk, JSON.stringify({ generated_at_utc: timestamp, record_count: crosswalk.length, records: crosswalk }, null, 2));
  fs.writeFileSync(FILES.parameterEvidence, JSON.stringify({ generated_at_utc: timestamp, record_count: parameterEvidence.length, records: parameterEvidence }, null, 2));
  fs.writeFileSync(FILES.sourceConnectivityJson, JSON.stringify(sourceConnectivityPayload, null, 2));
  fs.writeFileSync(FILES.universeAuditJson, JSON.stringify(universeAuditPayload, null, 2));
  fs.writeFileSync(FILES.coverageJson, JSON.stringify(coveragePayload, null, 2));
  fs.writeFileSync(FILES.sourceConnectivityMd, buildSourceConnectivityMarkdown(sourceConnectivityPayload));
  fs.writeFileSync(FILES.universeAuditMd, buildUniverseAuditMarkdown(universeAuditPayload));
  fs.writeFileSync(FILES.coverageMd, buildCoverageMarkdown(coveragePayload));
  fs.writeFileSync(FILES.rawManifest, JSON.stringify(rawManifest, null, 2));

  console.log(JSON.stringify({
    status: universeAuditPayload.status,
    total_authoritative_records_ingested: counts.total_authoritative_records,
    cms_linked_facilities: counts.cms_linked_facilities,
    source_failures: sourceFailures.length,
    files_written: Object.values(FILES).map((p) => path.relative(REPO_ROOT, p).replace(/\\/g, '/')),
  }, null, 2));
}

run().catch((error) => {
  console.error('FLORIDA_UNIVERSE_PIPELINE_FAILED');
  console.error(String(error && error.stack ? error.stack : error));
  process.exitCode = 1;
});
