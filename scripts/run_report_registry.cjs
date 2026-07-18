const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const versionsDir = path.join(reportsDir, 'versions');
const registryJsonPath = path.join(reportsDir, 'report_registry.json');
const registryMdPath = path.join(reportsDir, 'agent_report_registry.md');
const orchestratorLivePath = path.join(reportsDir, 'orchestrator_live_operations_dashboard.md');
const instituteDashboardPath = path.join(reportsDir, 'institute_operations_dashboard.md');
const executiveDashboardPath = path.join(reportsDir, 'executive_dashboard.md');

const AGENT_REPORT_PATTERNS = [
  { pattern: /clinical|evidence/i, agent: 'Clinical Knowledge Agent' },
  { pattern: /provider|discovery|inventory/i, agent: 'Provider Intelligence Agent' },
  { pattern: /activities|lifestyle/i, agent: 'Activities Intelligence Agent' },
  { pattern: /nutrition|dining/i, agent: 'Nutrition Intelligence Agent' },
  { pattern: /outcome|accuracy|real_world/i, agent: 'Outcome Learning Agent' },
  { pattern: /knowledge_graph|graph/i, agent: 'Knowledge Graph Agent' },
  { pattern: /quality|trust|verification|freshness|conflict/i, agent: 'Data Quality & Trust Agent' },
  { pattern: /narrative|summary|brief/i, agent: 'Narrative Intelligence Agent' },
  { pattern: /matching|ranking|benchmark/i, agent: 'Matching Improvement Agent' },
  { pattern: /competitive|market|demand/i, agent: 'Competitive Intelligence Agent' },
  { pattern: /supervisor|orchestrator|institute_operations|executive|agent_status|agent_task_queue|agent_registry|agent_missions|agent_daily/i, agent: 'Chief AI Supervisor' },
  { pattern: /fear|decision|psychology/i, agent: 'Senior Living Research Agent' },
];

function readFile(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeFile(filePath, content) {
  fs.writeFileSync(filePath, `${content.trimEnd()}\n`, 'utf8');
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

function isoSafe(ts) {
  return new Date(ts).toISOString().replace(/[:.]/g, '-');
}

function sha1(content) {
  return crypto.createHash('sha1').update(content, 'utf8').digest('hex');
}

function detectAgent(reportName) {
  const lower = reportName.toLowerCase();
  for (const rule of AGENT_REPORT_PATTERNS) {
    if (rule.pattern.test(lower)) return rule.agent;
  }
  return 'Chief AI Supervisor';
}

function loadRegistry() {
  if (!fs.existsSync(registryJsonPath)) {
    return {
      generated_at_utc: null,
      reports: [],
      versions: {},
    };
  }
  try {
    return JSON.parse(readFile(registryJsonPath));
  } catch {
    return {
      generated_at_utc: null,
      reports: [],
      versions: {},
    };
  }
}

function getAgentActivitySnapshot() {
  const statusPath = path.join(reportsDir, 'agent_status_report.md');
  const productivityPath = path.join(reportsDir, 'agent_productivity_dashboard.md');
  const queuePath = path.join(reportsDir, 'agent_task_queue.md');

  const statusRows = fs.existsSync(statusPath)
    ? tableToObjects(parseMarkdownTables(readFile(statusPath))[0] || { headers: [], rows: [] })
    : [];
  const productivityRows = fs.existsSync(productivityPath)
    ? tableToObjects(parseMarkdownTables(readFile(productivityPath))[0] || { headers: [], rows: [] })
    : [];
  const queueRows = fs.existsSync(queuePath)
    ? tableToObjects(parseMarkdownTables(readFile(queuePath))[0] || { headers: [], rows: [] })
    : [];

  const keyToName = {
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

  const statusBy = new Map(statusRows.map((r) => [keyToName[r['Agent Key']] || r['Agent Key'], r]));
  const productivityBy = new Map(productivityRows.map((r) => [r.Agent, r]));
  const queueBy = new Map(queueRows.map((r) => [r.Agent, r]));

  const allAgents = new Set([
    ...statusBy.keys(),
    ...productivityBy.keys(),
    ...queueBy.keys(),
  ]);

  return [...allAgents].sort().map((agent) => {
    const status = statusBy.get(agent);
    const prod = productivityBy.get(agent);
    const queue = queueBy.get(agent);
    return {
      agent,
      health: status?.Health || 'UNPROVEN',
      refreshStatus: status?.['Refresh Status'] || 'UNPROVEN',
      lastRefresh: status?.['Last Refresh'] || 'UNPROVEN',
      queueStatus: queue?.['Queue Status'] || 'UNPROVEN',
      currentPriorityTask: queue?.['Priority 1'] || 'UNPROVEN',
      outputStatus: prod?.Status || 'UNPROVEN',
      growth: prod?.Growth || 'UNPROVEN',
      knowledgeObjects: prod?.['Knowledge Objects'] || 'UNPROVEN',
      evidenceObjects: prod?.['Evidence Objects'] || 'UNPROVEN',
    };
  });
}

function updateDashboard(pathToDashboard, extraSectionTitle, extraSectionBody) {
  if (!fs.existsSync(pathToDashboard)) return;
  const raw = readFile(pathToDashboard);
  const marker = `\n## ${extraSectionTitle}\n`;
  const idx = raw.indexOf(marker);
  const section = `\n## ${extraSectionTitle}\n\n${extraSectionBody.trim()}\n`;
  if (idx >= 0) {
    const nextHeader = raw.indexOf('\n## ', idx + marker.length);
    const updated = nextHeader >= 0
      ? `${raw.slice(0, idx)}${section}${raw.slice(nextHeader)}`
      : `${raw.slice(0, idx)}${section}`;
    writeFile(pathToDashboard, updated);
  } else {
    writeFile(pathToDashboard, `${raw.trimEnd()}\n${section}`);
  }
}

function main() {
  fs.mkdirSync(versionsDir, { recursive: true });

  const registry = loadRegistry();
  const now = new Date().toISOString();
  const reportFiles = fs.readdirSync(reportsDir)
    .filter((f) => f.endsWith('.md'))
    .filter((f) => !['agent_report_registry.md', 'orchestrator_live_operations_dashboard.md'].includes(f));

  const reportEntries = [];
  const versions = registry.versions || {};

  for (const fileName of reportFiles) {
    const filePath = path.join(reportsDir, fileName);
    const stat = fs.statSync(filePath);
    const content = readFile(filePath);
    const hash = sha1(content);
    const versionId = `${isoSafe(stat.mtimeMs)}-${hash.slice(0, 8)}`;
    const agent = detectAgent(fileName);

    const versionFolder = path.join(versionsDir, fileName.replace(/\.md$/i, ''));
    fs.mkdirSync(versionFolder, { recursive: true });
    const snapshotPath = path.join(versionFolder, `${versionId}.md`);
    if (!fs.existsSync(snapshotPath)) {
      writeFile(snapshotPath, content);
    }

    if (!versions[fileName]) versions[fileName] = [];
    if (!versions[fileName].some((v) => v.version_id === versionId)) {
      versions[fileName].push({
        version_id: versionId,
        hash,
        snapshot_path: path.relative(repoRoot, snapshotPath).replace(/\\/g, '/'),
        created_at_utc: now,
      });
    }

    reportEntries.push({
      report_name: fileName,
      report_path: `reports/${fileName}`,
      responsible_agent: agent,
      latest_version_id: versionId,
      latest_hash: hash,
      latest_snapshot_path: path.relative(repoRoot, snapshotPath).replace(/\\/g, '/'),
      last_updated_utc: stat.mtime.toISOString(),
      size_bytes: stat.size,
      status: 'AVAILABLE',
    });
  }

  const agentReportCounts = new Map();
  for (const entry of reportEntries) {
    agentReportCounts.set(entry.responsible_agent, (agentReportCounts.get(entry.responsible_agent) || 0) + 1);
  }

  registry.generated_at_utc = now;
  registry.reports = reportEntries.sort((a, b) => a.report_name.localeCompare(b.report_name));
  registry.versions = versions;
  writeFile(registryJsonPath, JSON.stringify(registry, null, 2));

  const registryMd = [
    '# Agent Report Registry',
    '',
    `- Generated At (UTC): **${now}**`,
    `- Total Reports Indexed: **${registry.reports.length}**`,
    `- Versioned Snapshots Directory: **reports/versions/**`,
    '',
    '## Report Index',
    '',
    markdownTable(
      ['Report', 'Responsible Agent', 'Current Version', 'Last Updated (UTC)', 'Status', 'Report Path', 'Snapshot Path'],
      registry.reports.map((r) => [
        r.report_name,
        r.responsible_agent,
        r.latest_version_id,
        r.last_updated_utc,
        r.status,
        r.report_path,
        r.latest_snapshot_path,
      ]),
    ),
    '',
    '## Reports By Agent',
    '',
    markdownTable(
      ['Agent', 'Reports Indexed'],
      [...agentReportCounts.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([agent, count]) => [agent, count]),
    ),
  ].join('\n');
  writeFile(registryMdPath, registryMd);

  const activity = getAgentActivitySnapshot();
  const reportsByAgent = new Map();
  registry.reports.forEach((r) => {
    reportsByAgent.set(r.responsible_agent, (reportsByAgent.get(r.responsible_agent) || 0) + 1);
  });
  const orchestratorLive = [
    '# Orchestrator Live Operations Dashboard',
    '',
    `- Generated At (UTC): **${now}**`,
    `- Indexed Reports: **${registry.reports.length}**`,
    '',
    '## Agent Activity And Report Status',
    '',
    markdownTable(
      ['Agent', 'Health', 'Refresh Status', 'Last Refresh', 'Queue', 'Current Priority Task', 'Output Status', 'Growth', 'Knowledge Objects', 'Evidence Objects', 'Reports Indexed'],
      activity.map((a) => [
        a.agent,
        a.health,
        a.refreshStatus,
        a.lastRefresh,
        a.queueStatus,
        a.currentPriorityTask,
        a.outputStatus,
        a.growth,
        a.knowledgeObjects,
        a.evidenceObjects,
        reportsByAgent.get(a.agent) || 0,
      ]),
    ),
    '',
    '## Registry Access',
    '',
    '- Report registry markdown: reports/agent_report_registry.md',
    '- Report registry json: reports/report_registry.json',
    '- Version snapshots root: reports/versions/',
  ].join('\n');
  writeFile(orchestratorLivePath, orchestratorLive);

  const unavailable = registry.reports.filter((r) => r.status !== 'AVAILABLE').length;
  const reportSection = [
    `- Report Registry: **reports/agent_report_registry.md**`,
    `- Indexed Reports: **${registry.reports.length}**`,
    `- Unavailable Reports: **${unavailable}**`,
    `- Versioned Snapshots: **${Object.values(versions).reduce((sum, list) => sum + list.length, 0)}**`,
  ].join('\n');
  updateDashboard(instituteDashboardPath, 'Report Operations', reportSection);

  const executiveSection = [
    `- Report Registry Indexed Reports: **${registry.reports.length}**`,
    `- Report Registry Unavailable Reports: **${unavailable}**`,
    `- Live Orchestrator Dashboard: **reports/orchestrator_live_operations_dashboard.md**`,
    `- Agent-Linked Report Coverage: **${agentReportCounts.size} agents mapped**`,
  ].join('\n');
  updateDashboard(executiveDashboardPath, 'Report Status', executiveSection);

  console.log(`REPORTS_INDEXED=${registry.reports.length}`);
  console.log(`REPORT_VERSION_SNAPSHOTS=${Object.values(versions).reduce((sum, list) => sum + list.length, 0)}`);
  console.log(`AGENTS_WITH_REPORTS=${agentReportCounts.size}`);
  console.log('REPORT_REGISTRY_PASS=PASS');
}

main();
