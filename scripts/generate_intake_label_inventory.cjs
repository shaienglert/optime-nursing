// Derive the review inventory from the actual questionnaire, never a copied list.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require('../frontend/node_modules/typescript');
const root = path.resolve(__dirname, '..');
const sourcePath = 'frontend/src/lib/intake-questions.ts';
const source = fs.readFileSync(path.join(root, sourcePath), 'utf8');
const cache = new Map();
function load(file) {
  if (cache.has(file)) return cache.get(file);
  const module = { exports: {} };
  cache.set(file, module.exports);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  }}).outputText;
  const requireLocal = name => {
    if (!name.startsWith('@/')) throw Error('Unexpected runtime import: ' + name);
    return load(path.join(root, 'frontend/src', name.slice(2) + '.ts'));
  };
  vm.runInNewContext(code, { module, exports: module.exports, require: requireLocal }, { filename: file });
  return module.exports;
}
const { QUESTIONS } = load(path.join(root, sourcePath));
const inventory = QUESTIONS.map(question => {
  const position = source.indexOf(`id: "${question.id}"`);
  return { id: question.id, kind: question.kind, prompt: question.prompt,
    source: `${sourcePath}:${source.slice(0, position).split('\n').length}`,
    required: question.required, options: question.options || [],
    read: String(question.get), write: String(question.set),
    semantic_review: 'PENDING_REVIEW_EXISTING_BEHAVIOR_NOT_CHANGED' };
});
const target = path.join(root, 'docs/generated/intake-label-inventory.json');
const content = JSON.stringify({ question_count: inventory.length,
  option_count: inventory.reduce((n,q) => n + q.options.length, 0), questions: inventory }, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== content) {
    console.error('Questionnaire labels or source access changed: regenerate and review the inventory.');
    process.exit(1);
  }
} else fs.writeFileSync(target, content);
console.log(`${inventory.length} questions; ${inventory.reduce((n,q) => n + q.options.length, 0)} option labels`);
