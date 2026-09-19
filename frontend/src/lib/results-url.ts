import type { QuestionnaireState } from "@/context/questionnaire-context";

type ResultsUrlState = Pick<
  QuestionnaireState,
  "notes" | "relationship" | "ageGroup" | "assistanceLevel" | "memoryStatus" | "budget" | "distanceFromFamily"
>;

export function buildResultsUrl(state: ResultsUrlState, pathname = "/results"): string {
  const requestedPathname = pathname.split(/[?#]/, 1)[0];
  const safePathname = requestedPathname.startsWith("/results") ? requestedPathname : "/results";
  const params = new URLSearchParams();
  const notes = state.notes.trim();

  if (notes) params.set("notes", notes);
  if (state.relationship) params.set("relationship", state.relationship);
  if (state.ageGroup) params.set("age", state.ageGroup);
  if (state.assistanceLevel) params.set("care", state.assistanceLevel);
  if (state.memoryStatus) params.set("memory", state.memoryStatus);
  if (state.budget > 0) params.set("budget", String(state.budget));
  if (state.distanceFromFamily) params.set("distanceStrategy", state.distanceFromFamily);

  return `${safePathname}${params.size > 0 ? `?${params.toString()}` : ""}`;
}
