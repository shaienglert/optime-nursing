import type { QuestionnaireState } from "@/context/questionnaire-context";

type ResultsUrlState = Pick<
  QuestionnaireState,
  "notes" | "relationship" | "ageGroup" | "assistanceLevel" | "memoryStatus" | "budget" | "distanceFromFamily"
>;

export function buildResultsUrl(_state: ResultsUrlState, pathname = "/results"): string {
  const requestedPathname = pathname.split(/[?#]/, 1)[0];
  // The questionnaire is persisted before navigation. Never duplicate its
  // medical, financial or family facts in browser history or request URLs.
  return /^\/results(?:\/[a-z-]+)*\/?$/.test(requestedPathname) ? requestedPathname : "/results";
}
