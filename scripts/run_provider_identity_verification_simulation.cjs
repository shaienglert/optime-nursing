const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveCanonicalPython } = require('./lib/python_runtime.cjs');

const repoRoot = path.join(__dirname, '..');

function runPythonSnippet(code, args = []) {
  const pythonPath = resolveCanonicalPython(repoRoot);
  const result = spawnSync(pythonPath, ['-c', code, ...args], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  if (result.status !== 0) {
    throw new Error(`Python execution failed: ${result.stderr || result.stdout}`.trim());
  }

  return (result.stdout || '').trim();
}

function main() {
  const code = [
    'import json, sys',
    'from datetime import timedelta',
    'sys.path.insert(0, r"' + path.join(repoRoot, 'backend').replace(/\\/g, '\\\\') + '")',
    'from app.database import Base, engine, SessionLocal',
    'import app.models.facility',
    'from app.services.schema_migrations import ensure_provider_identity_schema',
    'from app.models.facility import Facility, FacilityDomainAllowlist, ProviderIdentityChallenge, FacilityUser, FacilityAuditLog',
    'from app.services.provider_identity import start_email_verification, complete_email_verification, validate_license_ownership, invite_staff_member, request_role_change, apply_facility_field_update, revert_audit_change, run_annual_reverification',
    'Base.metadata.create_all(bind=engine)',
    'ensure_provider_identity_schema(engine)',
    'db = SessionLocal()',
    'try:',
    '  facility = db.query(Facility).order_by(Facility.id.asc()).first()',
    '  if facility is None:',
    '    raise RuntimeError("No facilities found for simulation")',
    '  domain = "johnknoxvillage.com"',
    '  allow = db.query(FacilityDomainAllowlist).filter(FacilityDomainAllowlist.facility_id == facility.id, FacilityDomainAllowlist.domain == domain).first()',
    '  if allow is None:',
    '    db.add(FacilityDomainAllowlist(facility_id=facility.id, domain=domain, is_parent_org=False, is_active=True, manual_approval_required=False))',
    '    db.commit()',
    '',
    '  # Scenario 1: Valid official email registration + verification',
    '  start = start_email_verification(db, facility.id, "owner@johnknoxvillage.com", "Owner User", "OWNER", "127.0.0.1")',
    '  complete = complete_email_verification(db, facility.id, "owner@johnknoxvillage.com", start["debug_verification_code"])',
    '  valid_email_pass = bool(complete.get("verification_completed_at"))',
    '',
    '  # Scenario 2: Gmail registration attempt blocked',
    '  gmail_blocked = False',
    '  try:',
    '    start_email_verification(db, facility.id, "bad.actor@gmail.com", "Bad Actor", "MARKETING", "127.0.0.1")',
    '  except Exception:',
    '    gmail_blocked = True',
    '',
    '  # Scenario 3: Expired verification challenge',
    '  expired_start = start_email_verification(db, facility.id, "admissions@johnknoxvillage.com", "Admissions", "ADMISSIONS", "127.0.0.1")',
    '  challenge = db.query(ProviderIdentityChallenge).filter(ProviderIdentityChallenge.user_id == expired_start["user_id"]).order_by(ProviderIdentityChallenge.id.desc()).first()',
    '  challenge.expires_at = challenge.expires_at - timedelta(hours=24)',
    '  db.commit()',
    '  expired_blocked = False',
    '  try:',
    '    complete_email_verification(db, facility.id, "admissions@johnknoxvillage.com", expired_start["debug_verification_code"])',
    '  except Exception:',
    '    expired_blocked = True',
    '',
    '  # Scenario 4: License mismatch',
    '  license_result = validate_license_ownership(db, facility.id, "WRONG-CCN", "AHCA-1", "MED-1", "Wrong Legal Name", "Wrong Address", "wrongdomain.com")',
    '  license_verification_pass = (license_result.get("status") == "MISMATCH")',
    '',
    '  # Create admin for invitation and audit/revert scenarios',
    '  admin_start = start_email_verification(db, facility.id, "admin@johnknoxvillage.com", "Admin User", "ADMIN", "127.0.0.1")',
    '  admin_complete = complete_email_verification(db, facility.id, "admin@johnknoxvillage.com", admin_start["debug_verification_code"])',
    '  admin_user = db.query(FacilityUser).filter(FacilityUser.id == admin_complete["user_id"]).first()',
    '',
    '  # Scenario 5: New staff invitation',
    '  invite = invite_staff_member(db, facility.id, admin_user.id, "activities@johnknoxvillage.com", "Activities User", "ACTIVITIES", "127.0.0.1")',
    '  new_staff_invite_pass = bool(invite.get("user_id"))',
    '',
    '  # Create admissions user for role escalation attempt',
    '  admissions_start = start_email_verification(db, facility.id, "staff@johnknoxvillage.com", "Staff User", "ADMISSIONS", "127.0.0.1")',
    '  admissions_complete = complete_email_verification(db, facility.id, "staff@johnknoxvillage.com", admissions_start["debug_verification_code"])',
    '  admissions_user = db.query(FacilityUser).filter(FacilityUser.id == admissions_complete["user_id"]).first()',
    '',
    '  # Scenario 6: Role escalation attempt blocked',
    '  role_security_pass = False',
    '  try:',
    '    request_role_change(db, facility.id, admissions_user.id, admin_user.id, "ADMIN")',
    '  except Exception:',
    '    role_security_pass = True',
    '',
    '  # Audit trail + reversible update check',
    '  update = apply_facility_field_update(db, facility.id, admin_user.id, "phone", "555-000-1212", "PHOTOS", "127.0.0.1")',
    '  revert = revert_audit_change(db, facility.id, update["audit_id"], admin_user.id, "127.0.0.1")',
    '  audit_count = db.query(FacilityAuditLog).filter(FacilityAuditLog.facility_id == facility.id).count()',
    '  audit_trail_pass = bool(revert.get("reversal_audit_id")) and audit_count >= 2',
    '',
    '  # Annual reverification execution (no strict assertion needed for pass flags here)',
    '  _ = run_annual_reverification(db)',
    '',
    '  output = {',
    '    "facility_id": facility.id,',
    '    "VALID_EMAIL_PASS": valid_email_pass,',
    '    "UNOFFICIAL_EMAIL_BLOCKED": gmail_blocked,',
    '    "EXPIRED_VERIFICATION_BLOCKED": expired_blocked,',
    '    "LICENSE_VERIFICATION_PASS": license_verification_pass,',
    '    "NEW_STAFF_INVITE_PASS": new_staff_invite_pass,',
    '    "AUDIT_TRAIL_PASS": audit_trail_pass,',
    '    "ROLE_SECURITY_PASS": role_security_pass,',
    '  }',
    '  print(json.dumps(output))',
    'finally:',
    '  db.close()',
  ].join('\n');

  const result = JSON.parse(runPythonSnippet(code));

  const lines = [];
  lines.push('# Provider Identity Verification Simulation');
  lines.push('');
  lines.push('## Scenario Outcomes');
  lines.push('');
  lines.push(`- VALID_EMAIL_PASS: **${result.VALID_EMAIL_PASS ? 'PASS' : 'FAIL'}**`);
  lines.push(`- UNOFFICIAL_EMAIL_BLOCKED: **${result.UNOFFICIAL_EMAIL_BLOCKED ? 'PASS' : 'FAIL'}**`);
  lines.push(`- EXPIRED_VERIFICATION_BLOCKED: **${result.EXPIRED_VERIFICATION_BLOCKED ? 'PASS' : 'FAIL'}**`);
  lines.push(`- LICENSE_VERIFICATION_PASS: **${result.LICENSE_VERIFICATION_PASS ? 'PASS' : 'FAIL'}**`);
  lines.push(`- NEW_STAFF_INVITE_PASS: **${result.NEW_STAFF_INVITE_PASS ? 'PASS' : 'FAIL'}**`);
  lines.push(`- AUDIT_TRAIL_PASS: **${result.AUDIT_TRAIL_PASS ? 'PASS' : 'FAIL'}**`);
  lines.push(`- ROLE_SECURITY_PASS: **${result.ROLE_SECURITY_PASS ? 'PASS' : 'FAIL'}**`);
  lines.push('');
  lines.push('## Facility');
  lines.push('');
  lines.push(`- facility_id: ${result.facility_id}`);

  const reportPath = path.join(repoRoot, 'reports', 'provider_identity_verification_simulation.md');
  fs.writeFileSync(reportPath, lines.join('\n'));

  const simulationPass = result.VALID_EMAIL_PASS
    && result.UNOFFICIAL_EMAIL_BLOCKED
    && result.LICENSE_VERIFICATION_PASS
    && result.AUDIT_TRAIL_PASS
    && result.ROLE_SECURITY_PASS
    && result.EXPIRED_VERIFICATION_BLOCKED
    && result.NEW_STAFF_INVITE_PASS;

  console.log(`Wrote ${reportPath}`);
  console.log(`VALID_EMAIL_PASS=${result.VALID_EMAIL_PASS ? 'PASS' : 'FAIL'}`);
  console.log(`UNOFFICIAL_EMAIL_BLOCKED=${result.UNOFFICIAL_EMAIL_BLOCKED ? 'PASS' : 'FAIL'}`);
  console.log(`LICENSE_VERIFICATION_PASS=${result.LICENSE_VERIFICATION_PASS ? 'PASS' : 'FAIL'}`);
  console.log(`AUDIT_TRAIL_PASS=${result.AUDIT_TRAIL_PASS ? 'PASS' : 'FAIL'}`);
  console.log(`ROLE_SECURITY_PASS=${result.ROLE_SECURITY_PASS ? 'PASS' : 'FAIL'}`);
  console.log(`SIMULATION_PASS=${simulationPass ? 'PASS' : 'FAIL'}`);
}

main();
