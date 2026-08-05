"use client";

import { useState } from "react";

import { ConversationalAssessment } from "@/components/assessment/conversational-assessment";
import { ComparisonNarrative } from "@/components/assessment/comparison-narrative";
import { HomeProgressIllustration } from "@/components/assessment/home-progress-illustration";
import { AssessmentPhotoEnvironment } from "@/components/assessment/assessment-photo-environment";
import { LivingRecommendationDocument } from "@/components/assessment/living-recommendation-document";
import { QuestionnaireShell } from "@/components/assessment/questionnaire-shell";
import { useQuestionnaire } from "@/context/questionnaire-context";
import { useAssessmentDraft } from "@/hooks/use-assessment-draft";
import { fetchPatientDecisionRecommendations, upsertPatientCaseFromQuestionnaire, type DecisionEngineResponse } from "@/lib/api";
import { convertAssessmentToQuestionnaireState } from "@/lib/assessment-profile";
import { ASSESSMENT_QUESTIONS, ASSESSMENT_SCHEMA_VERSION } from "@/lib/assessment-schema";
import {
  clearAssessmentData,
  loadPatientCaseId,
  savePatientCaseId,
} from "@/lib/search-session";

function documentTitle(answer: unknown): string {
  if (answer === "Mom") return "Finding the Right Care for Your Mom";
  if (answer === "Dad") return "Finding the Right Care for Your Dad";
  if (answer === "Spouse") return "Finding the Right Care for Your Partner";
  if (answer === "Myself") return "Finding the Right Care for You";
  if (answer === "Grandparent") return "Finding the Right Care for Your Grandparent";
  return "Finding the Right Care for Your Family";
}

function personLabel(answer: unknown): string {
  if (answer === "Mom") return "your mom";
  if (answer === "Dad") return "your dad";
  if (answer === "Spouse") return "your partner";
  if (answer === "Myself") return "you";
  if (answer === "Grandparent") return "your grandparent";
  return "your family member";
}

export function AssessmentAdvisorExperience() {
  const { state, setState, resetState } = useQuestionnaire();
  const { draft, hydrated, updateAnswers, updateCurrentQuestion, clearDraft } = useAssessmentDraft(ASSESSMENT_QUESTIONS[0].id);
  const [validation, setValidation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [decisionResponse, setDecisionResponse] = useState<DecisionEngineResponse | null>(null);

  const clearData = () => {
    if (!window.confirm("Clear your saved answers and recommendations from this device?")) return;

    clearDraft();
    clearAssessmentData();
    resetState();
    setDecisionResponse(null);
    setValidation("");
  };

  const submit = async () => {
    setSubmitting(true);
    setValidation("");
    try {
      const conversion = convertAssessmentToQuestionnaireState(draft.answers, state);
      setState(conversion.questionnaireState);
      const patientCase = await upsertPatientCaseFromQuestionnaire({
        patient_case_id: loadPatientCaseId() || undefined,
        questionnaire_state: conversion.questionnaireState as unknown as Record<string, unknown>,
        source_name: ASSESSMENT_SCHEMA_VERSION,
        reason: "family_assessment_submission",
      });
      savePatientCaseId(patientCase.id);
      const recommendations = await fetchPatientDecisionRecommendations({
        patient_case_id: patientCase.id,
        questionnaire_state: conversion.questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: conversion.naturalLanguageQuery,
        limit: 50,
      });
      setDecisionResponse(recommendations);
    } catch (error) {
      setValidation(error instanceof Error ? error.message : "We could not create recommendations. Your answers remain saved on this device.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <QuestionnaireShell
      eyebrow="A living family decision document"
      title={documentTitle(draft.answers.who_needs_care)}
      description="I’m going to help you find the community that best matches your family’s needs. I’ll only ask what can meaningfully improve the recommendation, and I’ll write what we learn together as we go."
      aside={hydrated ? <HomeProgressIllustration answers={draft.answers} /> : null}
      environment={hydrated ? <AssessmentPhotoEnvironment answers={draft.answers} topRecommendation={decisionResponse?.results[0]} /> : null}
      actions={(
        <button
          type="button"
          onClick={clearData}
          className="inline-flex min-h-11 items-center gap-2 border-b border-[#8b5146] px-1 py-2 text-sm font-semibold text-[#7a4037] transition-colors hover:border-[#5f2e28] hover:text-[#5f2e28] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#7a4037]"
        >
          <span aria-hidden="true" className="text-lg leading-none">↻</span>
          Clear data
        </button>
      )}
    >
      {hydrated ? (
        <ConversationalAssessment
          answers={draft.answers}
          validation={validation}
          submitting={submitting}
          recommendationsReady={Boolean(decisionResponse)}
          onAnswersChange={(answers) => {
            updateAnswers(answers);
            setValidation("");
          }}
          onCurrentQuestionChange={updateCurrentQuestion}
          onSubmit={submit}
        />
      ) : <p className="py-12 text-lg text-[#405d53]" role="status">Restoring our conversation...</p>}
      {submitting || decisionResponse ? <ComparisonNarrative /> : null}
      {decisionResponse ? <LivingRecommendationDocument response={decisionResponse} personLabel={personLabel(draft.answers.who_needs_care)} /> : null}
    </QuestionnaireShell>
  );
}