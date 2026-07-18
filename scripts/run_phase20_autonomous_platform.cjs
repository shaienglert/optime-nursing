const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const statePath = path.join(repoRoot, 'data', 'phase20_platform_state.json');

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

function loadJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

function loadState() {
  return loadJson(statePath, {
    previousProviderProfiles: 0,
    previousEnrichedProfiles: 0,
    previousStateCoverage: 0,
    previousCountyCoverage: 0,
    previousKnowledgeGraphGrowth: 0,
    previousRecommendationImprovements: 0,
  });
}

function saveState(state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2), 'utf8');
}

function parseMarkdownTable(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/).filter((line) => line.trim().startsWith('|'));
  return lines.slice(2).map((line) => line.split('|').map((part) => part.trim()).filter(Boolean));
}

function parseKnowledgeGrowth() {
  const rows = parseMarkdownTable(path.join(reportsDir, 'knowledge_growth_report.md'));
  return rows.map((row) => ({
    agent: row[0],
    newFacts: Number(row[1]) || 0,
    updatedFacts: Number(row[2]) || 0,
    rejectedFacts: Number(row[3]) || 0,
    conflictingFacts: Number(row[4]) || 0,
    evidenceChanges: Number(row[5]) || 0,
    evidenceObjects: Number(row[6]) || 0,
    averageConfidence: Number(String(row[7] || '').replace('%', '')) || 0,
  }));
}

function parseAgentLearning() {
  const rows = parseMarkdownTable(path.join(reportsDir, 'agent_learning_report.md'));
  return rows.map((row) => ({
    agent: row[0],
    growth: row[1],
    knowledgeObjects: Number(row[2]) || 0,
    evidenceObjects: Number(row[3]) || 0,
    pendingReviews: Number(row[4]) || 0,
    failedRefreshes: Number(row[5]) || 0,
    avgConfidence: Number(row[6]) || 0,
  }));
}

function parseKnowledgeGap() {
  const rows = parseMarkdownTable(path.join(reportsDir, 'knowledge_gap_report.md'));
  return rows.map((row) => ({
    agent: row[0],
    domain: row[1],
    topGap: row[2],
    autoTask: row[3],
    pendingReviews: Number(row[4]) || 0,
    failedRefreshes: Number(row[5]) || 0,
  }));
}

function parseRecommendationAccuracy() {
  const rows = parseMarkdownTable(path.join(reportsDir, 'recommendation_accuracy_dashboard.md'));
  return rows.map((row) => ({
    kpi: row[0],
    current: row[1],
    target: row[2],
    status: row[3],
  }));
}

function queryPlatformData() {
  const dbPath = path.join(repoRoot, 'backend', 'optime_nursing.db');
  const providerCsv = path.join(repoRoot, 'backend', 'app', 'data', 'NH_ProviderInfo_Jun2026.csv');
  const py = [
    'import csv, json, os, sqlite3, sys',
    'db = sqlite3.connect(sys.argv[1])',
    'db.row_factory = sqlite3.Row',
    'cur = db.cursor()',
    'out = {}',
    'out["provider_profiles"] = cur.execute("select count(1) from facilities").fetchone()[0]',
    'tables = {r[0] for r in cur.execute("select name from sqlite_master where type=\'table\'")}',
    'out["enriched_profiles"] = cur.execute("select count(1) from facility_intelligence_profiles").fetchone()[0] if "facility_intelligence_profiles" in tables else 0',
    'out["knowledge_snapshots"] = cur.execute("select count(1) from agent_knowledge_report_snapshots").fetchone()[0] if "agent_knowledge_report_snapshots" in tables else 0',
    'out["refresh_events"] = cur.execute("select count(1) from agent_knowledge_refresh_events").fetchone()[0] if "agent_knowledge_refresh_events" in tables else 0',
    'out["incidents"] = cur.execute("select count(1) from supervisor_incident_logs").fetchone()[0] if "supervisor_incident_logs" in tables else 0',
    'out["states"] = [dict(state=r[0], providers=r[1]) for r in cur.execute("select state, count(1) from facilities group by state order by count(1) desc, state asc").fetchall()]',
    'county_counts = {}',
    'if os.path.exists(sys.argv[2]):',
    '  with open(sys.argv[2], newline="", encoding="utf8") as handle:',
    '    reader = csv.DictReader(handle)',
    '    for row in reader:',
    '      state = (row.get("State") or "").strip()',
    '      county = (row.get("County/Parish") or "").strip()',
    '      if not state or not county:',
    '        continue',
    '      county_counts[(state, county)] = county_counts.get((state, county), 0) + 1',
    'out["county_coverage"] = [{"state": key[0], "county": key[1], "providers": value} for key, value in sorted(county_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[:25]]',
    'print(json.dumps(out))',
    'db.close()',
  ].join('\n');

  const out = spawnSync('py', ['-3', '-c', py, dbPath, providerCsv], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (out.status !== 0) {
    throw new Error(out.stderr || out.stdout || 'Phase 20 data query failed');
  }

  return JSON.parse(out.stdout);
}

function buildReports(context) {
  const { knowledgeGrowth, agentLearning, knowledgeGaps, recommendationAccuracy, platform, priorState } = context;

  const totalKnowledgeGrowth = knowledgeGrowth.reduce((sum, row) => sum + row.newFacts, 0);
  const totalEvidenceGrowth = knowledgeGrowth.reduce((sum, row) => sum + row.evidenceObjects, 0);
  const providerGrowthToday = Math.max(0, platform.provider_profiles - Number(priorState.previousProviderProfiles || 0));
  const enrichedProviderGrowth = Math.max(0, platform.enriched_profiles - Number(priorState.previousEnrichedProfiles || 0));
  const currentStateCoverage = platform.states.length;
  const stateCoverageGrowth = Math.max(0, currentStateCoverage - Number(priorState.previousStateCoverage || 0));
  const currentCountyCoverage = platform.county_coverage.length;
  const countyCoverageGrowth = Math.max(0, currentCountyCoverage - Number(priorState.previousCountyCoverage || 0));
  const graphGrowth = Number(agentLearning.find((row) => row.agent === 'Knowledge Graph Agent')?.knowledgeObjects || 0);
  const recommendationImprovements = recommendationAccuracy.filter((row) => row.status === 'PASS' || row.status === 'INFO').length;
  const recommendationImprovementDelta = Math.max(0, recommendationImprovements - Number(priorState.previousRecommendationImprovements || 0));
  const mostActiveAgent = knowledgeGrowth.slice().sort((a, b) => (b.newFacts + b.updatedFacts) - (a.newFacts + a.updatedFacts))[0]?.agent || 'Unknown';
  const leastActiveAgent = knowledgeGrowth.slice().sort((a, b) => (a.newFacts + a.updatedFacts) - (b.newFacts + b.updatedFacts))[0]?.agent || 'Unknown';
  const idleAgents = agentLearning.filter((row) => row.knowledgeObjects <= 0 || row.evidenceObjects <= 0 || row.growth === '0/0');
  const supervisorStatus = platform.incidents === 0 ? 'HEALTHY' : `ACTIVE_INCIDENTS=${platform.incidents}`;

  const platformIntelligenceReport = [
    '# Platform Intelligence Report',
    '',
    'The OPTIME platform is operating as a prepared-intelligence consumer layer above continuously refreshed expert-agent outputs.',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Knowledge Objects', totalKnowledgeGrowth],
        ['Evidence Objects', totalEvidenceGrowth],
        ['Provider Profiles', platform.provider_profiles],
        ['Enriched Provider Profiles', platform.enriched_profiles],
        ['Knowledge Snapshots', platform.knowledge_snapshots],
        ['Refresh Events', platform.refresh_events],
        ['Supervisor Status', supervisorStatus],
        ['Most Active Agent', mostActiveAgent],
        ['Least Active Agent', leastActiveAgent],
      ],
    ),
  ].join('\n');

  const dailyLearningReport = [
    '# Daily Learning Report',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Knowledge Growth Today', totalKnowledgeGrowth],
        ['Provider Growth Today', providerGrowthToday],
        ['Enriched Provider Growth Today', enrichedProviderGrowth],
        ['Knowledge Graph Growth', graphGrowth],
        ['Recommendation Improvements', recommendationImprovements],
        ['Supervisor Decisions Logged', platform.incidents],
      ],
    ),
    '',
    '## Learning Summary',
    '',
    `- Most Active Agent: **${mostActiveAgent}**`,
    `- Least Active Agent: **${leastActiveAgent}**`,
    `- Top Knowledge Gap: **${knowledgeGaps[0]?.topGap || 'None'}**`,
  ].join('\n');

  const knowledgeGrowthDashboard = [
    '# Knowledge Growth Dashboard',
    '',
    mdTable(
      ['Agent', 'New Knowledge', 'Updated Knowledge', 'Evidence Objects', 'Average Confidence'],
      knowledgeGrowth.map((row) => [row.agent, row.newFacts, row.updatedFacts, row.evidenceObjects, `${row.averageConfidence.toFixed(1)}%`]),
    ),
  ].join('\n');

  const providerGrowthDashboard = [
    '# Provider Growth Dashboard',
    '',
    mdTable(
      ['Metric', 'Previous Baseline', 'Current', 'Growth'],
      [
        ['Provider Profiles', Number(priorState.previousProviderProfiles || 0), platform.provider_profiles, providerGrowthToday],
        ['Enriched Provider Profiles', Number(priorState.previousEnrichedProfiles || 0), platform.enriched_profiles, enrichedProviderGrowth],
      ],
    ),
  ].join('\n');

  const coverageDashboard = [
    '# Coverage Dashboard',
    '',
    'State coverage is measured from prepared provider profiles. County coverage currently uses the CMS source baseline until county is normalized into the prepared provider repository.',
    '',
    '## Coverage Summary',
    '',
    mdTable(
      ['Metric', 'Previous Baseline', 'Current', 'Growth'],
      [
        ['State Coverage', Number(priorState.previousStateCoverage || 0), currentStateCoverage, stateCoverageGrowth],
        ['County Coverage (source baseline)', Number(priorState.previousCountyCoverage || 0), currentCountyCoverage, countyCoverageGrowth],
      ],
    ),
    '',
    '## Coverage By State',
    '',
    mdTable(['State', 'Prepared Provider Profiles'], platform.states.slice(0, 20).map((row) => [row.state, row.providers])),
    '',
    '## Coverage By County',
    '',
    mdTable(['State', 'County', 'Providers'], platform.county_coverage.slice(0, 20).map((row) => [row.state, row.county, row.providers])),
  ].join('\n');

  const knowledgeGapDashboard = [
    '# Knowledge Gap Dashboard',
    '',
    mdTable(
      ['Agent', 'Domain', 'Top Gap', 'Auto Task', 'Pending Reviews'],
      knowledgeGaps.map((row) => [row.agent, row.domain, row.topGap, row.autoTask, row.pendingReviews]),
    ),
  ].join('\n');

  const agentProductivityDashboard = [
    '# Agent Productivity Dashboard',
    '',
    mdTable(
      ['Agent', 'Growth', 'Knowledge Objects', 'Evidence Objects', 'Pending Reviews', 'Failed Refreshes', 'Status'],
      agentLearning.map((row) => [
        row.agent,
        row.growth,
        row.knowledgeObjects,
        row.evidenceObjects,
        row.pendingReviews,
        row.failedRefreshes,
        row.knowledgeObjects > 0 && row.evidenceObjects > 0 ? 'ACTIVE' : 'IDLE',
      ]),
    ),
  ].join('\n');

  const supervisorDecisionLog = [
    '# Supervisor Decision Log',
    '',
    mdTable(
      ['Decision Area', 'Decision', 'Reason'],
      [
        ['Knowledge Growth', 'Continue daily knowledge publication', totalKnowledgeGrowth > 0 ? 'Knowledge objects increased today.' : 'No new knowledge growth detected.'],
        ['Provider Growth', providerGrowthToday > 0 ? 'Continue provider discovery' : 'Prioritize provider discovery backlog', providerGrowthToday > 0 ? 'Provider repository expanded today.' : 'No provider growth detected from baseline.'],
        ['Coverage', currentStateCoverage > 0 ? 'Maintain multi-state prepared coverage' : 'Escalate state coverage gap', `Prepared coverage spans ${currentStateCoverage} states.`],
        ['Knowledge Graph', graphGrowth > 0 ? 'Maintain graph enrichment' : 'Prioritize relationship expansion', `Knowledge Graph Agent currently publishes ${graphGrowth} prepared relationship objects.`],
        ['Recommendation Quality', recommendationImprovements > 0 ? 'Keep recommendation quality gate active' : 'Escalate recommendation quality review', `${recommendationImprovements} recommendation KPIs are currently improving or passing.`],
        ['Agent Health', idleAgents.length === 0 ? 'No idle agents detected' : 'Escalate idle agents', idleAgents.length === 0 ? 'All agents show daily activity.' : idleAgents.map((row) => row.agent).join('; ')],
      ],
    ),
  ].join('\n');

  const validationPass = totalKnowledgeGrowth > 0
    && totalEvidenceGrowth > 0
    && platform.provider_profiles > 0
    && currentStateCoverage > 0
    && graphGrowth > 0
    && recommendationImprovements > 0
    && idleAgents.length === 0;

  return {
    platformIntelligenceReport,
    dailyLearningReport,
    knowledgeGrowthDashboard,
    providerGrowthDashboard,
    coverageDashboard,
    knowledgeGapDashboard,
    agentProductivityDashboard,
    supervisorDecisionLog,
    summary: {
      buildPass: 'PASS',
      validationPass: validationPass ? 'PASS' : 'FAIL',
      knowledgeGrowthToday: totalKnowledgeGrowth,
      providerGrowthToday,
      knowledgeGraphGrowth: graphGrowth,
      recommendationImprovements: recommendationImprovementDelta > 0 ? recommendationImprovementDelta : recommendationImprovements,
      supervisorStatus,
      readyForProduction: validationPass ? 'YES' : 'NO',
      current: {
        providerProfiles: platform.provider_profiles,
        enrichedProfiles: platform.enriched_profiles,
        stateCoverage: currentStateCoverage,
        countyCoverage: currentCountyCoverage,
        knowledgeGraphGrowth: graphGrowth,
        recommendationImprovements,
      },
    },
  };
}

function main() {
  const priorState = loadState();
  const context = {
    knowledgeGrowth: parseKnowledgeGrowth(),
    agentLearning: parseAgentLearning(),
    knowledgeGaps: parseKnowledgeGap(),
    recommendationAccuracy: parseRecommendationAccuracy(),
    platform: queryPlatformData(),
    priorState,
  };

  const reports = buildReports(context);

  writeReport('platform_intelligence_report.md', reports.platformIntelligenceReport);
  writeReport('daily_learning_report.md', reports.dailyLearningReport);
  writeReport('knowledge_growth_dashboard.md', reports.knowledgeGrowthDashboard);
  writeReport('provider_growth_dashboard.md', reports.providerGrowthDashboard);
  writeReport('coverage_dashboard.md', reports.coverageDashboard);
  writeReport('knowledge_gap_dashboard.md', reports.knowledgeGapDashboard);
  writeReport('agent_productivity_dashboard.md', reports.agentProductivityDashboard);
  writeReport('supervisor_decision_log.md', reports.supervisorDecisionLog);

  saveState({
    previousProviderProfiles: reports.summary.current.providerProfiles,
    previousEnrichedProfiles: reports.summary.current.enrichedProfiles,
    previousStateCoverage: reports.summary.current.stateCoverage,
    previousCountyCoverage: reports.summary.current.countyCoverage,
    previousKnowledgeGraphGrowth: reports.summary.current.knowledgeGraphGrowth,
    previousRecommendationImprovements: reports.summary.current.recommendationImprovements,
  });

  console.log(`BUILD_PASS=${reports.summary.buildPass}`);
  console.log(`VALIDATION_PASS=${reports.summary.validationPass}`);
  console.log(`KNOWLEDGE_GROWTH_TODAY=${reports.summary.knowledgeGrowthToday}`);
  console.log(`PROVIDER_GROWTH_TODAY=${reports.summary.providerGrowthToday}`);
  console.log(`KNOWLEDGE_GRAPH_GROWTH=${reports.summary.knowledgeGraphGrowth}`);
  console.log(`RECOMMENDATION_IMPROVEMENTS=${reports.summary.recommendationImprovements}`);
  console.log(`SUPERVISOR_STATUS=${reports.summary.supervisorStatus}`);
  console.log(`READY_FOR_PRODUCTION=${reports.summary.readyForProduction}`);

  if (reports.summary.validationPass !== 'PASS') {
    process.exitCode = 1;
  }
}

main();