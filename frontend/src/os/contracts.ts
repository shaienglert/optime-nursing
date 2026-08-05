export type RequirementLevel = 'MUST' | 'IMPORTANT' | 'NICE_TO_HAVE';
export type EvidenceState = 'YES' | 'NO' | 'UNKNOWN' | 'LIMITED' | 'CONFLICTING';
export type EligibilityStatus = 'ELIGIBLE' | 'ELIGIBLE_WITH_UNKNOWNS' | 'NOT_ELIGIBLE';
export type DecisionParty = { partyId: string; partyType: string; attributes: Record<string, unknown> };
export type DecisionOption = { optionId: string; optionType: string; label: string; attributes: Record<string, unknown> };
export type Requirement = { requirementId: string; label: string; level: RequirementLevel; desiredValue: unknown; acceptableValues: readonly unknown[]; source: string; rationale?: string };
export type EvidenceRecord = { optionId: string; requirementId: string; state: EvidenceState; value?: unknown; source: string; confidence?: number; observedAt?: string; explanation?: string };
export type RequirementEvaluation = { requirementId: string; state: EvidenceState; matched: boolean | null; explanation: string; evidence: readonly EvidenceRecord[] };
export type ClarificationQuestion = { questionId: string; targetParty: string; question: string; reason: string };
export type DecisionExplanation = { whyPresented: readonly string[]; advantages: readonly string[]; disadvantages: readonly string[]; unknowns: readonly string[]; questions: readonly ClarificationQuestion[] };
export type TradeOff = { subject: string; benefit: string; cost: string };
export type AuditTrace = { rulesApplied: readonly string[]; evidenceSources: readonly string[]; warnings: readonly string[] };
export type PairEvaluation = { party: DecisionParty; option: DecisionOption; eligibility: EligibilityStatus; requirementEvaluations: readonly RequirementEvaluation[]; explanation: DecisionExplanation; tradeOffs: readonly TradeOff[]; audit: AuditTrace };

// Version-pinned, import-free copy of the domain-neutral OPTIME OS contract boundary.
