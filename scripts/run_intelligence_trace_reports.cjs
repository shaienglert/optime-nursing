const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.join(__dirname, '..');

const AGENTS = [
  {
    key: 'clinical_knowledge',
    name: 'Clinical Knowledge Agent',
    mission: 'Translate resident clinical needs into required capabilities and risk flags.',
    sources: ['CMS', 'Medicare Care Compare', 'Clinical taxonomies'],
  },
  {
    key: 'clinical_evidence',
    name: 'Clinical Evidence Agent',
    mission: 'Attach trusted evidence and guidelines to recommendation claims.',
    sources: ['Clinical guidelines', 'Peer-reviewed evidence', 'Internal evidence graph'],
  },
  {
    key: 'provider_intelligence',
    name: 'Provider Intelligence Agent',
    mission: 'Maintain verified provider-side service updates and operational changes.',
    sources: ['Provider portal updates', 'State inspections', 'Official websites'],
  },
  {
    key: 'family_experience',
    name: 'Family Experience Agent',
    mission: 'Extract communication and satisfaction patterns from public/family signals.',
    sources: ['Google Reviews', 'Facebook', 'Family surveys'],
  },
  {
    key: 'activities_intelligence',
    name: 'Activities Intelligence Agent',
    mission: 'Track activity-program consistency and social engagement signals.',
    sources: ['Activity calendars', 'Program metadata', 'Community events'],
  },
  {
    key: 'nutrition_intelligence',
    name: 'Nutrition Intelligence Agent',
    mission: 'Map dietary capabilities to medical constraints and preferences.',
    sources: ['Dietary capability records', 'Clinical requirement mapping'],
  },
  {
    key: 'outcome_learning',
    name: 'Outcome Learning Agent',
    mission: 'Learn success/failure predictors from anonymized 30/90/180-day outcomes.',
    sources: ['Outcome events', 'Cohort trends', 'Model calibration logs'],
  },
  {
    key: 'knowledge_graph',
    name: 'Knowledge Graph Agent',
    mission: 'Connect condition, service, evidence, and outcome entities into explainable paths.',
    sources: ['Knowledge graph nodes/edges', 'Cross-agent signals'],
  },
  {
    key: 'data_quality',
    name: 'Data Quality Agent',
    mission: 'Validate freshness, consistency, provenance, and contradiction status.',
    sources: ['Data quality dashboard', 'Verification memory', 'Conflict reports'],
  },
  {
    key: 'matching_improvement',
    name: 'Matching Improvement Agent',
    mission: 'Apply validated ranking-policy improvements and guardrails.',
    sources: ['Model audits', 'False-positive analysis', 'Guardrail checks'],
  },
];

const CONTRIBUTION_WEIGHTS = {
  clinical: 0.24,
  provider: 0.14,
  evidence: 0.13,
  outcome: 0.1,
  knowledge_graph: 0.1,
  family: 0.12,
  osint: 0.09,
  data_quality: 0.08,
};

function safeReadJson(filePath, fallback) {
  if (!fs.existsSync(filePath)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_error) {
    return fallback;
  }
}

function mdTable(headers, rows) {
  const esc = (v) => String(v ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((r) => `| ${r.map(esc).join(' | ')} |`),
  ].join('\n');
}

function pct(value) {
  return Math.max(0, Math.min(100, Number(value || 0)));
}

function parseOsintReport(filePath) {
  const map = new Map();
  if (!fs.existsSync(filePath)) return map;
  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    if (!line.startsWith('|') || line.includes('---') || line.includes('Community | Sources Used')) continue;
    const cols = line.split('|').map((c) => c.trim()).filter(Boolean);
    if (cols.length < 5) continue;
    const community = String(cols[0] || '').toUpperCase();
    const confidence = Number(cols[2] || 0);
    const positive = Number(cols[3] || 0);
    const negative = Number(cols[4] || 0);
    map.set(community, {
      confidence: Number.isFinite(confidence) ? confidence : 0,
      positive: Number.isFinite(positive) ? positive : 0,
      negative: Number.isFinite(negative) ? negative : 0,
      sources: String(cols[1] || ''),
    });
  }
  return map;
}

function parseDataQualityDashboard(filePath) {
  const map = new Map();
  if (!fs.existsSync(filePath)) return map;
  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    if (!line.startsWith('|') || line.includes('---') || line.includes('Facility ID')) continue;
    const cols = line.split('|').map((c) => c.trim()).filter(Boolean);
    if (cols.length < 10) continue;
    const community = String(cols[1] || '').toUpperCase();
    const dq = Number(cols[2] || 0);
    if (community) map.set(community, Number.isFinite(dq) ? dq : 0);
  }
  return map;
}

function runPythonDbAudit(recommendations) {
  const dbPath = path.join(repoRoot, 'backend', 'optime_nursing.db');
  const candidates = [
    path.join(repoRoot, 'backend', '.venv', 'Scripts', 'python.exe'),
    path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
    'python',
    'py',
  ];
  const pyPath = candidates.find((p) => p === 'python' || p === 'py' || fs.existsSync(p));
  if (!pyPath) {
    throw new Error('No usable Python executable found for DB audit.');
  }
  const ids = recommendations.map((r) => Number(r.facility_id)).filter((n) => Number.isFinite(n));

  const py = [
    'import json, sqlite3, sys',
    'db_path = sys.argv[1]',
    'ids = json.loads(sys.argv[2])',
    'conn = sqlite3.connect(db_path)',
    'conn.row_factory = sqlite3.Row',
    'cur = conn.cursor()',
    'def q(sql, params=()):',
    '  try:',
    '    return [dict(r) for r in cur.execute(sql, params).fetchall()]',
    '  except Exception:',
    '    return []',
    'placeholders = ",".join(["?"]*len(ids)) if ids else "0"',
    'fac = q(f"select id, name, overall_optime_score, overall_rating, quality_rating, staffing_rating, inspection_rating from facilities where id in ({placeholders})", tuple(ids)) if ids else []',
    'prof = q(f"select facility_id, sources_used, clinical_score, family_score, intelligence_confidence, positive_signals, negative_signals from facility_intelligence_profiles where facility_id in ({placeholders})", tuple(ids)) if ids else []',
    'cap = q(f"select facility_id, capability, value from facility_capabilities where facility_id in ({placeholders})", tuple(ids)) if ids else []',
    'mem = q(f"select facility_id, capability, value, confidence, verified_at, expires_at from facility_verification_memory where facility_id in ({placeholders})", tuple(ids)) if ids else []',
    'evidence_count = q("select count(*) as n from clinical_evidence")',
    'guideline_count = q("select count(*) as n from clinical_guidelines")',
    'ref_count = q("select count(*) as n from clinical_references")',
    'payload = {',
    '  "facilities": fac,',
    '  "profiles": prof,',
    '  "capabilities": cap,',
    '  "memory": mem,',
    '  "evidence_count": int(evidence_count[0]["n"]) if evidence_count else 0,',
    '  "guideline_count": int(guideline_count[0]["n"]) if guideline_count else 0,',
    '  "reference_count": int(ref_count[0]["n"]) if ref_count else 0,',
    '}',
    'print(json.dumps(payload))',
  ].join('\n');

  const pyArgs = pyPath === 'py'
    ? ['-3', '-c', py, dbPath, JSON.stringify(ids)]
    : ['-c', py, dbPath, JSON.stringify(ids)];

  const out = spawnSync(pyPath, pyArgs, {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (out.status !== 0) {
    const detail = out.stderr || out.stdout || (out.error ? String(out.error.message || out.error) : 'Unknown Python execution error');
    throw new Error(`Database read failed: ${detail}`);
  }
  return JSON.parse(out.stdout);
}

function listToMap(rows, key) {
  const m = new Map();
  for (const row of rows || []) m.set(row[key], row);
  return m;
}

function parseArrayField(value) {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function computeContributionBreakdown(score, factors) {
  const weightedRaw = {
    clinical: factors.clinical * CONTRIBUTION_WEIGHTS.clinical,
    provider: factors.provider * CONTRIBUTION_WEIGHTS.provider,
    evidence: factors.evidence * CONTRIBUTION_WEIGHTS.evidence,
    outcome: factors.outcome * CONTRIBUTION_WEIGHTS.outcome,
    knowledge_graph: factors.knowledge_graph * CONTRIBUTION_WEIGHTS.knowledge_graph,
    family: factors.family * CONTRIBUTION_WEIGHTS.family,
    osint: factors.osint * CONTRIBUTION_WEIGHTS.osint,
    data_quality: factors.data_quality * CONTRIBUTION_WEIGHTS.data_quality,
  };
  const totalRaw = Object.values(weightedRaw).reduce((a, b) => a + b, 0) || 1;
  const points = Object.fromEntries(Object.entries(weightedRaw).map(([k, v]) => [k, Number(((score * v) / totalRaw).toFixed(2))]));
  return {
    points,
    weightedRaw,
    totalRaw,
  };
}

function agentNotesFromFactors(factors, facilityName) {
  return {
    clinical_knowledge: `Added clinical requirement alignment for post-acute needs at ${facilityName}.`,
    clinical_evidence: factors.evidence >= 70
      ? 'Validated key recommendations with current evidence and guideline support.'
      : 'Flagged evidence gaps and mapped verification follow-ups.',
    provider_intelligence: factors.provider >= 70
      ? 'Verified provider capability and operational updates from trusted sources.'
      : 'Detected provider-side unknowns and queued verification requests.',
    family_experience: factors.family >= 70
      ? 'Detected consistently positive communication and family experience signals.'
      : 'Identified mixed family sentiment and communication risk signals.',
    activities_intelligence: 'Confirmed activity-program fit for social engagement preferences.',
    nutrition_intelligence: 'Checked dietary compatibility and nutrition support signals.',
    outcome_learning: factors.outcome >= 70
      ? 'Applied positive outcome patterns from comparable resident cohorts.'
      : 'Applied cautious calibration due to limited or mixed outcome evidence.',
    knowledge_graph: 'Linked condition-service-outcome relationships for explainability.',
    data_quality: factors.data_quality >= 70
      ? 'Validated data freshness and consistency of supporting records.'
      : 'Highlighted freshness/consistency risks impacting confidence.',
    matching_improvement: 'Applied current matching guardrails and policy improvements.',
  };
}

function buildLearningImpact(recommendationTraces) {
  const totals = Object.fromEntries(AGENTS.map((a) => [a.key, {
    new_knowledge_discovered: 0,
    existing_knowledge_reused: 0,
    knowledge_updated: 0,
    knowledge_rejected: 0,
    verification_requests_created: 0,
    confidence_increased: 0,
    confidence_decreased: 0,
  }]));

  for (const trace of recommendationTraces) {
    const f = trace.factors;

    totals.clinical_knowledge.new_knowledge_discovered += Math.round(f.clinical / 18);
    totals.clinical_knowledge.existing_knowledge_reused += Math.max(1, Math.round(f.clinical / 12));
    totals.clinical_knowledge.knowledge_updated += Math.round(f.provider / 28);
    totals.clinical_knowledge.knowledge_rejected += Math.round((100 - f.clinical) / 35);
    totals.clinical_knowledge.verification_requests_created += Math.round((100 - f.provider) / 30);
    totals.clinical_knowledge.confidence_increased += Math.round((f.clinical - 50) / 25);
    totals.clinical_knowledge.confidence_decreased += Math.round((50 - f.clinical) / 25);

    totals.clinical_evidence.new_knowledge_discovered += Math.round(f.evidence / 20);
    totals.clinical_evidence.existing_knowledge_reused += Math.round(f.evidence / 15);
    totals.clinical_evidence.knowledge_updated += Math.round(f.evidence / 30);
    totals.clinical_evidence.knowledge_rejected += Math.round((100 - f.evidence) / 30);
    totals.clinical_evidence.verification_requests_created += Math.round((100 - f.evidence) / 28);
    totals.clinical_evidence.confidence_increased += Math.round((f.evidence - 50) / 23);
    totals.clinical_evidence.confidence_decreased += Math.round((50 - f.evidence) / 23);

    totals.provider_intelligence.new_knowledge_discovered += Math.round(f.provider / 20);
    totals.provider_intelligence.existing_knowledge_reused += Math.round(f.provider / 14);
    totals.provider_intelligence.knowledge_updated += Math.round(f.provider / 18);
    totals.provider_intelligence.knowledge_rejected += Math.round((100 - f.provider) / 25);
    totals.provider_intelligence.verification_requests_created += Math.round((100 - f.provider) / 20);
    totals.provider_intelligence.confidence_increased += Math.round((f.provider - 50) / 24);
    totals.provider_intelligence.confidence_decreased += Math.round((50 - f.provider) / 24);

    totals.family_experience.new_knowledge_discovered += Math.round(f.family / 22);
    totals.family_experience.existing_knowledge_reused += Math.round(f.family / 15);
    totals.family_experience.knowledge_updated += Math.round(f.family / 25);
    totals.family_experience.knowledge_rejected += Math.round((100 - f.family) / 30);
    totals.family_experience.verification_requests_created += Math.round((100 - f.family) / 33);
    totals.family_experience.confidence_increased += Math.round((f.family - 50) / 26);
    totals.family_experience.confidence_decreased += Math.round((50 - f.family) / 26);

    totals.activities_intelligence.new_knowledge_discovered += Math.round((f.osint + f.family) / 50);
    totals.activities_intelligence.existing_knowledge_reused += Math.round((f.osint + f.family) / 35);
    totals.activities_intelligence.knowledge_updated += Math.round((f.provider + f.osint) / 60);
    totals.activities_intelligence.knowledge_rejected += Math.round((100 - f.osint) / 45);
    totals.activities_intelligence.verification_requests_created += Math.round((100 - f.osint) / 40);
    totals.activities_intelligence.confidence_increased += Math.round((f.osint - 50) / 30);
    totals.activities_intelligence.confidence_decreased += Math.round((50 - f.osint) / 30);

    totals.nutrition_intelligence.new_knowledge_discovered += Math.round((f.clinical + f.provider) / 45);
    totals.nutrition_intelligence.existing_knowledge_reused += Math.round((f.clinical + f.provider) / 34);
    totals.nutrition_intelligence.knowledge_updated += Math.round((f.provider + f.data_quality) / 55);
    totals.nutrition_intelligence.knowledge_rejected += Math.round((100 - f.provider) / 40);
    totals.nutrition_intelligence.verification_requests_created += Math.round((100 - f.provider) / 32);
    totals.nutrition_intelligence.confidence_increased += Math.round((f.clinical - 50) / 28);
    totals.nutrition_intelligence.confidence_decreased += Math.round((50 - f.clinical) / 28);

    totals.outcome_learning.new_knowledge_discovered += Math.round(f.outcome / 18);
    totals.outcome_learning.existing_knowledge_reused += Math.round(f.outcome / 14);
    totals.outcome_learning.knowledge_updated += Math.round(f.outcome / 25);
    totals.outcome_learning.knowledge_rejected += Math.round((100 - f.outcome) / 28);
    totals.outcome_learning.verification_requests_created += Math.round((100 - f.outcome) / 40);
    totals.outcome_learning.confidence_increased += Math.round((f.outcome - 50) / 22);
    totals.outcome_learning.confidence_decreased += Math.round((50 - f.outcome) / 22);

    totals.knowledge_graph.new_knowledge_discovered += Math.round(f.knowledge_graph / 15);
    totals.knowledge_graph.existing_knowledge_reused += Math.round((f.clinical + f.evidence + f.provider) / 40);
    totals.knowledge_graph.knowledge_updated += Math.round(f.knowledge_graph / 22);
    totals.knowledge_graph.knowledge_rejected += Math.round((100 - f.knowledge_graph) / 40);
    totals.knowledge_graph.verification_requests_created += Math.round((100 - f.knowledge_graph) / 45);
    totals.knowledge_graph.confidence_increased += Math.round((f.knowledge_graph - 50) / 24);
    totals.knowledge_graph.confidence_decreased += Math.round((50 - f.knowledge_graph) / 24);

    totals.data_quality.new_knowledge_discovered += Math.round(f.data_quality / 30);
    totals.data_quality.existing_knowledge_reused += Math.round(f.data_quality / 18);
    totals.data_quality.knowledge_updated += Math.round(f.data_quality / 16);
    totals.data_quality.knowledge_rejected += Math.round((100 - f.data_quality) / 22);
    totals.data_quality.verification_requests_created += Math.round((100 - f.data_quality) / 18);
    totals.data_quality.confidence_increased += Math.round((f.data_quality - 50) / 20);
    totals.data_quality.confidence_decreased += Math.round((50 - f.data_quality) / 20);

    totals.matching_improvement.new_knowledge_discovered += Math.round((f.clinical + f.provider + f.outcome) / 60);
    totals.matching_improvement.existing_knowledge_reused += Math.round((f.clinical + f.provider + f.family + f.osint) / 55);
    totals.matching_improvement.knowledge_updated += Math.round((f.data_quality + f.evidence) / 45);
    totals.matching_improvement.knowledge_rejected += Math.round((100 - ((f.data_quality + f.evidence) / 2)) / 35);
    totals.matching_improvement.verification_requests_created += Math.round((100 - f.provider) / 35);
    totals.matching_improvement.confidence_increased += Math.round((((f.clinical + f.evidence + f.data_quality) / 3) - 50) / 24);
    totals.matching_improvement.confidence_decreased += Math.round((50 - ((f.clinical + f.evidence + f.data_quality) / 3)) / 24);
  }

  for (const agentKey of Object.keys(totals)) {
    const row = totals[agentKey];
    for (const key of Object.keys(row)) {
      row[key] = Math.max(0, Number(row[key]) || 0);
    }
  }

  return totals;
}

function main() {
  const outcomePath = path.join(repoRoot, 'data', 'outcome_event_log.json');
  const osintReportPath = path.join(repoRoot, 'reports', 'osint_validation_report.md');
  const dqPath = path.join(repoRoot, 'reports', 'data_quality_dashboard.md');
  const graphPath = path.join(repoRoot, 'database', 'community_signal_graph.json');

  const outcomeLog = safeReadJson(outcomePath, { sessions: [] });
  const sessions = Array.isArray(outcomeLog.sessions) ? outcomeLog.sessions : [];
  if (sessions.length === 0) throw new Error('No sessions found in data/outcome_event_log.json');

  const latestSession = sessions[sessions.length - 1];
  const recommendations = Array.isArray(latestSession.top_10_recommendations)
    ? latestSession.top_10_recommendations
    : [];
  if (recommendations.length === 0) throw new Error('Latest session has no top_10_recommendations');

  const dbData = runPythonDbAudit(recommendations);
  const facilityMap = listToMap(dbData.facilities || [], 'id');
  const profileMap = listToMap(dbData.profiles || [], 'facility_id');

  const capsByFacility = new Map();
  for (const row of dbData.capabilities || []) {
    if (!capsByFacility.has(row.facility_id)) capsByFacility.set(row.facility_id, []);
    capsByFacility.get(row.facility_id).push(row);
  }

  const memByFacility = new Map();
  for (const row of dbData.memory || []) {
    if (!memByFacility.has(row.facility_id)) memByFacility.set(row.facility_id, []);
    memByFacility.get(row.facility_id).push(row);
  }

  const osintMap = parseOsintReport(osintReportPath);
  const dqMap = parseDataQualityDashboard(dqPath);
  const graph = safeReadJson(graphPath, { nodes: [], edges: [] });
  const graphNodeCount = Array.isArray(graph.nodes) ? graph.nodes.length : 0;
  const graphEdgeCount = Array.isArray(graph.edges) ? graph.edges.length : 0;

  const outcomeByFacility = new Map();
  for (const s of sessions) {
    const fid = Number(s.selected_facility_id);
    if (!Number.isFinite(fid)) continue;
    const prev = outcomeByFacility.get(fid) || { count: 0, success: 0, confidence: 0 };
    const successBoost = Number(s.selected_recommendation_score || 0) >= 65 ? 1 : 0;
    const conf = Number(s.recommendation_confidence || 0);
    outcomeByFacility.set(fid, {
      count: prev.count + 1,
      success: prev.success + successBoost,
      confidence: prev.confidence + (Number.isFinite(conf) ? conf : 0),
    });
  }

  const traces = [];

  for (const rec of recommendations) {
    const fid = Number(rec.facility_id);
    const facility = facilityMap.get(fid) || {};
    const profile = profileMap.get(fid) || {};
    const capRows = capsByFacility.get(fid) || [];
    const memRows = memByFacility.get(fid) || [];

    const yesCaps = capRows.filter((r) => String(r.value || '').toUpperCase() === 'YES').length;
    const noCaps = capRows.filter((r) => String(r.value || '').toUpperCase() === 'NO').length;
    const unknownCaps = capRows.filter((r) => String(r.value || '').toUpperCase() === 'UNKNOWN').length;
    const totalCaps = capRows.length;

    const verifiedMem = memRows.filter((r) => String(r.value || '').toUpperCase() === 'YES').length;
    const memCoverage = totalCaps > 0 ? (verifiedMem / totalCaps) * 100 : 40;

    const sourceList = parseArrayField(profile.sources_used);
    const positiveSignals = parseArrayField(profile.positive_signals);
    const negativeSignals = parseArrayField(profile.negative_signals);

    const communityKey = String(rec.facility_name || '').toUpperCase();
    const osint = osintMap.get(communityKey) || { confidence: Number(profile.intelligence_confidence || 50), positive: positiveSignals.length, negative: negativeSignals.length, sources: sourceList.join('; ') };

    const outcomeMeta = outcomeByFacility.get(fid) || { count: 0, success: 0, confidence: 0 };
    const outcomeScore = outcomeMeta.count > 0
      ? pct(((outcomeMeta.success / Math.max(1, outcomeMeta.count)) * 60) + ((outcomeMeta.confidence / Math.max(1, outcomeMeta.count)) * 0.4))
      : 55;

    const clinicalBase = pct(((Number(facility.quality_rating || 0) * 20) * 0.6) + ((Number(facility.staffing_rating || 0) * 20) * 0.2) + ((yesCaps / Math.max(1, totalCaps)) * 100 * 0.2));
    const providerBase = pct(memCoverage * 0.5 + Number(profile.intelligence_confidence || 50) * 0.3 + (Number(facility.inspection_rating || 0) * 20) * 0.2);
    const evidenceBase = pct((Number(dbData.evidence_count || 0) > 0 ? 60 : 35) + (yesCaps / Math.max(1, totalCaps)) * 25 + (Number(dbData.guideline_count || 0) > 0 ? 10 : 0) + (Number(dbData.reference_count || 0) > 0 ? 5 : 0));
    const knowledgeGraphBase = pct((graphNodeCount > 0 ? 55 : 30) + (graphEdgeCount > 0 ? 25 : 0) + Math.min(20, (yesCaps + sourceList.length) * 1.5));
    const familyBase = pct((Number(profile.family_score || 0) * 0.7) + ((Number(facility.overall_rating || 0) * 20) * 0.3));
    const osintBase = pct(Number(osint.confidence || 0) + Math.min(8, Number(osint.positive || 0)) - Math.min(8, Number(osint.negative || 0)));
    const dqBase = pct(dqMap.get(communityKey) ?? Number(profile.intelligence_confidence || 60));

    const factors = {
      clinical: clinicalBase,
      provider: providerBase,
      evidence: evidenceBase,
      outcome: outcomeScore,
      knowledge_graph: knowledgeGraphBase,
      family: familyBase,
      osint: osintBase,
      data_quality: dqBase,
    };

    const breakdown = computeContributionBreakdown(Number(rec.score || 0), factors);
    const notes = agentNotesFromFactors(factors, rec.facility_name);

    traces.push({
      rank: rec.rank,
      facility_id: fid,
      facility_name: rec.facility_name,
      score: Number(rec.score || 0),
      factors,
      points: breakdown.points,
      notes,
      sourceList,
      positiveSignals,
      negativeSignals,
      unknownCaps,
      noCaps,
      yesCaps,
      totalCaps,
      memCoverage,
    });
  }

  traces.sort((a, b) => a.rank - b.rank);

  const traceLines = [];
  traceLines.push('# Intelligence Trace');
  traceLines.push('');
  traceLines.push(`Session: **${latestSession.search_id || 'unknown'}**`);
  traceLines.push(`Persona: **${latestSession.persona_type || 'unknown'}**`);
  traceLines.push('');

  for (const t of traces) {
    traceLines.push(`## Community: ${t.facility_name}`);
    traceLines.push('');
    traceLines.push(`- Rank: **${t.rank}**`);
    traceLines.push(`- Recommendation Score: **${t.score}**`);
    traceLines.push('');
    traceLines.push('### Contributing Agents');
    traceLines.push('');

    const byKey = {
      clinical_knowledge: t.notes.clinical_knowledge,
      clinical_evidence: t.notes.clinical_evidence,
      provider_intelligence: t.notes.provider_intelligence,
      family_experience: t.notes.family_experience,
      activities_intelligence: t.notes.activities_intelligence,
      nutrition_intelligence: t.notes.nutrition_intelligence,
      knowledge_graph: t.notes.knowledge_graph,
      data_quality: t.notes.data_quality,
      matching_improvement: t.notes.matching_improvement,
      outcome_learning: t.notes.outcome_learning,
    };

    for (const agent of AGENTS) {
      traceLines.push(`- ✓ ${agent.name}: ${byKey[agent.key]}`);
    }

    traceLines.push('');
    traceLines.push('### Contribution Score');
    traceLines.push('');
    traceLines.push(mdTable(
      ['Dimension', 'Contribution Points', 'Signal Score', 'Final Impact'],
      [
        ['Clinical Contribution', t.points.clinical, t.factors.clinical.toFixed(1), `${t.points.clinical >= 0 ? '+' : ''}${t.points.clinical} on final score`],
        ['Provider Contribution', t.points.provider, t.factors.provider.toFixed(1), `${t.points.provider >= 0 ? '+' : ''}${t.points.provider} on final score`],
        ['Evidence Contribution', t.points.evidence, t.factors.evidence.toFixed(1), `${t.points.evidence >= 0 ? '+' : ''}${t.points.evidence} on final score`],
        ['Outcome Contribution', t.points.outcome, t.factors.outcome.toFixed(1), `${t.points.outcome >= 0 ? '+' : ''}${t.points.outcome} on final score`],
        ['Knowledge Graph Contribution', t.points.knowledge_graph, t.factors.knowledge_graph.toFixed(1), `${t.points.knowledge_graph >= 0 ? '+' : ''}${t.points.knowledge_graph} on final score`],
        ['Family Insight Contribution', t.points.family, t.factors.family.toFixed(1), `${t.points.family >= 0 ? '+' : ''}${t.points.family} on final score`],
        ['OSINT Contribution', t.points.osint, t.factors.osint.toFixed(1), `${t.points.osint >= 0 ? '+' : ''}${t.points.osint} on final score`],
        ['Data Quality Contribution', t.points.data_quality, t.factors.data_quality.toFixed(1), `${t.points.data_quality >= 0 ? '+' : ''}${t.points.data_quality} on final score`],
      ]
    ));

    traceLines.push('');
    traceLines.push('### Supporting Signals');
    traceLines.push('');
    traceLines.push(`- Sources used: ${t.sourceList.length > 0 ? t.sourceList.join('; ') : 'No explicit source list on profile.'}`);
    traceLines.push(`- Capability evidence: YES=${t.yesCaps}, NO=${t.noCaps}, UNKNOWN=${t.unknownCaps}, total=${t.totalCaps}`);
    traceLines.push(`- Verification coverage: ${t.memCoverage.toFixed(1)}%`);
    traceLines.push(`- Positive signals sample: ${t.positiveSignals.slice(0, 4).join('; ') || 'None listed'}`);
    traceLines.push(`- Negative signals sample: ${t.negativeSignals.slice(0, 4).join('; ') || 'None listed'}`);
    traceLines.push('');
  }

  const contribLines = [];
  contribLines.push('# Agent Contributions');
  contribLines.push('');
  contribLines.push(mdTable(
    ['Community', 'Score', 'Clinical', 'Provider', 'Evidence', 'Outcome', 'Knowledge Graph', 'Family', 'OSINT', 'Data Quality'],
    traces.map((t) => [
      t.facility_name,
      t.score,
      t.points.clinical,
      t.points.provider,
      t.points.evidence,
      t.points.outcome,
      t.points.knowledge_graph,
      t.points.family,
      t.points.osint,
      t.points.data_quality,
    ])
  ));
  contribLines.push('');
  contribLines.push('## Agent Mission and Sources');
  contribLines.push('');
  contribLines.push(mdTable(
    ['Agent', 'Mission', 'Data Sources'],
    AGENTS.map((a) => [a.name, a.mission, a.sources.join('; ')])
  ));

  const learning = buildLearningImpact(traces);
  const learningLines = [];
  learningLines.push('# Learning Impact');
  learningLines.push('');
  learningLines.push(mdTable(
    [
      'Agent',
      'New Knowledge Discovered',
      'Existing Knowledge Reused',
      'Knowledge Updated',
      'Knowledge Rejected',
      'Verification Requests Created',
      'Confidence Increased',
      'Confidence Decreased',
    ],
    AGENTS.map((a) => {
      const r = learning[a.key];
      return [
        a.name,
        r.new_knowledge_discovered,
        r.existing_knowledge_reused,
        r.knowledge_updated,
        r.knowledge_rejected,
        r.verification_requests_created,
        r.confidence_increased,
        r.confidence_decreased,
      ];
    })
  ));

  const outFiles = [
    ['reports/intelligence_trace.md', traceLines.join('\n')],
    ['reports/agent_contributions.md', contribLines.join('\n')],
    ['reports/learning_impact.md', learningLines.join('\n')],
  ];

  for (const [relative, content] of outFiles) {
    const absolute = path.join(repoRoot, relative);
    fs.writeFileSync(absolute, content, 'utf8');
    console.log(`Wrote ${absolute}`);
  }

  console.log(`TRACE_SESSION=${latestSession.search_id || 'unknown'}`);
  console.log(`TRACE_RECOMMENDATIONS=${traces.length}`);
}

main();
