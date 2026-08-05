import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";


const root = resolve(import.meta.dirname, "..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("living family decision document", () => {
  it("keeps recommendations in the same experience without results navigation", () => {
    const experience = read("src/components/assessment/assessment-advisor-experience.tsx");
    expect(experience).not.toContain("useRouter");
    expect(experience).not.toContain("router.push");
    expect(experience).not.toContain("/results");
    expect(experience).toContain("<LivingRecommendationDocument response={decisionResponse}");
  });

  it("uses editorial prose rather than chat or wizard framing", () => {
    const document = read("src/components/assessment/conversational-assessment.tsx");
    const livingDocument = read("src/components/assessment/living-assessment-document.tsx");
    const presentation = `${document}\n${livingDocument}`;
    expect(presentation).not.toContain("What I understand so far");
    expect(presentation).not.toContain("CHECKPOINT_SIZE");
    expect(livingDocument).toContain("completedAnswerSentence");
    expect(livingDocument).toContain("buildAdvisorPrompt(question, answers)");
    expect(presentation).not.toContain("rounded-tl-sm");
    expect(presentation).not.toContain("rounded-tr-sm");
    expect(presentation).not.toContain("Current conversation");
    expect(presentation).not.toContain("Find matching communities");
  });

  it("uses a quiet document masthead instead of application navigation", () => {
    const header = read("src/components/brand/site-header.tsx");
    expect(header).toContain("A family decision document");
    expect(header).not.toContain("NAV_LINKS");
    expect(header).not.toContain("Results");
    expect(header).not.toContain("Compare");
    expect(header).not.toContain("Admin");
  });

  it("does not present recommendations as ranks, scores, or confidence cards", () => {
    const recommendations = read("src/components/assessment/living-recommendation-document.tsx");
    expect(recommendations).toContain("My first recommendation");
    expect(recommendations).toContain("What has already been verified");
    expect(recommendations).toContain("What I would verify before a final decision");
    expect(recommendations).toContain("If this were my own family");
    expect(recommendations).not.toContain("Rank #");
    expect(recommendations).not.toContain("match_score");
    expect(recommendations).not.toContain("evidence_confidence");
  });
});