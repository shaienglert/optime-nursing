"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConversationalAssessment } from "@/components/assessment/conversational-assessment";
import { QuestionnaireShell } from "@/components/assessment/questionnaire-shell";
import { useQuestionnaire } from "@/context/questionnaire-context";
import { useAssessmentDraft } from "@/hooks/use-assessment-draft";
import { fetchPatientDecisionRecommendations, upsertPatientCaseFromQuestionnaire } from "@/lib/api";
import { convertAssessmentToQuestionnaireState } from "@/lib/assessment-profile";
import { ASSESSMENT_QUESTIONS, ASSESSMENT_SCHEMA_VERSION } from "@/lib/assessment-schema";
import { loadPatientCaseId, savePatientCaseId } from "@/lib/search-session";

export default function AssessmentPage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const { draft, hydrated, updateAnswers, updateCurrentQuestion, clearDraft } = useAssessmentDraft(ASSESSMENT_QUESTIONS[0].id);
  const [validation, setValidation] = useState("");
  const [submitting, setSubmitting] = useState(false);

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
      await fetchPatientDecisionRecommendations({
        patient_case_id: patientCase.id,
        questionnaire_state: conversion.questionnaireState as unknown as Record<string, unknown>,
        natural_language_query: conversion.naturalLanguageQuery,
        limit: 50,
      });
      clearDraft();
      const params = new URLSearchParams();
      if (conversion.naturalLanguageQuery) params.set("notes", conversion.naturalLanguageQuery);
      if (conversion.questionnaireState.relationship) params.set("relationship", conversion.questionnaireState.relationship);
      if (conversion.questionnaireState.assistanceLevel) params.set("care", conversion.questionnaireState.assistanceLevel);
      if (conversion.questionnaireState.memoryStatus) params.set("memory", conversion.questionnaireState.memoryStatus);
      if (conversion.questionnaireState.budget) params.set("budget", String(conversion.questionnaireState.budget));
      router.push(`/results?${params.toString()}`);
    } catch (error) {
      setValidation(error instanceof Error ? error.message : "We could not create recommendations. Your answers remain saved on this device.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <QuestionnaireShell eyebrow="Find the Right Care" title="Let’s understand what the right care looks like" description="Share what you know at your own pace. OPTIME will adapt the conversation, save your progress, and keep anything uncertain as unknown.">
      {hydrated ? <ConversationalAssessment answers={draft.answers} validation={validation} submitting={submitting} onAnswersChange={(answers) => { updateAnswers(answers); setValidation(""); }} onCurrentQuestionChange={updateCurrentQuestion} onSubmit={submit} /> : <p className="py-12 text-sm text-[#60736c]" role="status">Restoring your conversation…</p>}
    </QuestionnaireShell>
  );
}