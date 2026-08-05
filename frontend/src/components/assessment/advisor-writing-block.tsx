"use client";

import { useEffect, useState, type ElementType } from "react";

export type AdvisorWritingLine = {
  text: string;
  id?: string;
  as?: "p" | "h2";
  className: string;
};

export function AdvisorWritingBlock({ lines, label }: { lines: AdvisorWritingLine[]; label: string }) {
  const [stableLines] = useState(lines);
  const [lengths, setLengths] = useState(() => stableLines.map(() => 0));
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    let animationFrame = 0;
    const finish = () => {
      setLengths(stableLines.map((line) => line.text.length));
      setComplete(true);
    };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      animationFrame = window.requestAnimationFrame(finish);
      return () => window.cancelAnimationFrame(animationFrame);
    }

    const durations = stableLines.map((line) => Math.min(1800, Math.max(520, line.text.length * 13)));
    let startedAt = 0;
    const write = (timestamp: number) => {
      if (!startedAt) startedAt = timestamp;
      let cursor = timestamp - startedAt - 200;
      const nextLengths = stableLines.map((line, index) => {
        if (cursor <= 0) return 0;
        const duration = durations[index];
        const length = Math.min(line.text.length, Math.ceil((cursor / duration) * line.text.length));
        cursor -= duration + 140;
        return length;
      });
      setLengths(nextLengths);
      if (nextLengths.every((length, index) => length >= stableLines[index].text.length)) {
        setComplete(true);
        return;
      }
      animationFrame = window.requestAnimationFrame(write);
    };
    animationFrame = window.requestAnimationFrame(write);
    return () => window.cancelAnimationFrame(animationFrame);
  }, [stableLines]);

  const finishWriting = () => {
    setLengths(stableLines.map((line) => line.text.length));
    setComplete(true);
  };
  const activeLine = lengths.findIndex((length, index) => length < stableLines[index].text.length);

  return (
    <div data-advisor-writing-block={label} data-writing-state={complete ? "complete" : "writing"} onPointerDown={finishWriting}>
      {stableLines.map((line, index) => {
        const Tag = (line.as || "p") as ElementType;
        return (
          <Tag key={line.text} id={line.id} aria-label={line.text} className={line.className}>
            <span aria-hidden="true">{line.text.slice(0, lengths[index])}</span>
            {!complete && activeLine === index ? <span data-writing-cursor aria-hidden="true" className="ml-0.5 inline-block h-[1em] w-px translate-y-[0.12em] bg-[#55766a] align-baseline motion-safe:animate-pulse" /> : null}
          </Tag>
        );
      })}
    </div>
  );
}