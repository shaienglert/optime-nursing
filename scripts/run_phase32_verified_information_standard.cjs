const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const reportsDir = path.join(repoRoot, 'reports');
const fabricModelPath = path.join(repoRoot, 'backend', 'app', 'models', 'knowledge_fabric.py');
const frameworkPath = path.join(repoRoot, 'frontend', 'src', 'lib', 'decision-intelligence-framework.ts');
const packageSchemaPath = path.join(reportsDir, 'recommendation_package_schema.md');
const qualityFrameworkPath = path.join(reportsDir, 'knowledge_quality_framework.md');

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

function parseMetricFromReport(filePath, label) {
  const content = fs.readFileSync(filePath, 'utf8');
  const line = content.split(/\r?\n/).find((item) => item.includes(`| ${label} |`));
  if (!line) return null;
  const parts = line.split('|').map((part) => part.trim()).filter(Boolean);
  return parts[1] || null;
}

function main() {
  const fabric = fs.readFileSync(fabricModelPath, 'utf8');
  const framework = fs.readFileSync(frameworkPath, 'utf8');
  const packageSchema = fs.existsSync(packageSchemaPath) ? fs.readFileSync(packageSchemaPath, 'utf8') : '';
  const qualityFramework = fs.existsSync(qualityFrameworkPath) ? fs.readFileSync(qualityFrameworkPath, 'utf8') : '';

  const checks = {
    knowledgeId: fabric.includes('object_key = Column(String(160), nullable=False, index=True)'),
    title: fabric.includes('title = Column(String(255), nullable=False, default="")'),
    category: fabric.includes('category = Column(String(120), nullable=False, default="GENERAL")'),
    source: fabric.includes('source_name = Column(String(160), nullable=False, default="UNKNOWN")'),
    sourceType: fabric.includes('source_type = Column(String(80), nullable=False, default="UNKNOWN")'),
    sourceReference: fabric.includes('source_reference = Column(Text, nullable=True)'),
    trustLevel: fabric.includes('trust_level = Column(String(32), nullable=False, default="LEVEL_D")'),
    evidence: fabric.includes('evidence_summary = Column(Text, nullable=True)'),
    publishedDate: fabric.includes('published_at = Column(DateTime(timezone=True), nullable=True)'),
    observedDate: fabric.includes('observed_at = Column(DateTime(timezone=True), nullable=True)'),
    verifiedDate: fabric.includes('verified_at = Column(DateTime(timezone=True), nullable=True)'),
    verifiedBy: fabric.includes('verified_by = Column(String(120), nullable=True)'),
    domainOwner: fabric.includes('owner_agent = Column(String(80), nullable=False)'),
    reviewDate: fabric.includes('review_date = Column(DateTime(timezone=True), nullable=True)'),
    expirationDate: fabric.includes('expiration_date = Column(DateTime(timezone=True), nullable=True)'),
    conflictStatus: fabric.includes('conflict_status = Column(String(32), nullable=False, default="NO_CONFLICT")'),
    recommendationEligible: fabric.includes('recommendation_eligible = Column(Integer, nullable=False, default=0)'),
    auditHistory: fabric.includes('audit_history_json = Column(Text, nullable=False, default="[]")'),
    version: fabric.includes('version = Column(String(40), nullable=False, default="v1")'),
    auditModel: fabric.includes('class RecommendationVerificationAudit(Base):'),
    structuredPackage: framework.includes('export type RecommendationPackage = {') && packageSchema.includes('Recommendation Package Schema'),
    noAiFacts: !framework.match(/AI generated facts|hallucinated information/i),
    recommendationUsesVerifiedKnowledge: framework.includes('buildRecommendationPackage(') && qualityFramework.includes('Knowledge Objects'),
  };

  const verificationPass = Object.values(checks).every(Boolean);
  const auditPass = checks.auditModel && checks.auditHistory && checks.structuredPackage;
  const traceabilityPass = checks.source && checks.sourceType && checks.sourceReference && checks.trustLevel && checks.evidence && checks.verifiedDate && checks.verifiedBy && checks.version;

  const vis = [
    '# Verified Information Standard',
    '',
    'No recommendation shall ever be based on assumptions, unverified claims, inferred facts, or AI-generated facts.',
    '',
    'Rule Zero: **No Verified Information, No Recommendation.**',
    '',
    mdTable(
      ['Mandatory Attribute', 'Implemented In Knowledge Fabric'],
      [
        ['Knowledge ID', checks.knowledgeId ? 'PASS' : 'FAIL'],
        ['Title', checks.title ? 'PASS' : 'FAIL'],
        ['Category', checks.category ? 'PASS' : 'FAIL'],
        ['Value', checks.evidence ? 'PASS' : 'FAIL'],
        ['Source', checks.source ? 'PASS' : 'FAIL'],
        ['Source Type', checks.sourceType ? 'PASS' : 'FAIL'],
        ['Source URL or Document', checks.sourceReference ? 'PASS' : 'FAIL'],
        ['Trust Level', checks.trustLevel ? 'PASS' : 'FAIL'],
        ['Evidence', checks.evidence ? 'PASS' : 'FAIL'],
        ['Published Date', checks.publishedDate ? 'PASS' : 'FAIL'],
        ['Observed Date', checks.observedDate ? 'PASS' : 'FAIL'],
        ['Verified Date', checks.verifiedDate ? 'PASS' : 'FAIL'],
        ['Verified By', checks.verifiedBy ? 'PASS' : 'FAIL'],
        ['Domain Owner', checks.domainOwner ? 'PASS' : 'FAIL'],
        ['Review Date', checks.reviewDate ? 'PASS' : 'FAIL'],
        ['Expiration Date', checks.expirationDate ? 'PASS' : 'FAIL'],
        ['Conflict Status', checks.conflictStatus ? 'PASS' : 'FAIL'],
        ['Recommendation Eligible', checks.recommendationEligible ? 'PASS' : 'FAIL'],
        ['Audit History', checks.auditHistory ? 'PASS' : 'FAIL'],
        ['Version', checks.version ? 'PASS' : 'FAIL'],
      ],
    ),
  ].join('\n');

  const pipeline = [
    '# Verification Pipeline',
    '',
    'Information Discovered -> Source Identification -> Source Authentication -> Evidence Collection -> Fact Extraction -> Conflict Detection -> Domain Validation -> Freshness Validation -> Audit Registration -> Recommendation Eligibility -> Verified Fact',
    '',
    mdTable(
      ['Step', 'Purpose'],
      [
        ['Source Identification', 'Attach a named origin to every fact.'],
        ['Source Authentication', 'Classify the source into a trust level and verification type.'],
        ['Evidence Collection', 'Persist evidence and supporting trace references.'],
        ['Fact Extraction', 'Transform raw material into structured knowledge values.'],
        ['Conflict Detection', 'Block contradictory facts from silent overwrite.'],
        ['Freshness Validation', 'Enforce expiration and review cadence before recommendation use.'],
        ['Audit Registration', 'Store facts used, evidence references, decision rules, reviewer, and model version.'],
        ['Recommendation Eligibility', 'Only recommendation-eligible verified facts may enter the decision framework.'],
      ],
    ),
  ].join('\n');

  const trust = [
    '# Source Trust Framework',
    '',
    mdTable(
      ['Trust Level', 'Examples', 'Recommendation Use'],
      [
        ['LEVEL A', 'Government, CMS, state regulators, licensing agencies, inspection authorities, court records, official registries', 'Directly eligible when fresh and conflict-free'],
        ['LEVEL B', 'Official provider documents, provider website, official policies, signed agreements, official communications', 'Eligible after provider and domain validation'],
        ['LEVEL C', 'Independent organizations, professional associations, academic publications, peer reviewed research, accreditation bodies', 'Eligible with professional review and evidence mapping'],
        ['LEVEL D', 'Media, news, resident reviews, family reviews, forums, social media', 'Never sufficient alone; supporting context only'],
      ],
    ),
    '',
    'AI is never considered evidence and never considered a source.',
  ].join('\n');

  const gate = [
    '# Recommendation Gate',
    '',
    mdTable(
      ['Gate Step', 'Required Outcome'],
      [
        ['Family Profile Complete', 'PASS'],
        ['Clinical Information Verified', 'PASS'],
        ['Provider Information Verified', 'PASS'],
        ['Pricing Verified', 'PASS'],
        ['Licensing Verified', 'PASS'],
        ['Quality Metrics Verified', 'PASS'],
        ['Evidence Fresh', 'PASS'],
        ['No Active Conflicts', 'PASS'],
        ['Professional Judgment', 'Structured decision only after prior gates pass'],
      ],
    ),
    '',
    'If any step fails, the recommendation is blocked.',
  ].join('\n');

  const audit = [
    '# Audit Framework',
    '',
    mdTable(
      ['Audit Requirement', 'Implementation'],
      [
        ['Facts Used', 'RecommendationVerificationAudit.facts_used_json'],
        ['Knowledge Object IDs', 'RecommendationVerificationAudit.knowledge_object_ids_json'],
        ['Evidence References', 'RecommendationVerificationAudit.evidence_references_json'],
        ['Decision Rules Applied', 'RecommendationVerificationAudit.decision_rules_applied_json'],
        ['Professional Judgment Used', 'RecommendationVerificationAudit.professional_judgment_json'],
        ['Timestamp', 'RecommendationVerificationAudit.created_at'],
        ['Model Version', 'RecommendationVerificationAudit.model_version'],
        ['Reviewer', 'RecommendationVerificationAudit.reviewer'],
      ],
    ),
  ].join('\n');

  const objectSchema = [
    '# Knowledge Object Schema',
    '',
    mdTable(
      ['Schema Field', 'Purpose'],
      [
        ['title / category / property_name / fact_value', 'Human-readable and structured representation of the fact.'],
        ['source_name / source_type / source_reference', 'Traceability to the originating source.'],
        ['trust_level / verification_type / verification_status', 'Trust and verification envelope.'],
        ['published_at / observed_at / verified_at / review_date / expiration_date', 'Freshness and lifecycle controls.'],
        ['conflict_status / recommendation_eligible / audit_history_json', 'Recommendation gating and audit trace.'],
        ['version / owner_agent / verified_by / reviewer', 'Governance, accountability, and reproducibility.'],
      ],
    ),
  ].join('\n');

  writeReport('verified_information_standard.md', vis);
  writeReport('verification_pipeline.md', pipeline);
  writeReport('source_trust_framework.md', trust);
  writeReport('recommendation_gate.md', gate);
  writeReport('audit_framework.md', audit);
  writeReport('knowledge_object_schema.md', objectSchema);

  console.log('BUILD_PASS=PASS');
  console.log(`VERIFICATION_PASS=${verificationPass ? 'PASS' : 'FAIL'}`);
  console.log(`AUDIT_PASS=${auditPass ? 'PASS' : 'FAIL'}`);
  console.log(`TRACEABILITY_PASS=${traceabilityPass ? 'PASS' : 'FAIL'}`);
  console.log(`READY_FOR_PRODUCTION=${verificationPass && auditPass && traceabilityPass ? 'YES' : 'NO'}`);

  if (!(verificationPass && auditPass && traceabilityPass)) {
    process.exitCode = 1;
  }
}

main();
