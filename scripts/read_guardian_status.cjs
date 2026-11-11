const fs = require('node:fs');
const path = require('node:path');

function readGuardianStatus(statusPath, startedMs, nowMs = Date.now()) {
  if (!Number.isFinite(startedMs) || startedMs <= 0) throw new Error('Missing Guardian start time');
  const status = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
  const runMs = Date.parse(status.runAt);
  if (!Number.isFinite(runMs) || runMs < startedMs || runMs > nowMs) {
    throw new Error('Guardian status is stale or has an invalid timestamp');
  }
  if (!['PASS', 'WARN', 'BLOCK'].includes(status.verdict)) throw new Error('Invalid Guardian verdict');
  if (!Number.isInteger(status.violationCount) || status.violationCount < 0) {
    throw new Error('Invalid Guardian violation count');
  }
  if (!/^[a-f0-9]{16}$/.test(status.fingerprint)) throw new Error('Invalid Guardian fingerprint');
  const blocked = status.verdict === 'BLOCK';
  if (blocked !== (status.violationCount > 0) || status.gate !== (blocked ? 'STOP' : 'GO')
      || status.agentExecutionAllowed !== !blocked) {
    throw new Error('Inconsistent Guardian verdict');
  }
  return status;
}

if (require.main === module) {
  try {
    const status = readGuardianStatus(
      path.resolve(__dirname, '../reports/guardian/status.json'), Number(process.env.GUARDIAN_STARTED_MS),
    );
    process.stdout.write(`verdict=${status.verdict}\nfingerprint=${status.fingerprint}\nviolations=${status.violationCount}\n`);
  } catch (error) {
    console.error(`Guardian status rejected: ${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { readGuardianStatus };
