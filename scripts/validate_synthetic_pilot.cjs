const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const root = path.resolve(__dirname, '..');
const load = (name) => {
  const encoded = fs.readFileSync(path.join(root, 'database', 'synthetic_pilot', `${name}.gz.b64`), 'ascii').trim();
  return JSON.parse(zlib.gunzipSync(Buffer.from(encoded, 'base64')).toString('utf8'));
};
const canonical = load('facility_universe.json');
const evidence = load('facility_parameter_evidence.json');
const rooms = load('room_inventory.json');
const media = load('facility_media_registry.json');
const capabilities = load('provider_capabilities.json');
const expectedCount = 500;
const capacityRanges = {
  INDEPENDENT_LIVING: [50, 240], ACTIVE_ADULT_55_PLUS: [60, 300],
  ASSISTED_LIVING_RFG: [30, 180], MEMORY_CARE: [24, 120],
  SKILLED_NURSING: [40, 180], REHABILITATION: [30, 120],
  CONTINUING_CARE: [120, 450], SMALL_GROUP_HOME: [6, 16],
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(canonical.dataset_mode === 'SYNTHETIC_PILOT', 'canonical data must be labeled synthetic');
assert(canonical.records.length === expectedCount, `pilot must contain exactly ${expectedCount} facilities`);
const facilityIds = new Set(canonical.records.map((row) => row.canonical_id));
assert(facilityIds.size === expectedCount, 'pilot IDs must be unique');
assert(new Set(canonical.records.map((row) => row.facility_name)).size === expectedCount, 'every pilot community must have a unique name: two different communities with one name are indistinguishable in results');
assert(canonical.records.every((row) => row.synthetic_pilot === true && row.truth_label.includes('FICTIONAL')), 'every facility must be visibly fictional');
assert(canonical.records.every((row) => row.license_status === 'SYNTHETIC_PILOT_ACTIVE'
  && row.expiration_date === '12/31/2030'
  && row.license_expiration_source === 'SYNTHETIC_PILOT_TEST_ONLY'), 'all pilot license expirations must be explicitly synthetic');
for (const row of canonical.records) {
  const range = capacityRanges[row.synthetic_archetype];
  assert(range && Number.isInteger(row.licensed_capacity)
    && row.licensed_capacity >= range[0] && row.licensed_capacity <= range[1],
  `${row.canonical_id}: capacity must be in its archetype range`);
  const size = row.licensed_capacity < 45 ? 'SMALL' : row.licensed_capacity < 100 ? 'MEDIUM' : 'LARGE';
  assert(row.community_size === size, `${row.canonical_id}: community size contradicts capacity`);
}
for (const dataset of [canonical, evidence, rooms, media, capabilities]) {
  assert(dataset.record_count === dataset.records.length, 'record_count must match the actual records');
  assert(dataset.dataset_mode === 'SYNTHETIC_PILOT', 'every dataset must be labeled synthetic');
}
for (const dataset of [evidence, rooms, media, capabilities]) {
  assert(dataset.records.every((row) => facilityIds.has(row.canonical_facility_id)), 'child records must reference a catalog facility');
}
// canonical_type is intentionally collapsed onto the 3 values backend/app/services/
// patient_decision_engine's _care_setting_fit() recognizes (matching how real Nevada
// data is coded); care-type diversity lives in synthetic_archetype instead.
assert(new Set(canonical.records.map((row) => row.synthetic_archetype)).size >= 8, 'pilot needs care-type diversity');
assert(new Set(canonical.records.map((row) => row.canonical_type)).size === 3, 'canonical_type must stay within the production-recognized taxonomy');
assert(new Set(canonical.records.map((row) => row.city)).size >= 3, 'pilot needs geographic diversity');
assert(evidence.records.length >= 4000, 'pilot needs broad parameter coverage');
assert(evidence.records.every((row) => row.provenance?.synthetic_pilot === true), 'every evidence row must carry synthetic provenance');
assert(rooms.records.length === expectedCount * 2, 'each facility needs two room offerings');
assert(rooms.records.every((row) => Number.isInteger(row.monthly_price_cents) && row.monthly_price_cents > 0), 'every room needs a price');
assert(new Set(rooms.records.map((row) => row.availability_status)).size === 3, 'availability must include available, waitlist and unavailable');
assert(media.records.length === expectedCount, 'each facility needs a media profile');
assert(media.records.every((row) => row.gallery_images?.length === 5 && row.synthetic_pilot === true), 'each facility needs five labeled synthetic illustrations');
assert(capabilities.records.length === expectedCount * 33, 'each facility must have the complete 33-question provider capability profile');
for (const id of facilityIds) {
  const offers = rooms.records.filter((row) => row.canonical_facility_id === id);
  assert(offers.length === 2 && new Set(offers.map((row) => row.room_type_name)).size === 2, `${id}: exactly two distinct rooms required`);
  assert(offers.every((row) => Number.isInteger(row.available_units)
    && (row.availability_status === 'AVAILABLE' ? row.available_units > 0
      : ['WAITLIST', 'UNAVAILABLE'].includes(row.availability_status) && row.available_units === 0)),
  `${id}: room availability must agree with available units`);
  const units = offers.reduce((sum, row) => sum + row.available_units, 0);
  const expected = units > 1 ? 'YES' : units === 1 ? 'LIMITED' : 'NO';
  const availability = evidence.records.filter((row) => row.canonical_facility_id === id && row.parameter_id === 'current_availability');
  assert(availability.length === 1 && availability[0].value === expected && availability[0].evidence_value === expected,
    `${id}: facility availability contradicts room inventory`);
  assert(media.records.filter((row) => row.canonical_facility_id === id).length === 1, `${id}: exactly one media profile required`);
  const provider = capabilities.records.filter((row) => row.canonical_facility_id === id);
  assert(provider.length === 33 && new Set(provider.map((row) => row.capability)).size === 33, `${id}: 33 distinct provider capabilities required`);
}
for (const limit of [50, 100, 150, 200, 500]) {
  const exposed = canonical.records.slice().sort((a, b) => a.pilot_exposure_order - b.pilot_exposure_order).slice(0, limit);
  assert(exposed.length === limit, `cohort ${limit} must be reproducible`);
  assert(exposed.at(-1).pilot_exposure_order === limit, `cohort ${limit} must be nested and deterministic`);
}

// A name-prefix systematically tied to one archetype (e.g. every Continuing Care
// facility named "Canyon"/"Desert", every Memory Care facility named "Mesa"/"Mojave")
// meant every alphabetical tiebreak or shortlist cutoff by name -- see
// must_ai_nice_pipeline.py's rankable[:interactive_shortlist_limit] -- always favored
// the same archetypes regardless of clinical fit. Each archetype must draw from a real
// spread of prefixes, not a narrow, name-correlated subset.
{
  const prefixesByArchetype = new Map();
  for (const row of canonical.records) {
    const prefix = row.facility_name.split(' ')[0];
    if (!prefixesByArchetype.has(row.synthetic_archetype)) prefixesByArchetype.set(row.synthetic_archetype, new Set());
    prefixesByArchetype.get(row.synthetic_archetype).add(prefix);
  }
  for (const [archetype, prefixes] of prefixesByArchetype) {
    assert(prefixes.size >= 5, `${archetype} facility names must span at least 5 distinct prefixes, got ${prefixes.size}`);
  }
}

console.log(JSON.stringify({
  status: 'PASS',
  facilities: canonical.records.length,
  evidence: evidence.records.length,
  rooms: rooms.records.length,
  mediaProfiles: media.records.length,
  providerCapabilities: capabilities.records.length,
  cohorts: [50, 100, 150, 200, 500],
  types: [...new Set(canonical.records.map((row) => row.canonical_type))],
}, null, 2));
