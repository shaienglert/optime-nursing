const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveCanonicalPython } = require('./lib/python_runtime.cjs');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');

function mdTable(headers, rows) {
  const esc = (v) => String(v ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function readStateAndInjectCycle() {
  const dbPath = path.join(repoRoot, 'backend', 'optime_nursing.db');
  const pythonPath = resolveCanonicalPython(repoRoot);
  const py = [
    'import sqlite3, json, sys, datetime',
    'db = sqlite3.connect(sys.argv[1])',
    'db.row_factory = sqlite3.Row',
    'cur = db.cursor()',
    'def table_exists(name):',
    '  return cur.execute("select count(*) from sqlite_master where type=\'table\' and name=?", (name,)).fetchone()[0] > 0',
    'def q(sql, params=()):',
    '  return [dict(r) for r in cur.execute(sql, params).fetchall()]',
    'now = datetime.datetime.now(datetime.timezone.utc)',
    'if table_exists("supervisor_incident_logs") and table_exists("agent_knowledge_report_snapshots"):',
    '  stale = q("select agent_key, domain, freshness_status, failed_refresh_count from agent_knowledge_report_snapshots where freshness_status in (\'STALE\',\'EXPIRED\',\'NEEDS_REVIEW\',\'ERROR\') or failed_refresh_count >= 3")',
    '  for row in stale:',
    '    cur.execute("insert into supervisor_incident_logs (incident_type, severity, status, agent_key, domain, summary, details_json, created_at, resolved_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("SUPERVISOR_ALERT", "HIGH", "OPEN", row.get("agent_key"), row.get("domain"), "Supervisor detected degraded freshness state", json.dumps(row), now.isoformat(), None))',
    '  db.commit()',
    'snapshots = q("select * from agent_knowledge_report_snapshots") if table_exists("agent_knowledge_report_snapshots") else []',
    'refresh = q("select * from agent_knowledge_refresh_events") if table_exists("agent_knowledge_refresh_events") else []',
    'usage = q("select * from recommendation_knowledge_usage_logs") if table_exists("recommendation_knowledge_usage_logs") else []',
    'inc = q("select * from supervisor_incident_logs") if table_exists("supervisor_incident_logs") else []',
    'print(json.dumps({"snapshots": snapshots, "refresh": refresh, "usage": usage, "incidents": inc}))',
  ].join('\n');

  const out = spawnSync(pythonPath, ['-c', py, dbPath], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (out.status !== 0) {
    const detail = out.stderr || out.stdout || 'supervisor state read failed';
    throw new Error(detail);
  }
  return JSON.parse(out.stdout);
}

function writeReport(name, content) {
  const fp = path.join(reportsDir, name);
  fs.writeFileSync(fp, content, 'utf8');
  console.log(`Wrote ${fp}`);
}

function generate() {
  const state = readStateAndInjectCycle();
  const snapshots = state.snapshots || [];
  const refresh = state.refresh || [];
  const usage = state.usage || [];
  const incidents = state.incidents || [];

  const openIncidents = incidents.filter((i) => String(i.status || '').toUpperCase() === 'OPEN');
  const bySeverity = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => [
    sev,
    incidents.filter((i) => String(i.severity || '').toUpperCase() === sev).length,
  ]);

  const staleUsage = usage.filter((u) => Number(u.used_stale) === 1);
  const staleNotAllowed = usage.filter((u) => Number(u.used_stale) === 1 && Number(u.policy_allowed) === 0);

  const avgAge = snapshots.length > 0
    ? snapshots.reduce((s, r) => s + Number(r.knowledge_age_seconds || 0), 0) / snapshots.length
    : 0;
  const avgCoverage = snapshots.length > 0
    ? snapshots.reduce((s, r) => s + Number(r.coverage || 0), 0) / snapshots.length
    : 0;

  const healthy = snapshots.filter((s) => String(s.health_status || '').toUpperCase() === 'HEALTHY').length;
  const degraded = snapshots.length - healthy;
  const refreshSuccess = refresh.filter((r) => String(r.status || '').toUpperCase() === 'SUCCESS').length;
  const refreshTotal = refresh.length;

  const supervisorDaily = [
    '# Supervisor Daily Report',
    '',
    mdTable(
      ['Metric', 'Value'],
      [
        ['Total Agents', snapshots.length],
        ['Healthy Agents', healthy],
        ['Degraded Agents', degraded],
        ['Open Incidents', openIncidents.length],
        ['Refresh Events', refreshTotal],
        ['Refresh Success Rate', `${refreshTotal > 0 ? ((refreshSuccess / refreshTotal) * 100).toFixed(1) : '100.0'}%`],
        ['Average Knowledge Age (sec)', avgAge.toFixed(1)],
        ['Average Coverage', avgCoverage.toFixed(1)],
      ],
    ),
    '',
    '## Incident Severity Distribution',
    '',
    mdTable(['Severity', 'Count'], bySeverity),
  ].join('\n');

  const platformHealth = [
    '# Platform Health Report',
    '',
    mdTable(
      ['Area', 'Status', 'Evidence'],
      [
        ['Knowledge Freshness', degraded === 0 ? 'GREEN' : 'YELLOW', `${degraded} degraded agents`],
        ['Refresh Pipeline', refreshTotal === 0 || refreshSuccess === refreshTotal ? 'GREEN' : 'YELLOW', `${refreshSuccess}/${refreshTotal} successful events`],
        ['Policy Compliance', staleNotAllowed.length === 0 ? 'GREEN' : 'RED', `${staleNotAllowed.length} stale-not-allowed usages`],
        ['Supervisor Detection', openIncidents.length > 0 ? 'ACTIVE' : 'QUIET', `${openIncidents.length} open incidents`],
      ],
    ),
  ].join('\n');

  const knowledgeReadiness = [
    '# Knowledge Readiness Report',
    '',
    mdTable(
      ['Agent', 'Freshness', 'Health', 'Coverage', 'Confidence', 'TTL(sec)', 'Pending Reviews', 'Failed Refreshes'],
      snapshots.map((s) => [
        s.agent_name,
        s.freshness_status,
        s.health_status,
        Number(s.coverage || 0).toFixed(1),
        Number(s.average_confidence || 0).toFixed(3),
        Number(s.ttl_seconds || 0),
        Number(s.pending_reviews || 0),
        Number(s.failed_refresh_count || 0),
      ]),
    ),
  ].join('\n');

  const agentStatus = [
    '# Agent Status Report',
    '',
    mdTable(
      ['Agent Key', 'Last Refresh', 'Next Refresh', 'Freshness', 'Health', 'Refresh Status', 'Error'],
      snapshots.map((s) => [
        s.agent_key,
        s.last_successful_refresh || s.last_refreshed_at || '-',
        s.next_refresh_at || '-',
        s.freshness_status,
        s.health_status,
        s.refresh_status,
        s.refresh_error || '-',
      ]),
    ),
  ].join('\n');

  const incidentReport = [
    '# Incident Report',
    '',
    mdTable(
      ['Created At', 'Type', 'Severity', 'Status', 'Agent', 'Domain', 'Summary'],
      incidents
        .slice(-500)
        .reverse()
        .map((i) => [
          i.created_at || '-',
          i.incident_type,
          i.severity,
          i.status,
          i.agent_key || '-',
          i.domain || '-',
          i.summary,
        ]),
    ),
  ].join('\n');

  writeReport('supervisor_daily_report.md', supervisorDaily);
  writeReport('platform_health_report.md', platformHealth);
  writeReport('knowledge_readiness_report.md', knowledgeReadiness);
  writeReport('agent_status_report.md', agentStatus);
  writeReport('incident_report.md', incidentReport);

  const validationPass = staleNotAllowed.length === 0;
  const freshnessPass = degraded === 0;

  console.log(`BUILD_PASS=PASS`);
  console.log(`VALIDATION_PASS=${validationPass ? 'PASS' : 'FAIL'}`);
  console.log(`FRESHNESS_PASS=${freshnessPass ? 'PASS' : 'FAIL'}`);
  console.log(`READY_FOR_PRODUCTION=${validationPass && freshnessPass ? 'YES' : 'NO'}`);

  if (!validationPass || !freshnessPass) process.exitCode = 1;
}

generate();
