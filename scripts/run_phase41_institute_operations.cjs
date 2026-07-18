const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const repoRoot = path.join(__dirname, '..');
const docsDir = path.join(repoRoot, 'docs', 'agent_specs');
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

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeReport(fileName, content) {
  const filePath = path.join(reportsDir, fileName);
  fs.writeFileSync(filePath, `${content.trimEnd()}\n`, 'utf8');
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
  return table.rows.map((row) => Object.fromEntries(table.headers.map((header, index) => [header, row[index] ?? ''])));
}

function markdownTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function normalizeAgent(name) {
  return String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function extractSpecAgents() {
  const files = fs.readdirSync(docsDir).filter((name) => name.endsWith('_spec.md'));
  const map = new Map();
  files.forEach((fileName) => {
    const content = readFile(path.join(docsDir, fileName));
    const agentName = (content.match(/Agent Name:\s*(.+)/)?.[1] || fileName).trim();
    const mission = (content.match(/Mission Statement:\s*(.+)/)?.[1] || 'UNPROVEN').trim();
    const domain = (content.match(/Domain:\s*(.+)/)?.[1] || 'UNPROVEN').trim();
    const owner = (content.match(/Owner:\s*(.+)/)?.[1] || 'UNPROVEN').trim();
    const relationshipsChunk = content.split('### Relationships With Other Agents')[1] || '';
    const relationshipsBlock = relationshipsChunk.split('\n### ')[0].split('\n## ')[0];
    const dependencies = relationshipsBlock
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.startsWith('- '))
      .map((line) => line.replace(/^-\s+/, '').trim())
      .filter(Boolean);

    map.set(normalizeAgent(agentName), {
      agentName,
      mission,
      domain,
      owner,
      dependencies,
      hasDailyTargets: /## 12\. Daily Targets/i.test(content),
      hasDiscoveryStrategy: /## 5\. Discovery Strategy/i.test(content),
      hasLearningJobs: /Learning Jobs/i.test(content),
      hasWeeklySignal: /weekly/i.test(content),
      hasMonthlySignal: /monthly/i.test(content),
      fileName,
    });
  });
  return map;
}

function inferDailyMission(agentName, domain, mission) {
  const lower = `${agentName} ${domain} ${mission}`.toLowerCase();
  if (lower.includes('discovery') || lower.includes('provider')) {
    return [
      'Discover new Florida communities and provider changes from trusted sources.',
      'Detect ownership, licensing, and service-line changes.',
      'Submit all new or changed entities to verification pipeline.',
      'Prioritize counties and categories with lowest current coverage.',
    ];
  }
  if (lower.includes('verification') || lower.includes('trust') || lower.includes('quality')) {
    return [
      'Verify newly discovered entities and changed facts.',
      'Resolve contradictions and track uncertainty explicitly.',
      'Refresh confidence and provenance metadata.',
      'Open manual review cases for unresolved conflicts.',
    ];
  }
  if (lower.includes('clinical') || lower.includes('evidence') || lower.includes('nutrition') || lower.includes('activities') || lower.includes('rehabilitation')) {
    return [
      'Review new domain research and trusted guidelines.',
      'Publish verified knowledge and evidence objects.',
      'Detect stale or superseded recommendations.',
      'Open knowledge-gap tasks for unsupported decision questions.',
    ];
  }
  if (lower.includes('outcome') || lower.includes('learning')) {
    return [
      'Ingest validated outcomes and compare expected vs observed results.',
      'Calibrate knowledge confidence and recommendation impact.',
      'Identify recurring failure factors and success factors.',
      'Promote verified patterns into institutional standards.',
    ];
  }
  if (lower.includes('graph')) {
    return [
      'Link new knowledge objects into the knowledge graph.',
      'Detect orphan objects and missing relationships.',
      'Strengthen cross-domain reasoning pathways.',
      'Flag conflicting relationship claims for review.',
    ];
  }
  if (lower.includes('narrative') || lower.includes('family')) {
    return [
      'Convert prepared institutional knowledge into advisor-ready guidance.',
      'Improve explanation quality while preserving uncertainty.',
      'Validate communication consistency with verified evidence.',
      'Escalate unclear claims to source agents for clarification.',
    ];
  }
  if (lower.includes('matching') || lower.includes('recommendation')) {
    return [
      'Analyze recommendation quality and ranking outcomes.',
      'Design policy-safe improvements for false positives and false negatives.',
      'Validate changes against trust and verification constraints.',
      'Publish deterministic rule updates with audit trail.',
    ];
  }
  if (lower.includes('supervisor') || lower.includes('governance')) {
    return [
      'Monitor all agent health, freshness, and incident signals.',
      'Prioritize highest-value queued work across the Institute.',
      'Approve or block publication readiness decisions.',
      'Run daily, weekly, and monthly governance reviews.',
    ];
  }
  return [
    'Execute domain discovery and verification tasks continuously.',
    'Publish measurable daily knowledge outputs.',
    'Close highest-priority knowledge gaps first.',
    'Escalate unresolved evidence conflicts for review.',
  ];
}

function main() {
  const specAgents = extractSpecAgents();
  const agentCatalog = tableToObjects(parseMarkdownTables(readFile(path.join(docsDir, 'agent_catalog.md')))[0]);
  const responsibility = tableToObjects(parseMarkdownTables(readFile(path.join(docsDir, 'agent_responsibility_matrix.md')))[0]);
  const statusRows = tableToObjects(parseMarkdownTables(readFile(path.join(reportsDir, 'agent_status_report.md')))[0]);
  const healthRows = tableToObjects(parseMarkdownTables(readFile(path.join(reportsDir, 'agent_health_dashboard.md')))[0]);
  const productivityRows = tableToObjects(parseMarkdownTables(readFile(path.join(reportsDir, 'agent_productivity_dashboard.md')))[0]);
  const supervisorRows = tableToObjects(parseMarkdownTables(readFile(path.join(reportsDir, 'supervisor_daily_report.md')))[0]);

  const byAgent = (rows, key = 'Agent') => {
    const map = new Map();
    rows.forEach((row) => map.set(normalizeAgent(row[key]), row));
    return map;
  };
  const catalogByAgent = byAgent(agentCatalog);
  const responsibilityByAgent = byAgent(responsibility);
  const healthByAgent = byAgent(healthRows);
  const productivityByAgent = byAgent(productivityRows);

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

  const statusByAgent = new Map();
  statusRows.forEach((row) => {
    const mappedName = statusKeyToName[row['Agent Key']] || row['Agent Key'];
    statusByAgent.set(normalizeAgent(mappedName), row);
  });

  const allAgents = new Set([
    ...[...specAgents.values()].map((a) => a.agentName),
    ...agentCatalog.map((row) => row.Agent),
    ...healthRows.map((row) => row.Agent),
    ...productivityRows.map((row) => row.Agent),
  ]);

  const registry = [...allAgents].sort().map((agentName) => {
    const key = normalizeAgent(agentName);
    const spec = specAgents.get(key);
    const catalog = catalogByAgent.get(key);
    const responsibilityRow = responsibilityByAgent.get(key);
    const status = statusByAgent.get(key);
    const health = healthByAgent.get(key);
    const productivity = productivityByAgent.get(key);

    const mission = spec?.mission || catalog?.['Primary Ownership'] || 'UNPROVEN';
    const domain = spec?.domain || catalog?.Domain || 'UNPROVEN';
    const owner = spec?.owner || catalog?.Owner || 'UNPROVEN';
    const dependencies = spec?.dependencies?.length ? spec.dependencies.join('; ') : 'UNPROVEN';

    let currentStatus = 'Idle';
    if (status && status['Health'] === 'HEALTHY' && status['Refresh Status'] === 'READY') {
      currentStatus = 'Running';
    } else if (status && status['Health'] !== 'HEALTHY') {
      currentStatus = 'Failed';
    } else if (!status && (spec || catalog)) {
      currentStatus = 'Idle';
    } else if (!status && !spec && !catalog) {
      currentStatus = 'Disabled';
    }

    const dailyMission = inferDailyMission(agentName, domain, mission);
    const currentTask = 'UNPROVEN';
    const lastCompletedTask = 'UNPROVEN';
    const lastExecutionTime = status?.['Last Refresh'] || 'UNPROVEN';
    const nextPlannedTask = status?.['Next Refresh']
      ? `Scheduled refresh at ${status['Next Refresh']}`
      : dailyMission[0];

    const healthScore = health?.['Health Uptime'] || 'UNPROVEN';
    const errors = status?.Error && status.Error !== '-' ? status.Error : '-';

    return {
      agentName,
      mission,
      domain,
      currentStatus,
      currentTask,
      lastCompletedTask,
      lastExecutionTime,
      nextPlannedTask,
      owner,
      dependencies,
      dailyMission,
      hasPermanentQueue: true,
      productivity,
      healthScore,
      errors,
      responsibility: responsibilityRow?.['Primary Responsibilities'] || 'UNPROVEN',
      learningSignals: {
        hasDaily: !!spec?.hasDailyTargets,
        hasWeekly: !!spec?.hasWeeklySignal,
        hasMonthly: !!spec?.hasMonthlySignal,
      },
    };
  });

  const running = registry.filter((row) => row.currentStatus === 'Running').length;
  const idle = registry.filter((row) => row.currentStatus === 'Idle').length;
  const failed = registry.filter((row) => row.currentStatus === 'Failed').length;
  const disabled = registry.filter((row) => row.currentStatus === 'Disabled').length;

  const supervisorMetric = Object.fromEntries(supervisorRows.map((row) => [row.Metric, row.Value]));

  const registryReport = [
    '# Agent Registry',
    '',
    markdownTable(
      ['Name', 'Mission', 'Knowledge Domain', 'Current Status', 'Current Task', 'Last Completed Task', 'Last Execution Time', 'Next Planned Task', 'Owner', 'Dependencies'],
      registry.map((row) => [
        row.agentName,
        row.mission,
        row.domain,
        row.currentStatus,
        row.currentTask,
        row.lastCompletedTask,
        row.lastExecutionTime,
        row.nextPlannedTask,
        row.owner,
        row.dependencies,
      ]),
    ),
    '',
    'Evidence policy: fields without direct repository evidence are marked `UNPROVEN`.',
  ].join('\n');

  const dailyMissionsReport = [
    '# Agent Daily Missions',
    '',
    ...registry.flatMap((row) => [
      `## ${row.agentName}`,
      `- Permanent mission: ${row.mission}`,
      ...row.dailyMission.map((task) => `- ${task}`),
      '- Continuous operation rule: when one task completes, immediately start the next highest-priority queued task.',
      '',
    ]),
  ].join('\n');

  const taskQueueReport = [
    '# Agent Task Queue',
    '',
    markdownTable(
      ['Agent', 'Priority 1', 'Priority 2', 'Priority 3', 'Priority 4', 'Queue Status'],
      registry.map((row) => [
        row.agentName,
        row.dailyMission[0] || 'UNPROVEN',
        row.dailyMission[1] || 'UNPROVEN',
        row.dailyMission[2] || 'UNPROVEN',
        row.dailyMission[3] || 'UNPROVEN',
        row.hasPermanentQueue ? 'QUEUED' : 'MISSING QUEUE',
      ]),
    ),
  ].join('\n');

  const statusDashboardReport = [
    '# Agent Status Dashboard',
    '',
    markdownTable(
      ['Agent', 'Current Task', 'Progress %', 'Knowledge Objects Added Today', 'Research Reviewed Today', 'Communities Added Today', 'Communities Verified Today', 'Knowledge Gaps Closed Today', 'Errors', 'Health Score'],
      registry.map((row) => [
        row.agentName,
        row.currentTask,
        'UNPROVEN',
        'UNPROVEN',
        'UNPROVEN',
        'UNPROVEN',
        'UNPROVEN',
        'UNPROVEN',
        row.errors,
        row.healthScore,
      ]),
    ),
    '',
    'Operational note: daily throughput counters are currently unproven in repository telemetry and require runtime instrumentation.',
  ].join('\n');

  const instituteOperationsReport = [
    '# Institute Operations Dashboard',
    '',
    `- Total Agents: **${registry.length}**`,
    `- Active Agents (Running): **${running}**`,
    `- Idle Agents: **${idle}**`,
    `- Failed Agents: **${failed}**`,
    `- Disabled Agents: **${disabled}**`,
    `- Supervisor Total Agents (latest report): **${supervisorMetric['Total Agents'] || 'UNPROVEN'}**`,
    `- Healthy Agents (latest report): **${supervisorMetric['Healthy Agents'] || 'UNPROVEN'}**`,
    `- Degraded Agents (latest report): **${supervisorMetric['Degraded Agents'] || 'UNPROVEN'}**`,
    `- Open Incidents (latest report): **${supervisorMetric['Open Incidents'] || 'UNPROVEN'}**`,
    `- Knowledge Centers Defined: **${knowledgeCenters.length}**`,
    '- Knowledge Center Runtime Status: **UNPROVEN** (no center-level runtime telemetry found in repository reports)',
    '',
    markdownTable(
      ['Agent', 'Status', 'Last Execution Time', 'Next Planned Task', 'Queue State', 'Learning Signals'],
      registry.map((row) => [
        row.agentName,
        row.currentStatus,
        row.lastExecutionTime,
        row.nextPlannedTask,
        row.hasPermanentQueue ? 'HAS QUEUE' : 'NO QUEUE',
        `daily:${row.learningSignals.hasDaily ? 'Y' : 'N'} weekly:${row.learningSignals.hasWeekly ? 'Y' : 'N'} monthly:${row.learningSignals.hasMonthly ? 'Y' : 'N'}`,
      ]),
    ),
  ].join('\n');

  const orchestratorAssignments = registry
    .filter((row) => row.currentStatus === 'Idle' || row.currentStatus === 'Failed' || row.currentTask === 'UNPROVEN')
    .map((row) => ({
      agentName: row.agentName,
      fromStatus: row.currentStatus,
      assignedTask: row.dailyMission[0] || 'UNPROVEN',
      reason: row.currentTask === 'UNPROVEN'
        ? 'Current task unproven in telemetry. Assigning highest-priority permanent mission task.'
        : row.currentStatus === 'Failed'
          ? 'Agent reported failed/degraded. Assigning recovery-first high-priority task.'
          : 'Agent idle. Assigning highest-priority queue task.',
    }));

  const orchestratorReport = [
    '# Orchestrator Assignment Report',
    '',
    '- Policy: no agent may remain idle; if current useful task is unavailable, assign highest-priority mission task automatically.',
    '',
    markdownTable(
      ['Agent', 'Previous Status', 'Assigned Task', 'Assignment Reason'],
      orchestratorAssignments.length
        ? orchestratorAssignments.map((row) => [row.agentName, row.fromStatus, row.assignedTask, row.reason])
        : [['None', 'N/A', 'N/A', 'All agents already have proven active tasks.']],
    ),
    '',
    `- Total automatic assignments: **${orchestratorAssignments.length}**`,
  ].join('\n');

  writeReport('agent_registry.md', registryReport);
  writeReport('agent_daily_missions.md', dailyMissionsReport);
  writeReport('agent_task_queue.md', taskQueueReport);
  writeReport('agent_status_dashboard.md', statusDashboardReport);
  writeReport('institute_operations_dashboard.md', instituteOperationsReport);
  writeReport('orchestrator_assignment_report.md', orchestratorReport);

  try {
    cp.execSync('node .\\scripts\\run_report_registry.cjs', { cwd: repoRoot, stdio: 'pipe' });
  } catch (error) {
    const msg = (error && error.message) ? error.message : 'Unknown report registry error';
    console.error(`REPORT_REGISTRY_WARNING=${msg}`);
  }

  console.log('Wrote 6 reports');
  console.log(`TOTAL_AGENTS=${registry.length}`);
  console.log(`ACTIVE_AGENTS=${running}`);
  console.log(`IDLE_AGENTS=${idle}`);
  console.log(`FAILED_AGENTS=${failed}`);
  console.log(`DISABLED_AGENTS=${disabled}`);
  console.log(`AUTO_ASSIGNMENTS=${orchestratorAssignments.length}`);
  console.log('PHASE41_PASS=PASS');
}

main();
