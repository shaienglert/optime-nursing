"use client";

import { createContext, useContext, useMemo, useState } from "react";

export type QuestionnaireState = {
  relationship: string;
  gender: string;
  coupleAssistance: string;
  ageGroup: string;
  assistanceLevel: string;
  memoryStatus: string;
  happinessPreferences: string[];
  budget: number;
  distanceFromFamily: string;
  notes: string;
};

const DEFAULT_STATE: QuestionnaireState = {
  relationship: "",
  gender: "",
  coupleAssistance: "",
  ageGroup: "",
  assistanceLevel: "",
  memoryStatus: "",
  happinessPreferences: [],
  budget: 7000,
  distanceFromFamily: "",
  notes: "",
};

type QuestionnaireContextValue = {
  state: QuestionnaireState;
  setState: (next: QuestionnaireState) => void;
};

const QuestionnaireContext = createContext<QuestionnaireContextValue | undefined>(undefined);

export function QuestionnaireProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<QuestionnaireState>(DEFAULT_STATE);

  const value = useMemo(() => ({ state, setState }), [state]);

  return (
    <QuestionnaireContext.Provider value={value}>
      {children}
    </QuestionnaireContext.Provider>
  );
}

export function useQuestionnaire() {
  const context = useContext(QuestionnaireContext);
  if (!context) {
    throw new Error("useQuestionnaire must be used within QuestionnaireProvider");
  }

  return context;
}
