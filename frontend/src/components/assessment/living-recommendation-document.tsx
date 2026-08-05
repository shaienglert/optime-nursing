"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { DecisionEngineRecommendation, DecisionEngineResponse } from "@/lib/api";
import { fetchFacilityDetails } from "@/lib/api";
import { displayParameterLabel } from "@/lib/comparison-flow";
import { resolveFacilityImage } from "@/lib/facility-experience";

const PHOTO_PENDING = "PHOTO_PENDING";

function recommendationHeading(index: number): string {
  if (index === 0) return "My first recommendation";
  if (index === 1) return "Another community I would consider carefully";
  return "A third option worth keeping in the conversation";
}

function appearsSupported(recommendation: DecisionEngineRecommendation): string[] {
  const reasons = recommendation.explanation.why_matches || [];
  return reasons.length ? reasons.slice(0, 4) : recommendation.explanation.eligibility_reasons.slice(0, 3);
}

function verifiedStatements(recommendation: DecisionEngineRecommendation): string[] {
  const proven = recommendation.match_evidence_profile?.proven_critical_matches || 0;
  const statements: string[] = [];
  if (proven > 0) {
    statements.push(`${proven} ${proven === 1 ? "important care requirement has" : "important care requirements have"} verified support in OPTIME's current evidence.`);
  }
  if (recommendation.eligibility_status === "ELIGIBLE") {
    statements.push("The currently verified information does not show a critical care gap for the needs you shared.");
  }
  return statements;
}

function unknownStatements(recommendation: DecisionEngineRecommendation): string[] {
  return (recommendation.unknown_critical_needs || []).slice(0, 4).map((item) => {
    const parameterId = typeof item.parameter_id === "string" ? item.parameter_id : "this care need";
    return `${displayParameterLabel(parameterId)} remains unknown in the current evidence.`;
  });
}

function FacilityRecommendation({ recommendation, index, imageUrl, personLabel }: {
  recommendation: DecisionEngineRecommendation;
  index: number;
  imageUrl: string;
  personLabel: string;
}) {
  const [saved, setSaved] = useState(false);
  const verified = verifiedStatements(recommendation);
  const supported = appearsSupported(recommendation);
  const verifying = recommendation.explanation.needs_verification.slice(0, 4);
  const unknown = unknownStatements(recommendation);

  return (
    <article className="border-t border-[#d8d5cd] pt-12 sm:pt-16" aria-labelledby={`recommendation-${index}`}>
      <p className="font-serif text-lg italic text-[#6f675e]">{recommendationHeading(index)}</p>
      <h3 id={`recommendation-${index}`} className="mt-3 font-serif text-3xl leading-tight text-[#25231f] sm:text-5xl">
        {recommendation.facility_name}
      </h3>
      <p className="mt-3 text-lg text-[#625d55]">
        {[recommendation.city, recommendation.state].filter(Boolean).join(", ")}
      </p>

      <div className="mt-7 aspect-[16/9] w-full overflow-hidden bg-[#e9e6df]">
        {imageUrl === PHOTO_PENDING ? <div className="flex h-full items-center justify-center px-8 text-center font-serif text-2xl text-[#625d55]">Community photo is being verified.</div> : (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img src={imageUrl} alt={`${recommendation.facility_name} community`} className="h-full w-full object-cover" />
        )}
      </div>

      <section className="mt-9 max-w-3xl">
        <h4 className="font-serif text-2xl text-[#2b2925]">Why this appears to fit {personLabel}</h4>
        <div className="mt-4 space-y-3 text-lg leading-8 text-[#4f4a43]">
          {supported.map((reason) => <p key={reason}>{reason}</p>)}
        </div>
      </section>

      <div className="mt-10 grid gap-9 border-l-2 border-[#d7ded8] pl-6 sm:grid-cols-2 sm:pl-8">
        <section id={`verification-${index}`} className="scroll-mt-24">
          <p className="text-lg font-semibold text-[#3d6f5e]">Verified</p>
          <h4 className="mt-2 font-serif text-xl text-[#2b2925]">What has already been verified</h4>
          <ul className="mt-4 space-y-3 text-lg leading-8 text-[#565149]">
            {(verified.length ? verified : ["No critical requirement is fully verified yet; I am keeping this recommendation provisional."]).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
        <section>
          <p className="text-lg font-semibold text-[#8a5b26]">Still verifying</p>
          <h4 className="mt-2 font-serif text-xl text-[#2b2925]">What I would verify before a final decision</h4>
          <ul className="mt-4 space-y-3 text-lg leading-8 text-[#565149]">
            {(verifying.length ? verifying : [recommendation.explanation.availability_note]).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      </div>

      {(unknown.length > 0 || recommendation.explanation.concerns.length > 0) ? (
        <section className="mt-9 bg-[#f5f1e9] px-6 py-6 sm:px-8">
          <p className="text-lg font-semibold text-[#625d55]">Not yet confirmed</p>
          <ul className="mt-3 space-y-2 text-lg leading-8 text-[#5d574e]">
            {[...unknown, ...recommendation.explanation.concerns.slice(0, 3)].map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      ) : null}
      {recommendation.explanation.concerns.length === 0 ? <p className="mt-9 text-lg leading-8 text-[#565149]">No material concerns were identified in the sources currently available.</p> : null}

      <nav aria-label={`Next actions for ${recommendation.facility_name}`} className="mt-10 flex flex-wrap gap-x-7 gap-y-4 border-y border-[#d8d5cd] py-6 text-lg font-semibold text-[#2f6f5e]">
        <button type="button" onClick={() => document.getElementById(`verification-${index}`)?.scrollIntoView()} className="min-h-12 underline decoration-[#8ea49b] underline-offset-4">Verify the remaining details</button>
        {recommendation.facility_profile_id ? <Link className="flex min-h-12 items-center underline decoration-[#8ea49b] underline-offset-4" href={`/facilities/${recommendation.facility_profile_id}`}>Contact this community</Link> : null}
        {index < 2 ? <button type="button" onClick={() => document.getElementById(`recommendation-${index + 1}`)?.scrollIntoView()} className="min-h-12 underline decoration-[#8ea49b] underline-offset-4">Compare with the next recommendation</button> : null}
        <button type="button" aria-pressed={saved} onClick={() => setSaved((value) => !value)} className="min-h-12 underline decoration-[#8ea49b] underline-offset-4">{saved ? "Option saved" : "Save this option"}</button>
        <button type="button" onClick={() => window.scrollTo({ top: 0, behavior: "auto" })} className="min-h-12 underline decoration-[#8ea49b] underline-offset-4">Ask OPTIME another question</button>
      </nav>

      <details className="mt-7 border-b border-[#d8d5cd] pb-7">
        <summary className="min-h-12 cursor-pointer text-lg font-semibold leading-8 text-[#3d6f5e]">How OPTIME reached this recommendation</summary>
        <p className="mt-3 text-lg leading-8 text-[#565149]">I compared the care needs and priorities you shared with the currently available facility evidence. Verified matches supported this recommendation; unknown information stayed neutral and appears above as something to confirm.</p>
      </details>
    </article>
  );
}

export function LivingRecommendationDocument({ response, personLabel = "your family member" }: { response: DecisionEngineResponse; personLabel?: string }) {
  const recommendations = useMemo(() => response.results.slice(0, 3), [response.results]);
  const [images, setImages] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    async function loadImages() {
      const entries = await Promise.all(recommendations.map(async (recommendation) => {
        if (!recommendation.facility_profile_id) return [recommendation.canonical_facility_id, PHOTO_PENDING] as const;
        try {
          const details = await fetchFacilityDetails(String(recommendation.facility_profile_id));
          const resolved = resolveFacilityImage(details);
          return [recommendation.canonical_facility_id, resolved.isPlaceholder ? PHOTO_PENDING : resolved.url] as const;
        } catch {
          return [recommendation.canonical_facility_id, PHOTO_PENDING] as const;
        }
      }));
      if (!cancelled) setImages(Object.fromEntries(entries));
    }
    void loadImages();
    return () => { cancelled = true; };
  }, [recommendations]);

  return (
    <section className="scroll-mt-20 pt-14 sm:pt-20" aria-labelledby="recommendations-heading">
      <div className="border-t-2 border-[#2c493f] pt-10">
        <p className="text-lg font-semibold text-[#3d6f5e]">What OPTIME learned</p>
        <h2 id="recommendations-heading" className="mt-4 max-w-4xl font-serif text-4xl leading-tight text-[#25231f] sm:text-6xl">
          These are the communities I would consider first for your family.
        </h2>
        <p className="mt-6 max-w-3xl text-lg leading-8 text-[#565149]">
          I reviewed the verified information currently available for each community and kept the few items that still require confirmation clearly separate. Nothing unknown has been treated as a negative fact.
        </p>
      </div>

      <div className="mt-14 space-y-16 sm:mt-20 sm:space-y-24">
        {recommendations.map((recommendation, index) => (
          <FacilityRecommendation
            key={recommendation.canonical_facility_id}
            recommendation={recommendation}
            index={index}
            imageUrl={images[recommendation.canonical_facility_id] || PHOTO_PENDING}
            personLabel={personLabel}
          />
        ))}
      </div>

      <section className="mt-20 border-y border-[#d8d5cd] py-12 sm:mt-28 sm:py-16">
        <p className="text-lg font-semibold text-[#3d6f5e]">Next steps</p>
        <h2 className="mt-4 font-serif text-3xl text-[#25231f] sm:text-5xl">If this were my own family...</h2>
        <p className="mt-6 max-w-3xl text-lg leading-8 text-[#565149]">
          I would begin with the first community, but I would treat this as the start of careful verification rather than a final answer. I would confirm every item marked still verifying, ask the clinical team to compare the care plan with the community&apos;s current capabilities, and keep the next two options open until availability, cost, and the most important care details are confirmed in writing.
        </p>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-[#625d55]">
          The strongest decision is the one supported by verified facts, a visit that feels right to your family, and clear answers to the remaining unknowns. I would not let a polished profile or an unverified promise outweigh those things.
        </p>
      </section>
    </section>
  );
}