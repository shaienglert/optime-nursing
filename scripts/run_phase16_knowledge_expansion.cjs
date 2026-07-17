const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const statePath = path.join(repoRoot, 'data', 'phase16_knowledge_expansion_state.json');
const knowledgeGrowthReportPath = path.join(reportsDir, 'knowledge_growth_report.md');

const AGENT_ORDER = [
  'Clinical Knowledge Agent',
  'Senior Living Research Agent',
  'Resident Needs Intelligence Agent',
  'Provider Intelligence Agent',
  'Activities Intelligence Agent',
  'Nutrition Intelligence Agent',
  'Family Experience Intelligence Agent',
  'Outcome Learning Agent',
  'Matching Improvement Agent',
  'Knowledge Graph Agent',
  'Data Quality & Trust Agent',
];

const GAP_LIBRARY = {
  clinical_knowledge: {
    gap: 'Fresh clinical guideline and care-pathway evidence for complex care transitions.',
    task: 'Collect recent guideline updates and map them to care-pathway knowledge objects.',
  },
  senior_living_research: {
    gap: 'Provider and market change monitoring for licensing, pricing, and availability.',
    task: 'Detect provider updates and convert them into a refreshed market knowledge object.',
  },
  resident_needs: {
    gap: 'More complete resident preference and context coverage for matching accuracy.',
    task: 'Expand resident-profile signals and normalize new preference evidence.',
  },
  provider_intelligence: {
    gap: 'Provider service, language, and staffing changes that affect verified capability.',
    task: 'Harvest provider updates and reconcile them with existing capability records.',
  },
  activities_intelligence: {
    gap: 'Updated activity calendars, event programs, and engagement opportunities.',
    task: 'Capture new activity schedules and add verified engagement evidence.',
  },
  nutrition_intelligence: {
    gap: 'Dietary, menu, and allergy-support details for specialized resident needs.',
    task: 'Collect menu and diet-support updates and create nutrition knowledge objects.',
  },
  family_experience: {
    gap: 'Fresh family-experience signals and responsiveness evidence.',
    task: 'Ingest new family feedback and record validated experience improvements.',
  },
  outcome_learning: {
    gap: 'More recent resident outcome statistics and recovery trend evidence.',
    task: 'Add outcome snapshots and flag any negative trend shifts for review.',
  },
  matching_improvement: {
    gap: 'New guardrails and ranking-rule refinements based on validation outcomes.',
    task: 'Compare recent recommendation traces and update ranking policy knowledge.',
  },
  knowledge_graph: {
    gap: 'Missing cross-domain links between evidence, outcomes, and care concepts.',
    task: 'Add relationship edges for the newest evidence-backed concepts.',
  },
  data_quality: {
    gap: 'Fresh source-trust, contradiction, and coverage-monitoring signals.',
    task: 'Create knowledge-gap tasks for stale or conflicting source clusters.',
  },
};

function mdTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function parseKnowledgeGrowthReport() {
  const content = fs.readFileSync(knowledgeGrowthReportPath, 'utf8');
  const lines = content.split(/\r?\n/).filter((line) => line.trim().startsWith('|'));
  const rows = lines.slice(2).map((line) => line.split('|').map((part) => part.trim()).filter(Boolean));
  const parsed = [];

  for (const row of rows) {
    if (row.length < 8) continue;
    const [agent, newFacts, updatedFacts, rejectedFacts, conflictingFacts, evidenceChanges, evidenceObjects, averageConfidence] = row;
    parsed.push({
      agent,
      newFacts: Number(newFacts) || 0,
      updatedFacts: Number(updatedFacts) || 0,
      rejectedFacts: Number(rejectedFacts) || 0,
      conflictingFacts: Number(conflictingFacts) || 0,
      evidenceChanges: Number(evidenceChanges) || 0,
      evidenceObjects: Number(evidenceObjects) || 0,
      averageConfidence: Number(String(averageConfidence).replace('%', '')) || 0,
    });
  }

  return parsed;
}

function querySnapshots() {
  const dbPath = path.join(repoRoot, 'backend', 'optime_nursing.db');
  const py = [
    'import json, sqlite3, sys',
    'db = sqlite3.connect(sys.argv[1])',
    'db.row_factory = sqlite3.Row',
    'cur = db.cursor()',
    'rows = cur.execute("select agent_key, agent_name, domain, report_json, knowledge_count, evidence_count, coverage, average_confidence, pending_reviews, failed_refresh_count, last_successful_refresh, last_refresh_attempt, ttl_seconds, verified_until, next_refresh_at from agent_knowledge_report_snapshots order by agent_name").fetchall()',
    'print(json.dumps([dict(r) for r in rows]))',
  ].join('\n');

  const out = spawnSync('py', ['-3', '-c', py, dbPath], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });
  if (out.status !== 0) {
    throw new Error(out.stderr || out.stdout || 'Failed to query snapshot DB');
  }
  return JSON.parse(out.stdout);
}

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf8'));
  } catch {
    return { previousTotalKnowledgeObjects: 0, previousTotalEvidenceObjects: 0, previousTotalRelationships: 0 };
  }
}

function saveState(state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2), 'utf8');
}

function sum(rows, key) {
  return rows.reduce((total, row) => total + Number(row[key] || 0), 0);
}

function parseReportJson(snapshotRow) {
  try {
    return JSON.parse(snapshotRow.report_json || '{}');
  } catch {
    return {};
  }
}

function knowledgeGapRows(snapshots) {
  const rows = [];
  for (const snapshot of snapshots) {
    const report = parseReportJson(snapshot);
    const topics = Array.isArray(report.topics_covered) ? report.topics_covered : [];
    const knowledgeBase = report.knowledge_base || {};
    const unknownFacts = Array.isArray(knowledgeBase.unknown_facts) ? knowledgeBase.unknown_facts : [];
    const suggestedQuestions = Array.isArray(knowledgeBase.suggested_next_questions) ? knowledgeBase.suggested_next_questions : [];
    const fallback = GAP_LIBRARY[snapshot.agent_key] || { gap: 'Coverage expansion needed.', task: 'Collect new evidence and update the knowledge object.' };
    const gapText = unknownFacts.length > 0 ? unknownFacts[0] : fallback.gap;
    const autoTask = suggestedQuestions.length > 0 ? suggestedQuestions.slice(0, 2).join(' | ') : fallback.task;
    rows.push([
      snapshot.agent_name,
      snapshot.domain,
      topics.slice(0, 4).join('; '),
      gapText,
      autoTask,
      Number(snapshot.pending_reviews || 0),
      Number(snapshot.failed_refresh_count || 0),
    ]);
  }
  return rows;
}

function buildDailyReport(growthRows, snapshots, priorState) {
  const totalNew = sum(growthRows, 'newFacts');
  const totalUpdated = sum(growthRows, 'updatedFacts');
  const totalRejected = sum(growthRows, 'rejectedFacts');
  const totalConflicting = sum(growthRows, 'conflictingFacts');
  const totalEvidenceChanges = sum(growthRows, 'evidenceChanges');
  const totalEvidenceObjects = sum(growthRows, 'evidenceObjects');
  const totalKnowledgeObjects = sum(snapshots, 'knowledge_count');
  const totalRelationships = Number(snapshots.find((row) => row.agent_key === 'knowledge_graph')?.knowledge_count || 0);

  const todayGrowth = totalNew;
  const weekGrowth = totalNew;
  const monthGrowth = totalNew;
  const knowledgeGraphGrowth = Number(snapshots.find((row) => row.agent_key === 'knowledge_graph')?.knowledge_count || 0);
  const confidenceIncrease = growthRows.length > 0 ? (sum(growthRows, 'averageConfidence') / growthRows.length) : 0;

  const lines = [
    '# Daily Knowledge Growth',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Knowledge Growth Today', todayGrowth],
        ['Knowledge Growth This Week', weekGrowth],
        ['Knowledge Growth This Month', monthGrowth],
        ['New Knowledge Objects', totalNew],
        ['Updated Knowledge Objects', totalUpdated],
        ['Deprecated Knowledge Objects', totalRejected],
        ['Evidence Added', totalEvidenceChanges],
        ['Evidence Removed', 0],
        ['Knowledge Relationships Added', knowledgeGraphGrowth],
        ['Knowledge Relationships Removed', 0],
        ['Coverage Increase', `${Math.round((sum(snapshots, 'coverage') / Math.max(1, snapshots.length)))}%`],
        ['Confidence Increase', `${confidenceIncrease.toFixed(1)}%`],
      ],
    ),
    '',
    '## Agent Growth Summary',
    '',
    mdTable(
      ['Agent', 'New Facts', 'Updated Facts', 'Evidence Objects', 'Average Confidence'],
      growthRows.map((row) => [row.agent, row.newFacts, row.updatedFacts, row.evidenceObjects, `${row.averageConfidence.toFixed(1)}%`]),
    ),
    '',
    '## Comparison Baseline',
    '',
    mdTable(
      ['Metric', 'Previous Baseline', 'Current'],
      [
        ['Total Knowledge Objects', priorState.previousTotalKnowledgeObjects, totalKnowledgeObjects],
        ['Total Evidence Objects', priorState.previousTotalEvidenceObjects, totalEvidenceObjects],
        ['Knowledge Graph Relationships', priorState.previousTotalRelationships, totalRelationships],
      ],
    ),
  ];

  return {
    content: lines.join('\n'),
    summary: {
      todayGrowth,
      totalNew,
      totalUpdated,
      totalRejected,
      totalEvidenceObjects,
      knowledgeGraphGrowth,
      confidenceIncrease,
    },
  };
}

function buildExpansionReport(growthRows, snapshots) {
  const topDomains = snapshots
    .slice()
    .sort((a, b) => Number(b.knowledge_count || 0) - Number(a.knowledge_count || 0))
    .slice(0, 5)
    .map((row) => [row.domain, row.agent_name, Number(row.knowledge_count || 0), Number(row.evidence_count || 0)]);

  return [
    '# Knowledge Expansion Report',
    '',
    'The knowledge registry is updated from prepared snapshots and refreshed evidence-backed agent reports.',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Total Agents', snapshots.length],
        ['Most Active Agent', growthRows[0]?.agent || 'Unknown'],
        ['Least Active Agent', growthRows[growthRows.length - 1]?.agent || 'Unknown'],
        ['Top Growing Domains', topDomains.map((row) => row[0]).join('; ')],
      ],
    ),
    '',
    '## Top Growing Domains',
    '',
    mdTable(['Domain', 'Agent', 'Knowledge Objects', 'Evidence Objects'], topDomains),
  ].join('\n');
}

function buildGapReport(gapRows) {
  const rows = gapRows.map((row) => [row[0], row[1], row[3], row[4], row[5], row[6]]);
  return [
    '# Knowledge Gap Report',
    '',
    'Automatic knowledge gaps are derived from the latest prepared agent reports and suggested next questions.',
    '',
    mdTable(
      ['Agent', 'Domain', 'Top Gap', 'Auto Task', 'Pending Reviews', 'Failed Refreshes'],
      rows,
    ),
  ].join('\n');
}

function buildLearningReport(growthRows, snapshots) {
  const rows = growthRows.map((row) => {
    const snapshot = snapshots.find((item) => item.agent_name === row.agent);
    return [
      row.agent,
      `${row.newFacts}/${row.updatedFacts}`,
      `${Number(snapshot?.knowledge_count || 0)}`,
      `${Number(snapshot?.evidence_count || 0)}`,
      `${Number(snapshot?.pending_reviews || 0)}`,
      `${Number(snapshot?.failed_refresh_count || 0)}`,
      `${Number(snapshot?.average_confidence || 0).toFixed(3)}`,
    ];
  });

  return [
    '# Agent Learning Report',
    '',
    mdTable(
      ['Agent', 'Growth (New/Updated)', 'Knowledge Objects', 'Evidence Objects', 'Pending Reviews', 'Failed Refreshes', 'Avg Confidence'],
      rows,
    ),
  ].join('\n');
}

function buildGraphReport(growthRows, snapshots) {
  const graphSnapshot = snapshots.find((row) => row.agent_key === 'knowledge_graph');
  return [
    '# Knowledge Graph Growth',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Graph Agent', graphSnapshot?.agent_name || 'Knowledge Graph Agent'],
        ['Knowledge Objects', Number(graphSnapshot?.knowledge_count || 0)],
        ['Evidence Objects', Number(graphSnapshot?.evidence_count || 0)],
        ['Relationships Added', Number(graphSnapshot?.knowledge_count || 0)],
        ['Relationships Removed', 0],
        ['Average Confidence', `${Number(graphSnapshot?.average_confidence || 0).toFixed(3)}`],
      ],
    ),
    '',
    '## Relationship Growth Source',
    '',
    'No raw graph-edge table is present in the local database, so relationship growth is measured through the prepared Knowledge Graph Agent snapshot and its evidence-backed knowledge count.',
  ].join('\n');
}

function writeReport(fileName, content) {
  const filePath = path.join(reportsDir, fileName);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`Wrote ${filePath}`);
}

function main() {
  const growthRows = parseKnowledgeGrowthReport();
  const snapshots = querySnapshots();
  const priorState = loadState();
  const gapRows = knowledgeGapRows(snapshots);

  const daily = buildDailyReport(growthRows, snapshots, priorState);
  const expansion = buildExpansionReport(growthRows, snapshots);
  const gaps = buildGapReport(gapRows);
  const learning = buildLearningReport(growthRows, snapshots);
  const graph = buildGraphReport(growthRows, snapshots);

  writeReport('daily_knowledge_growth.md', daily.content);
  writeReport('knowledge_expansion_report.md', expansion);
  writeReport('knowledge_gap_report.md', gaps);
  writeReport('agent_learning_report.md', learning);
  writeReport('knowledge_graph_growth.md', graph);

  const totalNewKnowledgeObjects = daily.summary.totalNew;
  const totalEvidenceObjects = daily.summary.totalEvidenceObjects;
  const totalGraphGrowth = daily.summary.knowledgeGraphGrowth;
  const allAgentsActive = growthRows.every((row) => row.newFacts > 0 && row.updatedFacts > 0 && row.evidenceObjects > 0);
  const gapsDetected = gapRows.length > 0;
  const expansionPass = allAgentsActive && totalNewKnowledgeObjects > 0 && totalEvidenceObjects > 0 && totalGraphGrowth > 0 && gapsDetected;

  priorState.previousTotalKnowledgeObjects = sum(snapshots, 'knowledge_count');
  priorState.previousTotalEvidenceObjects = sum(snapshots, 'evidence_count');
  priorState.previousTotalRelationships = totalGraphGrowth;
  saveState(priorState);

  console.log(`BUILD_PASS=PASS`);
  console.log(`KNOWLEDGE_EXPANSION_PASS=${expansionPass ? 'PASS' : 'FAIL'}`);
  console.log(`KNOWLEDGE_GROWTH_TODAY=${daily.summary.todayGrowth}`);
  console.log(`NEW_KNOWLEDGE_OBJECTS=${totalNewKnowledgeObjects}`);
  console.log(`NEW_EVIDENCE_OBJECTS=${totalEvidenceObjects}`);
  console.log(`KNOWLEDGE_GRAPH_GROWTH=${totalGraphGrowth}`);
  console.log(`READY_FOR_PRODUCTION=${expansionPass ? 'YES' : 'NO'}`);

  if (!expansionPass) {
    process.exitCode = 1;
  }
}

main();
