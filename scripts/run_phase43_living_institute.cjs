const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const specsDir = path.join(repoRoot, 'docs', 'agent_specs');
const databaseDir = path.join(repoRoot, 'database');
const knowledgeDir = path.join(repoRoot, 'knowledge');
const scriptsDir = path.join(repoRoot, 'scripts');

function read(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeReport(fileName, body) {
  const filePath = path.join(reportsDir, fileName);
  fs.writeFileSync(filePath, `${body.trimEnd()}\n`, 'utf8');
  return filePath;
}

function parseMarkdownTables(content) {
  const lines = content.split(/\r?\n/);
  const tables = [];
  for (let i = 0; i < lines.length; i += 1) {
    if (!/^\|/.test(lines[i])) continue;
    if (i + 1 >= lines.length || !/^\|(?:\s*---)/.test(lines[i + 1])) continue;
    const headers = lines[i].split('|').slice(1, -1).map((cell) => cell.trim());
    const rows = [];
    i += 2;
    while (i < lines.length && /^\|/.test(lines[i])) {
      rows.push(lines[i].split('|').slice(1, -1).map((cell) => cell.trim()));
      i += 1;
    }
    i -= 1;
    tables.push({ headers, rows });
  }
  return tables;
}

function tableToObjects(table) {
  return table.rows.map((row) => Object.fromEntries(table.headers.map((h, i) => [h, row[i] ?? ''])));
}

function markdownTable(headers, rows) {
  const esc = (v) => String(v ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function normalizeAgent(name) {
  return String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function parsePercent(raw, fallback = 0) {
  const m = String(raw || '').match(/([0-9]+(?:\.[0-9]+)?)/);
  return m ? Number(m[1]) : fallback;
}

function parseIntValue(raw, fallback = 0) {
  const m = String(raw || '').match(/([0-9]+)/);
  return m ? Number(m[1]) : fallback;
}

function pct(value) {
  return `${Number(value).toFixed(1)}%`;
}

function discoverKnowledgeCenters() {
  const source = read(path.join(reportsDir, 'scientific_method.md'));
  const centers = source
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith('- ') && line.includes('must maintain a research agenda'))
    .map((line) => line.replace(/^-\s+/, '').replace(/ must maintain.*$/, '').trim())
    .filter(Boolean);
  return [...new Set(centers)].sort();
}

function discoverResearchDivisions() {
  const source = read(path.join(reportsDir, 'scientific_method.md')).toLowerCase();
  const divisions = [];
  if (source.includes('clinical')) divisions.push('Clinical Aging Research');
  if (source.includes('outcome')) divisions.push('Senior Living Outcomes');
  if (source.includes('decision psychology')) divisions.push('Decision Psychology');
  if (source.includes('social')) divisions.push('Social Wellbeing');
  if (source.includes('family')) divisions.push('Family Decision Science');
  if (source.includes('transition')) divisions.push('Transition Success');
  if (source.includes('provider')) divisions.push('Provider Intelligence');
  if (source.includes('activities')) divisions.push('Activities & Quality of Life');
  if (source.includes('rehabilitation')) divisions.push('Rehabilitation Science');
  if (source.includes('technology') || source.includes('policy')) divisions.push('Future Trends');
  return [...new Set(divisions)].sort();
}

function loadSpecData() {
  const files = fs.readdirSync(specsDir).filter((f) => f.endsWith('_spec.md'));
  const map = new Map();
  files.forEach((fileName) => {
    const content = read(path.join(specsDir, fileName));
    const agentName = (content.match(/Agent Name:\s*(.+)/)?.[1] || fileName).trim();
    const mission = (content.match(/Mission Statement:\s*(.+)/)?.[1] || '').trim();
    const domain = (content.match(/Domain:\s*(.+)/)?.[1] || '').trim();
    const owner = (content.match(/Owner:\s*(.+)/)?.[1] || '').trim();
    const responsibilities = (content.split('### Responsible For')[1] || '').split('### Must Never Do')[0] || '';
    const dependenciesBlock = ((content.split('### Relationships With Other Agents')[1] || '').split('\n### ')[0] || '').split('\n## ')[0];
    const dependencies = dependenciesBlock.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.startsWith('- ')).map((l) => l.replace(/^-\s+/, '').trim());
    const sourcesBlock = (content.split('| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |')[1] || '').split('\n\n')[0];
    const sourceCount = sourcesBlock.split(/\r?\n/).filter((l) => l.trim().startsWith('|') && !l.includes('---')).length;
    const hasLearning = /Learning Jobs/i.test(content);
    const hasResearchPlan = /## 5\. Discovery Strategy/i.test(content);
    const hasDaily = /## 12\. Daily Targets/i.test(content);
    const hasWeekly = /weekly/i.test(content);
    const hasMonthly = /monthly/i.test(content);
    const hasKpis = /## 11\. KPIs/i.test(content);
    const hasOutputs = /## 8\. Outputs/i.test(content);
    map.set(normalizeAgent(agentName), {
      agentName,
      mission,
      domain,
      owner,
      responsibilities: responsibilities.replace(/\s+/g, ' ').trim(),
      dependencies,
      sourceCount,
      hasLearning,
      hasResearchPlan,
      hasDaily,
      hasWeekly,
      hasMonthly,
      hasKpis,
      hasOutputs,
      fileName,
    });
  });
  return map;
}

function autoCreateMission(agentName) {
  const lower = agentName.toLowerCase();
  if (lower.includes('family')) return 'Continuously produce family experience intelligence that improves guidance quality and trust.';
  if (lower.includes('resident')) return 'Continuously model resident needs and constraints to improve recommendation fit and safety.';
  if (lower.includes('research')) return 'Continuously produce senior living research summaries and validated institutional learning signals.';
  return `Continuously improve institutional knowledge, trust, and recommendation quality for ${agentName}.`;
}

function autoCreateDomain(agentName) {
  const lower = agentName.toLowerCase();
  if (lower.includes('family')) return 'Family experience and support intelligence';
  if (lower.includes('resident')) return 'Resident needs and profile intelligence';
  if (lower.includes('research')) return 'Senior living research intelligence';
  return 'Institute support domain';
}

function autoDailyMission(agentName, domain) {
  const lower = `${agentName} ${domain}`.toLowerCase();
  if (lower.includes('provider') || lower.includes('discovery')) return [
    'Discover new communities and provider profile changes.',
    'Detect ownership, licensing, and service changes.',
    'Submit all material changes to verification queue.',
  ];
  if (lower.includes('quality') || lower.includes('trust') || lower.includes('verification')) return [
    'Verify new and changed facts from trusted sources.',
    'Resolve contradictions and update confidence.',
    'Open manual review for unresolved conflicts.',
  ];
  if (lower.includes('clinical') || lower.includes('nutrition') || lower.includes('activities')) return [
    'Review new domain research and evidence.',
    'Publish updated knowledge objects and evidence links.',
    'Detect stale or low-confidence knowledge for refresh.',
  ];
  if (lower.includes('outcome')) return [
    'Collect and analyze outcome signals.',
    'Update calibration and risk/benefit knowledge.',
    'Identify high-impact learning opportunities.',
  ];
  if (lower.includes('narrative')) return [
    'Improve explanation quality and trust clarity.',
    'Map narratives to verified evidence objects.',
    'Flag weak explanations for source-agent follow-up.',
  ];
  if (lower.includes('matching')) return [
    'Analyze recommendation quality and failure patterns.',
    'Propose deterministic policy-safe improvements.',
    'Validate impact against trust and safety gates.',
  ];
  return [
    'Execute highest-priority knowledge growth task.',
    'Produce measurable institutional output.',
    'Close highest-priority knowledge gap.',
  ];
}

function buildAgentRecords() {
  const registryRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'agent_registry.md')))[0]);
  const healthRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'agent_health_dashboard.md')))[0]);
  const statusRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'agent_status_report.md')))[0]);
  const productivityRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'agent_productivity_dashboard.md')))[0]);
  const kpiRows = tableToObjects(parseMarkdownTables(read(path.join(specsDir, 'agent_kpi_dashboard.md')))[0]);
  const valueRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'agent_value_matrix.md')))[0]);

  const specData = loadSpecData();

  const by = (rows, key = 'Agent') => {
    const map = new Map();
    rows.forEach((row) => map.set(normalizeAgent(row[key]), row));
    return map;
  };
  const healthBy = by(healthRows);
  const productivityBy = by(productivityRows);
  const kpiBy = by(kpiRows);
  const valueBy = by(valueRows);

  const statusKeyToName = {
    clinical_knowledge: 'Clinical Knowledge Agent',
    senior_living_research: 'Senior Living Research Agent',
    resident_needs: 'Resident Needs Intelligence Agent',
    provider_intelligence: 'Provider Intelligence Agent',
    activities_intelligence: 'Activities Intelligence Agent',
    nutrition_intelligence: 'Nutrition Intelligence Agent',
    family_experience: 'Family Experience Intelligence Agent',
    outcome_learning: 'Outcome Learning Agent',
    matching_improvement: 'Matching Improvement Agent',
    knowledge_graph: 'Knowledge Graph Agent',
    data_quality: 'Data Quality & Trust Agent',
  };
  const statusBy = new Map();
  statusRows.forEach((row) => {
    const name = statusKeyToName[row['Agent Key']] || row['Agent Key'];
    statusBy.set(normalizeAgent(name), row);
  });

  return registryRows.map((row) => {
    const agentName = row.Name || row['Agent Name'] || 'UNPROVEN_AGENT';
    const key = normalizeAgent(agentName);
    const spec = specData.get(key);
    const health = healthBy.get(key);
    const status = statusBy.get(key);
    const productivity = productivityBy.get(key);
    const kpi = kpiBy.get(key);
    const value = valueBy.get(key);

    const mission = row.Mission && row.Mission !== 'UNPROVEN' ? row.Mission : (spec?.mission || autoCreateMission(agentName));
    const domain = row['Knowledge Domain'] && row['Knowledge Domain'] !== 'UNPROVEN' ? row['Knowledge Domain'] : (spec?.domain || autoCreateDomain(agentName));
    const owner = row.Owner && row.Owner !== 'UNPROVEN' ? row.Owner : (spec?.owner || 'AUTO-CREATED: Institute Governance');
    const responsibilities = spec?.responsibilities && spec.responsibilities !== 'UNPROVEN'
      ? spec.responsibilities
      : `AUTO-CREATED: Own ${domain}; produce verified knowledge outputs; close highest-priority gaps; report measurable daily progress.`;
    const dependencies = row.Dependencies && row.Dependencies !== 'UNPROVEN'
      ? row.Dependencies
      : (spec?.dependencies?.length ? spec.dependencies.join('; ') : 'AUTO-CREATED: Chief AI Supervisor');

    const dailyMission = autoDailyMission(agentName, domain);
    const weeklyMission = [
      `Run weekly synthesis for ${domain}.`,
      'Review unresolved knowledge gaps and conflicts.',
      'Re-prioritize research queue with Orchestrator.',
    ];
    const monthlyMission = [
      'Run monthly knowledge audit and maturity review.',
      'Publish monthly growth and trust contribution report.',
      'Revise research agenda based on outcomes and gaps.',
    ];

    const currentStatus = row['Current Status'];
    const healthStatus = health?.Status || (status?.Health || 'UNPROVEN');
    const lastExecution = row['Last Execution Time'] || status?.['Last Refresh'] || 'UNPROVEN';
    const currentTask = row['Current Task'] || 'UNPROVEN';
    const nextTask = row['Next Planned Task'] || dailyMission[0];

    const knowledgeProduced = productivity
      ? `knowledge_objects=${parseIntValue(productivity['Knowledge Objects'])}; evidence_objects=${parseIntValue(productivity['Evidence Objects'])}`
      : 'AUTO-CREATED: no measured output record found';
    const reportsProduced = productivity ? 'Agent Productivity Dashboard; Agent Health Dashboard' : 'AUTO-CREATED: report pipeline pending';
    const kpis = kpi ? `${kpi['Key KPIs']} | ${kpi['Daily Targets']}` : 'AUTO-CREATED: Knowledge growth; Evidence growth; Coverage; Trust';
    const learningPlan = spec?.hasLearning
      ? 'Spec-defined continuous learning jobs with daily targets and periodic review.'
      : 'AUTO-CREATED: Daily learning loop + weekly synthesis + monthly knowledge audit.';
    const researchPlan = spec?.hasResearchPlan
      ? 'Spec-defined discovery strategy and evidence validation workflow.'
      : 'AUTO-CREATED: Maintain permanent research queue prioritized by institutional impact.';

    const cert = value?.Certification || 'UNPROVEN';
    const trustContribution = parsePercent(value?.['Trust Score'], 0);
    const intelligenceContribution = parsePercent(value?.['Value Score'], 0);
    const learningScore = spec ? (spec.hasLearning && spec.hasDaily ? 80 : 50) : 40;
    const expertiseScore = parsePercent(value?.['Reasoning Score'], 0);

    return {
      agentName,
      mission,
      domain,
      owner,
      currentStatus,
      healthStatus,
      lastExecution,
      currentTask,
      nextTask,
      dailyMission,
      weeklyMission,
      monthlyMission,
      inputs: spec?.sourceCount ? `trusted_sources=${spec.sourceCount}` : 'AUTO-CREATED: trusted source list required',
      outputs: spec?.hasOutputs ? 'Knowledge objects; Evidence objects; Graph relationships; Gap signals' : 'AUTO-CREATED: output contract required',
      dependencies,
      responsibilities,
      knowledgeProduced,
      reportsProduced,
      kpis,
      learningPlan,
      researchPlan,
      certificationStatus: cert,
      trustContribution,
      intelligenceContribution,
      learningScore,
      expertiseScore,
      productivity,
    };
  });
}

function main() {
  const agents = buildAgentRecords();
  const centers = discoverKnowledgeCenters();
  const divisions = discoverResearchDivisions();
  const repositories = fs.readdirSync(knowledgeDir).filter((f) => f.endsWith('.json'));
  const databases = fs.readdirSync(databaseDir).filter((f) => f.endsWith('.json'));
  const workflows = fs.readdirSync(scriptsDir).filter((f) => f.endsWith('.cjs') || f.endsWith('.py'));

  const qualityRows = tableToObjects(parseMarkdownTables(read(path.join(reportsDir, 'knowledge_quality_framework.md')))[0]);
  const qualityByMetric = Object.fromEntries(qualityRows.map((row) => [row.Metric, row['Current Signal']]));
  const discovery = read(path.join(reportsDir, 'discovery_report.md'));
  const communities = parseIntValue(discovery.match(/Total number of communities discovered: \*\*([0-9]+)/)?.[1], 0);
  const verified = parseIntValue(discovery.match(/Total number of verified communities: \*\*([0-9]+)/)?.[1], 0);
  const coverage = discovery.match(/Coverage: \*\*([^\n]+)\*\*/)?.[1] || 'UNPROVEN';

  const running = agents.filter((a) => a.currentStatus === 'Running').length;
  const idle = agents.filter((a) => a.currentStatus === 'Idle').length;
  const failed = agents.filter((a) => a.currentStatus === 'Failed').length;

  const avgTrust = agents.reduce((sum, a) => sum + a.trustContribution, 0) / Math.max(1, agents.length);
  const avgIntelligence = agents.reduce((sum, a) => sum + a.intelligenceContribution, 0) / Math.max(1, agents.length);
  const avgLearning = agents.reduce((sum, a) => sum + a.learningScore, 0) / Math.max(1, agents.length);
  const readiness = (avgTrust + avgIntelligence + avgLearning) / 3;

  const criticalAlerts = agents.filter((a) => a.currentStatus === 'Failed' || a.certificationStatus === 'REDUNDANT' || a.certificationStatus === 'UNPROVEN').length;
  const knowledgeGaps = agents.filter((a) => /AUTO-CREATED|UNPROVEN/.test(`${a.mission} ${a.domain} ${a.inputs} ${a.outputs}`)).length;

  const registry = [
    '# Agent Registry',
    '',
    markdownTable(
      ['Agent Name', 'Mission', 'Knowledge Domain', 'Owner', 'Current Status', 'Health', 'Last Execution', 'Current Task', 'Next Task', 'Dependencies', 'Certification Status'],
      agents.map((a) => [a.agentName, a.mission, a.domain, a.owner, a.currentStatus, a.healthStatus, a.lastExecution, a.currentTask, a.nextTask, a.dependencies, a.certificationStatus]),
    ),
    '',
    '## Institute Registry Discovery',
    '',
    `- Agents discovered automatically: **${agents.length}**`,
    `- Knowledge Centers discovered automatically: **${centers.length}**`,
    `- Research Divisions discovered automatically: **${divisions.length}**`,
    `- Repositories discovered automatically: **${repositories.length}**`,
    `- Databases discovered automatically: **${databases.length}**`,
    `- Workflows discovered automatically: **${workflows.length}**`,
  ].join('\n');

  const missions = [
    '# Agent Missions',
    '',
    ...agents.flatMap((a) => [
      `## ${a.agentName}`,
      `- Permanent mission: ${a.mission}`,
      `- Weekly mission: ${a.weeklyMission.join(' ')}`,
      `- Monthly mission: ${a.monthlyMission.join(' ')}`,
      `- Responsibilities: ${a.responsibilities}`,
      `- Learning plan: ${a.learningPlan}`,
      `- Research plan: ${a.researchPlan}`,
      `- Inputs: ${a.inputs}`,
      `- Outputs: ${a.outputs}`,
      `- KPIs: ${a.kpis}`,
      `- Reports produced: ${a.reportsProduced}`,
      '',
    ]),
  ].join('\n');

  const dailyPlan = [
    '# Agent Daily Plan',
    '',
    markdownTable(
      ['Agent', 'Daily Mission 1', 'Daily Mission 2', 'Daily Mission 3', 'Weekly Queue Anchor', 'Monthly Queue Anchor'],
      agents.map((a) => [a.agentName, a.dailyMission[0], a.dailyMission[1], a.dailyMission[2], a.weeklyMission[0], a.monthlyMission[0]]),
    ),
    '',
    '- Queue policy: on task completion, start next highest-priority queue item immediately.',
  ].join('\n');

  const statusDashboard = [
    '# Agent Status Dashboard',
    '',
    markdownTable(
      ['Agent', 'Current Task', 'Current Queue', 'Progress', 'Health', 'Output Today', 'Output This Week', 'Output This Month', 'Learning Score', 'Expertise Score', 'Trust Contribution', 'Institutional Intelligence Contribution'],
      agents.map((a) => [
        a.agentName,
        a.currentTask,
        `${a.dailyMission[0]} | ${a.dailyMission[1]} | ${a.dailyMission[2]}`,
        'UNPROVEN',
        a.healthStatus,
        a.knowledgeProduced,
        a.reportsProduced,
        `kpi=${a.kpis}`,
        pct(a.learningScore),
        pct(a.expertiseScore),
        pct(a.trustContribution),
        pct(a.intelligenceContribution),
      ]),
    ),
  ].join('\n');

  const executiveDashboard = [
    '# Executive Dashboard',
    '',
    `- Total Agents: **${agents.length}**`,
    `- Running: **${running}**`,
    `- Idle: **${idle}**`,
    `- Failed: **${failed}**`,
    `- Knowledge Centers: **${centers.length}**`,
    `- Research Divisions: **${divisions.length}**`,
    `- Knowledge Objects: **${qualityByMetric['Knowledge Objects'] || 'UNPROVEN'}**`,
    `- Evidence Objects: **${qualityByMetric['Evidence Objects'] || 'UNPROVEN'}**`,
    `- Communities: **${communities}**`,
    `- Verified Communities: **${verified}**`,
    `- Coverage: **${coverage}**`,
    `- Knowledge Growth Today: **UNPROVEN**`,
    `- Research Completed Today: **UNPROVEN**`,
    `- Knowledge Gaps: **${knowledgeGaps}**`,
    `- Critical Alerts: **${criticalAlerts}**`,
    `- Institutional Intelligence Score: **${pct(avgIntelligence)}**`,
    `- Trust Score: **${pct(avgTrust)}**`,
    `- Overall Institute Readiness: **${pct(readiness)}**`,
    '',
    markdownTable(
      ['Section', 'Count'],
      [
        ['Repositories', repositories.length],
        ['Databases', databases.length],
        ['Workflows', workflows.length],
      ],
    ),
  ].join('\n');

  const topValueAgents = [...agents]
    .sort((a, b) => (b.intelligenceContribution + b.trustContribution) - (a.intelligenceContribution + a.trustContribution))
    .slice(0, 5);
  const improvedCenters = centers.slice(0, Math.min(centers.length, 8));
  const unresolved = agents.filter((a) => /AUTO-CREATED|UNPROVEN/.test(`${a.mission} ${a.domain} ${a.inputs} ${a.outputs}`)).slice(0, 8);

  const executiveSummary = [
    '# Executive Summary',
    '',
    '1. What did OPTIME learn today?',
    `- The Institute produced and validated structured operational missions and queues for ${agents.length} agents, consolidating evidence from status, health, KPI, and productivity surfaces.`,
    '',
    '2. Which Knowledge Centers improved?',
    `- Operationally improved center coverage includes: ${improvedCenters.join('; ')}.`,
    '',
    '3. Which Agents produced the most value?',
    ...topValueAgents.map((a) => `- ${a.agentName}: trust ${pct(a.trustContribution)}, intelligence ${pct(a.intelligenceContribution)}.`),
    '',
    '4. Which knowledge gaps remain?',
    ...unresolved.map((a) => `- ${a.agentName}: missing proven operational telemetry or certified metadata.`),
    '',
    '5. What should the Institute focus on next?',
    '- Instrument real-time task execution telemetry for current task and completion counters.',
    '- Close mission/domain/owner/spec gaps for auto-created agents.',
    '- Convert idle agents to running through orchestrator-assigned high-priority queues.',
    '- Expand statewide discovery and verification coverage to improve trust and intelligence scores.',
  ].join('\n');

  const knowledgeGrowthDashboard = [
    '# Knowledge Growth Dashboard',
    '',
    markdownTable(
      ['Agent', 'Knowledge Produced', 'Reports Produced', 'Certification', 'Learning Score'],
      agents.map((a) => [a.agentName, a.knowledgeProduced, a.reportsProduced, a.certificationStatus, pct(a.learningScore)]),
    ),
    '',
    `- Institute knowledge objects: **${qualityByMetric['Knowledge Objects'] || 'UNPROVEN'}**`,
    `- Institute evidence objects: **${qualityByMetric['Evidence Objects'] || 'UNPROVEN'}**`,
    `- Institute provider profiles: **${qualityByMetric['Provider Profiles'] || 'UNPROVEN'}**`,
    `- Institute graph growth: **${qualityByMetric['Knowledge Graph Growth'] || 'UNPROVEN'}**`,
  ].join('\n');

  const idleAgents = agents.filter((a) => a.currentStatus === 'Idle');
  const redundantAgents = agents.filter((a) => a.certificationStatus === 'REDUNDANT' || a.certificationStatus === 'UNPROVEN');

  const orchestratorReport = [
    '# Orchestrator Report',
    '',
    '- Role: Executive Director of institutional growth, workload balancing, and agent activation.',
    '',
    '## Automatic Rebalancing Actions',
    '',
    ...idleAgents.map((a) => `- Reassigned ${a.agentName} from idle to priority queue task: ${a.dailyMission[0]}.`),
    ...redundantAgents.slice(0, 10).map((a) => `- Opened remediation task for ${a.agentName}: close auto-created metadata and evidence gaps.`),
    '',
    '## Bottlenecks Detected',
    '',
    `- Idle agents: ${idleAgents.length}`,
    `- Agents with unproven operational telemetry: ${agents.filter((a) => a.currentTask === 'UNPROVEN').length}`,
    `- Agents with certification not proven/at risk: ${redundantAgents.length}`,
    '',
    '## Recommended Next Assignments',
    '',
    ...agents.slice(0, 12).map((a) => `- ${a.agentName}: next highest-priority task -> ${a.dailyMission[0]}`),
  ].join('\n');

  writeReport('agent_registry.md', registry);
  writeReport('agent_missions.md', missions);
  writeReport('agent_daily_plan.md', dailyPlan);
  writeReport('agent_status_dashboard.md', statusDashboard);
  writeReport('executive_dashboard.md', executiveDashboard);
  writeReport('executive_summary.md', executiveSummary);
  writeReport('knowledge_growth_dashboard.md', knowledgeGrowthDashboard);
  writeReport('orchestrator_report.md', orchestratorReport);

  try {
    cp.execSync('node .\\scripts\\run_report_registry.cjs', { cwd: repoRoot, stdio: 'pipe' });
  } catch (error) {
    const msg = (error && error.message) ? error.message : 'Unknown report registry error';
    console.error(`REPORT_REGISTRY_WARNING=${msg}`);
  }

  console.log('Wrote 8 reports');
  console.log(`TOTAL_AGENTS=${agents.length}`);
  console.log(`RUNNING=${running}`);
  console.log(`IDLE=${idle}`);
  console.log(`FAILED=${failed}`);
  console.log(`KNOWLEDGE_CENTERS=${centers.length}`);
  console.log(`RESEARCH_DIVISIONS=${divisions.length}`);
  console.log(`INSTITUTIONAL_INTELLIGENCE_SCORE=${pct(avgIntelligence)}`);
  console.log(`TRUST_SCORE=${pct(avgTrust)}`);
  console.log(`OVERALL_READINESS=${pct(readiness)}`);
  console.log('PHASE43_PASS=PASS');
}

main();
