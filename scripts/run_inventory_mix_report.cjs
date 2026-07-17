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

function buildCategoryStats(facilities) {
  const stats = new Map();

  TARGET_CATEGORIES.forEach((category) => {
    stats.set(category, {
      facilities: [],
      states: new Set(),
      cities: new Set(),
    });
  });

  facilities.forEach((facility) => {
    TARGET_CATEGORIES.forEach((category) => {
      if (!facility.careTypes.includes(category)) return;

      const entry = stats.get(category);
      entry.facilities.push(facility);
      if (facility.state) entry.states.add(String(facility.state));
      if (facility.city) entry.cities.add(String(facility.city));
    });
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

function main() {
  const backendFacilities = simulationHelpers.loadBackendFacilities();
  const facilities = backendFacilities.map((facility) => simulationHelpers.toSearchFacility(facility, 'post'));

  const totalFacilities = facilities.length;
  const categoryStats = buildCategoryStats(facilities);
  const geography = buildGeographicCoverage(facilities);

  const categoryRows = TARGET_CATEGORIES.map((category) => {
    const entry = categoryStats.get(category);
    const count = entry.facilities.length;
    const pct = percentage(count, totalFacilities);
    return [
      category,
      count,
      `${pct}%`,
      entry.states.size,
      entry.cities.size,
    ];
  });

  const missingCategories = TARGET_CATEGORIES.filter((category) => categoryStats.get(category).facilities.length === 0);
  const maxCategory = TARGET_CATEGORIES
    .map((category) => ({
      category,
      count: categoryStats.get(category).facilities.length,
      percentage: percentage(categoryStats.get(category).facilities.length, totalFacilities),
    }))
    .sort((a, b) => b.percentage - a.percentage)[0];

  const independentGroupCount =
    categoryStats.get('Active Adult 55+').facilities.length +
    categoryStats.get('Independent Living').facilities.length +
    categoryStats.get('Assisted Living').facilities.length;
  const independentGroupPct = percentage(independentGroupCount, totalFacilities);

  const threshold1Pass = maxCategory.percentage <= 40;
  const threshold2Pass = independentGroupPct >= 50;

  const reportLines = [];
  reportLines.push('# Inventory Mix Report');
  reportLines.push('');
  reportLines.push('## Goal');
  reportLines.push('');
  reportLines.push('Expand support across the full senior living journey categories.');
  reportLines.push('');
  reportLines.push('## Inventory Summary');
  reportLines.push('');
  reportLines.push(`- Total facilities analyzed: **${totalFacilities}**`);
  reportLines.push(`- Categories requested: **${TARGET_CATEGORIES.length}**`);
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Category', 'Facility Count', 'Inventory Share', 'States Covered', 'Cities Covered'],
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
  reportLines.push('## Success Criteria Validation');
  reportLines.push('');
  reportLines.push(`- No single care category exceeds 40% of total inventory: **${threshold1Pass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`  - Highest category: ${maxCategory.category} (${maxCategory.percentage}%)`);
  reportLines.push(`- Independent Living + Assisted Living + Active Adult >= 50%: **${threshold2Pass ? 'PASS' : 'FAIL'}**`);
  reportLines.push(`  - Combined share: ${independentGroupPct}%`);
  reportLines.push('');
  reportLines.push('## Notes');
  reportLines.push('');
  reportLines.push('- Facilities may belong to multiple categories; percentages are per-category coverage over total facilities and are not mutually exclusive.');
  reportLines.push('- Category assignment uses the post-taxonomy inference pipeline (`toSearchFacility(..., "post")`).');

  const reportPath = path.join(repoRoot, 'reports', 'inventory_mix_report.md');
  fs.writeFileSync(reportPath, reportLines.join('\n'));

  console.log(`Wrote ${reportPath}`);
  console.log(`TOTAL_FACILITIES=${totalFacilities}`);
  console.log(`MAX_CATEGORY=${maxCategory.category}`);
  console.log(`MAX_CATEGORY_PCT=${maxCategory.percentage}`);
  console.log(`INDEPENDENT_GROUP_PCT=${independentGroupPct}`);
  console.log(`CRITERIA_40=${threshold1Pass ? 'PASS' : 'FAIL'}`);
  console.log(`CRITERIA_50=${threshold2Pass ? 'PASS' : 'FAIL'}`);
}

main();