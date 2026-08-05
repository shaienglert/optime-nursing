"use client";

import { useEffect, useRef, useState } from "react";

import type { AssessmentAnswers } from "@/lib/assessment-schema";
import { loadLocalJson, removeLocalKey, saveLocalJson } from "@/lib/search-session";

const ASSESSMENT_DRAFT_KEY = "optime.family-assessment.v2.draft";

type AssessmentDraft = { answers: AssessmentAnswers; currentQuestionId: string; updatedAt: string };

export function useAssessmentDraft(initialQuestionId: string) {
  const [draft, setDraft] = useState<AssessmentDraft>({ answers: {}, currentQuestionId: initialQuestionId, updatedAt: "" });
  const [hydrated, setHydrated] = useState(false);
  const skipNextSave = useRef(false);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const restored = loadLocalJson<AssessmentDraft>(ASSESSMENT_DRAFT_KEY);
      if (restored) setDraft(restored);
      setHydrated(true);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (!hydrated) return;
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    saveLocalJson(ASSESSMENT_DRAFT_KEY, draft);
  }, [draft, hydrated]);
  const updateAnswers = (answers: AssessmentAnswers) => setDraft((current) => ({ ...current, answers, updatedAt: new Date().toISOString() }));
  const updateCurrentQuestion = (currentQuestionId: string) => setDraft((current) => ({ ...current, currentQuestionId, updatedAt: new Date().toISOString() }));
  const clearDraft = () => {
    skipNextSave.current = true;
    removeLocalKey(ASSESSMENT_DRAFT_KEY);
    setDraft({ answers: {}, currentQuestionId: initialQuestionId, updatedAt: new Date().toISOString() });
  };
  return { draft, hydrated, updateAnswers, updateCurrentQuestion, clearDraft };
}