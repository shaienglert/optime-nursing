"use client";

import { useEffect, useState } from "react";

import { QuestionStep } from "@/components/assessment/question-step";
import { hasAssessmentAnswer } from "@/lib/assessment-conversation";
import type { AssessmentAnswer, AssessmentQuestion } from "@/lib/assessment-schema";

export function ConversationQuestion({ question, prompt, answer, advisorResponse, current, onDraftChange, onCommit }: {
  question: AssessmentQuestion;
  prompt: string;
  answer: AssessmentAnswer | undefined;
  advisorResponse: string;
  current: boolean;
  onDraftChange?: (answer: AssessmentAnswer) => void;
  onCommit: (answer: AssessmentAnswer) => void;
}) {
  const [draftAnswer, setDraftAnswer] = useState<AssessmentAnswer | undefined>(answer);
  const [writing, setWriting] = useState(() => ({
    responseLength: current ? 0 : advisorResponse.length,
    promptLength: current ? 0 : prompt.length,
    complete: !current,
    phase: current ? "pause" : "complete",
  }));
  useEffect(() => {
    if (!current) return;
    let animationFrame = 0;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      animationFrame = window.requestAnimationFrame(() => {
        setWriting({ responseLength: advisorResponse.length, promptLength: prompt.length, complete: true, phase: "complete" });
      });
      return () => window.cancelAnimationFrame(animationFrame);
    }

    let startedAt = 0;
    const responseDuration = Math.min(1400, Math.max(420, advisorResponse.length * 14));
    const promptDuration = Math.min(1700, Math.max(480, prompt.length * 13));
    const responseStart = 200;
    const promptStart = responseStart + responseDuration + 120;
    const finishAt = promptStart + promptDuration;

    const write = (timestamp: number) => {
      if (!startedAt) startedAt = timestamp;
      const elapsed = timestamp - startedAt;
      if (elapsed < responseStart) {
        setWriting((value) => value.phase === "pause" ? value : { ...value, phase: "pause" });
      } else if (elapsed < promptStart) {
        setWriting({
          responseLength: Math.min(advisorResponse.length, Math.ceil(((elapsed - responseStart) / responseDuration) * advisorResponse.length)),
          promptLength: 0,
          complete: false,
          phase: "response",
        });
      } else if (elapsed < finishAt) {
        setWriting({
          responseLength: advisorResponse.length,
          promptLength: Math.min(prompt.length, Math.ceil(((elapsed - promptStart) / promptDuration) * prompt.length)),
          complete: false,
          phase: "prompt",
        });
      } else {
        setWriting({ responseLength: advisorResponse.length, promptLength: prompt.length, complete: true, phase: "complete" });
        return;
      }
      animationFrame = window.requestAnimationFrame(write);
    };
    animationFrame = window.requestAnimationFrame(write);
    return () => window.cancelAnimationFrame(animationFrame);
  }, [advisorResponse, current, prompt]);

  const finishWriting = () => {
    if (!writing.complete) setWriting({ responseLength: advisorResponse.length, promptLength: prompt.length, complete: true, phase: "complete" });
  };

  const handleChange = (next: AssessmentAnswer) => {
    setDraftAnswer(next);
    if (question.answerType === "single") {
      onCommit(next);
      return;
    }
    onDraftChange?.(next);
  };

  const finishTypedAnswer = () => {
    if (hasAssessmentAnswer(draftAnswer)) onCommit(draftAnswer as AssessmentAnswer);
  };

  const cursor = <span data-writing-cursor aria-hidden="true" className="ml-0.5 inline-block h-[1em] w-px translate-y-[0.12em] bg-[#55766a] align-baseline motion-safe:animate-pulse" />;

  return (
    <article
      data-question-id={question.id}
      data-advisor-writing
      data-writing-state={writing.phase}
      tabIndex={-1}
      onPointerDown={finishWriting}
      className="min-h-[28rem] scroll-mt-24 border-t border-[#d8d5cd] pt-10 outline-none sm:min-h-[34rem] sm:pt-14"
    >
      <p aria-label={advisorResponse} className="max-w-2xl font-serif text-lg italic leading-8 text-[#6b655d]">
        <span aria-hidden="true">{advisorResponse.slice(0, writing.responseLength)}{!writing.complete && writing.phase !== "prompt" ? cursor : null}</span>
      </p>
      <div className="mt-5">
        <QuestionStep
          question={question}
          prompt={<span aria-hidden={!writing.complete}>{prompt.slice(0, writing.promptLength)}{!writing.complete && writing.phase === "prompt" ? cursor : null}</span>}
          accessiblePrompt={prompt}
          answer={draftAnswer}
          choicesVisible={writing.complete}
          onChange={handleChange}
          onFinish={finishTypedAnswer}
        />
      </div>
    </article>
  );
}