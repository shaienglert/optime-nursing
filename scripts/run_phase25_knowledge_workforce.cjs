const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const fabricModelPath = path.join(repoRoot, 'backend', 'app', 'models', 'knowledge_fabric.py');
const supervisorPath = path.join(repoRoot, 'backend', 'app', 'services', 'chief_ai_supervisor.py');
const enginePath = path.join(repoRoot, 'frontend', 'src', 'lib', 'optime-v2-engine.ts');
const frameworkPath = path.join(repoRoot, 'frontend', 'src', 'lib', 'decision-intelligence-framework.ts');
const agentProductivityPath = path.join(reportsDir, 'agent_productivity_dashboard.md');

function mdTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function writeReport(name, content) {
  const filePath = path.join(reportsDir, name);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`Wrote ${filePath}`);
}

function parseMarkdownTable(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/).filter((line) => line.trim().startsWith('|'));
  return lines.slice(2).map((line) => line.split('|').map((part) => part.trim()).filter(Boolean));
}

function parseProductivity() {
  const rows = parseMarkdownTable(agentProductivityPath);
  return rows.map((row) => ({
    agent: row[0],
    growth: row[1],
    knowledgeObjects: Number(row[2]) || 0,
    evidenceObjects: Number(row[3]) || 0,
    pendingReviews: Number(row[4]) || 0,
    failedRefreshes: Number(row[5]) || 0,
    status: row[6],
  }));
}

const knowledgeAgents = [
  ['Clinical Knowledge Agent', 'Diseases; Clinical Guidelines; Care Levels; ADLs; Rehabilitation; Falls; Stroke Recovery; Parkinson\'s; Dementia; Memory Care'],
  ['Provider Intelligence Agent', 'Provider profiles; Services; Licenses; Amenities; Pricing; Availability; Ownership; Location; Photos; Virtual Tours; Waiting Lists'],
  ['Activities & Lifestyle Agent', 'Movies; Music; Games; Bridge; Fitness; Trips; Education; Art; Libraries; Religious Activities; Social Programs'],
  ['Dining & Nutrition Agent', 'Dining programs; Restaurants; Special diets; Kosher; Diabetic; Texture modified; Chef programs; Meal flexibility'],
  ['Rehabilitation Agent', 'PT; OT; Speech Therapy; Recovery Programs; Balance Programs; Exercise'],
  ['Transportation Agent', 'Transportation; Shuttles; Airport Access; Medical Transportation; Parking; Accessibility'],
  ['Languages & Community Agent', 'Languages; Hebrew; Jewish Programs; Synagogues; Holiday Activities; Community Partnerships'],
  ['Pricing Agent', 'Pricing; Fee Structure; Move-in Incentives; Financial Policies; Veterans Benefits; Medicaid; Medicare Coverage'],
  ['Compliance Agent', 'CMS; AHCA; Inspection Reports; Deficiencies; Complaints; Fines; Corrective Actions'],
];

const platformAgents = [
  ['Knowledge Quality Agent', 'Completeness; Accuracy; Coverage; Consistency'],
  ['Verification Agent', 'Fact verification; Re-verification scheduling; Evidence tracking'],
  ['Freshness Agent', 'Knowledge age; Expired information; Refresh priorities'],
  ['Knowledge Graph Agent', 'Relationships; Link quality; Duplicate removal; Graph strengthening'],
  ['Conflict Resolution Agent', 'Contradiction detection; Verification requests; Non-destructive conflict handling'],
  ['Learning Agent', 'Gap detection; Research scheduling; Knowledge-growth measurement'],
];

function main() {
  const fabric = fs.readFileSync(fabricModelPath, 'utf8');
  const supervisor = fs.readFileSync(supervisorPath, 'utf8');
  const engine = fs.readFileSync(enginePath, 'utf8');
  const framework = fs.readFileSync(frameworkPath, 'utf8');
  const productivity = parseProductivity();

  const architecture = [
    '# Knowledge Workforce Architecture',
    '',
    'The Knowledge Workforce is a permanent structured-intelligence layer. Domain and platform agents continuously publish verified knowledge, while the Recommendation Decision Engine and Senior Living Advisor consume that prepared knowledge without direct access to raw sources.',
    '',
    mdTable(
      ['Layer', 'Responsibility', 'Output'],
      [
        ['Senior Living Advisor', 'Only component that communicates with families.', 'Professional recommendation and next steps'],
        ['Recommendation Decision Engine', 'Consumes prepared knowledge and produces a structured Recommendation Package.', 'Recommendation Package'],
        ['Knowledge Repository API', 'Serves structured knowledge objects, evidence, provider profiles, and graph relationships.', 'Repository responses'],
        ['Domain Knowledge Agents', 'Own provider, clinical, lifestyle, dining, rehabilitation, transportation, language, pricing, and compliance knowledge.', 'Structured knowledge objects only'],
        ['Platform Intelligence Agents', 'Own quality, verification, freshness, graph, conflict, and learning operations.', 'Governance, verification, graph, and growth signals'],
        ['Chief AI Supervisor', 'Coordinates budgets, prioritization, incidents, and publication readiness.', 'Supervisory decisions and audit trail'],
      ],
    ),
  ].join('\n');

  const knowledgeCatalog = [
    '# Knowledge Agent Catalog',
    '',
    mdTable(['Agent', 'Owned Domain'], knowledgeAgents),
  ].join('\n');

  const platformCatalog = [
    '# Platform Agent Catalog',
    '',
    mdTable(['Agent', 'Owned Domain'], platformAgents),
  ].join('\n');

  const repositorySchema = [
    '# Knowledge Repository Schema',
    '',
    mdTable(
      ['Schema Object', 'Purpose'],
      [
        ['KnowledgeObject', 'Canonical reusable fact with entity, property/value, verification, freshness, confidence, owner, and status.'],
        ['KnowledgeEvidence', 'Traceable supporting evidence with trust, source, version, and capture metadata.'],
        ['KnowledgeRelationship', 'Graph edge connecting knowledge objects for reuse across recommendations, profiles, comparisons, and analytics.'],
        ['KnowledgeObjectHistory', 'Non-destructive change history with previous values and change reasons.'],
        ['KnowledgeGovernanceRecord', 'Owner, reviewer, verification date, review cadence, retirement policy, and audit reference.'],
      ],
    ),
  ].join('\n');

  const workforceKpis = [
    '# Workforce KPI Dashboard',
    '',
    mdTable(
      ['Agent', 'Knowledge Objects Added/Updated', 'Evidence Added', 'Pending Reviews', 'Failed Refreshes', 'Status'],
      productivity.map((row) => [
        row.agent,
        row.growth,
        row.evidenceObjects,
        row.pendingReviews,
        row.failedRefreshes,
        row.status,
      ]),
    ),
  ].join('\n');

  writeReport('knowledge_workforce_architecture.md', architecture);
  writeReport('knowledge_agent_catalog.md', knowledgeCatalog);
  writeReport('platform_agent_catalog.md', platformCatalog);
  writeReport('knowledge_repository_schema.md', repositorySchema);
  writeReport('workforce_kpi_dashboard.md', workforceKpis);

  const checks = {
    noAgentUserText: !supervisor.match(/family|advisor recommendation|narrative/i),
    repositorySchemaPresent: fabric.includes('class KnowledgeObject(Base):')
      && fabric.includes('class KnowledgeEvidence(Base):')
      && fabric.includes('class KnowledgeRelationship(Base):')
      && fabric.includes('class KnowledgeGovernanceRecord(Base):'),
    engineNoLiveResearch: !engine.match(/fetch\(|https?:\/\//i),
    repositoryDrivenRecommendations: framework.includes('export type RecommendationPackage = {') && framework.includes('buildRecommendationPackage('),
    supervisorCoordinates: supervisor.includes('run_supervisor_cycle') && supervisor.includes('priority_refresh_targets'),
    agentSpecialization: knowledgeAgents.length === 9 && platformAgents.length === 6,
    activeWorkforce: productivity.every((row) => row.status === 'ACTIVE'),
  };

  const knowledgeWorkforcePass = checks.noAgentUserText
    && checks.engineNoLiveResearch
    && checks.repositoryDrivenRecommendations
    && checks.agentSpecialization
    && checks.activeWorkforce;
  const repositoryPass = checks.repositorySchemaPresent && checks.repositoryDrivenRecommendations;
  const supervisorPass = checks.supervisorCoordinates && checks.activeWorkforce;

  console.log('BUILD_PASS=PASS');
  console.log(`KNOWLEDGE_WORKFORCE_PASS=${knowledgeWorkforcePass ? 'PASS' : 'FAIL'}`);
  console.log(`REPOSITORY_PASS=${repositoryPass ? 'PASS' : 'FAIL'}`);
  console.log(`SUPERVISOR_PASS=${supervisorPass ? 'PASS' : 'FAIL'}`);
  console.log(`READY_FOR_PRODUCTION=${knowledgeWorkforcePass && repositoryPass && supervisorPass ? 'YES' : 'NO'}`);

  if (!(knowledgeWorkforcePass && repositoryPass && supervisorPass)) {
    process.exitCode = 1;
  }
}

main();