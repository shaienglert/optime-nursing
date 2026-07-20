import { QuestionnaireState } from "@/context/questionnaire-context";
import { GovernanceRuntimeContext, SearchFacility } from "@/lib/api";

export type GovernedEvidenceState = "YES" | "NO" | "UNKNOWN" | "CONFLICTING" | "LIMITED" | "NEEDS_VERIFICATION";

export type GovernedRequirementRecord = {
  requirement_id: string;
  label: string;
  classification: "MUST" | "OUR_RECOMMENDATION" | "NICE_TO_HAVE" | "CLARIFY" | "INVESTIGATE" | "UNKNOWN";
  origin: "EXPLICIT_USER_REQUIREMENT" | "PROFESSIONAL_RULE_VALIDATED" | "PROFESSIONAL_RULE_PENDING_VALIDATION" | "INTERNAL_HEURISTIC" | "UNKNOWN";
  rule_id: string | null;
  source_evidence: string;
  authority_level: "A" | "B" | "C" | "D" | "UNKNOWN";
  validation_status: string;
  reason: string;
  confidence: number;
  user_explicit: boolean;
  unknowns: string[];
};

export type FacilityEvidenceRecord = {
  facility_id: number;
  requirement_id: string;
  state: GovernedEvidenceState;
  source: string;
  source_type: string;
  source_date: string | null;
  retrieval_date: string;
  confidence: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  reason: string;
};

export type CandidateStage =
  | "DISCOVERED"
  | "IDENTITY_RESOLVED"
  | "EVIDENCE_EVALUATED"
  | "MUST_ELIGIBLE"
  | "MUST_VERIFICATION_REQUIRED"
  | "MUST_REJECTED"
  | "RANKED"
  | "TOP5_SELECTED";

export type CandidateTransition = {
  stage: CandidateStage;
  reason: string;
};

export type WeightGovernanceRecord = {
  weight_id: string;
  purpose: string;
  runtime_location: string;
  decision_effect: "ELIGIBILITY" | "RANKING";
  authority: "GOVERNED" | "LEGACY_REQUIRED_TEMPORARILY" | "NON_MATERIAL" | "REMOVE_FROM_DECISION" | "UNKNOWN";
  validation_status: string;
  default_behavior: string;
};

export type GovernedRecommendationDetails = {
  canonical_facility_id: number | null;
  identity_status: "CONFIRMED_CANONICAL_ID" | "UNRESOLVED_IDENTITY";
  must_satisfied: string[];
  must_failed: string[];
  must_unknown: string[];
  must_conflicting: string[];
  verification_required: string[];
  eligibility_status: "MUST_ELIGIBLE" | "ELIGIBLE_WITH_VERIFICATION_REQUIRED" | "EXCLUDED_PENDING_VERIFICATION" | "MUST_REJECTED";
  ranking_factors: Array<{ factor: string; contribution: number; type: string }>;
  source_traceability: string[];
  evidence_records: FacilityEvidenceRecord[];
  candidate_transitions: CandidateTransition[];
};

export type GovernedRuntimeMeta = {
  runtime_path: string[];
  registry_consumed: boolean;
  registry_hash: string;
  three_layer_hash: string;
  candidate_policy_hash: string;
  canonical_coverage: {
    canonical_total: number;
    runtime_total: number;
    confirmed_canonical_identity: number;
    unresolved_identity: number;
  };
  confidence_status: {
    total_evaluated: number;
    known_confidence: number;
    unknown_confidence: number;
    reason_breakdown: Record<string, number>;
  };
  external_professional_validation: string;
  benchmark_52_status: string;
};

export type ClinicalAssessmentLike = {
  key: string;
  label: string;
  priority: "CRITICAL" | "IMPORTANT" | "PREFERENCE";
  state: "YES" | "NO" | "UNKNOWN" | "LIMITED";
  evidence: string;
  rationale: string;
};

function normalize(text: string): string {
  return text.trim().toLowerCase();
}

function isExplicitNeed(label: string, state: QuestionnaireState): boolean {
  const hay = [state.notes || "", state.assistanceLevel || "", state.futureCarePreference || "", ...(state.happinessPreferences || [])]
    .join(" ")
    .toLowerCase();
  const key = normalize(label);
  if (!key) return false;
  if (key.includes("24/7") || key.includes("licensed nurses")) {
    return hay.includes("24/7") || hay.includes("nursing");
  }
  if (key.includes("rehabilitation") || key.includes("physical therapy") || key.includes("occupational therapy") || key.includes("speech therapy")) {
    return hay.includes("rehab") || hay.includes("rehabilitation") || hay.includes("stroke");
  }
  if (key.includes("medication")) {
    return hay.includes("medication");
  }
  if (key.includes("mobility") || key.includes("walker") || key.includes("wheelchair")) {
    return hay.includes("mobility") || hay.includes("walker") || hay.includes("wheelchair") || hay.includes("fall");
  }
  if (key.includes("social") || key.includes("activities")) {
    return (state.happinessPreferences || []).map(normalize).some((item) => item.includes("social"));
  }
  return hay.includes(key);
}

function explicitMustGuard(label: string): boolean {
  const key = normalize(label);
  return key.includes("24/7") || key.includes("rehabilitation") || key.includes("medication") || key.includes("mobility") || key.includes("nursing");
}

function confidenceFromState(state: ClinicalAssessmentLike["state"]): number {
  if (state === "YES" || state === "NO") return 0.85;
  if (state === "LIMITED") return 0.45;
  return 0.25;
}

function sourceConfidence(source: string): "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN" {
  const value = source.toLowerCase();
  if (value.includes("verified") || value.includes("provider")) return "HIGH";
  if (value.includes("facility") || value.includes("db") || value.includes("profile")) return "MEDIUM";
  if (value.includes("heuristic") || value.includes("inferred")) return "LOW";
  return "UNKNOWN";
}

function mapEvidenceState(state: ClinicalAssessmentLike["state"]): GovernedEvidenceState {
  if (state === "YES") return "YES";
  if (state === "NO") return "NO";
  if (state === "LIMITED") return "LIMITED";
  return "UNKNOWN";
}

function findRegistryRule(label: string, context?: GovernanceRuntimeContext | null): { rule_id: string; authority_level: "A" | "B" | "C" | "D" | "UNKNOWN"; validation_status: string } | null {
  const rules = context?.professional_rule_registry?.rules || [];
  const needle = normalize(label);
  const matched = rules.find((rule) => {
    const asText = `${String(rule.name || "")} ${String(rule.description || "")} ${String(rule.trigger_input || "")}`.toLowerCase();
    return asText.includes(needle) || needle.includes(String(rule.rule_id || "").toLowerCase());
  });
  if (!matched) return null;
  return {
    rule_id: String(matched.rule_id || ""),
    authority_level: (String(matched.authority_level || "UNKNOWN").toUpperCase() as "A" | "B" | "C" | "D" | "UNKNOWN"),
    validation_status: String(matched.validation_status || "UNKNOWN"),
  };
}

export function buildGovernedRequirements(
  assessments: ClinicalAssessmentLike[],
  state: QuestionnaireState,
  context?: GovernanceRuntimeContext | null,
): GovernedRequirementRecord[] {
  const rows = assessments.map((assessment, index) => {
    const explicit = isExplicitNeed(assessment.label, state);
    const registryRule = findRegistryRule(assessment.label, context);
    const authority = registryRule?.authority_level || "UNKNOWN";
    const validationStatus = registryRule?.validation_status || "UNKNOWN";
    const requirementId = `REQ-${index + 1}-${assessment.key.toUpperCase().replace(/[^A-Z0-9]+/g, "_")}`;

    let classification: GovernedRequirementRecord["classification"];
    if (assessment.priority === "CRITICAL") {
      classification = explicitMustGuard(assessment.label) || explicit ? "MUST" : "OUR_RECOMMENDATION";
    } else if (assessment.priority === "IMPORTANT") {
      classification = "OUR_RECOMMENDATION";
    } else {
      classification = "NICE_TO_HAVE";
    }

    // Preserve explicit user-declared safety-critical requirements even when upstream priority is softer.
    if (explicit && explicitMustGuard(assessment.label)) {
      classification = "MUST";
    }

    let origin: GovernedRequirementRecord["origin"] = "UNKNOWN";
    if (explicit && classification === "MUST") {
      origin = "EXPLICIT_USER_REQUIREMENT";
    } else if (registryRule && authority === "A" && validationStatus !== "UNVALIDATED") {
      origin = "PROFESSIONAL_RULE_VALIDATED";
    } else if (registryRule) {
      origin = "PROFESSIONAL_RULE_PENDING_VALIDATION";
    } else {
      origin = "INTERNAL_HEURISTIC";
    }

    // Do not allow unvalidated/pending rules to silently promote hard MUST.
    if (classification === "MUST" && origin === "PROFESSIONAL_RULE_PENDING_VALIDATION") {
      classification = "OUR_RECOMMENDATION";
    }

    return {
      requirement_id: requirementId,
      label: assessment.label,
      classification,
      origin,
      rule_id: registryRule?.rule_id || null,
      source_evidence: assessment.evidence,
      authority_level: authority,
      validation_status: validationStatus,
      reason: assessment.rationale,
      confidence: confidenceFromState(assessment.state),
      user_explicit: explicit,
      unknowns: assessment.state === "UNKNOWN" || assessment.state === "LIMITED" ? [assessment.label] : [],
    };
  });

  const hasMedicationRequirement = rows.some((item) => normalize(item.label).includes("medication"));
  const explicitMedicationNeed = normalize([state.notes || "", state.assistanceLevel || ""].join(" ")).includes("medication");
  if (explicitMedicationNeed && !hasMedicationRequirement) {
    rows.push({
      requirement_id: "REQ-EXPLICIT-MEDICATION_MANAGEMENT",
      label: "Medication management",
      classification: "MUST",
      origin: "EXPLICIT_USER_REQUIREMENT",
      rule_id: null,
      source_evidence: "user_notes",
      authority_level: "UNKNOWN",
      validation_status: "UNKNOWN",
      reason: "Medication support was explicitly requested in user input.",
      confidence: 0.85,
      user_explicit: true,
      unknowns: ["Medication management"],
    });
  }

  return rows;
}

export function evaluateGovernedFacility(
  facility: SearchFacility,
  requirements: GovernedRequirementRecord[],
  assessments: ClinicalAssessmentLike[],
  hardRejectionReasons: string[],
  totalScore: number,
  recommendationScore: number,
  niceToHaveScore: number,
  context?: GovernanceRuntimeContext | null,
): GovernedRecommendationDetails {
  const runtimeIdentity = (context?.canonical_runtime_coverage?.reconciliation || []).find(
    (item) => item.runtime_facility_id === facility.id,
  );

  const must = requirements.filter((item) => item.classification === "MUST");
  const evidenceRecords: FacilityEvidenceRecord[] = must.map((requirement) => {
    const matched = assessments.find((assessment) => requirement.label === assessment.label);
    const source = matched?.evidence || "runtime_facility_payload";
    const state = matched ? mapEvidenceState(matched.state) : "UNKNOWN";

    return {
      facility_id: facility.id,
      requirement_id: requirement.requirement_id,
      state,
      source,
      source_type: source.includes("verified") ? "PROVIDER_PORTAL" : source.includes("db") ? "RUNTIME_DB" : "HEURISTIC_INFERRED",
      source_date: null,
      retrieval_date: new Date().toISOString(),
      confidence: sourceConfidence(source),
      reason: matched?.rationale || "No matched assessment for requirement.",
    };
  });

  const mustSatisfied = evidenceRecords.filter((row) => row.state === "YES").map((row) => {
    const item = must.find((candidate) => candidate.requirement_id === row.requirement_id);
    return item?.label || row.requirement_id;
  });
  const mustFailed = evidenceRecords.filter((row) => row.state === "NO").map((row) => {
    const item = must.find((candidate) => candidate.requirement_id === row.requirement_id);
    return item?.label || row.requirement_id;
  });
  const mustUnknown = evidenceRecords.filter((row) => row.state === "UNKNOWN" || row.state === "LIMITED").map((row) => {
    const item = must.find((candidate) => candidate.requirement_id === row.requirement_id);
    return item?.label || row.requirement_id;
  });
  const mustConflicting = evidenceRecords.filter((row) => row.state === "CONFLICTING").map((row) => {
    const item = must.find((candidate) => candidate.requirement_id === row.requirement_id);
    return item?.label || row.requirement_id;
  });

  const verificationRequired = [...mustUnknown, ...mustConflicting];

  let eligibilityStatus: GovernedRecommendationDetails["eligibility_status"] = "MUST_ELIGIBLE";
  if (mustFailed.length > 0 || hardRejectionReasons.length > 0) {
    eligibilityStatus = "MUST_REJECTED";
  } else if (verificationRequired.length > 0) {
    eligibilityStatus = "ELIGIBLE_WITH_VERIFICATION_REQUIRED";
  }

  const transitions: CandidateTransition[] = [
    { stage: "DISCOVERED", reason: "Facility entered candidate pool from runtime /facilities feed." },
    {
      stage: "IDENTITY_RESOLVED",
      reason: runtimeIdentity?.identity_status === "CONFIRMED_CANONICAL_ID"
        ? "Canonical identity resolved by CMS certification number."
        : "Facility lacks confirmed canonical ID and remains unresolved.",
    },
    { stage: "EVIDENCE_EVALUATED", reason: "MUST evidence evaluated using governed requirement-to-evidence mapping." },
    {
      stage: eligibilityStatus === "MUST_REJECTED" ? "MUST_REJECTED" : eligibilityStatus === "ELIGIBLE_WITH_VERIFICATION_REQUIRED" ? "MUST_VERIFICATION_REQUIRED" : "MUST_ELIGIBLE",
      reason: eligibilityStatus === "MUST_REJECTED"
        ? "Verified MUST failure or governed hard rejection detected."
        : eligibilityStatus === "ELIGIBLE_WITH_VERIFICATION_REQUIRED"
          ? "MUST unknown/conflicting evidence preserved; verification required."
          : "All MUST requirements currently satisfied.",
    },
  ];

  return {
    canonical_facility_id: runtimeIdentity?.canonical_facility_id || null,
    identity_status: runtimeIdentity?.identity_status || "UNRESOLVED_IDENTITY",
    must_satisfied: mustSatisfied,
    must_failed: mustFailed,
    must_unknown: mustUnknown,
    must_conflicting: mustConflicting,
    verification_required: verificationRequired,
    eligibility_status: mustFailed.length > 0 ? "MUST_REJECTED" : eligibilityStatus,
    ranking_factors: [
      { factor: "OUR_RECOMMENDATION alignment", contribution: recommendationScore, type: "GOVERNED_RANKING" },
      { factor: "NICE_TO_HAVE alignment", contribution: niceToHaveScore, type: "GOVERNED_RANKING" },
      { factor: "Legacy heuristic match score", contribution: totalScore, type: "LEGACY_HEURISTIC_COMPONENT" },
    ],
    source_traceability: evidenceRecords.map((item) => `${item.requirement_id}:${item.state}:${item.source_type}`),
    evidence_records: evidenceRecords,
    candidate_transitions: transitions,
  };
}

export function buildWeightGovernanceSnapshot(): WeightGovernanceRecord[] {
  return [
    {
      weight_id: "W-PERSONA-WEIGHTS",
      purpose: "Persona weighting profile",
      runtime_location: "frontend/src/lib/optime-v2-engine.ts::PERSONA_WEIGHT_PROFILES",
      decision_effect: "RANKING",
      authority: "LEGACY_REQUIRED_TEMPORARILY",
      validation_status: "INTERNAL_HEURISTIC",
      default_behavior: "Used as ranking context only; cannot override MUST_FAILED.",
    },
    {
      weight_id: "W-DISTANCE-BANDS",
      purpose: "Distance-to-score band conversion",
      runtime_location: "frontend/src/lib/optime-v2-engine.ts::parseDistancePoints",
      decision_effect: "RANKING",
      authority: "LEGACY_REQUIRED_TEMPORARILY",
      validation_status: "INTERNAL_HEURISTIC",
      default_behavior: "Affects ranking only after eligibility.",
    },
    {
      weight_id: "W-COMPLETENESS-TIEBREAK",
      purpose: "Profile completeness tie-breaker",
      runtime_location: "frontend/src/lib/optime-v2-engine.ts::accepted.sort",
      decision_effect: "RANKING",
      authority: "NON_MATERIAL",
      validation_status: "INTERNAL_HEURISTIC",
      default_behavior: "Used only on score ties.",
    },
    {
      weight_id: "W-CRITICAL-NO-GATE",
      purpose: "Critical NO eligibility gate",
      runtime_location: "frontend/src/lib/optime-v2-engine.ts::hardRejectionReasons",
      decision_effect: "ELIGIBILITY",
      authority: "GOVERNED",
      validation_status: "PROFESSIONAL_RULE_PENDING_VALIDATION",
      default_behavior: "Cannot be overridden by ranking score.",
    },
  ];
}

export function buildGovernedRuntimeMeta(context?: GovernanceRuntimeContext | null): GovernedRuntimeMeta {
  return {
    runtime_path: [
      "QUESTIONNAIRE_INPUT",
      "NORMALIZED_PERSON_PROFILE",
      "EXPLICIT_NEEDS",
      "KNOWN_UNKNOWNS",
      "PROFESSIONAL_RULE_EVALUATION",
      "THREE_LAYER_CLASSIFICATION",
      "CANONICAL_FACILITY_CANDIDATES",
      "FACILITY_EVIDENCE_RESOLUTION",
      "MUST_ELIGIBILITY",
      "CANDIDATE_GOVERNANCE",
      "GOVERNED_RANKING",
      "TOP_5",
      "TRACEABILITY_PACKAGE",
      "FRONTEND_RESULTS",
    ],
    registry_consumed: Boolean(context?.professional_rule_registry?.hash),
    registry_hash: context?.professional_rule_registry?.hash || "",
    three_layer_hash: context?.three_layer_model?.hash || "",
    candidate_policy_hash: context?.candidate_governance?.hash || "",
    canonical_coverage: {
      canonical_total: context?.canonical_runtime_coverage?.canonical_total || 0,
      runtime_total: context?.canonical_runtime_coverage?.runtime_total || 0,
      confirmed_canonical_identity: context?.canonical_runtime_coverage?.confirmed_canonical_identity || 0,
      unresolved_identity: context?.canonical_runtime_coverage?.unresolved_identity || 0,
    },
    confidence_status: {
      total_evaluated: context?.confidence_status?.total_evaluated || 0,
      known_confidence: context?.confidence_status?.known_confidence || 0,
      unknown_confidence: context?.confidence_status?.unknown_confidence || 0,
      reason_breakdown: context?.confidence_status?.reason_breakdown || {},
    },
    external_professional_validation: context?.validation_truth?.external_professional_validation || "PARTIAL",
    benchmark_52_status: context?.validation_truth?.benchmark_52_status || "FAIL",
  };
}
