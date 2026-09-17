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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(canonical.dataset_mode === 'SYNTHETIC_PILOT', 'canonical data must be labeled synthetic');
assert(canonical.records.length === 200, 'pilot must contain exactly 200 facilities');
assert(new Set(canonical.records.map((row) => row.canonical_id)).size === 200, 'pilot IDs must be unique');
assert(canonical.records.every((row) => row.synthetic_pilot === true && row.truth_label.includes('FICTIONAL')), 'every facility must be visibly fictional');
assert(new Set(canonical.records.map((row) => row.canonical_type)).size >= 8, 'pilot needs care-type diversity');
assert(new Set(canonical.records.map((row) => row.city)).size >= 3, 'pilot needs geographic diversity');
assert(evidence.records.length >= 4000, 'pilot needs broad parameter coverage');
assert(evidence.records.every((row) => row.provenance?.synthetic_pilot === true), 'every evidence row must carry synthetic provenance');
assert(rooms.records.length === 400, 'each facility needs two room offerings');
assert(rooms.records.every((row) => Number.isInteger(row.monthly_price_cents) && row.monthly_price_cents > 0), 'every room needs a price');
assert(new Set(rooms.records.map((row) => row.availability_status)).size === 3, 'availability must include available, waitlist and unavailable');
assert(media.records.length === 200, 'each facility needs a media profile');
assert(media.records.every((row) => row.gallery_images?.length === 5 && row.synthetic_pilot === true), 'each facility needs five labeled synthetic illustrations');
assert(capabilities.records.length === 6600, 'each facility must have the complete 33-question provider capability profile');
for (const limit of [50, 100, 150, 200]) {
  const exposed = canonical.records.slice().sort((a, b) => a.pilot_exposure_order - b.pilot_exposure_order).slice(0, limit);
  assert(exposed.length === limit, `cohort ${limit} must be reproducible`);
  assert(exposed.at(-1).pilot_exposure_order === limit, `cohort ${limit} must be nested and deterministic`);
}

console.log(JSON.stringify({
  status: 'PASS',
  facilities: canonical.records.length,
  evidence: evidence.records.length,
  rooms: rooms.records.length,
  mediaProfiles: media.records.length,
  providerCapabilities: capabilities.records.length,
  cohorts: [50, 100, 150, 200],
  types: [...new Set(canonical.records.map((row) => row.canonical_type))],
}, null, 2));
