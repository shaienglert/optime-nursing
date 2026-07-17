const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');

function read(relativePath) {
  const filePath = path.join(repoRoot, relativePath);
  return fs.readFileSync(filePath, 'utf8');
}

function hasAll(text, required) {
  return required.every((token) => text.includes(token));
}

function main() {
  const failures = [];

  const clinical = read(path.join('reports', 'clinical_knowledge_platform.md'));
  const architecture = read(path.join('reports', 'agent_architecture.md'));
  const graph = read(path.join('reports', 'knowledge_graph_design.md'));

  const agents = [
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
  ];

  if (!hasAll(architecture, agents)) {
    failures.push('Agent architecture report is missing one or more required agents.');
  }

  const rules = [
    'Agents NEVER modify verified facility data',
    'Agents cannot invent facts',
  ];

  if (!hasAll(architecture, rules)) {
    failures.push('Agent architecture report is missing required platform rules.');
  }

  const clinicalSources = ['CMS', 'PubMed', 'NIH', 'CDC', 'AGS', 'Cochrane', 'AHRQ', 'JAMA', 'NEJM'];
  if (!hasAll(clinical, clinicalSources)) {
    failures.push('Clinical platform report is missing one or more required trusted sources.');
  }

  const graphTables = ['kg_entities', 'kg_relationships', 'kg_source_lineage', 'kg_conflict_edges'];
  if (!hasAll(graph, graphTables)) {
    failures.push('Knowledge graph design report is missing required graph tables.');
  }

  const dbRequirement = ['Database Design', 'Table:'];
  if (!hasAll(architecture, dbRequirement) || !hasAll(clinical, dbRequirement) || !hasAll(graph, dbRequirement)) {
    failures.push('One or more reports do not include explicit database table design.');
  }

  if (failures.length > 0) {
    console.log('AGENT_PLATFORM_PASS=FAIL');
    failures.forEach((failure) => console.log(`- ${failure}`));
    process.exit(1);
  }

  console.log('AGENT_PLATFORM_PASS=PASS');
}

main();
