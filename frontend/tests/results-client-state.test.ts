import { describe, expect, it } from "vitest";
import { resultsClientState } from "../src/lib/results-client-state";

const question = { question_key: "care_path", question: "Would you prefer care that can increase later?", target_fact_key: "futureCarePreference", answer_options: ["Yes", "No preference"] };
const decision = (client: string, system = "HEALTHY") => ({ canonical_decision_state: { authoritative: true, client, system } });

describe("results client follow-up", () => {
  it.each(["top", "nested", "audit"])("shows the exact server question from %s", location => {
    const response = {
      decision_intelligence: { ...decision("INCOMPLETE"), ...(location === "top" ? { adaptive_questions: [question] } : {}), ...(location === "nested" ? { human_intelligence: { adaptive_questions: [question] } } : {}) },
      recommendation_audit_trace: location === "audit" ? { adaptive_questions: [question] } : {},
      results: [],
    };
    expect(resultsClientState(response)).toEqual({ blocked: false, needsAnswer: true, question });
  });
  it("does not ask stale questions when the client is complete and prices await research", () => {
    expect(resultsClientState({ decision_intelligence: { ...decision("COMPLETE"), adaptive_questions: [question] } }).question).toBeUndefined();
  });
  it("does not turn AI failure into a request for a family answer", () => {
    expect(resultsClientState({ decision_intelligence: { ...decision("INCOMPLETE", "BLOCKED"), adaptive_questions: [question] } })).toEqual({ blocked: true, needsAnswer: false, question: undefined });
  });
  it("fails closed without authority even if legacy questions exist", () => {
    expect(resultsClientState({ decision_intelligence: { adaptive_questions: [question] } }).blocked).toBe(true);
  });
  it("keeps a recovery path when no usable question was returned", () => {
    expect(resultsClientState({ decision_intelligence: { ...decision("INCOMPLETE"), adaptive_questions: [null, {}, { question: "Missing key" }] } })).toEqual({ blocked: false, needsAnswer: true, question: undefined });
  });
});
