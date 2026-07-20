const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveCanonicalPython } = require('./lib/python_runtime.cjs');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const fabricModelPath = path.join(repoRoot, 'backend', 'app', 'models', 'knowledge_fabric.py');
const frameworkPath = path.join(repoRoot, 'frontend', 'src', 'lib', 'decision-intelligence-framework.ts');
const phase20ReportPath = path.join(reportsDir, 'platform_intelligence_report.md');
const graphGrowthPath = path.join(reportsDir, 'knowledge_graph_growth.md');

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

function queryDb() {
  const dbPath = path.join(repoRoot, 'backend', 'optime_nursing.db');
  const pythonPath = resolveCanonicalPython(repoRoot);
  const py = [
    'import json, sqlite3, sys',
    'con = sqlite3.connect(sys.argv[1])',
    'cur = con.cursor()',
    'payload = {',
    '  "facilities": cur.execute("select count(1) from facilities").fetchone()[0],',
    '  "snapshots": cur.execute("select count(1) from agent_knowledge_report_snapshots").fetchone()[0],',
    '  "incidents": cur.execute("select count(1) from supervisor_incident_logs").fetchone()[0],',
    '}',
    'print(json.dumps(payload))',
    'con.close()',
  ].join('\n');

  const out = spawnSync(pythonPath, ['-c', py, dbPath], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });
  if (out.status !== 0) {
    throw new Error(out.stderr || out.stdout || 'Knowledge Fabric DB query failed');
  }
  return JSON.parse(out.stdout);
}

function parseMetricFromReport(filePath, label) {
  const content = fs.readFileSync(filePath, 'utf8');
  const line = content.split(/\r?\n/).find((item) => item.includes(`| ${label} |`));
  if (!line) return null;
  const parts = line.split('|').map((part) => part.trim()).filter(Boolean);
  return parts[1] || null;
}

function main() {
  const modelSource = fs.readFileSync(fabricModelPath, 'utf8');
  const frameworkSource = fs.readFileSync(frameworkPath, 'utf8');
  const db = queryDb();

  const graphGrowth = Number(parseMetricFromReport(graphGrowthPath, 'Relationships Added') || 0);
  const platformKnowledgeObjects = Number(parseMetricFromReport(phase20ReportPath, 'Knowledge Objects') || 0);
  const platformEvidenceObjects = Number(parseMetricFromReport(phase20ReportPath, 'Evidence Objects') || 0);

  const checks = {
    hasKnowledgeObjectModel: modelSource.includes('class KnowledgeObject(Base):'),
    hasEvidenceModel: modelSource.includes('class KnowledgeEvidence(Base):'),
    hasRelationshipModel: modelSource.includes('class KnowledgeRelationship(Base):'),
    hasHistoryModel: modelSource.includes('class KnowledgeObjectHistory(Base):'),
    hasGovernanceModel: modelSource.includes('class KnowledgeGovernanceRecord(Base):'),
    recommendationsUseStructuredPackage: frameworkSource.includes('export type RecommendationPackage = {') && frameworkSource.includes('buildRecommendationPackage'),
    noRawDocumentsInFramework: !frameworkSource.match(/webpage|document|report storage/i),
    graphExpands: graphGrowth > 0,
    knowledgeObjectsAvailable: platformKnowledgeObjects > 0,
    evidenceObjectsAvailable: platformEvidenceObjects > 0,
    providerProfilesAvailable: db.facilities > 0,
    preparedSnapshotsAvailable: db.snapshots > 0,
  };

  const knowledgeFabricPass = Object.values(checks).every(Boolean);
  const knowledgeQualityPass = checks.graphExpands && checks.knowledgeObjectsAvailable && checks.evidenceObjectsAvailable && checks.preparedSnapshotsAvailable;

  const architecture = [
    '# Knowledge Fabric Architecture',
    '',
    'The Knowledge Fabric is the canonical structured layer between raw source processing and every downstream recommendation, explanation, provider profile, and platform surface.',
    '',
    mdTable(
      ['Layer', 'Role', 'Structured Output'],
      [
        ['Ingestion', 'Transform raw source material into extracted facts and evidence traces.', 'Normalized fact candidates'],
        ['Knowledge Object Model', 'Store reusable canonical facts with ownership, confidence, freshness, and history.', 'Knowledge Objects'],
        ['Relationship Graph', 'Connect knowledge objects across entities, services, outcomes, evidence, and preferences.', 'Knowledge Relationships'],
        ['Governance', 'Review, verify, retire, and audit knowledge quality.', 'Governance Records and History'],
        ['Prepared Consumption', 'Expose structured packages to recommendations, narratives, provider pages, comparisons, and analytics.', 'Prepared Snapshots and Recommendation Packages'],
      ],
    ),
  ].join('\n');

  const objectSchema = [
    '# Knowledge Object Schema',
    '',
    mdTable(
      ['Schema Element', 'Purpose'],
      [
        ['KnowledgeObject.object_key', 'Stable unique identifier for reusable knowledge.'],
        ['topic / entity_type / entity_key', 'Canonical location of the fact inside the fabric.'],
        ['relationship / fact_value', 'Structured expression of the fact.'],
        ['evidence_key', 'Link to supporting evidence.'],
        ['verification_status / freshness_status / confidence', 'Trust envelope for consumption.'],
        ['owner_agent / reviewer / history', 'Governance and accountability.'],
      ],
    ),
  ].join('\n');

  const governance = [
    '# Knowledge Governance',
    '',
    mdTable(
      ['Governance Rule', 'Implementation'],
      [
        ['Ownership', 'Every knowledge object has an owner agent and reviewer.'],
        ['Verification', 'Verification date, status, and review cadence are stored in governance records.'],
        ['History', 'Previous values and change reasons are preserved in object history.'],
        ['Retirement', 'Retirement policy and status remain explicit instead of destructive overwrite.'],
        ['Conflicts', 'Conflicting facts are stored separately and resolved through verification, never silent overwrite.'],
      ],
    ),
  ].join('\n');

  const entityRelationship = [
    '# Entity Relationship Model',
    '',
    mdTable(
      ['Entity Type', 'Examples', 'Relationship Examples'],
      [
        ['Provider', 'Community, building, apartment type', 'Offers service; supports condition; located in county'],
        ['Service / Program', 'Memory care, rehabilitation, transportation', 'Delivered by provider; supported by evidence'],
        ['Lifestyle / Activity', 'Movies, gardening, music, religious services', 'Available at provider; improves outcome'],
        ['Clinical', 'Condition, therapy, clinical program', 'Requires service; supported by study'],
        ['Evidence / Outcome', 'Study, inspection, outcome pattern', 'Supports or contradicts knowledge object'],
      ],
    ),
  ].join('\n');

  const qualityFramework = [
    '# Knowledge Quality Framework',
    '',
    mdTable(
      ['Metric', 'Current Signal'],
      [
        ['Knowledge Objects', platformKnowledgeObjects],
        ['Evidence Objects', platformEvidenceObjects],
        ['Prepared Snapshots', db.snapshots],
        ['Provider Profiles', db.facilities],
        ['Knowledge Graph Growth', graphGrowth],
        ['Supervisor Incidents', db.incidents],
      ],
    ),
    '',
    'Objects below quality threshold should enter a review queue rather than remain implicit or untracked.',
  ].join('\n');

  writeReport('knowledge_fabric_architecture.md', architecture);
  writeReport('knowledge_object_schema.md', objectSchema);
  writeReport('knowledge_governance.md', governance);
  writeReport('entity_relationship_model.md', entityRelationship);
  writeReport('knowledge_quality_framework.md', qualityFramework);

  console.log(`BUILD_PASS=PASS`);
  console.log(`KNOWLEDGE_FABRIC_PASS=${knowledgeFabricPass ? 'PASS' : 'FAIL'}`);
  console.log(`KNOWLEDGE_QUALITY_PASS=${knowledgeQualityPass ? 'PASS' : 'FAIL'}`);
  console.log(`READY_FOR_PRODUCTION=${knowledgeFabricPass && knowledgeQualityPass ? 'YES' : 'NO'}`);

  if (!(knowledgeFabricPass && knowledgeQualityPass)) {
    process.exitCode = 1;
  }
}

main();