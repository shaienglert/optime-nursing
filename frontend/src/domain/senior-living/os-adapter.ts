import type {
  AuditTrace,
  DecisionExplanation,
  DecisionOption,
  DecisionParty,
  EligibilityStatus,
  EvidenceState,
  PairEvaluation,
  Requirement,
  RequirementEvaluation,
  RequirementLevel,
} from '@/os/contracts';

export type LegacySeniorNeed = {
  parameter_id?: string;
  need_text?: string;
  requirement_level?: string;
  desired_value?: unknown;
  acceptable_values?: readonly unknown[];
  user_evidence_source?: string;
};

export type LegacySeniorProfile = {
  profile_key?: string;
  location_city?: string;
  need_tags?: readonly string[];
};

export type LegacySeniorResult = {
  canonical_facility_id?: string;
  facility_id?: string;
  facility_name?: string;
  city?: string;
  state?: string;
  canonical_type?: string;
  eligibility_status?: string;
  eligibility?: Record<string, readonly Record<string, unknown>[]>;
  explanation?: Record<string, readonly string[]>;
  evidence_sources?: readonly string[];
  warnings?: readonly string[];
};

const levelMap: Record<string, RequirementLevel> = {
  REQUIRED: 'MUST',
  HIGH: 'IMPORTANT',
  MEDIUM: 'IMPORTANT',
  PREFERENCE: 'NICE_TO_HAVE',
};

const eligibilityMap: Record<string, EligibilityStatus> = {
  ELIGIBLE: 'ELIGIBLE',
  POTENTIALLY_ELIGIBLE: 'ELIGIBLE_WITH_UNKNOWNS',
  INSUFFICIENT_EVIDENCE: 'ELIGIBLE_WITH_UNKNOWNS',
  INELIGIBLE: 'NOT_ELIGIBLE',
};

export function adaptSeniorRequirement(need: LegacySeniorNeed): Requirement {
  const level = String(need.requirement_level ?? 'PREFERENCE').toUpperCase();
  return {
    requirementId: String(need.parameter_id ?? 'UNKNOWN'),
    label: String(need.need_text ?? need.parameter_id ?? 'Unknown requirement'),
    level: levelMap[level] ?? 'NICE_TO_HAVE',
    desiredValue: need.desired_value,
    acceptableValues: need.acceptable_values ?? [],
    source: String(need.user_evidence_source ?? 'UNKNOWN'),
    rationale: String(need.need_text ?? ''),
  };
}

export function adaptSeniorParty(profile: LegacySeniorProfile, partyId = 'CURRENT_CASE'): DecisionParty {
  return {
    partyId,
    partyType: 'SENIOR_LIVING_SEEKER',
    attributes: {
      profileKey: profile.profile_key,
      locationCity: profile.location_city,
      needTags: profile.need_tags ?? [],
    },
  };
}

export function adaptSeniorOption(result: LegacySeniorResult): DecisionOption {
  const optionId = String(result.canonical_facility_id ?? result.facility_id ?? 'UNKNOWN');
  return {
    optionId,
    optionType: 'SENIOR_LIVING_FACILITY',
    label: String(result.facility_name ?? optionId),
    attributes: { city: result.city, state: result.state, canonicalType: result.canonical_type },
  };
}

function evidenceState(status: unknown): EvidenceState {
  const value = String(status ?? 'UNKNOWN').toUpperCase();
  if (value === 'MATCH') return 'YES';
  if (value === 'GAP' || value === 'VERIFIED_GAP') return 'NO';
  if (value === 'LIMITED') return 'LIMITED';
  if (value === 'CONFLICTING') return 'CONFLICTING';
  return 'UNKNOWN';
}

function evaluations(result: LegacySeniorResult): RequirementEvaluation[] {
  const eligibility = result.eligibility ?? {};
  const groups: Array<[string, boolean | null]> = [
    ['matched_needs', true],
    ['unmet_verified_needs', false],
    ['unknown_critical_needs', null],
    ['unknown_noncritical_needs', null],
  ];
  const seen = new Set<string>();
  const output: RequirementEvaluation[] = [];

  groups.forEach(([group, matched]) => {
    (eligibility[group] ?? []).forEach((item) => {
      const id = String(item.parameter_id ?? 'UNKNOWN');
      if (seen.has(id)) return;
      seen.add(id);
      const state = evidenceState(item.status ?? (matched === true ? 'MATCH' : 'UNKNOWN'));
      output.push({
        requirementId: id,
        state,
        matched,
        explanation: String(item.reason ?? item.need_text ?? ''),
        evidence: [{
          optionId: String(result.canonical_facility_id ?? result.facility_id ?? 'UNKNOWN'),
          requirementId: id,
          state,
          value: item.raw_value,
          source: String(item.source ?? 'UNKNOWN'),
          explanation: String(item.reason ?? item.need_text ?? ''),
        }],
      });
    });
  });
  return output;
}

function explanation(result: LegacySeniorResult): DecisionExplanation {
  const raw = result.explanation ?? {};
  return {
    whyPresented: raw.why_this_facility ?? raw.why_presented ?? [],
    advantages: raw.strengths ?? raw.advantages ?? [],
    disadvantages: raw.trade_offs ?? raw.disadvantages ?? [],
    unknowns: raw.unknowns ?? [],
    questions: (raw.questions_to_confirm ?? raw.questions ?? []).map((question, index) => ({
      questionId: `SENIOR-Q-${index + 1}`,
      targetParty: 'OPTION_PROVIDER',
      question,
      reason: 'Missing or unverified information',
    })),
  };
}

export function adaptSeniorEvaluation(
  profile: LegacySeniorProfile,
  result: LegacySeniorResult,
  partyId = 'CURRENT_CASE',
): PairEvaluation {
  const rawStatus = String(result.eligibility_status ?? 'INSUFFICIENT_EVIDENCE');
  const audit: AuditTrace = {
    rulesApplied: ['senior_living_legacy_decision_engine'],
    evidenceSources: result.evidence_sources ?? [],
    warnings: result.warnings ?? [],
  };
  return {
    party: adaptSeniorParty(profile, partyId),
    option: adaptSeniorOption(result),
    eligibility: eligibilityMap[rawStatus] ?? 'ELIGIBLE_WITH_UNKNOWNS',
    requirementEvaluations: evaluations(result),
    explanation: explanation(result),
    tradeOffs: (result.explanation?.trade_offs ?? []).map((text) => ({ subject: 'option', benefit: '', cost: text })),
    audit,
  };
}
