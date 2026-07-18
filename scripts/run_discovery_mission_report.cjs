const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const INVENTORY_PATH = path.join(REPO_ROOT, 'database', 'south_florida_senior_living_inventory.json');
const BASELINE_PATH = path.join(REPO_ROOT, 'database', 'market_communities_south_florida.json');
const REPORT_PATH = path.join(REPO_ROOT, 'reports', 'discovery_report.md');

const FLORIDA_COUNTIES_TOTAL = 67;

const REQUIRED_CARE_TYPES = [
  'Independent Living',
  'Assisted Living',
  'Memory Care',
  'Skilled Nursing',
  'Continuing Care Retirement Communities (CCRC)',
  'Active Adult (55+)',
  'Adult Family Care Homes',
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function normalizeName(name) {
  return String(name || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function parseCityFromAddress(address) {
  const text = String(address || '');
  const parts = text.split(',').map((part) => part.trim()).filter(Boolean);
  if (parts.length < 2) return 'UNKNOWN';
  // Typical format: street, city, FL, zip
  const candidate = parts[1] || 'UNKNOWN';
  return candidate ? candidate.toUpperCase() : 'UNKNOWN';
}

function pct(part, total) {
  if (!total) return '0.0%';
  return `${((part / total) * 100).toFixed(1)}%`;
}

function markdownTable(headers, rows) {
  const esc = (v) => String(v ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function main() {
  const inventory = readJson(INVENTORY_PATH);
  const baseline = readJson(BASELINE_PATH);

  const records = Array.isArray(inventory.records) ? inventory.records : [];
  const baselineRecords = Array.isArray(baseline.records) ? baseline.records : [];

  const totalDiscovered = records.length;

  const verified = records.filter(
    (r) => r.state_license_number || r.license_profile_url,
  );
  const verifiedCount = verified.length;
  const pendingVerification = Math.max(0, totalDiscovered - verifiedCount);

  const currentNameSet = new Set(records.map((r) => normalizeName(r.community_name)).filter(Boolean));
  const baselineNameSet = new Set(baselineRecords.map((r) => normalizeName(r.community_name)).filter(Boolean));

  let newlyDiscovered = 0;
  let updatedCommunities = 0;
  currentNameSet.forEach((name) => {
    if (baselineNameSet.has(name)) {
      updatedCommunities += 1;
    } else {
      newlyDiscovered += 1;
    }
  });

  let closedCommunities = 0;
  baselineNameSet.forEach((name) => {
    if (!currentNameSet.has(name)) {
      closedCommunities += 1;
    }
  });

  const dupCounter = new Map();
  records.forEach((r) => {
    const key = normalizeName(r.community_name);
    if (!key) return;
    dupCounter.set(key, (dupCounter.get(key) || 0) + 1);
  });
  const duplicatesMerged = [...dupCounter.values()].reduce((sum, count) => sum + Math.max(0, count - 1), 0);

  const allCareTypesCounter = new Map();
  records.forEach((r) => {
    const types = Array.isArray(r.community_types) ? r.community_types : (r.primary_community_type ? [r.primary_community_type] : []);
    types.forEach((t) => {
      const key = String(t || '').trim();
      if (!key) return;
      allCareTypesCounter.set(key, (allCareTypesCounter.get(key) || 0) + 1);
    });
  });

  const additionalTypes = [...allCareTypesCounter.keys()].filter((t) => !REQUIRED_CARE_TYPES.includes(t)).sort();
  const careTypeRows = [
    ...REQUIRED_CARE_TYPES,
    ...additionalTypes,
  ].map((typeName) => {
    const count = allCareTypesCounter.get(typeName) || 0;
    return [typeName, count, pct(count, totalDiscovered)];
  });

  const byState = new Map();
  const byCounty = new Map();
  const byCity = new Map();

  records.forEach((r) => {
    const state = 'FL';
    const county = String(r.county || 'UNKNOWN').trim() || 'UNKNOWN';
    const city = parseCityFromAddress(r.address);
    byState.set(state, (byState.get(state) || 0) + 1);
    byCounty.set(county, (byCounty.get(county) || 0) + 1);
    byCity.set(city, (byCity.get(city) || 0) + 1);
  });

  const stateRows = [...byState.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, v, pct(v, totalDiscovered)]);
  const countyRows = [...byCounty.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, v, pct(v, totalDiscovered)]);
  const cityRows = [...byCity.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25).map(([k, v]) => [k, v, pct(v, totalDiscovered)]);

  const discoveredCountyCount = byCounty.has('UNKNOWN') ? byCounty.size - 1 : byCounty.size;
  const countyCoveragePct = (discoveredCountyCount / FLORIDA_COUNTIES_TOTAL) * 100;

  const requiredFields = ['community_name', 'address', 'phone', 'county', 'state_license_number', 'license_profile_url'];
  const missingByField = new Map(requiredFields.map((f) => [f, 0]));
  let completedFieldCells = 0;
  const totalFieldCells = totalDiscovered * requiredFields.length;

  const manualReviewSet = new Set();

  records.forEach((r, idx) => {
    requiredFields.forEach((field) => {
      const value = r[field];
      const present = value !== null && value !== undefined && String(value).trim() !== '';
      if (present) {
        completedFieldCells += 1;
      } else {
        missingByField.set(field, (missingByField.get(field) || 0) + 1);
      }
    });

    const hasCriticalMissing = !r.community_name || !r.address || !r.phone || !r.county;
    const lacksVerification = !(r.state_license_number || r.license_profile_url);
    if (hasCriticalMissing || lacksVerification) {
      manualReviewSet.add(idx);
    }
  });

  const completenessPct = totalFieldCells ? (completedFieldCells / totalFieldCells) * 100 : 0;

  const generatedAt = new Date(inventory.generated_at_utc || Date.now());
  const ageDays = Math.max(0, Math.floor((Date.now() - generatedAt.getTime()) / (1000 * 60 * 60 * 24)));
  const freshnessLabel = ageDays <= 1 ? 'Fresh (0-1 days)' : ageDays <= 7 ? 'Recent (2-7 days)' : ageDays <= 30 ? 'Aging (8-30 days)' : 'Stale (>30 days)';

  const conflictRows = [];
  const licenseToNames = new Map();
  records.forEach((r) => {
    const license = String(r.state_license_number || '').trim();
    if (!license) return;
    const key = license;
    if (!licenseToNames.has(key)) licenseToNames.set(key, new Set());
    licenseToNames.get(key).add(String(r.community_name || '').trim());
  });
  licenseToNames.forEach((names, license) => {
    if (names.size > 1) {
      conflictRows.push([license, names.size, [...names].slice(0, 3).join('; ')]);
    }
  });

  const duplicateConflictCount = [...dupCounter.values()].filter((v) => v > 1).length;
  const licenseConflictCount = conflictRows.length;
  const totalConflicts = duplicateConflictCount + licenseConflictCount;

  const missingRows = requiredFields.map((field) => [field, missingByField.get(field) || 0, pct(missingByField.get(field) || 0, totalDiscovered)]);

  const lines = [];
  lines.push('# Discovery Report');
  lines.push('');
  lines.push('Discovery Mission Status: **COMPLETE (Report Generated)**');
  lines.push(`Report Generated At (UTC): **${new Date().toISOString()}**`);
  lines.push(`Inventory Snapshot Timestamp (UTC): **${inventory.generated_at_utc || 'UNKNOWN'}**`);
  lines.push('');
  lines.push('## Discovery Totals');
  lines.push('');
  lines.push(`- Total number of communities discovered: **${totalDiscovered}**`);
  lines.push(`- Total number of verified communities: **${verifiedCount}**`);
  lines.push(`- Total number of communities pending verification: **${pendingVerification}**`);
  lines.push(`- Total number of newly discovered communities: **${newlyDiscovered}**`);
  lines.push(`- Total number of updated communities: **${updatedCommunities}**`);
  lines.push(`- Total number of closed communities: **${closedCommunities}**`);
  lines.push(`- Total number of duplicate communities merged: **${duplicatesMerged}**`);
  lines.push('');
  lines.push('## Care Type Classification');
  lines.push('');
  lines.push(markdownTable(['Care Type', 'Community Count', 'Share'], careTypeRows));
  lines.push('');
  lines.push('## Geographic Summaries');
  lines.push('');
  lines.push('### State');
  lines.push('');
  lines.push(markdownTable(['State', 'Communities', 'Share'], stateRows));
  lines.push('');
  lines.push('### County');
  lines.push('');
  lines.push(markdownTable(['County', 'Communities', 'Share'], countyRows));
  lines.push('');
  lines.push('### City (Top 25)');
  lines.push('');
  lines.push(markdownTable(['City', 'Communities', 'Share'], cityRows));
  lines.push('');
  lines.push('## Database Quality');
  lines.push('');
  lines.push(`- Coverage: **${discoveredCountyCount}/${FLORIDA_COUNTIES_TOTAL} counties** represented (${countyCoveragePct.toFixed(1)}%)`);
  lines.push(`- Completeness: **${completenessPct.toFixed(1)}%** across required profile fields`);
  lines.push(`- Verification status: **${verifiedCount}/${totalDiscovered} verified** (${pct(verifiedCount, totalDiscovered)})`);
  lines.push(`- Freshness: **${freshnessLabel}** (snapshot age: ${ageDays} day(s))`);
  lines.push(`- Missing data rows: **${[...missingByField.values()].reduce((a, b) => a + b, 0)}**`);
  lines.push(`- Data conflicts: **${totalConflicts}** (duplicate-name conflicts: ${duplicateConflictCount}, license conflicts: ${licenseConflictCount})`);
  lines.push(`- Communities requiring manual review: **${manualReviewSet.size}**`);
  lines.push('');
  lines.push('### Missing Data By Field');
  lines.push('');
  lines.push(markdownTable(['Field', 'Missing Count', 'Missing Rate'], missingRows));
  lines.push('');
  lines.push('### Data Conflict Detail (License Conflicts)');
  lines.push('');
  lines.push(markdownTable(['License', 'Distinct Community Names', 'Sample Names'], conflictRows.length ? conflictRows : [['None', 0, 'N/A']]));
  lines.push('');
  lines.push('## Scope And Method Notes');
  lines.push('');
  lines.push('- Source inventory file: `database/south_florida_senior_living_inventory.json` (current discovery snapshot).');
  lines.push('- Baseline comparison file: `database/market_communities_south_florida.json` (used to estimate newly discovered/updated/closed totals).');
  lines.push('- This report quantifies current institutional visibility and quality; statewide completeness remains an ongoing expansion objective.');

  fs.writeFileSync(REPORT_PATH, `${lines.join('\n')}\n`, 'utf8');
  console.log(`Wrote ${REPORT_PATH}`);
  console.log(`DISCOVERED_TOTAL=${totalDiscovered}`);
  console.log(`VERIFIED_TOTAL=${verifiedCount}`);
  console.log(`PENDING_VERIFICATION_TOTAL=${pendingVerification}`);
  console.log(`NEWLY_DISCOVERED_TOTAL=${newlyDiscovered}`);
  console.log(`UPDATED_TOTAL=${updatedCommunities}`);
  console.log(`CLOSED_TOTAL=${closedCommunities}`);
  console.log(`DUPLICATES_MERGED_TOTAL=${duplicatesMerged}`);
  console.log(`MANUAL_REVIEW_TOTAL=${manualReviewSet.size}`);
}

main();
