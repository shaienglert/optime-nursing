const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');

const TARGET_REGION = ['Miami-Dade County', 'Broward County', 'Palm Beach County'];
const CATEGORIES = [
  'Independent Living',
  'Active Adult 55+',
  'Assisted Living',
  'Memory Care',
  'Skilled Nursing',
  'Rehabilitation',
  'Nursing Homes',
];

const SOURCE_CONFIG = [
  { name: 'Google Ads Keyword Planner', env: ['GOOGLE_ADS_DEVELOPER_TOKEN', 'GOOGLE_ADS_CLIENT_ID', 'GOOGLE_ADS_CLIENT_SECRET', 'GOOGLE_ADS_REFRESH_TOKEN'] },
  { name: 'Google Trends', env: [] },
  { name: 'SEMrush', env: ['SEMRUSH_API_KEY'] },
  { name: 'Ahrefs', env: ['AHREFS_API_KEY'] },
  { name: 'Bing Keyword Planner', env: ['BING_ADS_DEVELOPER_TOKEN', 'BING_ADS_CLIENT_ID', 'BING_ADS_CLIENT_SECRET', 'BING_ADS_REFRESH_TOKEN'] },
];

function markdownTable(headers, rows) {
  const escape = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(escape).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(escape).join(' | ')} |`),
  ].join('\n');
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function sourceStatus(source) {
  if (source.env.length === 0) {
    return { available: true, reason: 'No API key required for basic public trend access, but programmatic extraction is not configured in this repository.' };
  }

  const present = source.env.every((key) => Boolean(process.env[key]));
  return {
    available: present,
    reason: present
      ? 'Credentials detected in environment.'
      : `Missing required credentials: ${source.env.filter((key) => !process.env[key]).join(', ')}`,
  };
}

function buildRows() {
  return CATEGORIES.map((category) => ({
    category,
    monthlySearches: 'N/A',
    yoyGrowth: 'N/A',
    competition: 'N/A',
    cpc: 'N/A',
    trend12m: 'N/A',
    topQueries: 'N/A',
    geographicDistribution: 'N/A',
    note: 'Data unavailable: external paid keyword APIs are not configured in current runtime.',
  }));
}

function main() {
  const sourceRows = SOURCE_CONFIG.map((source) => ({
    source: source.name,
    ...sourceStatus(source),
  }));

  const availableSources = sourceRows.filter((row) => row.available).map((row) => row.source);
  const unavailableSources = sourceRows.filter((row) => !row.available).map((row) => row.source);

  const categoryRows = buildRows();

  const reportLines = [];
  reportLines.push('# Senior Living Search Demand Audit');
  reportLines.push('');
  reportLines.push(`Generated At: ${new Date().toISOString()}`);
  reportLines.push(`Target Region: ${TARGET_REGION.join(', ')}`);
  reportLines.push(`Target Categories: ${CATEGORIES.join(', ')}`);
  reportLines.push('');
  reportLines.push('## Source Availability');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Source', 'Available', 'Status'],
    sourceRows.map((row) => [row.source, row.available ? 'YES' : 'NO', row.reason])
  ));
  reportLines.push('');
  reportLines.push('## Data Quality Notice');
  reportLines.push('');
  reportLines.push('- This audit requires authenticated access to paid keyword platforms to provide monthly volume, CPC, and competition values.');
  reportLines.push(`- Available sources in current runtime: ${availableSources.length > 0 ? availableSources.join(', ') : 'None'}.`);
  reportLines.push(`- Unavailable sources in current runtime: ${unavailableSources.length > 0 ? unavailableSources.join(', ') : 'None'}.`);
  reportLines.push('');
  reportLines.push('## Category Demand Output');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Category', 'Monthly Searches', 'YoY Growth', 'Competition', 'CPC'],
    categoryRows.map((row) => [row.category, row.monthlySearches, row.yoyGrowth, row.competition, row.cpc])
  ));
  reportLines.push('');
  reportLines.push('## Extended Fields Requested');
  reportLines.push('');
  reportLines.push(markdownTable(
    ['Category', '12 Month Trend', 'Top Search Queries', 'Geographic Distribution', 'Note'],
    categoryRows.map((row) => [row.category, row.trend12m, row.topQueries, row.geographicDistribution, row.note])
  ));

  const mdPath = path.join(repoRoot, 'reports', 'senior_living_search_demand_report.md');
  fs.writeFileSync(mdPath, reportLines.join('\n'));

  const csvHeaders = [
    'category',
    'monthly_searches',
    'yoy_growth',
    'competition',
    'cpc',
    'trend_12m',
    'top_search_queries',
    'geographic_distribution',
    'note',
  ];

  const csvRows = categoryRows.map((row) => [
    row.category,
    row.monthlySearches,
    row.yoyGrowth,
    row.competition,
    row.cpc,
    row.trend12m,
    row.topQueries,
    row.geographicDistribution,
    row.note,
  ]);

  const csvPath = path.join(repoRoot, 'reports', 'senior_living_search_demand_report.csv');
  const csv = [csvHeaders, ...csvRows].map((line) => line.map(csvEscape).join(',')).join('\n');
  fs.writeFileSync(csvPath, csv);

  console.log(`Wrote ${mdPath}`);
  console.log(`Wrote ${csvPath}`);
  console.log(markdownTable(
    ['Category', 'Monthly Searches', 'YoY Growth', 'Competition', 'CPC'],
    categoryRows.map((row) => [row.category, row.monthlySearches, row.yoyGrowth, row.competition, row.cpc])
  ));
}

main();
