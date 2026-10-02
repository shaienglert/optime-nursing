import { QuestionnaireState } from "@/context/questionnaire-context";
import { DecisionEngineRecommendation } from "@/lib/api";
import { resolveBudgetValue } from "@/lib/budget-utils";

export type StructuredResidentProfile={relationship:string;ageGroup:string;budget:number;locationPreference:string;missingInformation:string[];clarificationQuestions:string[]};
export type RecommendationPackageEntry={rank:number;facilityId:string;facilityName:string;overallMatch:number;tradeOffs:string[];missingInformation:string[];supportingEvidence:string[]};
export type RecommendationPackage={residentProfile:StructuredResidentProfile;generatedAt:string;packageVersion:string;recommendationRanking:RecommendationPackageEntry[];unknowns:string[];verificationTasks:string[]};
export type RecommendationQualityScorecard={overall:number;passesThreshold:boolean};
export type RecommendationAuditResult={supportedEvidence:boolean;unknownsIdentified:boolean;issues:string[]};

function textOf(item:Record<string,unknown>):string{return String(item.need_text||item.parameter_id||item.need_key||"").trim()}

export function buildRecommendationPackage(state:QuestionnaireState,recommendations:DecisionEngineRecommendation[]):RecommendationPackage{
  const unknowns=[...new Set(recommendations.flatMap(r=>(r.unknown_critical_needs||[]).map(textOf)).filter(Boolean))];
  const ranking=recommendations.map((r,index)=>({
    rank:r.rank_position||index+1,
    facilityId:r.canonical_facility_id,
    facilityName:r.facility_name,
    overallMatch:r.match_score,
    tradeOffs:[...(r.explanation?.concerns||[]),...(r.explanation?.needs_verification||[])],
    missingInformation:(r.unknown_critical_needs||[]).map(textOf).filter(Boolean),
    supportingEvidence:[...(r.explanation?.why_matches||[]),...(r.explanation?.eligibility_reasons||[])].filter(Boolean),
  }));
  return {
    residentProfile:{
      relationship:String(state.relationship||""),
      ageGroup:String(state.ageGroup||""),
      budget:resolveBudgetValue(state.budget)||0,
      locationPreference:String(state.referenceLocationValue||state.referenceAddress||state.searchState||""),
      missingInformation:unknowns,
      clarificationQuestions:unknowns.map(x=>`Please verify: ${x}`),
    },
    generatedAt:new Date().toISOString(),
    packageVersion:"backend-decision-contract-v1",
    recommendationRanking:ranking,
    unknowns,
    verificationTasks:unknowns,
  };
}

export function scoreRecommendationPackage(pkg:RecommendationPackage):RecommendationQualityScorecard{
  const evidence=pkg.recommendationRanking.length===0?0:Math.round(100*pkg.recommendationRanking.filter(x=>x.supportingEvidence.length>0).length/pkg.recommendationRanking.length);
  return {overall:evidence,passesThreshold:evidence>=75};
}

export function auditRecommendationPackage(pkg:RecommendationPackage):RecommendationAuditResult{
  const issues:string[]=[];
  const supportedEvidence=pkg.recommendationRanking.every(x=>x.supportingEvidence.length>0);
  if(!supportedEvidence)issues.push("One or more recommendations do not include backend supporting evidence.");
  const unknownsIdentified=pkg.unknowns.length>0||pkg.verificationTasks.length>0||pkg.recommendationRanking.every(x=>x.missingInformation.length===0);
  if(!unknownsIdentified)issues.push("Unknowns are not explicitly represented.");
  return {supportedEvidence,unknownsIdentified,issues};
}
