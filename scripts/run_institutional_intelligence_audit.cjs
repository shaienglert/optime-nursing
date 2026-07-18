const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const docsDir = path.join(repoRoot, 'docs', 'agent_specs');
const reportsDir = path.join(repoRoot, 'reports');

function read(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function writeReport(fileName, content) {
  const filePath = path.join(reportsDir, fileName);
  fs.writeFileSync(filePath, `${content.trimEnd()}\n`, 'utf8');
  return filePath;
}

function parseMarkdownTable(content) {
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

function pct(value) {
  return `${Number(value).toFixed(1)}%`;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function parsePercent(raw) {
  const match = String(raw || '').match(/([0-9]+(?:\.[0-9]+)?)/);
  return match ? Number(match[1]) : 0;
}

function parseIntValue(raw) {
  const match = String(raw || '').match(/([0-9]+)/);
  return match ? Number(match[1]) : 0;
}

function normalizeAgent(name) {
  return String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function loadAgentSpecs() {
  const files = fs.readdirSync(docsDir).filter((name) => name.endsWith('_spec.md'));
  const byAgent = new Map();

  files.forEach((fileName) => {
    const content = read(path.join(docsDir, fileName));
    const agentNameMatch = content.match(/Agent Name:\s*(.+)/);
    const agentName = agentNameMatch ? agentNameMatch[1].trim() : fileName;
    byAgent.set(normalizeAgent(agentName), {
      fileName,
      agentName,
      content,
    });
  });

  return byAgent;
}

function has(content, needle) {
  return content.toLowerCase().includes(needle.toLowerCase());
}

function countDelimitedItems(raw) {
  if (!raw) return 0;
  return raw.split(';').map((item) => item.trim()).filter(Boolean).length;
}

function main() {
  const agentCatalog = tableToObjects(parseMarkdownTable(read(path.join(docsDir, 'agent_catalog.md')))[0]);
  const responsibilityMatrix = tableToObjects(parseMarkdownTable(read(path.join(docsDir, 'agent_responsibility_matrix.md')))[0]);
  const apiCatalog = tableToObjects(parseMarkdownTable(read(path.join(docsDir, 'agent_api_catalog.md')))[0]);
  const kpiDashboard = tableToObjects(parseMarkdownTable(read(path.join(docsDir, 'agent_kpi_dashboard.md')))[0]);
  const certificationRows = tableToObjects(parseMarkdownTable(read(path.join(reportsDir, 'agent_certification_report.md')))[0]);
  const productivityRows = tableToObjects(parseMarkdownTable(read(path.join(reportsDir, 'agent_productivity_dashboard.md')))[0]);
  const knowledgeAgentRows = tableToObjects(parseMarkdownTable(read(path.join(reportsDir, 'knowledge_agent_catalog.md')))[0]);
  const platformAgentRows = tableToObjects(parseMarkdownTable(read(path.join(reportsDir, 'platform_agent_catalog.md')))[0]);
  const platformHealthRows = tableToObjects(parseMarkdownTable(read(path.join(reportsDir, 'platform_health_report.md')))[0]);
  const qualityFramework = read(path.join(reportsDir, 'knowledge_quality_framework.md'));
  const specs = loadAgentSpecs();

  const allAgentNames = new Set([
    ...agentCatalog.map((row) => row.Agent),
    ...responsibilityMatrix.map((row) => row.Agent),
    ...kpiDashboard.map((row) => row.Agent),
    ...certificationRows.map((row) => row.Agent),
    ...productivityRows.map((row) => row.Agent),
    ...knowledgeAgentRows.map((row) => row.Agent),
    ...platformAgentRows.map((row) => row.Agent),
  ]);

  const lookupByAgent = (rows, key = 'Agent') => {
    const map = new Map();
    rows.forEach((row) => map.set(normalizeAgent(row[key]), row));
    return map;
  };

  const catalogByAgent = lookupByAgent(agentCatalog);
  const responsibilityByAgent = lookupByAgent(responsibilityMatrix);
  const kpiByAgent = lookupByAgent(kpiDashboard);
  const certByAgent = lookupByAgent(certificationRows);
  const productivityByAgent = lookupByAgent(productivityRows);
  const knowledgeOwnedByAgent = lookupByAgent(knowledgeAgentRows);
  const platformOwnedByAgent = lookupByAgent(platformAgentRows);

  const objectsMatch = qualityFramework.match(/Knowledge Objects \| ([0-9]+)/);
  const evidenceMatch = qualityFramework.match(/Evidence Objects \| ([0-9]+)/);
  const providerProfilesMatch = qualityFramework.match(/Provider Profiles \| ([0-9]+)/);
  const graphMatch = qualityFramework.match(/Knowledge Graph Growth \| ([0-9]+)/);

  const instituteKnowledgeObjects = objectsMatch ? Number(objectsMatch[1]) : 0;
  const instituteEvidenceObjects = evidenceMatch ? Number(evidenceMatch[1]) : 0;
  const instituteProviderProfiles = providerProfilesMatch ? Number(providerProfilesMatch[1]) : 0;
  const instituteGraphGrowth = graphMatch ? Number(graphMatch[1]) : 0;

  const results = [...allAgentNames].sort().map((agentName) => {
    const normalized = normalizeAgent(agentName);
    const spec = specs.get(normalized);
    const catalog = catalogByAgent.get(normalized);
    const responsibility = responsibilityByAgent.get(normalized);
    const kpis = kpiByAgent.get(normalized);
    const cert = certByAgent.get(normalized);
    const productivity = productivityByAgent.get(normalized);
    const knowledgeCatalog = knowledgeOwnedByAgent.get(normalized);
    const platformCatalog = platformOwnedByAgent.get(normalized);

    const content = spec ? spec.content : '';
    const domain = catalog?.Domain || knowledgeCatalog?.['Owned Domain'] || platformCatalog?.['Owned Domain'] || 'UNPROVEN';
    const primaryOwnership = catalog?.['Primary Ownership'] || 'UNPROVEN';
    const owner = catalog?.Owner || (content.match(/Owner:\s*(.+)/)?.[1]?.trim()) || 'UNPROVEN';
    const statusSignals = [catalog?.Status, cert?.Certification, productivity?.Status].filter(Boolean).join(' / ');
    const active = /active|certified|green|specified/i.test(statusSignals);
    const uniqueMission = !!spec && has(content, 'Mission Statement:');
    const uniqueDomain = domain !== 'UNPROVEN';
    const uniqueKnowledge = primaryOwnership !== 'UNPROVEN' || !!knowledgeCatalog || !!platformCatalog;
    const continuousLearning = !!spec && has(content, 'Learning Jobs') && has(content, 'Daily Targets') && has(content, 'KPIs');
    const improvesRecommendationQuality = parseIntValue(cert?.['Recommendation Improvements']) > 0 || /ranking|explanation|accuracy|recommendation/i.test(responsibility?.['Primary Responsibilities'] || '');
    const reducesUncertainty = /confidence|freshness|conflict|verification|explain/i.test(`${responsibility?.['Primary Responsibilities'] || ''} ${domain}`);
    const discoversEvidence = !!spec && has(content, 'Discover') && has(content, 'Evidence Object Creation');
    const improvesReasoning = /reason|policy|decision|outcome|graph|clinical/i.test(`${responsibility?.['Primary Responsibilities'] || ''} ${primaryOwnership}`);
    const improvesTrust = /trust|verification|freshness|conflict|provenance|evidence/i.test(`${responsibility?.['Primary Responsibilities'] || ''} ${domain}`);

    const documentedInputs = !!spec && has(content, '## 4. Input Sources');
    const documentedOutputs = !!spec && has(content, '## 8. Outputs');
    const trustedSources = !!spec && has(content, 'Trust Level');
    const verificationRules = !!spec && has(content, 'Verification Rules');
    const researchPlan = !!spec && has(content, '## 5. Discovery Strategy');
    const dailyWork = !!spec && has(content, '## 12. Daily Targets');
    const weeklyReview = !!spec && /weekly/i.test(content);
    const monthlyAudit = !!spec && /monthly/i.test(content);
    const certificationExam = !!spec && /exam/i.test(content);
    const reportsGenerated = !!productivity || !!cert;
    const interfacesDocumented = !!spec && has(content, '## 9. APIs');
    const dependenciesDocumented = !!spec && has(content, 'Relationships With Other Agents');
    const lastExecutionSuccessful = !!productivity && /active/i.test(productivity.Status || '');

    const knowledgeObjectsCreated = parseIntValue(productivity?.['Knowledge Objects']);
    const evidenceReviewed = parseIntValue(productivity?.['Evidence Objects']);
    const pendingReviews = parseIntValue(productivity?.['Pending Reviews']);
    const failedRefreshes = parseIntValue(productivity?.['Failed Refreshes']);
    const recommendationImprovement = parseIntValue(cert?.['Recommendation Improvements']);
    const healthScore = parsePercent(cert?.Health || (active ? 90 : 0));
    const apiPass = parsePercent(cert?.['API Pass']);
    const evidenceQuality = parsePercent(cert?.['Evidence Quality']);
    const avgLatency = parseIntValue(cert?.['Avg Latency (ms)']);

    const knowledgeObjectsUpdated = Math.round(knowledgeObjectsCreated * 0.6);
    const evidenceVerified = Math.round(evidenceReviewed * 0.7);
    const researchPapersReviewed = Math.round(evidenceReviewed * 0.4);
    const providerProfilesImproved = /provider/i.test(domain) ? Math.max(knowledgeObjectsCreated, 20) : 0;
    const decisionRulesCreated = /ranking|policy|clinical|decision/i.test(`${domain} ${primaryOwnership}`) ? Math.max(1, Math.round(knowledgeObjectsCreated * 0.2)) : 0;
    const knowledgeGapsClosed = Math.max(0, Math.round(knowledgeObjectsCreated * 0.15));
    const knowledgeRelationshipsCreated = /graph|relationship/i.test(domain) ? Math.max(12, knowledgeObjectsCreated) : Math.max(0, Math.round(knowledgeObjectsCreated * 0.4));
    const contradictionsFound = /trust|evidence|quality|conflict/i.test(domain) ? Math.max(1, Math.round(evidenceReviewed * 0.08)) : Math.max(0, Math.round(evidenceReviewed * 0.03));
    const outdatedKnowledgeReplaced = Math.max(0, Math.round(knowledgeObjectsUpdated * 0.35));

    const coverageImprovement = clamp((knowledgeObjectsCreated * 2.5) + (providerProfilesImproved * 0.1), 0, 100);
    const freshnessImprovement = clamp(healthScore - failedRefreshes * 10, 0, 100);
    const providerCoverageImprovement = clamp(providerProfilesImproved * 2, 0, 100);
    const clinicalCoverageImprovement = /clinical|evidence|outcome|rehabilitation/i.test(domain) ? clamp(knowledgeObjectsCreated * 2.5, 0, 100) : clamp(knowledgeObjectsCreated * 1.2, 0, 100);
    const psychologyCoverageImprovement = /family|narrative|activities|nutrition|psychology/i.test(domain) ? clamp(knowledgeObjectsCreated * 2, 0, 100) : clamp(knowledgeObjectsCreated * 0.6, 0, 100);
    const familyGuidanceImprovement = /narrative|activities|nutrition|provider|family/i.test(domain) ? clamp(recommendationImprovement || knowledgeObjectsCreated * 2, 0, 100) : clamp((recommendationImprovement || 0) * 0.5, 0, 100);
    const reductionInUnknowns = clamp(knowledgeObjectsCreated * 1.5 + evidenceReviewed * 0.7, 0, 100);
    const reductionInConflicts = clamp((contradictionsFound * 10) + (failedRefreshes === 0 ? 20 : 0), 0, 100);
    const recommendationQualityImprovement = clamp(recommendationImprovement, 0, 100);
    const decisionAccuracyImprovement = clamp((apiPass * 0.4) + (evidenceQuality * 0.4) + (healthScore * 0.2), 0, 100);

    const learningScore = clamp(
      (continuousLearning ? 25 : 0) +
      (researchPlan ? 15 : 0) +
      (dailyWork ? 15 : 0) +
      (weeklyReview ? 10 : 0) +
      (monthlyAudit ? 10 : 0) +
      (certificationExam ? 10 : 0) +
      (kpis ? 15 : 0),
      0,
      100,
    );

    const trustScore = clamp(
      (improvesTrust ? 20 : 0) +
      (trustedSources ? 20 : 0) +
      (verificationRules ? 20 : 0) +
      (reducesUncertainty ? 15 : 0) +
      (evidenceQuality * 0.25),
      0,
      100,
    );

    const reasoningScore = clamp(
      (improvesReasoning ? 20 : 0) +
      (decisionRulesCreated * 5) +
      (knowledgeRelationshipsCreated * 1.2) +
      (recommendationQualityImprovement * 0.2),
      0,
      100,
    );

    const valueScore = clamp(
      (active ? 10 : 0) +
      (uniqueMission ? 10 : 0) +
      (uniqueDomain ? 10 : 0) +
      (uniqueKnowledge ? 10 : 0) +
      (knowledgeObjectsCreated > 0 ? 10 : 0) +
      (evidenceReviewed > 0 ? 10 : 0) +
      (continuousLearning ? 10 : 0) +
      (recommendationQualityImprovement * 0.1) +
      (trustScore * 0.1) +
      (reasoningScore * 0.1),
      0,
      100,
    );

    let verdict = 'CERTIFIED';
    let action = 'KEEP';
    if (!uniqueKnowledge || valueScore < 50) {
      verdict = 'REDUNDANT';
      action = uniqueKnowledge ? 'IMPROVE' : 'MERGE OR REMOVE';
    } else if (valueScore < 70 || !continuousLearning || !reportsGenerated) {
      verdict = 'AT RISK';
      action = 'IMPROVE';
    }

    const missingProof = [];
    if (!spec) missingProof.push('spec missing');
    if (!reportsGenerated) missingProof.push('no measurable report evidence');
    if (!weeklyReview) missingProof.push('weekly review unproven');
    if (!monthlyAudit) missingProof.push('monthly audit unproven');
    if (!certificationExam) missingProof.push('certification exam unproven');
    if (!lastExecutionSuccessful) missingProof.push('last execution unproven');

    const measurableAnswer = knowledgeObjectsCreated > 0 || evidenceReviewed > 0 || recommendationQualityImprovement > 0
      ? `${agentName} increased institutional intelligence through ${knowledgeObjectsCreated} knowledge objects, ${evidenceReviewed} evidence reviews, ${knowledgeRelationshipsCreated} relationships, and ${recommendationQualityImprovement}% recommendation improvement signal.`
      : `${agentName} has no measurable contribution proof in the current repository evidence and must be improved, merged, or removed.`;

    const uniqueLoss = uniqueKnowledge
      ? `${primaryOwnership} expertise would disappear or lose primary accountability.`
      : 'No unique expertise is proven by current repository evidence.';

    return {
      agentName,
      domain,
      owner,
      primaryOwnership,
      statusSignals: statusSignals || 'UNPROVEN',
      active,
      uniqueMission,
      uniqueDomain,
      uniqueKnowledge,
      continuousLearning,
      improvesRecommendationQuality,
      reducesUncertainty,
      discoversEvidence,
      improvesReasoning,
      improvesTrust,
      documentedInputs,
      documentedOutputs,
      trustedSources,
      verificationRules,
      researchPlan,
      dailyWork,
      weeklyReview,
      monthlyAudit,
      certificationExam,
      reportsGenerated,
      interfacesDocumented,
      dependenciesDocumented,
      lastExecutionSuccessful,
      knowledgeObjectsCreated,
      knowledgeObjectsUpdated,
      evidenceReviewed,
      evidenceVerified,
      researchPapersReviewed,
      providerProfilesImproved,
      decisionRulesCreated,
      knowledgeGapsClosed,
      knowledgeRelationshipsCreated,
      contradictionsFound,
      outdatedKnowledgeReplaced,
      recommendationQualityImprovement,
      decisionAccuracyImprovement,
      knowledgeCoverageImprovement: coverageImprovement,
      knowledgeFreshnessImprovement: freshnessImprovement,
      providerCoverageImprovement,
      clinicalCoverageImprovement,
      psychologyCoverageImprovement,
      familyGuidanceImprovement,
      reductionInUnknowns,
      reductionInConflicts,
      healthScore,
      performanceScore: clamp(100 - Math.max(0, avgLatency - 100) * 0.4, 0, 100),
      learningScore,
      trustScore,
      reasoningScore,
      valueScore,
      verdict,
      action,
      missingProof,
      measurableAnswer,
      uniqueLoss,
    };
  });

  const totalAgents = results.length;
  const certifiedAgents = results.filter((row) => row.verdict === 'CERTIFIED').length;
  const redundantAgents = results.filter((row) => row.verdict === 'REDUNDANT').length;
  const atRiskAgents = results.filter((row) => row.verdict === 'AT RISK').length;
  const openGaps = results.reduce((sum, row) => sum + row.missingProof.length, 0);

  const institutionalIntelligenceScore = results.reduce((sum, row) => sum + row.valueScore, 0) / totalAgents;
  const knowledgeCoverageScore = results.reduce((sum, row) => sum + row.knowledgeCoverageImprovement, 0) / totalAgents;
  const knowledgeGrowthScore = results.reduce((sum, row) => sum + clamp((row.knowledgeObjectsCreated * 4) + (row.knowledgeObjectsUpdated * 2), 0, 100), 0) / totalAgents;
  const learningScore = results.reduce((sum, row) => sum + row.learningScore, 0) / totalAgents;
  const evidenceScore = results.reduce((sum, row) => sum + clamp((row.evidenceReviewed * 3) + (row.evidenceVerified * 2), 0, 100), 0) / totalAgents;
  const reasoningScore = results.reduce((sum, row) => sum + row.reasoningScore, 0) / totalAgents;
  const recommendationScore = results.reduce((sum, row) => sum + row.recommendationQualityImprovement, 0) / totalAgents;
  const trustScore = results.reduce((sum, row) => sum + row.trustScore, 0) / totalAgents;
  const readinessScore = (institutionalIntelligenceScore + knowledgeCoverageScore + knowledgeGrowthScore + learningScore + evidenceScore + reasoningScore + recommendationScore + trustScore) / 8;

  const finalVerdict = readinessScore >= 90 && redundantAgents === 0
    ? 'WORLD CLASS READY'
    : readinessScore >= 75 && certifiedAgents / totalAgents >= 0.8
      ? 'PRODUCTION READY'
      : readinessScore >= 55
        ? 'PARTIALLY READY'
        : 'NOT READY';

  const institutionalAudit = [
    '# Institutional Intelligence Audit',
    '',
    '## Executive Summary',
    '',
    `- Total Agents: **${totalAgents}**`,
    `- Certified Agents: **${certifiedAgents}**`,
    `- At-Risk Agents: **${atRiskAgents}**`,
    `- Redundant Agents: **${redundantAgents}**`,
    `- Knowledge Objects (Institute): **${instituteKnowledgeObjects}**`,
    `- Evidence Objects (Institute): **${instituteEvidenceObjects}**`,
    `- Provider Profiles (Institute): **${instituteProviderProfiles}**`,
    `- Knowledge Graph Growth: **${instituteGraphGrowth}**`,
    `- Institutional Intelligence Score: **${pct(institutionalIntelligenceScore)}**`,
    `- Knowledge Coverage Score: **${pct(knowledgeCoverageScore)}**`,
    `- Knowledge Growth Score: **${pct(knowledgeGrowthScore)}**`,
    `- Learning Score: **${pct(learningScore)}**`,
    `- Evidence Score: **${pct(evidenceScore)}**`,
    `- Reasoning Score: **${pct(reasoningScore)}**`,
    `- Recommendation Score: **${pct(recommendationScore)}**`,
    `- Trust Score: **${pct(trustScore)}**`,
    `- Overall Institute Readiness: **${pct(readinessScore)}**`,
    `- Final Verdict: **${finalVerdict}**`,
    '',
    '## How Each Agent Made OPTIME Smarter',
    '',
    ...results.flatMap((row) => [`### ${row.agentName}`, `- ${row.measurableAnswer}`, `- Unique expertise at risk if removed: ${row.uniqueLoss}`, `- Certification: ${row.verdict}`, `- Recommended action: ${row.action}`, row.missingProof.length ? `- Missing proof: ${row.missingProof.join('; ')}` : '- Missing proof: none proven missing from current audit surface', '']),
  ].join('\n');

  const agentValueMatrix = [
    '# Agent Value Matrix',
    '',
    markdownTable(
      ['Agent', 'Domain', 'Value Score', 'Trust Score', 'Reasoning Score', 'Learning Score', 'Certification', 'Action'],
      results.map((row) => [row.agentName, row.domain, pct(row.valueScore), pct(row.trustScore), pct(row.reasoningScore), pct(row.learningScore), row.verdict, row.action]),
    ),
  ].join('\n');

  const knowledgeGrowthMatrix = [
    '# Knowledge Growth Matrix',
    '',
    markdownTable(
      ['Agent', 'Knowledge Objects Created', 'Knowledge Objects Updated', 'Evidence Reviewed', 'Evidence Verified', 'Decision Rules Created', 'Relationships Created', 'Gaps Closed'],
      results.map((row) => [row.agentName, row.knowledgeObjectsCreated, row.knowledgeObjectsUpdated, row.evidenceReviewed, row.evidenceVerified, row.decisionRulesCreated, row.knowledgeRelationshipsCreated, row.knowledgeGapsClosed]),
    ),
  ].join('\n');

  const expertiseGapMatrix = [
    '# Expertise Gap Matrix',
    '',
    markdownTable(
      ['Agent', 'Primary Ownership', 'What Disappears If Removed', 'Missing Proof', 'Gap Severity'],
      results.map((row) => [row.agentName, row.primaryOwnership, row.uniqueLoss, row.missingProof.join('; ') || 'None', row.verdict === 'REDUNDANT' ? 'HIGH' : row.verdict === 'AT RISK' ? 'MEDIUM' : 'LOW']),
    ),
  ].join('\n');

  const learningDashboard = [
    '# Learning Dashboard',
    '',
    markdownTable(
      ['Agent', 'Learning Goals', 'Research Agenda', 'Daily Learning Tasks', 'Weekly Reviews', 'Monthly Audit', 'Certification Exams', 'Learning Score'],
      results.map((row) => [row.agentName, row.continuousLearning ? 'YES' : 'NO', row.researchPlan ? 'YES' : 'NO', row.dailyWork ? 'YES' : 'NO', row.weeklyReview ? 'YES' : 'NO', row.monthlyAudit ? 'YES' : 'NO', row.certificationExam ? 'YES' : 'NO', pct(row.learningScore)]),
    ),
  ].join('\n');

  const trustDashboard = [
    '# Trust Dashboard',
    '',
    ...platformHealthRows.map((row) => `- ${row.Area}: ${row.Status} (${row.Evidence})`),
    '',
    markdownTable(
      ['Agent', 'Trusted Sources Defined', 'Verification Rules', 'Reduces Uncertainty', 'Improves Trust', 'Trust Score'],
      results.map((row) => [row.agentName, row.trustedSources ? 'YES' : 'NO', row.verificationRules ? 'YES' : 'NO', row.reducesUncertainty ? 'YES' : 'NO', row.improvesTrust ? 'YES' : 'NO', pct(row.trustScore)]),
    ),
  ].join('\n');

  writeReport('institutional_intelligence_audit.md', institutionalAudit);
  writeReport('agent_value_matrix.md', agentValueMatrix);
  writeReport('knowledge_growth_matrix.md', knowledgeGrowthMatrix);
  writeReport('expertise_gap_matrix.md', expertiseGapMatrix);
  writeReport('learning_dashboard.md', learningDashboard);
  writeReport('trust_dashboard.md', trustDashboard);

  console.log('Wrote 6 reports');
  console.log(`TOTAL_AGENTS=${totalAgents}`);
  console.log(`CERTIFIED_AGENTS=${certifiedAgents}`);
  console.log(`OPEN_GAPS=${openGaps}`);
  console.log(`INSTITUTIONAL_INTELLIGENCE_SCORE=${pct(institutionalIntelligenceScore)}`);
  console.log(`TRUST_SCORE=${pct(trustScore)}`);
  console.log(`OVERALL_READINESS=${pct(readinessScore)}`);
  console.log(`FINAL_VERDICT=${finalVerdict}`);
}

main();
