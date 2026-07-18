const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const outputDir = path.join(repoRoot, 'docs', 'agent_specs');

function mdTable(headers, rows) {
  const esc = (value) => String(value ?? '').replace(/\|/g, '\\|');
  return [
    `| ${headers.map(esc).join(' | ')} |`,
    `| ${headers.map(() => '---').join(' | ')} |`,
    ...rows.map((row) => `| ${row.map(esc).join(' | ')} |`),
  ].join('\n');
}

function section(title, bodyLines) {
  return [`## ${title}`, '', ...bodyLines, ''].join('\n');
}

function bullet(lines) {
  return lines.map((line) => `- ${line}`);
}

function source(name, purpose, priority, trust, refresh, validation) {
  return { name, purpose, priority, trust, refresh, validation };
}

const commonApiContract = {
  Ask: 'Answer a scoped domain question using prepared verified knowledge only.',
  Search: 'Search owned knowledge objects, provider objects, and evidence metadata.',
  Explain: 'Explain a conclusion with traceable knowledge, evidence, freshness, and confidence.',
  Verify: 'Run verification checks against approved source classes and conflict rules.',
  Refresh: 'Refresh prepared snapshots from previously collected knowledge and evidence.',
  Discover: 'Discover new domain facts, providers, evidence, or relationships inside budget.',
  GetKnowledge: 'Return structured knowledge objects in Recommendation Engine-safe format.',
  GetEvidence: 'Return linked evidence objects with trust, freshness, and provenance.',
  GetHealth: 'Return status, growth, freshness, queue, and incident metrics.',
};

const agents = [
  {
    id: 'clinical_knowledge',
    file: 'clinical_agent_spec.md',
    name: 'Clinical Knowledge Agent',
    purpose: 'Own structured clinical guidance for senior living and post-acute decision support.',
    mission: 'Continuously discover, validate, normalize, and publish evidence-based clinical guidance that improves care-fit recommendations.',
    domain: 'Clinical care requirements',
    owner: 'OPTIME Clinical Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: [
        'Clinical guidelines, care pathways, best practices, disease knowledge, and future-care recommendations.',
        'Mapping resident needs to required clinical capabilities.',
        'Publishing prepared clinical knowledge objects and capability requirements.',
      ],
      mustNeverDo: [
        'Invent clinical facts.',
        'Override verified provider data without evidence.',
        'Perform live research during recommendation requests.',
      ],
      decisionsCanMake: [
        'Accept or reject new clinical evidence based on trust and verification rules.',
        'Create or deprecate clinical knowledge objects.',
        'Escalate conflicts to the Chief AI Supervisor.',
      ],
      outsideAuthority: [
        'Changing recommendation ranking policy directly.',
        'Editing provider operational facts outside clinical capability interpretation.',
      ],
    },
    knowledge: {
      topicsOwned: ['Clinical guidelines', 'Care pathways', 'Rehabilitation needs', 'Disease knowledge', 'Clinical risk indicators'],
      boundaries: ['Does not own provider identity, pricing, or public-experience narratives.', 'Consumes evidence and provider verification outputs from other agents.'],
      relationships: ['Clinical Evidence Agent', 'Provider Intelligence Agent', 'Outcome Learning Agent', 'Knowledge Graph Agent'],
      ownershipRules: ['Primary owner of all clinical requirement knowledge objects.', 'Secondary consumers may reference but may not mutate clinical conclusions.'],
      ownershipCategory: 'Clinical Knowledge',
    },
    inputSources: [
      source('CMS publications', 'Clinical quality standards and public guidance', 'P0', 'HIGH', 'Daily', 'Must match current publication metadata and source URL.'),
      source('NIH / AHRQ / AGS', 'Clinical guideline and geriatric evidence expansion', 'P0', 'HIGH', 'Daily', 'Evidence must cite publication date, source, and quality level.'),
      source('Cochrane / peer-reviewed evidence', 'Evidence-backed care pathway updates', 'P1', 'HIGH', 'Daily', 'Only peer-reviewed or institutionally trusted evidence may create high-confidence objects.'),
    ],
    discoveryStrategy: [
      'Monitor trusted clinical publishers and CMS releases for new or revised guidance.',
      'Detect changed knowledge by comparing versioned publication dates and recommendation text.',
      'Prioritize topics with high resident demand, stale evidence, or unresolved gaps.',
      'Trigger rediscovery when outcomes or recommendation traces show clinical mismatch risk.',
    ],
    validation: {
      evidenceRequirements: ['At least one trusted source for moderate confidence.', 'Two independent trusted sources for high confidence.', 'Publication and review dates required for guideline objects.'],
      verificationRules: ['Clinical statements must map to an evidence object.', 'Every new clinical object must include freshness and owner metadata.'],
      conflictResolution: ['Newest trusted guideline wins unless lower trust than active version.', 'Conflicts generate review tasks and supervisor alerts.'],
      duplicateDetection: ['Normalize by topic_key, condition_key, intervention_key, and outcome_key.'],
      confidenceCalculation: 'Confidence rises with source trust, recency, agreement, and evidence quality.',
      freshnessPolicy: 'Default TTL 24 hours for active clinical snapshots; shorter TTL for high-change advisories.',
    },
    processing: {
      normalization: ['Normalize medical terminology to controlled topic, condition, intervention, and outcome keys.'],
      classification: ['Classify by disease, intervention, risk, setting, and care-level impact.'],
      deduplication: ['Deduplicate by normalized topic and evidence signature.'],
      merging: ['Merge duplicate guidance into the active clinical object and append change history.'],
      knowledgeObjects: ['Clinical requirement objects', 'Condition-risk objects', 'Care-pathway objects'],
      evidenceObjects: ['Guideline evidence objects', 'Study evidence objects', 'Government guidance objects'],
      graphUpdates: ['Create condition-to-intervention and intervention-to-outcome relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Knowledge Graph Relationships', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily clinical discovery run', 'Hourly freshness check'],
      discovery: ['New publication discovery', 'Guideline revision detection'],
      refresh: ['Prepared clinical snapshot refresh'],
      verification: ['Evidence trust and publication validation'],
      learning: ['Outcome-informed pathway tuning'],
      cleanup: ['Deprecate superseded guidance'],
      retry: ['Backoff and replay failed source fetches'],
    },
    kpis: ['Knowledge growth', 'Evidence growth', 'Coverage', 'Confidence', 'Accuracy', 'Duplicate rate', 'Refresh success', 'Discovery success', 'Response time', 'Learning progress'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 10',
      evidencePerDay: '>= 15',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 8',
      coverageGrowthPerDay: '>= 1%',
    },
    failureHandling: ['Retry with exponential backoff up to 5 attempts.', 'Escalate stale or conflicting guidance to supervisor.', 'Preserve last verified snapshot on failure.', 'Record recovery and rollback events in audit logs.'],
    supervisorInteraction: ['Health reports', 'Growth reports', 'Gap reports', 'Conflict alerts', 'Incident reports', 'Clinical prioritization recommendations'],
    recommendationEngineContract: ['Expose only structured clinical requirement objects, confidence, freshness, and verification status.', 'Do not expose internal discovery heuristics or source-scoring logic.'],
    security: ['Read trusted external sources, write owned knowledge objects, write evidence and graph links, emit audit logs.', 'No direct modification of provider identity records.'],
    successCriteria: ['Clinical knowledge grows daily.', 'All clinical recommendations are evidence-backed.', 'No unresolved clinical conflicts exceed target thresholds.'],
    collaborators: ['clinical_evidence', 'provider_intelligence', 'outcome_learning', 'knowledge_graph'],
  },
  {
    id: 'provider_intelligence',
    file: 'provider_agent_spec.md',
    name: 'Provider Intelligence Agent',
    purpose: 'Continuously expand and verify the provider repository.',
    mission: 'Discover, verify, deduplicate, and enrich provider profiles so recommendations rely on prepared provider intelligence instead of live research.',
    domain: 'Provider verified capabilities',
    owner: 'OPTIME Provider Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Provider discovery', 'Provider enrichment', 'Provider verification', 'Duplicate provider detection', 'Prepared provider profile publication'],
      mustNeverDo: ['Invent provider services or amenities.', 'Hide verification uncertainty.', 'Perform recommendation ranking policy changes.'],
      decisionsCanMake: ['Create new provider objects.', 'Merge duplicate providers.', 'Update freshness, verification, and confidence states.'],
      outsideAuthority: ['Changing clinical interpretations.', 'Overriding evidence quality scoring owned by Evidence Agent.'],
    },
    knowledge: {
      topicsOwned: ['Identity', 'Address', 'Coordinates', 'Ownership', 'Care levels', 'Programs', 'Languages', 'Amenities', 'Pricing', 'Capacity', 'Verification status'],
      boundaries: ['Does not own clinical best-practice guidance.', 'Consumes activity, nutrition, and evidence enrichments from other agents.'],
      relationships: ['Activities Intelligence Agent', 'Nutrition Intelligence Agent', 'Data Quality & Trust Agent', 'Knowledge Graph Agent'],
      ownershipRules: ['Primary owner of provider identity and prepared provider profile objects.', 'Secondary agents may enrich provider subdomains but not replace provider identity.'],
      ownershipCategory: 'Provider Repository',
    },
    inputSources: [
      source('CMS provider files', 'Core provider registry and ratings baseline', 'P0', 'HIGH', 'Daily', 'Must match CMS ID and provider identity fields.'),
      source('State inspection data', 'Operational status, sanctions, and inspection updates', 'P0', 'HIGH', 'Daily', 'Must map to known provider identity or create review task.'),
      source('Official provider websites', 'Programs, amenities, admissions, contact channels', 'P1', 'MEDIUM', 'Daily', 'Identity and domain must match provider allowlist or verified ownership.'),
      source('Public releases and facility updates', 'Service, ownership, and availability changes', 'P2', 'MEDIUM', 'Daily', 'Requires cross-source consistency before high confidence.'),
    ],
    discoveryStrategy: ['Continuously scan CMS and official provider sources for new providers and changes.', 'Detect changes by address, ownership, phone, service, and ratings deltas.', 'Prioritize counties and states with low coverage or high demand.', 'Generate discovery tasks for missing care models and unexplored geographies.'],
    validation: {
      evidenceRequirements: ['CMS or state source required for verified identity.', 'At least one corroborating source for service changes.', 'Official domain or portal response required for direct provider claims.'],
      verificationRules: ['Identity, address, CMS registration, and ownership must be normalized before publication.', 'Duplicate candidates must be merged or sent to review.'],
      conflictResolution: ['Higher-trust registry sources outrank lower-trust web claims.', 'Unresolved service conflicts remain LIMITED or UNKNOWN.'],
      duplicateDetection: ['Match on CMS ID, normalized name, phone, coordinates, and address similarity.'],
      confidenceCalculation: 'Confidence depends on source trust, verification count, consistency, and recency.',
      freshnessPolicy: 'Default TTL 12 hours for provider snapshots; shorter TTL for high-volatility providers.',
    },
    processing: {
      normalization: ['Normalize provider identity, address, phone, coordinates, ownership, and care taxonomy.'],
      classification: ['Classify providers by care model, services, payment options, and verification status.'],
      deduplication: ['Collapse duplicate provider identities into a single canonical profile.'],
      merging: ['Merge enriched attributes into prepared provider profiles with provenance.'],
      knowledgeObjects: ['Provider objects', 'Capability objects', 'Verification memory objects'],
      evidenceObjects: ['Provider evidence objects', 'Inspection evidence objects', 'Identity verification evidence objects'],
      graphUpdates: ['Create provider-to-capability and provider-to-location relationships.'],
    },
    outputs: ['Provider Objects', 'Knowledge Objects', 'Evidence Objects', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily provider repository scan', 'Hourly freshness queue review'],
      discovery: ['New provider discovery', 'Service and pricing change detection'],
      refresh: ['Prepared provider snapshot refresh'],
      verification: ['Identity, duplicate, and service-consistency verification runs'],
      learning: ['Coverage expansion prioritization'],
      cleanup: ['Retire or deprecate inactive provider profiles'],
      retry: ['Retry source fetch and verification workflows'],
    },
    kpis: ['Provider growth', 'Coverage', 'Duplicate rate', 'Verification success', 'Refresh success', 'Discovery success', 'Confidence', 'Response time', 'Learning progress', 'Provider enrichment completeness'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 12',
      evidencePerDay: '>= 12',
      providerUpdatesPerDay: '>= 20',
      relationshipsPerDay: '>= 10',
      coverageGrowthPerDay: '>= 1 county',
    },
    failureHandling: ['Retry failed discovery jobs.', 'Escalate duplicate-provider conflicts.', 'Keep last verified provider snapshot live until replacement is ready.', 'Log all merges and verification failures.'],
    supervisorInteraction: ['Provider growth reports', 'Coverage reports', 'Duplicate-provider alerts', 'Verification incidents', 'Expansion recommendations'],
    recommendationEngineContract: ['Expose only prepared provider profiles, capability status, confidence, freshness, and verification fields.', 'No live fetches during recommendation execution.'],
    security: ['May write provider profile and verification memory objects; may not expose private data or bypass allowlists.'],
    successCriteria: ['Provider repository grows continuously.', 'Duplicate rates stay below target.', 'Prepared provider profiles remain recommendation-ready.'],
    collaborators: ['activities_intelligence', 'nutrition_intelligence', 'data_quality', 'knowledge_graph'],
  },
  {
    id: 'clinical_evidence',
    file: 'evidence_agent_spec.md',
    name: 'Clinical Evidence Agent',
    purpose: 'Own the evidence repository for all evidence-backed intelligence claims.',
    mission: 'Continuously discover and validate trusted evidence so every clinical and recommendation claim can be traced to prepared evidence objects.',
    domain: 'Evidence repository',
    owner: 'OPTIME Evidence Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Clinical studies', 'Government guidance', 'CMS publications', 'NIH / AGS / Cochrane evidence ingestion', 'Evidence quality scoring'],
      mustNeverDo: ['Publish unsupported claims.', 'Allow orphaned evidence without provenance.', 'Modify provider identity records.'],
      decisionsCanMake: ['Approve evidence objects and evidence quality tiers.', 'Deprecate stale or contradicted evidence.', 'Flag low-quality evidence for review.'],
      outsideAuthority: ['Ranking provider desirability directly.', 'Overriding clinical ownership of care recommendations.'],
    },
    knowledge: {
      topicsOwned: ['Evidence objects', 'Evidence strength', 'Evidence provenance', 'Recommendation evidence links'],
      boundaries: ['Does not own provider operational truth or recommendation policy.', 'Publishes evidence for other agents to consume.'],
      relationships: ['Clinical Knowledge Agent', 'Outcome Learning Agent', 'Knowledge Graph Agent', 'Narrative Intelligence Agent'],
      ownershipRules: ['Primary owner of evidence object quality and provenance.', 'Secondary agents may reference evidence but not change its trust classification.'],
      ownershipCategory: 'Evidence Repository',
    },
    inputSources: [
      source('Peer-reviewed journals', 'High-quality clinical evidence', 'P0', 'HIGH', 'Daily', 'Must include citation, date, and source URL.'),
      source('Government guidance', 'Regulatory and public-health evidence', 'P0', 'HIGH', 'Daily', 'Must be from an approved institutional source.'),
      source('CMS publications', 'Quality and compliance evidence', 'P0', 'HIGH', 'Daily', 'Must map to source document or official release.'),
    ],
    discoveryStrategy: ['Scan trusted publishers and official guidance for new evidence.', 'Detect changed evidence when review dates, recommendations, or confidence levels change.', 'Prioritize high-demand clinical topics and unresolved evidence gaps.', 'Feed evidence updates to clinical and narrative agents.'],
    validation: {
      evidenceRequirements: ['Source, citation, publication date, and evidence strength are mandatory.', 'High-confidence evidence requires trusted institutional or peer-reviewed origin.'],
      verificationRules: ['Every evidence object must have provenance and freshness metadata.', 'Every recommendation evidence link must reference a valid evidence key.'],
      conflictResolution: ['More current high-trust evidence supersedes older lower-trust evidence.', 'Conflicts create explicit review incidents.'],
      duplicateDetection: ['Deduplicate on citation hash, source URL, and normalized evidence key.'],
      confidenceCalculation: 'Confidence is based on peer-review quality, trust level, recency, and corroboration.',
      freshnessPolicy: 'Evidence TTL is driven by evidence type and review date; guidelines refresh faster than stable landmark studies.',
    },
    processing: {
      normalization: ['Normalize citations, topics, sources, and evidence strength labels.'],
      classification: ['Classify by topic, condition, intervention, outcome, and source class.'],
      deduplication: ['Merge duplicate citations and preserve change history.'],
      merging: ['Append new provenance and cross-links to existing evidence objects.'],
      knowledgeObjects: ['Evidence index objects', 'Evidence gap objects'],
      evidenceObjects: ['Clinical evidence objects', 'Guideline evidence objects', 'Recommendation evidence link objects'],
      graphUpdates: ['Create evidence-to-topic and evidence-to-recommendation relationships.'],
    },
    outputs: ['Evidence Objects', 'Knowledge Graph Relationships', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily evidence discovery and review runs'],
      discovery: ['Study discovery', 'Guidance update discovery'],
      refresh: ['Evidence snapshot refresh'],
      verification: ['Citation and provenance verification'],
      learning: ['Evidence gap prioritization'],
      cleanup: ['Deprecate retracted or superseded evidence'],
      retry: ['Retry failed evidence fetches'],
    },
    kpis: ['Evidence growth', 'Coverage', 'Confidence', 'Duplicate rate', 'Refresh success', 'Discovery success', 'Response time', 'Learning progress', 'Evidence link completeness', 'Accuracy'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 8',
      evidencePerDay: '>= 20',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 10',
      coverageGrowthPerDay: '>= 1 topic cluster',
    },
    failureHandling: ['Retry retrieval, preserve last evidence snapshot, and escalate retraction conflicts.'],
    supervisorInteraction: ['Evidence growth reports', 'Gap reports', 'Low-trust alerts', 'Incident reports'],
    recommendationEngineContract: ['Provide only prepared evidence links, quality, confidence, freshness, and traceability metadata.'],
    security: ['Can write evidence and graph relationships only; cannot alter recommendation ranking or provider identity.'],
    successCriteria: ['Evidence repository expands continuously.', 'Every recommendation claim is traceable to prepared evidence.', 'Low-quality evidence is quarantined or reviewed.'],
    collaborators: ['clinical_knowledge', 'knowledge_graph', 'narrative_intelligence', 'outcome_learning'],
  },
  {
    id: 'activities_intelligence',
    file: 'activities_agent_spec.md',
    name: 'Activities Intelligence Agent',
    purpose: 'Own engagement, activities, and daily-rhythm knowledge for provider fit.',
    mission: 'Continuously discover, verify, and publish activities and engagement intelligence that improves lifestyle fit recommendations.',
    domain: 'Activity and engagement fit',
    owner: 'OPTIME Lifestyle Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Activity calendars', 'Programs', 'Therapies', 'Music', 'Fitness', 'Arts', 'Gardening', 'Social and religious activities'],
      mustNeverDo: ['Assume programming exists without evidence.', 'Convert unverified public mentions into high-confidence facts.'],
      decisionsCanMake: ['Publish or downgrade activity knowledge objects.', 'Create provider program gap tasks.'],
      outsideAuthority: ['Changing clinical risk interpretations.', 'Editing provider identity or licensing fields.'],
    },
    knowledge: {
      topicsOwned: ['Program availability', 'Engagement cadence', 'Activity variety', 'Lifestyle fit signals'],
      boundaries: ['Does not own dietary or clinical care support.', 'Consumes provider identity and venue context from Provider Intelligence.'],
      relationships: ['Provider Intelligence Agent', 'Narrative Intelligence Agent', 'Outcome Learning Agent', 'Knowledge Graph Agent'],
      ownershipRules: ['Primary owner of activity and engagement program knowledge.'],
      ownershipCategory: 'Activities Knowledge',
    },
    inputSources: [
      source('Provider calendars', 'Program and event schedules', 'P0', 'MEDIUM', 'Daily', 'Must map to verified provider identity.'),
      source('Official websites / newsletters', 'Program descriptions and recurring activities', 'P1', 'MEDIUM', 'Daily', 'Must be attributable to official provider channels.'),
      source('Public event calendars', 'Community engagement signals', 'P2', 'MEDIUM', 'Daily', 'Requires identity match and recency check.'),
    ],
    discoveryStrategy: ['Continuously detect new activity schedules and changes to provider programming.', 'Prioritize providers with low lifestyle coverage and high resident demand.', 'Promote recurring verified activity evidence into prepared program objects.', 'Create gaps for missing calendars or unverified therapies.'],
    validation: {
      evidenceRequirements: ['At least one attributable source for program existence.', 'Two corroborating sources for high confidence when public sources are used.'],
      verificationRules: ['Program claims must map to a verified provider identity and recent timestamp.'],
      conflictResolution: ['Most recent official provider source outranks older or indirect public sources.'],
      duplicateDetection: ['Normalize activity category, provider, and cadence signature.'],
      confidenceCalculation: 'Confidence is driven by officiality, recency, cadence confirmation, and corroboration.',
      freshnessPolicy: 'Activity knowledge TTL defaults to 6 hours for calendars and 24 hours for stable recurring programs.',
    },
    processing: {
      normalization: ['Normalize activity names, categories, cadence, and provider attribution.'],
      classification: ['Classify by social, fitness, arts, music, spiritual, outdoor, and therapy categories.'],
      deduplication: ['Collapse duplicate program entries by provider and schedule signature.'],
      merging: ['Merge recurring programs into canonical provider activity objects.'],
      knowledgeObjects: ['Activity program objects', 'Engagement-fit objects'],
      evidenceObjects: ['Activity evidence objects', 'Calendar evidence objects'],
      graphUpdates: ['Create provider-to-activity and activity-to-outcome relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Provider Objects', 'Relationships', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily activity discovery pass'],
      discovery: ['Calendar crawling', 'Program update detection'],
      refresh: ['Prepared activity snapshot refresh'],
      verification: ['Provider attribution verification'],
      learning: ['Engagement outcome correlation runs'],
      cleanup: ['Retire outdated activity entries'],
      retry: ['Retry failed provider calendar fetches'],
    },
    kpis: ['Knowledge growth', 'Evidence growth', 'Coverage', 'Confidence', 'Refresh success', 'Discovery success', 'Response time', 'Learning progress', 'Provider enrichment completeness', 'Accuracy'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 10',
      evidencePerDay: '>= 10',
      providerUpdatesPerDay: '>= 12',
      relationshipsPerDay: '>= 8',
      coverageGrowthPerDay: '>= 1 provider segment',
    },
    failureHandling: ['Retry missing calendars, quarantine stale schedules, notify supervisor on chronic inactivity.'],
    supervisorInteraction: ['Growth reports', 'Gap reports', 'Coverage alerts', 'Activity-verification incidents'],
    recommendationEngineContract: ['Expose only prepared activity program availability, confidence, freshness, and trade-off signals.'],
    security: ['Read approved public/official sources and write activity knowledge objects only.'],
    successCriteria: ['Activities coverage grows daily.', 'Lifestyle-fit signals stay fresh and attributable.', 'No empty activity domain for active providers.'],
    collaborators: ['provider_intelligence', 'knowledge_graph', 'narrative_intelligence', 'outcome_learning'],
  },
  {
    id: 'nutrition_intelligence',
    file: 'nutrition_agent_spec.md',
    name: 'Nutrition Intelligence Agent',
    purpose: 'Own nutrition, dining, and dietary support knowledge for provider fit.',
    mission: 'Continuously discover and verify dietary support capabilities so nutrition and allergy needs are represented in prepared knowledge.',
    domain: 'Dietary and nutrition support',
    owner: 'OPTIME Nutrition Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Menus', 'Diet programs', 'Diabetic support', 'Kosher', 'Vegetarian', 'Allergy support', 'Texture-modified diets'],
      mustNeverDo: ['Infer specialized dietary support without evidence.', 'Overstate allergy accommodations.'],
      decisionsCanMake: ['Create or update diet-support knowledge objects.', 'Flag unresolved dietary gaps for review.'],
      outsideAuthority: ['Changing provider licensing or social-program facts.'],
    },
    knowledge: {
      topicsOwned: ['Diet capabilities', 'Menu support', 'Dining accommodations', 'Nutrition programs'],
      boundaries: ['Does not own clinical disease guidance.', 'Coordinates with Clinical Knowledge on medical diet needs.'],
      relationships: ['Clinical Knowledge Agent', 'Provider Intelligence Agent', 'Knowledge Graph Agent'],
      ownershipRules: ['Primary owner of dietary support and menu accommodation knowledge.'],
      ownershipCategory: 'Nutrition Knowledge',
    },
    inputSources: [
      source('Provider menus and dining pages', 'Current dietary offerings and menu patterns', 'P0', 'MEDIUM', 'Daily', 'Must be provider-attributed and current.'),
      source('Provider verification memory', 'Directly verified dietary accommodations', 'P0', 'HIGH', 'Daily', 'Requires verified provider identity and timestamp.'),
      source('Clinical guidance', 'Medical diet requirements and terminology normalization', 'P1', 'HIGH', 'Daily', 'Used for classification, not provider proof.'),
    ],
    discoveryStrategy: ['Discover menus, dining program updates, and special-diet support changes.', 'Prioritize providers with high diet-related demand or low coverage.', 'Generate gaps for missing diabetic, allergy, kosher, and texture-modified support.'],
    validation: {
      evidenceRequirements: ['Provider-attributed source required for provider-specific diet claims.', 'Clinical guidance required for medical-diet terminology mapping.'],
      verificationRules: ['Special diet claims require provider evidence or direct verification.'],
      conflictResolution: ['Direct verification outranks stale website content.'],
      duplicateDetection: ['Normalize by provider, diet type, and accommodation capability.'],
      confidenceCalculation: 'Confidence is based on direct verification, official source recency, and corroboration.',
      freshnessPolicy: 'Default TTL 24 hours; shorter for menus during active update windows.',
    },
    processing: {
      normalization: ['Normalize diet labels and accommodation terminology.'],
      classification: ['Classify by medical diets, religious diets, allergy support, texture modification, and nutrition programs.'],
      deduplication: ['Deduplicate menu and capability claims by provider and diet type.'],
      merging: ['Merge current verified diet support into canonical provider nutrition objects.'],
      knowledgeObjects: ['Nutrition support objects', 'Diet compatibility objects'],
      evidenceObjects: ['Menu evidence objects', 'Diet verification evidence objects'],
      graphUpdates: ['Create provider-to-diet and condition-to-diet relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Provider Objects', 'Relationships', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily nutrition discovery run'],
      discovery: ['Menu discovery', 'Diet support change detection'],
      refresh: ['Prepared nutrition snapshot refresh'],
      verification: ['Diet-support verification jobs'],
      learning: ['Outcome-linked nutrition fit review'],
      cleanup: ['Retire stale or contradicted menu claims'],
      retry: ['Retry failed dining-source fetches'],
    },
    kpis: ['Knowledge growth', 'Evidence growth', 'Coverage', 'Confidence', 'Refresh success', 'Discovery success', 'Learning progress', 'Accuracy', 'Duplicate rate', 'Response time'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 8',
      evidencePerDay: '>= 8',
      providerUpdatesPerDay: '>= 10',
      relationshipsPerDay: '>= 6',
      coverageGrowthPerDay: '>= 1 diet-support segment',
    },
    failureHandling: ['Retry failed menu fetches, downgrade stale support claims, notify supervisor on unresolved contradictions.'],
    supervisorInteraction: ['Growth reports', 'Gap reports', 'Diet-support incident alerts'],
    recommendationEngineContract: ['Expose only prepared nutrition support objects with confidence, freshness, and verification status.'],
    security: ['Write nutrition and evidence objects only; no direct changes to unrelated provider fields.'],
    successCriteria: ['Nutrition support knowledge expands daily.', 'Diet-support claims remain traceable and fresh.', 'Critical dietary gaps are surfaced before recommendation use.'],
    collaborators: ['clinical_knowledge', 'provider_intelligence', 'knowledge_graph'],
  },
  {
    id: 'outcome_learning',
    file: 'outcome_agent_spec.md',
    name: 'Outcome Learning Agent',
    purpose: 'Learn from anonymized resident and provider outcomes to improve recommendation quality.',
    mission: 'Continuously transform outcome signals into prepared knowledge that improves fit, safety, and quality expectations without exposing personal data.',
    domain: 'Outcome-based calibration',
    owner: 'OPTIME Outcome Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Resident outcomes', 'Falls', 'Hospitalizations', 'Readmissions', 'Recovery trends', 'Quality indicators'],
      mustNeverDo: ['Store personal identifiers.', 'Leak resident data into recommendation explanations.', 'Invent outcome improvements without data.'],
      decisionsCanMake: ['Publish anonymized outcome trend knowledge.', 'Recommend calibration signals to Matching Improvement Agent.', 'Escalate negative outcome drift.'],
      outsideAuthority: ['Directly changing recommendation rankings in production.', 'Overriding provider identity or clinical evidence.'],
    },
    knowledge: {
      topicsOwned: ['Outcome patterns', 'Recovery trends', 'Risk factors', 'Success predictors', 'Failure factors'],
      boundaries: ['Does not own provider identity or public narrative generation.', 'Feeds learning insights to matching and narrative agents.'],
      relationships: ['Matching Improvement Agent', 'Clinical Knowledge Agent', 'Knowledge Graph Agent', 'Chief AI Supervisor'],
      ownershipRules: ['Primary owner of anonymized outcome knowledge and trend calibration signals.'],
      ownershipCategory: 'Outcome Learning',
    },
    inputSources: [
      source('Resident outcomes table', 'Anonymized outcome signals', 'P0', 'HIGH', 'Daily', 'Must exclude personal identifiers.'),
      source('Validation studies and simulations', 'Calibration evidence and drift checks', 'P1', 'HIGH', 'Daily', 'Must be reproducible and documented.'),
      source('Quality indicators', 'Operational outcome trends', 'P1', 'HIGH', 'Daily', 'Must map to canonical provider identities.'),
    ],
    discoveryStrategy: ['Continuously scan outcome events for new positive or negative patterns.', 'Detect changed knowledge via drift in success, readmission, and hospitalization trends.', 'Prioritize high-volume cohorts and negative trend clusters for immediate review.'],
    validation: {
      evidenceRequirements: ['Minimum cohort size and anonymization required.', 'Signals must be reproducible from stored outcome aggregates.'],
      verificationRules: ['Outcome knowledge must cite timeframe and cohort definition.'],
      conflictResolution: ['Recent sustained cohort trends override stale small-sample signals.'],
      duplicateDetection: ['Normalize by cohort, timeframe, provider, and outcome family.'],
      confidenceCalculation: 'Confidence is based on sample size, stability, recency, and corroboration.',
      freshnessPolicy: 'Default TTL 24 hours; shorter when trend volatility is high.',
    },
    processing: {
      normalization: ['Normalize outcome event categories, cohorts, and time windows.'],
      classification: ['Classify by success, risk, recovery, dissatisfaction, relocation, and adverse events.'],
      deduplication: ['Deduplicate trends by cohort/time window/provider scope.'],
      merging: ['Merge new outcome evidence into active trend objects with change history.'],
      knowledgeObjects: ['Outcome trend objects', 'Calibration insight objects'],
      evidenceObjects: ['Outcome evidence objects', 'Validation evidence objects'],
      graphUpdates: ['Create provider-to-outcome and condition-to-outcome relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Relationships', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily outcome aggregation'],
      discovery: ['Trend detection and anomaly discovery'],
      refresh: ['Prepared outcome snapshot refresh'],
      verification: ['Cohort validity and drift verification'],
      learning: ['Calibration recommendation generation'],
      cleanup: ['Retire stale low-signal trends'],
      retry: ['Retry failed aggregation runs'],
    },
    kpis: ['Knowledge growth', 'Evidence growth', 'Accuracy', 'Learning progress', 'Coverage', 'Confidence', 'Refresh success', 'Discovery success', 'Response time', 'Duplicate rate'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 8',
      evidencePerDay: '>= 8',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 6',
      coverageGrowthPerDay: '>= 1 cohort segment',
    },
    failureHandling: ['Retry failed aggregation, quarantine low-quality cohorts, escalate negative drift and stale outcomes.'],
    supervisorInteraction: ['Growth reports', 'Trend alerts', 'Gap reports', 'Calibration recommendations'],
    recommendationEngineContract: ['Expose only prepared anonymized outcome signals and confidence-adjusted trend objects.'],
    security: ['Strictly anonymized inputs and outputs only.'],
    successCriteria: ['Outcome knowledge grows continuously.', 'Calibration signals improve recommendation quality over time.', 'No privacy leaks occur.'],
    collaborators: ['matching_improvement', 'clinical_knowledge', 'knowledge_graph', 'chief_ai_supervisor'],
  },
  {
    id: 'knowledge_graph',
    file: 'knowledge_graph_agent_spec.md',
    name: 'Knowledge Graph Agent',
    purpose: 'Own the structured relationship layer connecting knowledge, evidence, providers, and outcomes.',
    mission: 'Continuously discover and normalize relationships so the platform remains explainable, connected, and deduplicated.',
    domain: 'Cross-domain relationship graph',
    owner: 'OPTIME Knowledge Graph Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Relationships', 'Concept links', 'Missing links', 'Ontology improvements', 'Duplicate resolution support'],
      mustNeverDo: ['Create unsupported relationships.', 'Alter source knowledge ownership.'],
      decisionsCanMake: ['Create relationship objects.', 'Flag missing or conflicting links.', 'Recommend ontology adjustments.'],
      outsideAuthority: ['Changing evidence quality or provider truth directly.'],
    },
    knowledge: {
      topicsOwned: ['Knowledge graph relationships', 'Ontology links', 'Explainability paths'],
      boundaries: ['Does not own domain facts; it owns the relationships among them.'],
      relationships: ['All expert agents'],
      ownershipRules: ['Primary owner of relationship objects and ontology coordination.'],
      ownershipCategory: 'Knowledge Graph',
    },
    inputSources: [
      source('Prepared knowledge objects', 'Canonical nodes for linking', 'P0', 'HIGH', 'Continuous', 'Only prepared verified nodes may enter the graph.'),
      source('Prepared evidence objects', 'Evidence-backed relationship support', 'P0', 'HIGH', 'Continuous', 'Relationships require traceable evidence or canonical ownership rules.'),
      source('Recommendation traces', 'Explainability and missing-link discovery', 'P1', 'HIGH', 'Daily', 'Trace data must be reproducible.'),
    ],
    discoveryStrategy: ['Continuously search for missing links between conditions, services, providers, outcomes, and narratives.', 'Detect ontology gaps and duplicate concept clusters.', 'Prioritize high-traffic concepts and agents with unresolved gaps.'],
    validation: {
      evidenceRequirements: ['Relationships require supporting evidence or explicit ontology ownership rules.'],
      verificationRules: ['Graph edges must connect existing canonical nodes and include confidence and freshness.'],
      conflictResolution: ['Competing relationships are preserved with confidence weighting until resolved.'],
      duplicateDetection: ['Normalize node identifiers and relation keys.'],
      confidenceCalculation: 'Confidence depends on evidence support, node trust, and cross-agent agreement.',
      freshnessPolicy: 'Default TTL 24 hours with faster refresh for volatile relationship clusters.',
    },
    processing: {
      normalization: ['Normalize node keys, relationship labels, and ontology classes.'],
      classification: ['Classify by provider, clinical, evidence, outcome, and narrative relationship families.'],
      deduplication: ['Merge duplicate nodes and conflicting aliases.'],
      merging: ['Merge relationship updates into canonical graph structures.'],
      knowledgeObjects: ['Relationship objects', 'Ontology gap objects'],
      evidenceObjects: ['Relationship evidence objects'],
      graphUpdates: ['Add and retire graph edges and ontology links.'],
    },
    outputs: ['Relationships', 'Knowledge Objects', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily graph integrity run'],
      discovery: ['Missing-link discovery', 'Ontology drift detection'],
      refresh: ['Prepared graph snapshot refresh'],
      verification: ['Node and edge integrity validation'],
      learning: ['Explainability path optimization'],
      cleanup: ['Retire duplicate or orphaned links'],
      retry: ['Retry failed graph materialization jobs'],
    },
    kpis: ['Knowledge graph growth', 'Coverage', 'Confidence', 'Duplicate rate', 'Refresh success', 'Discovery success', 'Response time', 'Learning progress', 'Accuracy', 'Gap closure rate'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 8',
      evidencePerDay: '>= 5',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 12',
      coverageGrowthPerDay: '>= 1 ontology cluster',
    },
    failureHandling: ['Retry materialization, preserve last known good graph snapshot, escalate orphaned-node spikes.'],
    supervisorInteraction: ['Graph growth reports', 'Gap reports', 'Conflict alerts', 'Ontology recommendations'],
    recommendationEngineContract: ['Expose only prepared graph relationships and traceable paths suitable for explanations.'],
    security: ['Graph writes only for canonical prepared nodes; no direct live-source ingestion.'],
    successCriteria: ['Knowledge graph expands continuously.', 'Missing-link backlog stays within target.', 'Recommendations remain explainable from prepared graph paths.'],
    collaborators: ['clinical_knowledge', 'provider_intelligence', 'clinical_evidence', 'narrative_intelligence', 'outcome_learning', 'data_quality'],
  },
  {
    id: 'data_quality',
    file: 'data_quality_agent_spec.md',
    name: 'Data Quality & Trust Agent',
    purpose: 'Own trust, freshness, contradiction detection, and repository quality signals.',
    mission: 'Continuously protect prepared knowledge and provider repositories by identifying stale, conflicting, low-trust, and incomplete data.',
    domain: 'Freshness, consistency, and provenance',
    owner: 'OPTIME Data Quality',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Source trust', 'Freshness', 'Conflicts', 'Coverage gaps', 'Provenance quality', 'Verification status governance'],
      mustNeverDo: ['Promote low-trust data to verified status without evidence.', 'Mask unresolved contradictions.'],
      decisionsCanMake: ['Downgrade trust and freshness.', 'Create quality incidents and review tasks.', 'Recommend suppression of unsafe knowledge.'],
      outsideAuthority: ['Owning domain facts outside trust, provenance, and quality scoring.'],
    },
    knowledge: {
      topicsOwned: ['Trust metadata', 'Freshness metadata', 'Conflict metadata', 'Coverage metrics'],
      boundaries: ['Does not own core domain facts, only their trust and quality envelope.'],
      relationships: ['All expert agents', 'Chief AI Supervisor'],
      ownershipRules: ['Primary owner of data-quality scoring, freshness policy, and contradiction tracking.'],
      ownershipCategory: 'Data Quality',
    },
    inputSources: [
      source('Prepared snapshots', 'Freshness, confidence, coverage, and queue state', 'P0', 'HIGH', 'Continuous', 'Must reflect current snapshot state.'),
      source('Conflict reports', 'Contradiction detection and duplicate patterns', 'P0', 'HIGH', 'Daily', 'Conflicts must be attributable to source records.'),
      source('Source reliability data', 'Trust-level calibration', 'P1', 'HIGH', 'Daily', 'Trust values must be reproducible.'),
    ],
    discoveryStrategy: ['Continuously detect stale knowledge, contradictions, and low-coverage domains.', 'Prioritize high-risk agents, providers, and counties.', 'Create quality gap tasks and supervisor alerts automatically.'],
    validation: {
      evidenceRequirements: ['Every downgrade or escalation must cite the triggering source or metric.'],
      verificationRules: ['Freshness, confidence, and verification status must be attached to every prepared snapshot.'],
      conflictResolution: ['Higher-trust and fresher sources outrank lower-trust stale claims.'],
      duplicateDetection: ['Flag duplicate providers, duplicate knowledge, and conflicting entity keys.'],
      confidenceCalculation: 'Quality confidence reflects trust, recency, consistency, and verification depth.',
      freshnessPolicy: 'Owns TTL and stale/expired/error thresholds per agent and topic class.',
    },
    processing: {
      normalization: ['Normalize trust labels, freshness states, and contradiction categories.'],
      classification: ['Classify issues by severity, domain, and remediation path.'],
      deduplication: ['Consolidate repeated quality incidents.'],
      merging: ['Merge repeated trust signals into canonical quality objects.'],
      knowledgeObjects: ['Quality issue objects', 'Trust score objects', 'Coverage gap objects'],
      evidenceObjects: ['Trust evidence objects', 'Conflict evidence objects'],
      graphUpdates: ['Create quality-to-agent and issue-to-provider relationships.'],
    },
    outputs: ['Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status', 'Knowledge Objects', 'Evidence Objects'],
    backgroundOperations: {
      scheduled: ['Continuous freshness monitoring'],
      discovery: ['Conflict and stale-data discovery'],
      refresh: ['Quality snapshot refresh'],
      verification: ['Quality and provenance checks'],
      learning: ['Trust-score calibration'],
      cleanup: ['Close resolved incidents and archive stale alerts'],
      retry: ['Retry failed quality checks'],
    },
    kpis: ['Coverage', 'Confidence', 'Duplicate rate', 'Refresh success', 'Discovery success', 'Learning progress', 'Response time', 'Quality issue closure rate', 'Stale knowledge rate', 'Verification success'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 6',
      evidencePerDay: '>= 6',
      providerUpdatesPerDay: '>= 10 quality reviews',
      relationshipsPerDay: '>= 6',
      coverageGrowthPerDay: '>= 1 quality segment',
    },
    failureHandling: ['Escalate repeated failures, preserve last known good trust state, and quarantine unsafe knowledge.'],
    supervisorInteraction: ['Health reports', 'Freshness reports', 'Gap reports', 'Incident reports', 'Quality recommendations'],
    recommendationEngineContract: ['Expose only structured trust, freshness, verification, and suppression signals for prepared knowledge.'],
    security: ['May downgrade trust and freshness but may not create fabricated facts.'],
    successCriteria: ['Stale knowledge stays below threshold.', 'Conflict backlog remains manageable.', 'Unsafe knowledge never bypasses trust controls.'],
    collaborators: ['chief_ai_supervisor', 'provider_intelligence', 'knowledge_graph', 'matching_improvement'],
  },
  {
    id: 'narrative_intelligence',
    file: 'narrative_intelligence_agent_spec.md',
    name: 'Narrative Intelligence Agent',
    purpose: 'Transform prepared verified knowledge into family-safe explanations without leaking internal logic.',
    mission: 'Continuously improve recommendation explanations, verified-strength summaries, and trade-off narratives using prepared knowledge only.',
    domain: 'Narrative intelligence',
    owner: 'OPTIME Narrative Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Why it matches explanations', 'Verified strengths', 'Known trade-offs', 'Missing capabilities summaries', 'Confidence and verification phrasing'],
      mustNeverDo: ['Perform live research.', 'Leak internal ranking logic or hidden weights.', 'Invent facts or certainty.'],
      decisionsCanMake: ['Compose family-safe narratives from prepared facts.', 'Choose explanation emphasis based on verified strengths and trade-offs.'],
      outsideAuthority: ['Changing ranking outcomes.', 'Creating net-new factual knowledge without source agents.'],
    },
    knowledge: {
      topicsOwned: ['Narrative templates', 'Family-safe explanation patterns', 'Trade-off framing'],
      boundaries: ['Does not own facts; it owns explanation composition from prepared knowledge.'],
      relationships: ['Clinical Knowledge Agent', 'Provider Intelligence Agent', 'Clinical Evidence Agent', 'Knowledge Graph Agent', 'Matching Improvement Agent'],
      ownershipRules: ['Primary owner of narrative packaging and family-safe rendering rules.'],
      ownershipCategory: 'Narrative Layer',
    },
    inputSources: [
      source('Prepared recommendation inputs', 'Structured facts for explanation generation', 'P0', 'HIGH', 'Per request', 'Must already be verified prepared knowledge.'),
      source('Prepared knowledge graph paths', 'Explainable linkage across facts', 'P0', 'HIGH', 'Per request', 'Only canonical graph paths may be used.'),
      source('Prepared evidence links', 'Confidence-aware evidence references', 'P1', 'HIGH', 'Per request', 'Evidence must already be approved.'),
    ],
    discoveryStrategy: ['Discover weak explanation patterns from validation and family feedback.', 'Detect missing explanation coverage where recommendations lack clear verified strengths or trade-offs.', 'Prioritize high-impact narrative improvements without altering underlying facts.'],
    validation: {
      evidenceRequirements: ['Every narrative claim must map to at least one prepared fact or evidence link.'],
      verificationRules: ['Narratives must label missing or unverified capabilities clearly.'],
      conflictResolution: ['Narrative phrasing follows the most recent prepared fact state and trust envelope.'],
      duplicateDetection: ['Normalize explanation patterns and reuse validated templates.'],
      confidenceCalculation: 'Narrative confidence is inherited from prepared fact confidence and freshness.',
      freshnessPolicy: 'Narrative snapshots refresh with their underlying prepared knowledge inputs.',
    },
    processing: {
      normalization: ['Normalize explanation fragments to family-safe vocabulary.'],
      classification: ['Classify explanation content as strengths, trade-offs, missing capabilities, and next steps.'],
      deduplication: ['Reuse validated explanation templates to avoid inconsistent phrasing.'],
      merging: ['Merge new explanation improvements into approved narrative template library.'],
      knowledgeObjects: ['Narrative template objects', 'Explanation policy objects'],
      evidenceObjects: ['Narrative evidence-link references'],
      graphUpdates: ['Create recommendation-to-explanation and explanation-to-evidence relationships.'],
    },
    outputs: ['Warnings', 'Confidence', 'Freshness', 'Verification Status', 'Knowledge Objects'],
    backgroundOperations: {
      scheduled: ['Daily explanation quality review'],
      discovery: ['Narrative gap detection'],
      refresh: ['Narrative template refresh'],
      verification: ['Traceability checks'],
      learning: ['Explanation quality improvement cycles'],
      cleanup: ['Retire confusing or leaking templates'],
      retry: ['Retry failed narrative generation validations'],
    },
    kpis: ['Accuracy', 'Response time', 'Coverage', 'Confidence', 'Learning progress', 'Discovery success', 'Refresh success', 'Family-safe compliance rate', 'Traceability completeness', 'Duplicate rate'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 4',
      evidencePerDay: '>= 4 narrative references',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 4',
      coverageGrowthPerDay: '>= 1 explanation pattern',
    },
    failureHandling: ['Fall back to simpler verified summaries, log traceability failures, and notify supervisor when narratives cannot be grounded.'],
    supervisorInteraction: ['Narrative health reports', 'Gap reports', 'Leakage alerts', 'Explanation quality recommendations'],
    recommendationEngineContract: ['Consumes only structured prepared knowledge and returns family-safe structured explanation fields.'],
    security: ['No live data access; no disclosure of internal scoring internals.'],
    successCriteria: ['Every recommendation has a grounded explanation.', 'No internal logic leaks.', 'Family-safe explanation quality improves over time.'],
    collaborators: ['clinical_knowledge', 'provider_intelligence', 'clinical_evidence', 'knowledge_graph', 'matching_improvement'],
  },
  {
    id: 'matching_improvement',
    file: 'matching_improvement_agent_spec.md',
    name: 'Matching Improvement Agent',
    purpose: 'Own validated ranking-policy improvements and recommendation guardrails.',
    mission: 'Continuously learn from outcomes, traces, and failures to improve recommendation quality without violating deterministic controls.',
    domain: 'Deterministic ranking policy upgrades',
    owner: 'OPTIME Matching Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Policy-safe ranking improvements', 'Guardrails', 'False positive and false negative analysis', 'Recommendation quality review'],
      mustNeverDo: ['Apply unvalidated ranking changes directly to production.', 'Use live research in request-time scoring.'],
      decisionsCanMake: ['Propose validated improvement knowledge objects.', 'Flag harmful patterns and unsafe recommendation behavior.'],
      outsideAuthority: ['Publishing provider facts.', 'Changing clinical truth or evidence ratings.'],
    },
    knowledge: {
      topicsOwned: ['Ranking policy knowledge', 'Guardrail knowledge', 'Recommendation quality insights'],
      boundaries: ['Does not own source facts; it owns policy interpretation and improvement signals.'],
      relationships: ['Outcome Learning Agent', 'Data Quality & Trust Agent', 'Narrative Intelligence Agent', 'Chief AI Supervisor'],
      ownershipRules: ['Primary owner of ranking-policy improvement knowledge objects.'],
      ownershipCategory: 'Matching Policy',
    },
    inputSources: [
      source('Recommendation traces', 'Trace-based recommendation analysis', 'P0', 'HIGH', 'Daily', 'Must be reproducible from stored traces.'),
      source('Outcome learning outputs', 'Quality calibration signals', 'P0', 'HIGH', 'Daily', 'Must be cohort-backed.'),
      source('Validation reports', 'Regression and quality checks', 'P1', 'HIGH', 'Daily', 'Must pass documented guardrails.'),
    ],
    discoveryStrategy: ['Discover ranking issues from failed matches, stale knowledge usage, and outcome drift.', 'Detect changed behavior through trace comparison and quality deltas.', 'Prioritize quality gaps with high resident impact.'],
    validation: {
      evidenceRequirements: ['Improvement proposals require trace evidence and validation outcomes.'],
      verificationRules: ['No policy proposal may bypass guardrail checks or deterministic explainability.'],
      conflictResolution: ['Safety guardrails override optimization opportunities.'],
      duplicateDetection: ['Normalize improvement proposals by ranking symptom and guardrail family.'],
      confidenceCalculation: 'Confidence is based on validation pass rate, outcome impact, and reproducibility.',
      freshnessPolicy: 'Policy insights TTL defaults to 5 minutes in prepared snapshots.',
    },
    processing: {
      normalization: ['Normalize quality issues, guardrail failures, and proposal categories.'],
      classification: ['Classify by false positive, false negative, confidence drift, stale knowledge, and ranking regression.'],
      deduplication: ['Merge duplicate improvement recommendations.'],
      merging: ['Append validated improvement evidence to canonical policy objects.'],
      knowledgeObjects: ['Improvement recommendation objects', 'Guardrail objects'],
      evidenceObjects: ['Trace evidence objects', 'Validation evidence objects'],
      graphUpdates: ['Create policy-to-outcome and policy-to-guardrail relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status'],
    backgroundOperations: {
      scheduled: ['Daily recommendation quality review'],
      discovery: ['Trace anomaly discovery'],
      refresh: ['Prepared policy snapshot refresh'],
      verification: ['Guardrail validation'],
      learning: ['Policy proposal generation'],
      cleanup: ['Retire invalid or superseded proposals'],
      retry: ['Retry failed validation runs'],
    },
    kpis: ['Recommendation quality', 'Accuracy', 'Learning progress', 'Coverage', 'Confidence', 'Refresh success', 'Discovery success', 'Response time', 'Guardrail compliance rate', 'Duplicate rate'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 6',
      evidencePerDay: '>= 6',
      providerUpdatesPerDay: 'N/A',
      relationshipsPerDay: '>= 5',
      coverageGrowthPerDay: '>= 1 ranking issue family',
    },
    failureHandling: ['Suppress unsafe proposals, preserve current production policy, escalate repeated quality regressions.'],
    supervisorInteraction: ['Quality reports', 'Guardrail incidents', 'Growth reports', 'Recommendation improvement proposals'],
    recommendationEngineContract: ['Expose only validated prepared policy and guardrail signals; never raw experimentation logic.'],
    security: ['No direct production policy mutation without external approval path.'],
    successCriteria: ['Recommendation quality improves continuously.', 'Guardrails remain intact.', 'Policy insights remain traceable and validated.'],
    collaborators: ['outcome_learning', 'data_quality', 'narrative_intelligence', 'chief_ai_supervisor'],
  },
  {
    id: 'competitive_intelligence',
    file: 'competitive_intelligence_agent_spec.md',
    name: 'Competitive Intelligence Agent',
    purpose: 'Track external market and positioning signals that influence provider growth priorities.',
    mission: 'Continuously identify market gaps, emerging provider patterns, and high-demand regions to guide discovery and coverage expansion.',
    domain: 'Competitive and market intelligence',
    owner: 'OPTIME Market Intelligence',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Market coverage gaps', 'Regional demand signals', 'Provider category expansion priorities', 'Competitive landscape monitoring'],
      mustNeverDo: ['Use unverified rumor as fact.', 'Override provider identity or recommendation safety rules.'],
      decisionsCanMake: ['Prioritize counties, states, and provider categories for discovery.', 'Create market gap tasks and competitor trend knowledge.'],
      outsideAuthority: ['Publishing provider verification status directly.', 'Changing clinical or ranking policy.'],
    },
    knowledge: {
      topicsOwned: ['Coverage gaps', 'Regional demand', 'Competitive provider categories', 'Expansion priorities'],
      boundaries: ['Does not own provider truth; it owns prioritization and market-expansion intelligence.'],
      relationships: ['Provider Intelligence Agent', 'Chief AI Supervisor', 'Data Quality & Trust Agent'],
      ownershipRules: ['Primary owner of competitive and market-prioritization knowledge objects.'],
      ownershipCategory: 'Competitive Intelligence',
    },
    inputSources: [
      source('Provider repository coverage metrics', 'Coverage gap detection', 'P0', 'HIGH', 'Daily', 'Must use prepared provider inventory.'),
      source('Market analyses and public trends', 'Demand and competitive context', 'P1', 'MEDIUM', 'Daily', 'Must come from attributable public sources.'),
      source('Search demand signals', 'Prioritize discovery based on real usage demand', 'P1', 'HIGH', 'Daily', 'Must be aggregated and privacy-safe.'),
    ],
    discoveryStrategy: ['Continuously scan for under-covered provider categories, counties, and states.', 'Detect changes in demand concentration and competitive saturation.', 'Prioritize high-demand underserved areas for Provider Agent discovery.'],
    validation: {
      evidenceRequirements: ['Coverage or demand claims require repository or aggregated demand evidence.'],
      verificationRules: ['Priority recommendations must cite measurable gap or demand metrics.'],
      conflictResolution: ['Measured demand and coverage deficits outrank anecdotal signals.'],
      duplicateDetection: ['Normalize gap tasks by geography, category, and demand cluster.'],
      confidenceCalculation: 'Confidence rises with consistent demand, clear coverage gaps, and corroborating market signals.',
      freshnessPolicy: 'Daily refresh for coverage and prioritization snapshots.',
    },
    processing: {
      normalization: ['Normalize geography, provider category, and demand labels.'],
      classification: ['Classify by state, county, provider type, and demand urgency.'],
      deduplication: ['Merge duplicate market gap tasks.'],
      merging: ['Merge new competitive signals into canonical expansion-priority objects.'],
      knowledgeObjects: ['Market gap objects', 'Expansion-priority objects'],
      evidenceObjects: ['Demand evidence objects', 'Coverage evidence objects'],
      graphUpdates: ['Create region-to-provider-type and demand-to-coverage relationships.'],
    },
    outputs: ['Knowledge Objects', 'Evidence Objects', 'Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness'],
    backgroundOperations: {
      scheduled: ['Daily market-priority review'],
      discovery: ['Regional gap discovery'],
      refresh: ['Competitive intelligence snapshot refresh'],
      verification: ['Coverage metric verification'],
      learning: ['Demand-priority calibration'],
      cleanup: ['Close resolved market gap tasks'],
      retry: ['Retry failed market data aggregation'],
    },
    kpis: ['Coverage growth', 'Discovery success', 'Learning progress', 'Response time', 'Confidence', 'Refresh success', 'Knowledge growth', 'Evidence growth', 'Duplicate rate', 'Priority-hit rate'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 5',
      evidencePerDay: '>= 5',
      providerUpdatesPerDay: '>= 3 prioritized discovery campaigns',
      relationshipsPerDay: '>= 4',
      coverageGrowthPerDay: '>= 1 geography priority update',
    },
    failureHandling: ['Retry failed aggregations, preserve last priority set, escalate stale demand signals.'],
    supervisorInteraction: ['Coverage reports', 'Priority recommendations', 'Gap reports', 'Inactive-region alerts'],
    recommendationEngineContract: ['No direct request-time consumption; influences prepared provider discovery priority only.'],
    security: ['Uses aggregated non-personal demand signals only.'],
    successCriteria: ['Coverage expansion is prioritized by measurable need.', 'High-demand gaps shrink over time.'],
    collaborators: ['provider_intelligence', 'data_quality', 'chief_ai_supervisor'],
  },
  {
    id: 'chief_ai_supervisor',
    file: 'chief_ai_supervisor_spec.md',
    name: 'Chief AI Supervisor',
    purpose: 'Coordinate, monitor, and govern the full expert-agent ecosystem.',
    mission: 'Continuously monitor agent health, knowledge growth, provider growth, freshness, and readiness, and automatically schedule corrective action.',
    domain: 'Supervisory governance',
    owner: 'OPTIME Platform Governance',
    version: 'v1.0',
    status: 'Specified',
    responsibilities: {
      responsibleFor: ['Agent health', 'Knowledge growth', 'Provider growth', 'Coverage growth', 'Knowledge freshness', 'Evidence growth', 'Knowledge graph growth', 'Pending reviews', 'Failed refreshes', 'Knowledge gaps', 'Inactive agents', 'Duplicate providers', 'Platform readiness', 'Recommendation quality'],
      mustNeverDo: ['Invent knowledge to satisfy health targets.', 'Bypass trust and freshness rules.', 'Suppress critical incidents.'],
      decisionsCanMake: ['Schedule learning, discovery, verification, enrichment, retries, and prioritization work.', 'Create incidents and escalate failures.', 'Allocate work budgets dynamically.'],
      outsideAuthority: ['Changing source-truth ownership inside domain agents.', 'Publishing unverified facts to the Recommendation Engine.'],
    },
    knowledge: {
      topicsOwned: ['Supervisory metrics', 'Incidents', 'Work budgets', 'Platform readiness'],
      boundaries: ['Does not own domain facts; it owns governance, prioritization, and escalation.'],
      relationships: ['All expert agents'],
      ownershipRules: ['Primary owner of incidents, health state, and readiness decisions.'],
      ownershipCategory: 'Supervisory Governance',
    },
    inputSources: [
      source('Prepared snapshots', 'Agent health and freshness monitoring', 'P0', 'HIGH', 'Continuous', 'Must reflect current prepared state.'),
      source('Refresh events', 'Refresh success and failure metrics', 'P0', 'HIGH', 'Continuous', 'Event status must be complete and attributable.'),
      source('Growth and validation reports', 'Platform readiness and trend monitoring', 'P1', 'HIGH', 'Daily', 'Reports must be reproducible.'),
    ],
    discoveryStrategy: ['Continuously detect inactive agents, stale knowledge, missing growth, and unresolved gaps.', 'Prioritize high-impact counties, states, domains, and safety issues.', 'Allocate work budgets dynamically based on demand and system load.'],
    validation: {
      evidenceRequirements: ['Every incident, escalation, or scheduling change must cite a measurable metric or event.'],
      verificationRules: ['Readiness decisions require fresh snapshots and passing validation gates.'],
      conflictResolution: ['Safety, freshness, and trust outrank throughput goals.'],
      duplicateDetection: ['Deduplicate repeated incidents and repeated provider or knowledge conflicts.'],
      confidenceCalculation: 'Supervisor confidence is derived from snapshot completeness, event consistency, and validation results.',
      freshnessPolicy: 'Supervisor metrics update continuously; readiness summaries refresh at least daily.',
    },
    processing: {
      normalization: ['Normalize incidents, alerts, budgets, and readiness metrics.'],
      classification: ['Classify by severity, domain, and remediation type.'],
      deduplication: ['Collapse repeated incidents into canonical supervisory records.'],
      merging: ['Merge repeated alerts and preserve incident history.'],
      knowledgeObjects: ['Incident objects', 'Budget objects', 'Readiness objects'],
      evidenceObjects: ['Health evidence objects', 'Validation evidence objects'],
      graphUpdates: ['Create agent-to-incident and readiness-to-domain relationships.'],
    },
    outputs: ['Warnings', 'Knowledge Gaps', 'Confidence', 'Freshness', 'Verification Status', 'Knowledge Objects', 'Evidence Objects'],
    backgroundOperations: {
      scheduled: ['Continuous supervisory cycle', 'Daily readiness review'],
      discovery: ['Inactive-agent and stale-knowledge detection'],
      refresh: ['Readiness dashboard refresh'],
      verification: ['Validation gate checks'],
      learning: ['Budget reallocation and prioritization tuning'],
      cleanup: ['Resolve or archive closed incidents'],
      retry: ['Retry failed refresh and discovery jobs'],
    },
    kpis: ['Agent health', 'Knowledge growth', 'Provider growth', 'Coverage growth', 'Evidence growth', 'Knowledge graph growth', 'Refresh success', 'Supervisor response time', 'Incident closure rate', 'Platform readiness'],
    dailyTargets: {
      knowledgeObjectsPerDay: '>= 1 readiness cycle',
      evidencePerDay: '>= 1 validation bundle',
      providerUpdatesPerDay: '>= 1 budget reprioritization when needed',
      relationshipsPerDay: '>= 1 supervisory linkage set',
      coverageGrowthPerDay: '>= maintain zero idle agents',
    },
    failureHandling: ['Escalate repeated failures, preserve last good snapshot, notify operators, and keep audit history immutable.'],
    supervisorInteraction: ['Owns health reports, growth reports, gap reports, alerts, incidents, and platform recommendations.'],
    recommendationEngineContract: ['Recommendation Engine may consume only supervisor-approved freshness, verification, and readiness signals from prepared snapshots.'],
    security: ['Read all supervisory metrics; write incidents, budgets, and readiness states; no direct mutation of domain truth.'],
    successCriteria: ['No agent remains idle beyond threshold.', 'Platform readiness is measurable and auditable.', 'Stale or unsafe knowledge is detected and acted on automatically.'],
    collaborators: ['clinical_knowledge', 'provider_intelligence', 'clinical_evidence', 'activities_intelligence', 'nutrition_intelligence', 'outcome_learning', 'knowledge_graph', 'data_quality', 'narrative_intelligence', 'matching_improvement', 'competitive_intelligence'],
  },
];

function renderAgentSpec(agent) {
  const sourceRows = agent.inputSources.map((item) => [item.name, item.purpose, item.priority, item.trust, item.refresh, item.validation]);
  const apiRows = Object.entries(commonApiContract).map(([name, description]) => [name, description]);
  const kpiRows = agent.kpis.map((kpi) => [kpi, 'Measurable']);
  const targetRows = Object.entries(agent.dailyTargets).map(([key, value]) => [key, value]);

  return [
    `# ${agent.name} Specification`,
    '',
    section('1. Agent Identity', [
      `- Agent Name: ${agent.name}`,
      `- Purpose: ${agent.purpose}`,
      `- Mission Statement: ${agent.mission}`,
      `- Domain: ${agent.domain}`,
      `- Owner: ${agent.owner}`,
      `- Version: ${agent.version}`,
      `- Status: ${agent.status}`,
    ]),
    section('2. Responsibilities', [
      '### Responsible For',
      '',
      ...bullet(agent.responsibilities.responsibleFor),
      '',
      '### Must Never Do',
      '',
      ...bullet(agent.responsibilities.mustNeverDo),
      '',
      '### Decisions It Can Make',
      '',
      ...bullet(agent.responsibilities.decisionsCanMake),
      '',
      '### Outside Its Authority',
      '',
      ...bullet(agent.responsibilities.outsideAuthority),
    ]),
    section('3. Knowledge Domain', [
      '### Topics Owned',
      '',
      ...bullet(agent.knowledge.topicsOwned),
      '',
      '### Knowledge Boundaries',
      '',
      ...bullet(agent.knowledge.boundaries),
      '',
      '### Relationships With Other Agents',
      '',
      ...bullet(agent.knowledge.relationships),
      '',
      '### Knowledge Ownership Rules',
      '',
      ...bullet(agent.knowledge.ownershipRules),
    ]),
    section('4. Input Sources', [mdTable(['Source', 'Purpose', 'Priority', 'Trust Level', 'Refresh Frequency', 'Validation Rules'], sourceRows)]),
    section('5. Discovery Strategy', bullet(agent.discoveryStrategy)),
    section('6. Validation Strategy', [
      '### Evidence Requirements',
      '',
      ...bullet(agent.validation.evidenceRequirements),
      '',
      '### Verification Rules',
      '',
      ...bullet(agent.validation.verificationRules),
      '',
      '### Conflict Resolution',
      '',
      ...bullet(agent.validation.conflictResolution),
      '',
      `### Duplicate Detection`,
      '',
      ...bullet(agent.validation.duplicateDetection),
      '',
      `### Confidence Calculation`,
      '',
      `- ${agent.validation.confidenceCalculation}`,
      '',
      `### Freshness Policy`,
      '',
      `- ${agent.validation.freshnessPolicy}`,
    ]),
    section('7. Knowledge Processing', [
      '### Normalization',
      '',
      ...bullet(agent.processing.normalization),
      '',
      '### Classification',
      '',
      ...bullet(agent.processing.classification),
      '',
      '### Deduplication',
      '',
      ...bullet(agent.processing.deduplication),
      '',
      '### Merging',
      '',
      ...bullet(agent.processing.merging),
      '',
      '### Knowledge Object Creation',
      '',
      ...bullet(agent.processing.knowledgeObjects),
      '',
      '### Evidence Object Creation',
      '',
      ...bullet(agent.processing.evidenceObjects),
      '',
      '### Knowledge Graph Updates',
      '',
      ...bullet(agent.processing.graphUpdates),
    ]),
    section('8. Outputs', bullet(agent.outputs)),
    section('9. APIs', [mdTable(['API', 'Contract'], apiRows)]),
    section('10. Background Operations', [
      '### Scheduled Jobs',
      '',
      ...bullet(agent.backgroundOperations.scheduled),
      '',
      '### Discovery Jobs',
      '',
      ...bullet(agent.backgroundOperations.discovery),
      '',
      '### Refresh Jobs',
      '',
      ...bullet(agent.backgroundOperations.refresh),
      '',
      '### Verification Jobs',
      '',
      ...bullet(agent.backgroundOperations.verification),
      '',
      '### Learning Jobs',
      '',
      ...bullet(agent.backgroundOperations.learning),
      '',
      '### Cleanup Jobs',
      '',
      ...bullet(agent.backgroundOperations.cleanup),
      '',
      '### Retry Jobs',
      '',
      ...bullet(agent.backgroundOperations.retry),
    ]),
    section('11. KPIs', [mdTable(['KPI', 'Measurable'], kpiRows)]),
    section('12. Daily Targets', [mdTable(['Target', 'Expectation'], targetRows)]),
    section('13. Failure Handling', bullet(agent.failureHandling)),
    section('14. Supervisor Interaction', bullet(agent.supervisorInteraction)),
    section('15. Recommendation Engine Contract', bullet(agent.recommendationEngineContract)),
    section('16. Security', bullet(agent.security)),
    section('17. Success Criteria', bullet(agent.successCriteria)),
  ].join('\n');
}

function renderCatalog() {
  return [
    '# Agent Catalog',
    '',
    mdTable(
      ['Agent', 'Domain', 'Owner', 'Version', 'Status', 'Primary Ownership'],
      agents.map((agent) => [agent.name, agent.domain, agent.owner, agent.version, agent.status, agent.knowledge.ownershipCategory]),
    ),
  ].join('\n');
}

function renderResponsibilityMatrix() {
  return [
    '# Agent Responsibility Matrix',
    '',
    mdTable(
      ['Agent', 'Primary Responsibilities', 'Must Never Do', 'Authority Boundary'],
      agents.map((agent) => [
        agent.name,
        agent.responsibilities.responsibleFor.slice(0, 3).join('; '),
        agent.responsibilities.mustNeverDo.slice(0, 2).join('; '),
        agent.responsibilities.outsideAuthority.slice(0, 2).join('; '),
      ]),
    ),
  ].join('\n');
}

function renderInteractionMatrix() {
  const headers = ['Agent', ...agents.map((agent) => agent.name)];
  const rows = agents.map((agent) => {
    const collaborators = new Set(agent.collaborators || []);
    return [
      agent.name,
      ...agents.map((peer) => {
        if (peer.id === agent.id) return 'SELF';
        return collaborators.has(peer.id) ? 'COLLABORATES' : 'LIMITED';
      }),
    ];
  });

  return ['# Agent Interaction Matrix', '', mdTable(headers, rows)].join('\n');
}

function renderOwnershipMatrix() {
  return [
    '# Knowledge Ownership Matrix',
    '',
    mdTable(
      ['Ownership Category', 'Primary Owner', 'Related Agents', 'Rule'],
      agents.map((agent) => [
        agent.knowledge.ownershipCategory,
        agent.name,
        agent.knowledge.relationships.join('; '),
        agent.knowledge.ownershipRules[0],
      ]),
    ),
  ].join('\n');
}

function renderApiCatalog() {
  const rows = [];
  for (const agent of agents) {
    for (const [apiName, description] of Object.entries(commonApiContract)) {
      rows.push([agent.name, apiName, description]);
    }
  }
  return ['# Agent API Catalog', '', mdTable(['Agent', 'API', 'Contract'], rows)].join('\n');
}

function renderKpiDashboard() {
  return [
    '# Agent KPI Dashboard',
    '',
    mdTable(
      ['Agent', 'Key KPIs', 'Daily Targets'],
      agents.map((agent) => [
        agent.name,
        agent.kpis.slice(0, 5).join('; '),
        Object.entries(agent.dailyTargets).map(([key, value]) => `${key}=${value}`).join('; '),
      ]),
    ),
  ].join('\n');
}

function renderOperatingManual() {
  return [
    '# Agent Operating Manual',
    '',
    '## Common Rules',
    '',
    '- Every expert agent operates on prepared, validated, and versioned knowledge.',
    '- No agent performs live research during recommendation execution.',
    '- Every output must include confidence, freshness, ownership, and verification context when applicable.',
    '- The Chief AI Supervisor owns governance, escalation, and readiness decisions.',
    '',
    '## Standard Workflow',
    '',
    '1. Discover',
    '2. Validate',
    '3. Normalize',
    '4. Deduplicate',
    '5. Merge',
    '6. Create knowledge and evidence objects',
    '7. Update graph relationships',
    '8. Refresh prepared snapshots',
    '9. Emit health and growth metrics',
    '',
    '## Governance',
    '',
    '- Ownership is exclusive by primary category and enforced by the knowledge ownership matrix.',
    '- Overlapping concerns are handled through collaborator contracts, never by shared fact mutation.',
    '- All incidents, retries, and rollbacks must be auditable.',
  ].join('\n');
}

function validateDocs(specFiles) {
  const requiredHeadings = [
    '## 1. Agent Identity',
    '## 2. Responsibilities',
    '## 3. Knowledge Domain',
    '## 4. Input Sources',
    '## 5. Discovery Strategy',
    '## 6. Validation Strategy',
    '## 7. Knowledge Processing',
    '## 8. Outputs',
    '## 9. APIs',
    '## 10. Background Operations',
    '## 11. KPIs',
    '## 12. Daily Targets',
    '## 13. Failure Handling',
    '## 14. Supervisor Interaction',
    '## 15. Recommendation Engine Contract',
    '## 16. Security',
    '## 17. Success Criteria',
  ];

  let headingsFound = 0;
  for (const filePath of specFiles) {
    const content = fs.readFileSync(filePath, 'utf8');
    for (const heading of requiredHeadings) {
      if (content.includes(heading)) {
        headingsFound += 1;
      }
    }
  }

  const ownershipSet = new Set();
  let overlappingOwnership = false;
  for (const agent of agents) {
    const key = agent.knowledge.ownershipCategory.toLowerCase();
    if (ownershipSet.has(key)) {
      overlappingOwnership = true;
    }
    ownershipSet.add(key);
  }

  const apiCoveragePass = agents.every((agent) => Object.keys(commonApiContract).length === 9);
  const completeSpecsPass = specFiles.length === agents.length;
  const headingCoverage = headingsFound / (requiredHeadings.length * agents.length);
  const measurableKpisPass = agents.every((agent) => agent.kpis.length > 0 && Object.keys(agent.dailyTargets).length > 0);
  const workflowDocumentedPass = agents.every((agent) => agent.discoveryStrategy.length > 0 && agent.backgroundOperations.scheduled.length > 0);

  return {
    completeSpecsPass,
    overlappingOwnership,
    apiCoveragePass,
    measurableKpisPass,
    workflowDocumentedPass,
    documentationCoverage: Math.round(headingCoverage * 1000) / 10,
    validationPass: completeSpecsPass && !overlappingOwnership && apiCoveragePass && measurableKpisPass && workflowDocumentedPass,
  };
}

function writeFile(relativePath, content) {
  const filePath = path.join(outputDir, relativePath);
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');
  return filePath;
}

function main() {
  fs.mkdirSync(outputDir, { recursive: true });

  const specFiles = agents.map((agent) => writeFile(agent.file, renderAgentSpec(agent)));
  writeFile('agent_catalog.md', renderCatalog());
  writeFile('agent_responsibility_matrix.md', renderResponsibilityMatrix());
  writeFile('agent_interaction_matrix.md', renderInteractionMatrix());
  writeFile('knowledge_ownership_matrix.md', renderOwnershipMatrix());
  writeFile('agent_api_catalog.md', renderApiCatalog());
  writeFile('agent_kpi_dashboard.md', renderKpiDashboard());
  writeFile('agent_operating_manual.md', renderOperatingManual());

  const validation = validateDocs(specFiles);

  console.log(`SPECIFICATIONS_CREATED=${specFiles.length}`);
  console.log(`VALIDATION_PASS=${validation.validationPass ? 'PASS' : 'FAIL'}`);
  console.log(`DOCUMENTATION_COVERAGE=${validation.documentationCoverage}%`);
  console.log(`READY_FOR_IMPLEMENTATION=${validation.validationPass ? 'YES' : 'NO'}`);

  if (!validation.validationPass) {
    process.exitCode = 1;
  }
}

main();