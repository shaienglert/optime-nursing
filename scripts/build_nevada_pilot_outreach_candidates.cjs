#!/usr/bin/env node
/*
 * Builds the first 120 Nevada outreach candidates from the authoritative
 * statewide HCQC export and the independently verified housing overlay.
 *
 * It only prints JSON.  It does not create outreach records, discover emails,
 * or send anything.  A candidate with only a property source is deliberately
 * labelled NEEDS_CONTACT_DISCOVERY rather than being treated as ready to email.
 */
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const registry = JSON.parse(fs.readFileSync(path.join(root, 'data/nevada/verified/nv_hcqc_clark_registry.json'), 'utf8'));
const independent = JSON.parse(fs.readFileSync(path.join(root, 'data/nevada/verified/independent_living_primary_evidence.json'), 'utf8'));

const metro = (value) => /LAS VEGAS|HENDERSON|NORTH LAS VEGAS/i.test(String(value || ''));
const capacity = (row) => Number.parseInt(String(row.bed_count || '0'), 10) || 0;
const clean = (value) => String(value || '').trim();
const phoneKey = (row) => clean(row.phone).replace(/\D/g, '');
const contactKey = (row) => phoneKey(row) || clean(row.credential_number).toUpperCase();
const rank = (left, right) => capacity(right) - capacity(left) || clean(left.name).localeCompare(clean(right.name));

function licensedPool(types, minimumCapacity = 0) {
  return registry.records
    .filter((row) => row.status === 'Active')
    .filter((row) => metro(row.city))
    .filter((row) => types.includes(row.derived_care_type))
    .filter((row) => capacity(row) >= minimumCapacity)
    .filter((row) => phoneKey(row) && clean(row.credential_number))
    .sort(rank);
}

function licensedCandidate(row, segment) {
  return {
    candidate_key: `NV-LIC-${row.credential_number}`,
    facility_name: clean(row.name),
    segment,
    address: [clean(row.address), clean(row.city), 'NV', clean(row.zip)].filter(Boolean).join(', '),
    capacity: capacity(row),
    phone: clean(row.phone),
    license_number: clean(row.credential_number),
    evidence_status: 'VERIFIED',
    outreach_readiness: 'READY_FOR_CONTACT_REVIEW',
    source_url: clean(row.detail_url),
    source_name: 'Nevada DPBH HCQC active license registry',
  };
}

function independentCandidates() {
  const seenSourceDomains = new Set();
  return independent.records
    .filter((row) => row.classification === 'CONFIRMED_PRIMARY' && row.canonical_type === 'INDEPENDENT_LIVING')
    .map((row) => ({
      candidate_key: `NV-IL-${clean(row.expected_business_name).replace(/[^A-Z0-9]+/gi, '-').replace(/^-|-$/g, '').toUpperCase()}`,
      facility_name: clean(row.expected_business_name),
      segment: 'INDEPENDENT_LIVING',
      address: clean(row.expected_address),
      capacity: null,
      phone: null,
      license_number: clean(row.business_license_number) || null,
      evidence_status: 'VERIFIED',
      outreach_readiness: 'NEEDS_CONTACT_DISCOVERY',
      source_url: clean(row.primary_source_url),
      source_name: 'Independent-living primary property evidence',
    }))
    .filter((candidate) => {
      // One outreach relationship per verified operator/property domain in the
      // initial wave. Individual buildings remain represented in the universe.
      const domain = new URL(candidate.source_url).hostname.replace(/^www\./, '').toLowerCase();
      if (seenSourceDomains.has(domain)) return false;
      seenSourceDomains.add(domain);
      return true;
    });
}

const selected = [];
const usedContacts = new Set();
const usedNames = new Set();

function addFrom(pool, segment, quota, minimumCapacity = 0) {
  let added = 0;
  for (const row of pool) {
    if (added >= quota) break;
    if (capacity(row) < minimumCapacity) continue;
    const key = contactKey(row);
    const name = clean(row.name).toUpperCase();
    if (!key || usedContacts.has(key) || usedNames.has(name)) continue;
    selected.push(licensedCandidate(row, segment));
    usedContacts.add(key);
    usedNames.add(name);
    added += 1;
  }
  if (added !== quota) throw new Error(`Unable to fill ${segment}: expected ${quota}, got ${added}`);
}

// The quota is designed for product learning and commercial coverage, not to
// mirror arbitrary web-directory categories.
addFrom(licensedPool(['SKILLED_NURSING']), 'SKILLED_NURSING_REHAB', 35);
addFrom(licensedPool(['ASSISTED_LIVING_COMMUNITY', 'ASSISTED_LIVING_WITH_MEMORY_CARE']), 'ASSISTED_LIVING', 22);
addFrom(licensedPool(['MEMORY_CARE_DEDICATED_LARGE']), 'MEMORY_CARE_LARGE', 13);
addFrom(licensedPool(['GROUP_HOME_WITH_MEMORY_CARE']), 'MEMORY_CARE_SMALL', 9);
addFrom(licensedPool(['MEMORY_CARE_DEDICATED_HOME'], 10), 'MEMORY_CARE_SMALL', 23, 10);
addFrom(licensedPool(['RESIDENTIAL_GROUP_HOME'], 10), 'ASSISTED_LIVING_SMALL', 7, 10);

for (const candidate of independentCandidates()) {
  if (selected.length >= 120) break;
  const name = candidate.facility_name.toUpperCase();
  if (usedNames.has(name)) continue;
  selected.push(candidate);
  usedNames.add(name);
}

if (selected.length !== 120) throw new Error(`Expected 120 candidates, got ${selected.length}`);

const segmentCounts = selected.reduce((counts, row) => {
  counts[row.segment] = (counts[row.segment] || 0) + 1;
  return counts;
}, {});

process.stdout.write(`${JSON.stringify({
  generated_at: new Date().toISOString(),
  purpose: 'Initial facility-outreach pilot selection. Descriptive and operational only; not ranking input.',
  total_candidates: selected.length,
  segment_counts: segmentCounts,
  readiness_counts: selected.reduce((counts, row) => {
    counts[row.outreach_readiness] = (counts[row.outreach_readiness] || 0) + 1;
    return counts;
  }, {}),
  candidates: selected,
}, null, 2)}\n`);
