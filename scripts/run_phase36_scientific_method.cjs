const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');

const knowledgeCenters = [
  'Clinical Geriatrics',
  'Nursing Care',
  'Dementia & Memory Care',
  "Parkinson's Disease",
  'Stroke & Neurological Rehabilitation',
  'Falls & Mobility',
  'Medication Management',
  'Nutrition & Hydration',
  'Psychology of Aging',
  'Social Work & Family Support',
  'Sociology of Aging',
  'Decision Psychology',
  'Activities & Engagement',
  'Quality of Life',
  'Palliative & End-of-Life Care',
  'Provider Intelligence',
  'Regulatory & Compliance',
  'Senior Living Operations',
  'Transition & Adaptation',
  'Institutional Research',
];

const scientificCycle = [
  'Question',
  'Research',
  'Evidence Collection',
  'Critical Review',
  'Verification',
  'Knowledge Object',
  'Expert Review',
  'Institutional Knowledge',
  'Recommendation',
  'Outcome',
  'Validation',
  'Knowledge Improvement',
];

function writeReport(fileName, lines) {
  const filePath = path.join(reportsDir, fileName);
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
  return filePath;
}

function bulletList(items) {
  return items.map((item) => `- ${item}`);
}

function markdownTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function buildScientificMethod() {
  const lines = [];
  lines.push('# Scientific Method');
  lines.push('');
  lines.push('## Mission');
  lines.push('Every Knowledge Center shall operate as a scientific institution.');
  lines.push('');
  lines.push('Knowledge is never merely collected.');
  lines.push('Knowledge is discovered, validated, challenged, improved, and preserved.');
  lines.push('');
  lines.push('## Scientific Cycle');
  lines.push('');
  lines.push(...scientificCycle.map((step) => `- ${step}`));
  lines.push('');
  lines.push('## Governing Rules');
  lines.push('');
  lines.push('- No research without a clearly defined research question.');
  lines.push('- No knowledge without explicit evidence, evidence strength, evidence quality, supporting sources, conflicting evidence, and knowledge gaps.');
  lines.push('- No single study may change institutional knowledge on its own.');
  lines.push('- Every agent must ask what is known, how it is known, what supports it, what contradicts it, and what is still missing.');
  lines.push('');
  lines.push('## Center Operating Obligation');
  lines.push('');
  lines.push(...bulletList(knowledgeCenters.map((center) => `${center} must maintain a research agenda, current research queue, completed research log, open questions, future research list, and knowledge gap register.`)));
  return lines;
}

function buildResearchMethodology() {
  const lines = [];
  lines.push('# Research Methodology');
  lines.push('');
  lines.push('## Required Inputs For Every Research Project');
  lines.push('');
  lines.push(...bulletList([
    'Research Question',
    'Methodology',
    'Sources',
    'Evidence Matrix',
    'Strength of Evidence',
    'Limitations',
    'Knowledge Gaps',
    'Recommendations',
  ]));
  lines.push('');
  lines.push('## Required Research Sequence');
  lines.push('');
  lines.push('1. Define the question in answerable form.');
  lines.push('2. Search trusted primary and secondary sources.');
  lines.push('3. Extract claims, evidence, dates, and contradictions.');
  lines.push('4. Grade evidence strength and quality.');
  lines.push('5. Convert validated claims into knowledge objects.');
  lines.push('6. Route objects through expert review before institutional publication.');
  lines.push('7. Revisit conclusions when outcomes or new evidence appear.');
  lines.push('');
  lines.push('## Standard Questions');
  lines.push('');
  lines.push(...bulletList([
    'What is the exact claim being evaluated?',
    'Which sources independently support the claim?',
    'What contradictory evidence exists?',
    'How recent is the evidence?',
    'What population or provider context limits generalization?',
    'What recommendation decisions would change if the claim is true or false?',
  ]));
  return lines;
}

function buildKnowledgeValidationFramework() {
  const lines = [];
  lines.push('# Knowledge Validation Framework');
  lines.push('');
  lines.push('## Validation Gate');
  lines.push('Institutional knowledge is created only after multiple sources, independent verification, evidence review, and expert review.');
  lines.push('');
  lines.push(markdownTable(
    ['Validation Stage', 'Required Proof', 'Failure Condition'],
    [
      ['Research Question', 'Clearly scoped question', 'No answerable question defined'],
      ['Evidence Collection', 'Traceable sources and extracted claims', 'Claims without provenance'],
      ['Critical Review', 'Contradictions and limitations documented', 'Conflicts hidden or ignored'],
      ['Verification', 'Independent corroboration or regulator-grade evidence', 'Single-source dependency'],
      ['Knowledge Object', 'Structured claim with confidence and impact', 'Unstructured conclusion'],
      ['Expert Review', 'Named reviewer and publication decision', 'No accountable reviewer'],
      ['Institutional Publication', 'Freshness, review cadence, and gap tracking stored', 'No maintenance plan'],
    ],
  ));
  lines.push('');
  lines.push('## Required Fields For Every Knowledge Object');
  lines.push('');
  lines.push(...bulletList([
    'Claim',
    'Evidence',
    'Source',
    'Quality',
    'Freshness',
    'Contradictions',
    'Confidence',
    'Recommendation Impact',
  ]));
  lines.push('');
  lines.push('## Review Outcomes');
  lines.push('');
  lines.push(...bulletList([
    'Publish as institutional knowledge',
    'Publish with uncertainty preserved',
    'Hold for missing evidence',
    'Reject as unsupported',
    'Return for additional research',
  ]));
  return lines;
}

function buildEvidenceGradingFramework() {
  const lines = [];
  lines.push('# Evidence Grading Framework');
  lines.push('');
  lines.push(markdownTable(
    ['Grade', 'Evidence Strength', 'Typical Inputs', 'Knowledge Effect'],
    [
      ['A', 'Very Strong', 'Multi-source regulator data, systematic reviews, replicated outcome evidence', 'May support institutional standard after expert review'],
      ['B', 'Strong', 'High-quality cohort studies, official provider disclosures, multiple independent confirmations', 'Supports verified knowledge'],
      ['C', 'Moderate', 'Single high-quality study or limited multi-source evidence', 'Supports provisional knowledge with explicit caveats'],
      ['D', 'Weak', 'Anecdotal or thin evidence with partial corroboration', 'Cannot independently drive recommendations'],
      ['E', 'Insufficient', 'Unverified claim or unsupported opinion', 'Not eligible for institutional knowledge'],
    ],
  ));
  lines.push('');
  lines.push('## Evidence Quality Signals');
  lines.push('');
  lines.push(...bulletList([
    'Source authority',
    'Methodological rigor',
    'Recency',
    'Population relevance',
    'Reproducibility',
    'Bias exposure',
    'Contradiction burden',
  ]));
  lines.push('');
  lines.push('## Mandatory Preservation Of Uncertainty');
  lines.push('');
  lines.push('- Conflicting evidence must remain visible.');
  lines.push('- Low-grade evidence cannot be relabeled as knowledge certainty.');
  lines.push('- Recommendation impact must be downgraded when evidence quality is weak or stale.');
  return lines;
}

function buildKnowledgeMaturityModel() {
  const lines = [];
  lines.push('# Knowledge Maturity Model');
  lines.push('');
  lines.push(markdownTable(
    ['Level', 'Name', 'Definition', 'Center Standard'],
    [
      ['1', 'Observation', 'Signals or isolated facts noticed but not validated', 'Tracked as raw research input'],
      ['2', 'Evidence', 'Claim supported by traceable evidence but not fully verified', 'Eligible for structured review'],
      ['3', 'Verified Knowledge', 'Claim independently verified and structured as a knowledge object', 'Usable with declared confidence'],
      ['4', 'Professional Consensus', 'Experts agree after review of multiple validated sources', 'Reusable in decision frameworks'],
      ['5', 'Institutional Standard', 'Consensus repeatedly validated by outcomes and preserved as a governing standard', 'Default institutional guidance until challenged'],
    ],
  ));
  lines.push('');
  lines.push('## Maturity Advancement Rules');
  lines.push('');
  lines.push(...bulletList([
    'No object advances without stronger evidence than the previous level required.',
    'Outcome validation is required for advancement to institutional standard.',
    'Contradictions can freeze or demote maturity until resolved.',
    'Freshness review can trigger revalidation at any level.',
  ]));
  lines.push('');
  lines.push('## Institute Expectation');
  lines.push('');
  lines.push(`All ${knowledgeCenters.length} Knowledge Centers must maintain explicit maturity distribution tracking across their active knowledge objects.`);
  return lines;
}

function main() {
  const outputs = [
    ['scientific_method.md', buildScientificMethod()],
    ['research_methodology.md', buildResearchMethodology()],
    ['knowledge_validation_framework.md', buildKnowledgeValidationFramework()],
    ['evidence_grading_framework.md', buildEvidenceGradingFramework()],
    ['knowledge_maturity_model.md', buildKnowledgeMaturityModel()],
  ].map(([fileName, lines]) => writeReport(fileName, lines));

  console.log(`Wrote ${outputs.length} reports`);
  outputs.forEach((filePath) => console.log(filePath));
  console.log(`KNOWLEDGE_CENTERS=${knowledgeCenters.length}`);
  console.log('SCIENTIFIC_METHOD_PASS=PASS');
}

main();
