const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const simulationHelpers = require('./run_dynamic_persona_simulation_audit.cjs');

const TARGET_CATEGORIES = [
  'Active Adult 55+',
  'Independent Living',
  'Assisted Living',
  'Memory Care',
  'Skilled Nursing',
  'Rehabilitation',
  'CCRC',
];

const TARGET_MIX = {
  'Active Adult 55+': 15,
  'Independent Living': 25,
  'Assisted Living': 25,
  'Memory Care': 10,
  'Skilled Nursing': 15,
  Rehabilitation: 5,
  CCRC: 5,
};

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function percentage(part, whole) {
  if (!whole || whole <= 0) return 0;
  return Number(((part / whole) * 100).toFixed(2));
}

function topNEntries(mapLike, n = 10) {
  return [...mapLike.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}

function buildCategoryStats(primaryAssignments) {
  const stats = new Map();

  TARGET_CATEGORIES.forEach((category) => {
    stats.set(category, {
      facilities: 0,
      states: new Set(),
      cities: new Set(),
    });
  });

  primaryAssignments.forEach(({ facility, primaryCategory }) => {
    const entry = stats.get(primaryCategory);
    entry.facilities += 1;
    if (facility.state) entry.states.add(String(facility.state));
    if (facility.city) entry.cities.add(String(facility.city));
  });

  return stats;
}

function buildGeographicCoverage(facilities) {
  const byState = new Map();
  const byCity = new Map();

  facilities.forEach((facility) => {
    const state = String(facility.state || 'UNKNOWN');
    const city = String(facility.city || 'UNKNOWN');

    byState.set(state, (byState.get(state) || 0) + 1);
    byCity.set(city, (byCity.get(city) || 0) + 1);
  });

  return {
    byState,
    byCity,
  };
}

function normalizeCounty(value) {
  const county = String(value || '').trim();
  if (!county) return '';
  const withSuffix = county.toLowerCase().endsWith('county') ? county : `${county} County`;
  return withSuffix
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function inferCountyFromCity(city) {
  const normalized = String(city || '').trim().toUpperCase();
  const cityToCounty = {
    MIAMI: 'Miami-Dade County',
    'MIAMI BEACH': 'Miami-Dade County',
    'NORTH MIAMI': 'Miami-Dade County',
    'NORTH MIAMI BEACH': 'Miami-Dade County',
    HIALEAH: 'Miami-Dade County',
    DORAL: 'Miami-Dade County',
    AVENTURA: 'Miami-Dade County',
    HOMESTEAD: 'Miami-Dade County',
    'CORAL GABLES': 'Miami-Dade County',
    'MIAMI GARDENS': 'Miami-Dade County',
    SWEETWATER: 'Miami-Dade County',
    'FORT LAUDERDALE': 'Broward County',
    PLANTATION: 'Broward County',
    'POMPANO BEACH': 'Broward County',
    SUNRISE: 'Broward County',
    HOLLYWOOD: 'Broward County',
    DAVIE: 'Broward County',
    'DEERFIELD BEACH': 'Broward County',
    MARGATE: 'Broward County',
    LAUDERHILL: 'Broward County',
    'CORAL SPRINGS': 'Broward County',
    'PEMBROKE PINES': 'Broward County',
    'HALLANDALE BEACH': 'Broward County',
    'OAKLAND PARK': 'Broward County',
    'BOCA RATON': 'Palm Beach County',
    'DELRAY BEACH': 'Palm Beach County',
    'BOYNTON BEACH': 'Palm Beach County',
    'WEST PALM BEACH': 'Palm Beach County',
    'LAKE WORTH': 'Palm Beach County',
    'RIVIERA BEACH': 'Palm Beach County',
    GREENACRES: 'Palm Beach County',
    'PALM BEACH GARDENS': 'Palm Beach County',
    JUPITER: 'Palm Beach County',
  };

  return cityToCounty[normalized] || '';
}

function extractCountyFromAddress(address) {
  const match = String(address || '').match(/([A-Za-z .'-]+?)\s+County/i);
  if (!match) return '';
  return normalizeCounty(match[1]);
}

function buildCountyCoverage(backendFacilities) {
  const byCounty = new Map();

  backendFacilities.forEach((facility) => {
    const county =
      normalizeCounty(facility.county)
      || extractCountyFromAddress(facility.address)
      || inferCountyFromCity(facility.city)
      || 'UNKNOWN';
    byCounty.set(county, (byCounty.get(county) || 0) + 1);
  });

  return byCounty;
}

function primaryCategoryForFacility(facility) {
  const probabilities = facility.careTypeProbabilities || {};
  const ranked = TARGET_CATEGORIES
    .map((category) => ({
      category,
      probability: Number(probabilities[category] || 0),
    }))
    .sort((a, b) => b.probability - a.probability);

  if (ranked[0] && ranked[0].probability > 0) {
    return ranked[0].category;
  }

  const firstCareType = (facility.careTypes || []).find((careType) => TARGET_CATEGORIES.includes(careType));
  return firstCareType || 'Assisted Living';
}

function main() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));
  const primaryAssignments = facilities.map((facility, index) => ({
    facility,
    backend: backendFacilities[index] || {},
    primaryCategory: primaryCategoryForFacility(facility),
  }));

  const totalFacilities = facilities.length;
  const categoryStats = buildCategoryStats(primaryAssignments);
  const geography = buildGeographicCoverage(facilities);
  const countyCoverage = buildCountyCoverage(backendFacilities);

  const categoryRows = TARGET_CATEGORIES.map((category) => {
    const entry = categoryStats.get(category);
    const count = entry.facilities;
    const pct = percentage(count, totalFacilities);
    return [
      category,
      count,
      `${pct}%`,
      entry.states.size,
      entry.cities.size,
    ];
  });

  const missingCategories = TARGET_CATEGORIES.filter((category) => categoryStats.get(category).facilities === 0);
  const maxCategory = TARGET_CATEGORIES
    .map((category) => ({
      category,
      count: categoryStats.get(category).facilities,
      percentage: percentage(categoryStats.get(category).facilities, totalFacilities),
    }))
    .sort((a, b) => b.percentage - a.percentage)[0];

  const independentGroupCount =
    categoryStats.get('Active Adult 55+').facilities +
    categoryStats.get('Independent Living').facilities +
    categoryStats.get('Assisted Living').facilities;
  const independentGroupPct = percentage(independentGroupCount, totalFacilities);

  const threshold1Pass = maxCategory.percentage <= 40;
  const targetRows = TARGET_CATEGORIES.map((category) => {
    const count = categoryStats.get(category).facilities;
    const actualPct = percentage(count, totalFacilities);
    const targetPct = TARGET_MIX[category];
    return {
      category,
      count,
      actualPct,
      targetPct,
      delta: Number((actualPct - targetPct).toFixed(2)),
    };
  });

  const miamiDadeCount = countyCoverage.get('Miami-Dade County') || 0;
  const browardCount = countyCoverage.get('Broward County') || 0;
  const palmBeachCount = countyCoverage.get('Palm Beach County') || 0;

  const reportLines = [];
  reportLines.push('# Inventory Distribution Report');
  reportLines.push('');
  reportLines.push('## Goal');
  reportLines.push('');
  reportLines.push('Expand support across the full senior living journey categories.');
  reportLines.push('');
  reportLines.push('## Primary Category Distribution');
  reportLines.push('');
  reportLines.push(`- Total facilities analyzed: **${totalFacilities}**`);
  reportLines.push(`- Categories requested: **${TARGET_CATEGORIES.length}**`);
  reportLines.push('- Classification rule: each facility is assigned to exactly one primary category using the highest post-taxonomy category probability.');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Primary Category', 'Facility Count', 'Inventory Share', 'States Covered', 'Cities Covered'],
    categoryRows,
  ));
  reportLines.push('');
  reportLines.push('## Missing Categories');
  reportLines.push('');
  if (missingCategories.length === 0) {
    reportLines.push('- None. All requested categories are represented.');
  } else {
    missingCategories.forEach((category) => reportLines.push(`- ${category}`));
  }
  reportLines.push('');
  reportLines.push('## Geographic Coverage');
  reportLines.push('');
  reportLines.push('### County Distribution');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['County', 'Facility Count', 'Share'],
    topNEntries(countyCoverage, countyCoverage.size).map(([county, count]) => [county, count, `${percentage(count, totalFacilities)}%`]),
  ));
  reportLines.push('');
  reportLines.push('### Required County Coverage');
  reportLines.push('');
  reportLines.push(`- Miami-Dade coverage: **${miamiDadeCount}** facilities (${percentage(miamiDadeCount, totalFacilities)}%)`);
  reportLines.push(`- Broward coverage: **${browardCount}** facilities (${percentage(browardCount, totalFacilities)}%)`);
  reportLines.push(`- Palm Beach coverage: **${palmBeachCount}** facilities (${percentage(palmBeachCount, totalFacilities)}%)`);
  reportLines.push('');
  reportLines.push('### Top States by Facility Count');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['State', 'Facility Count', 'Share'],
    topNEntries(geography.byState, 10).map(([state, count]) => [state, count, `${percentage(count, totalFacilities)}%`]),
  ));
  reportLines.push('');
  reportLines.push('### Top Cities by Facility Count');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['City', 'Facility Count', 'Share'],
    topNEntries(geography.byCity, 15).map(([city, count]) => [city, count, `${percentage(count, totalFacilities)}%`]),
  ));
  reportLines.push('');
  reportLines.push('## Coverage Targets');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Category', 'Actual %', 'Target %', 'Delta'],
    targetRows.map((row) => [row.category, `${row.actualPct}%`, `${row.targetPct}%`, `${row.delta}%`]),
  ));
  reportLines.push('');
  reportLines.push(`- No single care category exceeds 40% of total inventory: **${threshold1Pass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`  - Highest category: ${maxCategory.category} (${maxCategory.percentage}%)`);
  reportLines.push(`- Independent pathway share (Active Adult + Independent + Assisted): **${independentGroupPct}%**`);
  reportLines.push('');
  reportLines.push('## Facility Primary Classification');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Facility', 'County', 'Primary Category'],
    primaryAssignments
      .map(({ facility, backend, primaryCategory }) => {
        const county = normalizeCounty(backend.county) || extractCountyFromAddress(backend.address) || inferCountyFromCity(backend.city) || 'UNKNOWN';
        return [facility.name, county, primaryCategory];
      })
      .sort((a, b) => String(a[0]).localeCompare(String(b[0]))),
  ));
  reportLines.push('');
  reportLines.push('## Notes');
  reportLines.push('');
  reportLines.push('- This report enforces exactly one primary category per facility.');
  reportLines.push('- Category assignment uses the post-taxonomy inference pipeline (`toSearchFacility(..., "post")`).');
  reportLines.push('- County coverage uses `county` when available in source data; if missing, it attempts address-based extraction, else marks `UNKNOWN`.');

  const distributionReportPath = path.join(repoRoot, 'reports', 'inventory_distribution_report.md');
  fs.writeFileSync(distributionReportPath, reportLines.join('\n'));

  const validationLines = [];
  validationLines.push('# Inventory Expansion Validation');
  validationLines.push('');
  validationLines.push(`- TOTAL_FACILITIES: ${totalFacilities}`);
  validationLines.push(`- INDEPENDENT_LIVING_COUNT: ${categoryStats.get('Independent Living').facilities}`);
  validationLines.push(`- ASSISTED_LIVING_COUNT: ${categoryStats.get('Assisted Living').facilities}`);
  validationLines.push(`- CCRC_COUNT: ${categoryStats.get('CCRC').facilities}`);
  validationLines.push(`- SKILLED_NURSING_COUNT: ${categoryStats.get('Skilled Nursing').facilities}`);
  validationLines.push(`- REHAB_COUNT: ${categoryStats.get('Rehabilitation').facilities}`);
  validationLines.push('');
  validationLines.push('## Percentage Distribution Per Category');
  validationLines.push('');
  validationLines.push(markdownTable(
    ['Category', 'Count', 'Percentage'],
    TARGET_CATEGORIES.map((category) => {
      const count = categoryStats.get(category).facilities;
      return [category, count, `${percentage(count, totalFacilities)}%`];
    }),
  ));
  validationLines.push('');
  validationLines.push(`- NO_CATEGORY_ABOVE_40: ${threshold1Pass ? 'PASS' : 'FAIL'}`);
  validationLines.push(`- MIAMI_DADE_COVERAGE: ${miamiDadeCount}`);
  validationLines.push(`- BROWARD_COVERAGE: ${browardCount}`);
  validationLines.push(`- PALM_BEACH_COVERAGE: ${palmBeachCount}`);

  const validationReportPath = path.join(repoRoot, 'reports', 'inventory_expansion_validation.md');
  fs.writeFileSync(validationReportPath, validationLines.join('\n'));

  console.log(`Wrote ${distributionReportPath}`);
  console.log(`Wrote ${validationReportPath}`);
  console.log(`TOTAL_FACILITIES=${totalFacilities}`);
  console.log(`INDEPENDENT_LIVING_COUNT=${categoryStats.get('Independent Living').facilities}`);
  console.log(`ASSISTED_LIVING_COUNT=${categoryStats.get('Assisted Living').facilities}`);
  console.log(`CCRC_COUNT=${categoryStats.get('CCRC').facilities}`);
  console.log(`SKILLED_NURSING_COUNT=${categoryStats.get('Skilled Nursing').facilities}`);
  console.log(`REHAB_COUNT=${categoryStats.get('Rehabilitation').facilities}`);
  TARGET_CATEGORIES.forEach((category) => {
    const safeKey = category.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_|_$/g, '');
    console.log(`${safeKey}_PCT=${percentage(categoryStats.get(category).facilities, totalFacilities)}`);
  });
  console.log(`MAX_CATEGORY=${maxCategory.category}`);
  console.log(`MAX_CATEGORY_PCT=${maxCategory.percentage}`);
  console.log(`NO_CATEGORY_ABOVE_40=${threshold1Pass ? 'PASS' : 'FAIL'}`);
  console.log(`MIAMI_DADE_COVERAGE=${miamiDadeCount}`);
  console.log(`BROWARD_COVERAGE=${browardCount}`);
  console.log(`PALM_BEACH_COVERAGE=${palmBeachCount}`);
}

main();