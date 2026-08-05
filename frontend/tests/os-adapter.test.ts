import { describe, expect, it } from 'vitest';
import { adaptSeniorEvaluation, adaptSeniorRequirement } from '../src/domain/senior-living/os-adapter';

describe('Senior Living OPTIME OS adapter', () => {
  it('maps senior requirements to domain-neutral requirement levels', () => {
    expect(adaptSeniorRequirement({ parameter_id: 'care', requirement_level: 'REQUIRED' }).level).toBe('MUST');
    expect(adaptSeniorRequirement({ parameter_id: 'distance', requirement_level: 'PREFERENCE' }).level).toBe('NICE_TO_HAVE');
  });

  it('preserves eligibility, evidence and explanation', () => {
    const result = adaptSeniorEvaluation(
      { profile_key: 'P1', location_city: 'Miami', need_tags: ['rehab'] },
      {
        canonical_facility_id: 'F1',
        facility_name: 'Example Facility',
        eligibility_status: 'ELIGIBLE',
        eligibility: {
          matched_needs: [{ parameter_id: 'care', status: 'MATCH', source: 'CMS' }],
        },
        explanation: {
          why_this_facility: ['Meets the verified care need'],
          strengths: ['Verified capability'],
          trade_offs: ['Availability requires confirmation'],
          unknowns: [],
          questions_to_confirm: ['Confirm availability'],
        },
      },
    );

    expect(result.party.partyType).toBe('SENIOR_LIVING_SEEKER');
    expect(result.option.optionType).toBe('SENIOR_LIVING_FACILITY');
    expect(result.eligibility).toBe('ELIGIBLE');
    expect(result.requirementEvaluations[0]?.state).toBe('YES');
    expect(result.explanation.questions).toHaveLength(1);
  });
});
