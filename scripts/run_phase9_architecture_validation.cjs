const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');

const REQUIRED_REPORTS = [
  'reports/system_architecture_review.md',
  'reports/gap_analysis.md',
  'reports/database_review.md',
  'reports/product_roadmap.md',
  'reports/risk_register.md',
  'reports/provider_portal_review.md',
  'reports/family_journey_review.md',
];

function read(relativePath) {
  const absolute = path.join(repoRoot, relativePath);
  return fs.readFileSync(absolute, 'utf8');
}

function score(content, checks, max) {
  let passed = 0;
  checks.forEach((check) => {
    if (check(content)) passed += 1;
  });
  return Math.round((passed / checks.length) * max);
}

function extractTop25(gapContent) {
  const lines = gapContent.split('\n');
  const start = lines.findIndex((line) => line.trim() === '## Top 25 Priority Improvements');
  if (start === -1) return [];

  const improvements = [];
  for (let i = start + 1; i < lines.length; i += 1) {
    const line = lines[i].trim();
    const match = line.match(/^(\d+)\.\s+(.+)$/);
    if (!match) {
      if (improvements.length > 0 && line.startsWith('## ')) break;
      continue;
    }
    improvements.push(match[2]);
    if (improvements.length === 25) break;
  }
  return improvements;
}

function main() {
  const missing = REQUIRED_REPORTS.filter((report) => !fs.existsSync(path.join(repoRoot, report)));

  if (missing.length > 0) {
    console.log('ARCHITECTURE_VALIDATION=FAIL');
    missing.forEach((item) => console.log(`MISSING_REPORT=${item}`));
    process.exit(1);
  }

  const architecture = read('reports/system_architecture_review.md');
  const gap = read('reports/gap_analysis.md');
  const database = read('reports/database_review.md');
  const roadmap = read('reports/product_roadmap.md');
  const risk = read('reports/risk_register.md');
  const provider = read('reports/provider_portal_review.md');
  const family = read('reports/family_journey_review.md');

  const architectureScore = score(
    `${architecture}\n${gap}\n${database}`,
    [
      (text) => text.includes('Matching Engine'),
      (text) => text.includes('Questionnaire'),
      (text) => text.includes('Clinical Reasoning'),
      (text) => text.includes('Narrative Engine'),
      (text) => text.includes('Facility Memory Engine'),
      (text) => text.includes('Provider Portal'),
      (text) => text.includes('Verification Engine'),
      (text) => text.includes('OSINT'),
      (text) => text.includes('Knowledge Graph'),
      (text) => text.includes('Evidence Engine'),
      (text) => text.includes('Performance and Scalability Risks'),
      (text) => text.includes('Security Risks'),
      (text) => text.includes('Legal/Privacy Risks'),
    ],
    100,
  );

  const productReadiness = score(
    `${roadmap}\n${provider}\n${family}`,
    [
      (text) => text.includes('Revenue Opportunities'),
      (text) => text.includes('Provider dashboard'),
      (text) => text.includes('lead'),
      (text) => text.includes('CRM'),
      (text) => text.includes('Family Value Assessment'),
      (text) => text.includes('High Priority'),
      (text) => text.includes('Medium Priority'),
      (text) => text.includes('Low Priority'),
      (text) => text.includes('Business Value'),
      (text) => text.includes('Competitive Advantage'),
    ],
    100,
  );

  const clinicalReadiness = score(
    `${architecture}\n${gap}\n${risk}`,
    [
      (text) => text.includes('Clinical Review'),
      (text) => text.includes('evidence'),
      (text) => text.includes('unsupported'),
      (text) => text.includes('contraindication'),
      (text) => text.includes('narrative'),
      (text) => text.includes('verification'),
      (text) => text.includes('family-language'),
      (text) => text.includes('clinical'),
    ],
    100,
  );

  const dataQuality = score(
    `${database}\n${architecture}\n${gap}`,
    [
      (text) => text.includes('Missing Indexes'),
      (text) => text.includes('Normalization Issues'),
      (text) => text.includes('Relationship and Integrity Gaps'),
      (text) => text.includes('Data model richness'),
      (text) => text.includes('Source'),
      (text) => text.includes('Trust Level'),
      (text) => text.includes('Refresh Frequency'),
      (text) => text.includes('Expiration/Decay Policy'),
    ],
    100,
  );

  const top25 = extractTop25(gap);

  const lines = [];
  lines.push('# Phase 9 Architecture Validation Summary');
  lines.push('');
  lines.push(`ARCHITECTURE_SCORE=${architectureScore}`);
  lines.push(`PRODUCT_READINESS=${productReadiness}`);
  lines.push(`CLINICAL_READINESS=${clinicalReadiness}`);
  lines.push(`DATA_QUALITY=${dataQuality}`);
  lines.push('');
  lines.push('## Top 25 Priority Improvements');
  lines.push('');
  top25.forEach((item, idx) => lines.push(`${idx + 1}. ${item}`));

  const outPath = path.join(repoRoot, 'reports', 'phase9_architecture_validation.md');
  fs.writeFileSync(outPath, lines.join('\n'));

  console.log(`Wrote ${outPath}`);
  console.log(`ARCHITECTURE_SCORE=${architectureScore}`);
  console.log(`PRODUCT_READINESS=${productReadiness}`);
  console.log(`CLINICAL_READINESS=${clinicalReadiness}`);
  console.log(`DATA_QUALITY=${dataQuality}`);
  console.log(`TOP25_COUNT=${top25.length}`);
}

main();
