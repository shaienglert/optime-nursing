"use client";

import { useEffect, useRef } from "react";

import { AdvisorWritingBlock } from "@/components/assessment/advisor-writing-block";

export function ComparisonNarrative() {
  const narrativeRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    narrativeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  return (
    <section ref={narrativeRef} data-comparison-narrative className="scroll-mt-24 border-t-2 border-[#2f4d43] pt-10 sm:pt-14" aria-label="How OPTIME is comparing communities">
      <AdvisorWritingBlock
        label="comparison"
        lines={[
          { text: "I'm now comparing the communities...", className: "font-serif text-3xl leading-tight text-[#292722] sm:text-4xl" },
          { text: "As I compare them, I'm looking first at rehabilitation, daily support, location and the things that matter most to your family.", className: "mt-5 max-w-3xl text-lg leading-8 text-[#565149]" },
        ]}
      />
    </section>
  );
}