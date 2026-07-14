"use client";

import { QuestionnaireProvider } from "@/context/questionnaire-context";

export function AppQuestionnaireProvider({ children }: { children: React.ReactNode }) {
  return <QuestionnaireProvider>{children}</QuestionnaireProvider>;
}
