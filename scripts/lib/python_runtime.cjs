const fs = require('fs');
const path = require('path');

function resolveCanonicalPython(repoRoot) {
  const overrideRaw = process.env.OPTIME_PYTHON ? String(process.env.OPTIME_PYTHON).trim() : '';
  const override = overrideRaw
    ? (path.isAbsolute(overrideRaw) ? overrideRaw : path.join(repoRoot, overrideRaw))
    : null;

  const candidates = [
    override,
    path.join(repoRoot, 'backend', 'venv', 'Scripts', 'python.exe'),
    path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error('No canonical OPTIME Python interpreter found. Checked backend/venv and .venv.');
}

module.exports = {
  resolveCanonicalPython,
};
