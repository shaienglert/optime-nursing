/**
 * Golden personas, checked against the live intake question graph -- no browser.
 *
 * Each persona is a set of answers keyed by question id. This test walks the interview the
 * way StructuredIntake does (same visibleQuestions, same set(), same step-after-current
 * rule) and reports, in one failure, EVERY question a persona reaches but does not answer
 * and every answer it carries that the interview never asks for. Before this, a missing
 * follow-up surfaced one per browser run, ninety seconds each.
 *
 * The resulting QuestionnaireState is written to the submissions fixture, which the backend
 * decision tests and the browser journey both read. Regenerate after editing personas:
 *   GOLDEN_PERSONAS_WRITE=1 npx vitest run tests/golden-personas.test.ts
 */
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { DEFAULT_STATE } from "../src/context/questionnaire-context";
import {
  QUESTIONS,
  buildSubmission,
  createExtras,
  isAnswered,
  missingQuestions,
  visibleQuestions,
  type IntakeAnswer,
  type IntakeContext,
} from "../src/lib/intake-questions";

const GOLD = join(__dirname, "../../backend/gold_examples");
const SOURCE = join(GOLD, "oomnik_golden_personas_v1.json");
const SUBMISSIONS = join(GOLD, "oomnik_golden_personas_v1.submissions.json");

type Persona = { id: string; title: string; answers: Record<string, IntakeAnswer>; oracle: Record<string, unknown> };
type Source = { defaults: Record<string, IntakeAnswer>; personas: Persona[] };

const source = JSON.parse(readFileSync(SOURCE, "utf8")) as Source;

function freshContext(): IntakeContext {
  const draft = JSON.parse(JSON.stringify(DEFAULT_STATE)) as typeof DEFAULT_STATE;
  return { draft, extras: createExtras(draft) };
}

type Step = { id: string; kind: string; required: boolean; answer: IntakeAnswer | null };

/** Walk the interview exactly as StructuredIntake steps through it. */
export function walk(answers: Record<string, IntakeAnswer>) {
  let context = freshContext();
  const steps: Step[] = [];
  const missing: { id: string; prompt: string; options?: string[] }[] = [];
  const initial = visibleQuestions(context);
  let stepId: string | undefined = (initial.find((q) => q.required && !isAnswered(q, context)) || initial[0])?.id;
  for (let guard = 0; stepId && guard < 200; guard += 1) {
    const question = visibleQuestions(context).find((q) => q.id === stepId);
    if (!question) break;
    const has = Object.prototype.hasOwnProperty.call(answers, question.id);
    if (has) context = question.set(context, answers[question.id]);
    else if (question.required && !isAnswered(question, context)) missing.push({ id: question.id, prompt: question.prompt, options: question.options });
    steps.push({ id: question.id, kind: question.kind, required: question.required, answer: has ? answers[question.id] : null });
    const updated = visibleQuestions(context);
    const position = updated.findIndex((q) => q.id === question.id);
    stepId = position === -1 ? undefined : updated[position + 1]?.id;
  }
  const asked = new Set(steps.map((s) => s.id));
  const unused = Object.keys(answers).filter((id) => !asked.has(id));
  const stillMissing = missingQuestions(context).map((q) => q.id).filter((id) => !missing.some((m) => m.id === id));
  return { context, steps, missing, unused, stillMissing };
}

function build() {
  return source.personas.map((persona) => {
    // Defaults fill only questions the persona actually reaches; a default for a question
    // the interview never asks is not an error, a persona-specific one is.
    const merged = { ...source.defaults, ...persona.answers };
    const run = walk(merged);
    const unusedOwn = run.unused.filter((id) => Object.prototype.hasOwnProperty.call(persona.answers, id));
    return { persona, run, unusedOwn, submission: buildSubmission(run.context) };
  });
}

describe("golden personas against the live intake question graph", () => {
  const built = build();

  it("every persona answers every question it reaches, and nothing it never reaches", () => {
    const problems = built.flatMap(({ persona, run, unusedOwn }) => [
      ...run.missing.map((m) => `${persona.id}: unanswered required question "${m.id}" — ${m.prompt}${m.options ? ` [${m.options.join(" / ")}]` : ""}`),
      ...run.stillMissing.map((id) => `${persona.id}: interview would still block on "${id}"`),
      ...unusedOwn.map((id) => `${persona.id}: answer for "${id}" is never asked — stale or wrong id`),
    ]);
    expect(problems, `\n${problems.join("\n")}\n`).toEqual([]);
  });

  it("every chosen option exists on the question it answers", () => {
    const byId = new Map(QUESTIONS.map((q) => [q.id, q]));
    const problems = built.flatMap(({ persona, run }) => run.steps.flatMap((step) => {
      const question = byId.get(step.id);
      if (step.answer === null || !question?.options || (question.kind !== "single" && question.kind !== "multi")) return [];
      const chosen = Array.isArray(step.answer) ? step.answer.map(String) : [String(step.answer)];
      return chosen.filter((value) => !question.options!.includes(value))
        .map((value) => `${persona.id}: "${value}" is not an option of "${step.id}" [${question.options!.join(" / ")}]`);
    }));
    expect(problems, `\n${problems.join("\n")}\n`).toEqual([]);
  });

  it("budgets sit on the selector's five-hundred-dollar grid", () => {
    const off = built.filter(({ persona }) => Number(persona.answers.budget) % 500 !== 0).map(({ persona }) => persona.id);
    expect(off, "golden budgets must be selectable in $500 steps").toEqual([]);
  });

  it("the submissions fixture is current", () => {
    const fixture = {
      schema_version: "oomnik-golden-persona-submissions/1",
      generated_from: "backend/gold_examples/oomnik_golden_personas_v1.json",
      personas: built.map(({ persona, run, submission }) => ({
        id: persona.id,
        title: persona.title,
        oracle: persona.oracle,
        steps: run.steps.map(({ id, kind, required, answer }) => ({ id, kind, required, answer })),
        questionnaire_state: submission,
      })),
    };
    const text = `${JSON.stringify(fixture, null, 2)}\n`;
    if (process.env.GOLDEN_PERSONAS_WRITE === "1") writeFileSync(SUBMISSIONS, text);
    const current = (() => { try { return readFileSync(SUBMISSIONS, "utf8"); } catch { return ""; } })();
    expect(current === text, "submissions fixture is stale — run: GOLDEN_PERSONAS_WRITE=1 npx vitest run tests/golden-personas.test.ts").toBe(true);
  });
});
