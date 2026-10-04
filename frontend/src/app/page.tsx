"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { LAS_VEGAS_MARKET_FACTS } from "@/content/public-market-content";
import { QUESTIONNAIRE_SESSION_KEY, clearCompareSelection, clearFavoriteFacilities, clearSearchSession, saveSessionJson } from "@/lib/search-session";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";
import { JourneyIcon } from "@/components/brand/journey-icon";

const RELATIONSHIP_OPTIONS = [
  { label: "me", value: "Myself" },
  { label: "my mother", value: "Mom" },
  { label: "my father", value: "Dad" },
  { label: "my husband", value: "Spouse" },
  { label: "my wife", value: "Spouse" },
  { label: "a couple", value: "Couple" },
  { label: "someone else", value: "Relative" },
] as const;

const AGE_OPTIONS = ["60–64", "65–69", "70–74", "75–79", "80–84", "85–89", "90–94", "95+"];

type HeroStep = "relationship" | "age";

function personCopy(label: string): string {
  if (label === "me") return "you";
  if (label === "a couple") return "both of you";
  if (label === "someone else") return "them";
  return label.replace(/^my /, "your ");
}

function ChoiceLink({
  label,
  selected = false,
  onClick,
}: {
  label: string;
  selected?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={`group relative inline-flex min-h-12 max-w-full items-center rounded-xl border px-4 py-3 text-left text-xl font-medium transition ${
        selected ? "border-forest bg-sand text-forest" : "border-line bg-white text-ink hover:border-forest hover:bg-sand"
      }`}
    >
      <span>
        {selected ? "✓ " : ""}{label}
      </span>
    </button>
  );
}

export default function HomePage() {
  const router = useRouter();
  const { state, setState, resetState } = useQuestionnaire();
  const [heroStep, setHeroStep] = useState<HeroStep>("relationship");
  const [relationshipLabel, setRelationshipLabel] = useState("your loved one");

  // Landing on "/" is always the start of a new case -- "Continue where I left
  // off" is the one sanctioned path back into an existing case, and it goes to
  // /intake, not here. Without this, a previous case's relationship/age/needs
  // silently persisted in sessionStorage, this page's own heroStep used to skip
  // straight to "age" whenever a stale relationship was present, and every
  // subsequent setState({ ...state, ... }) in this component spread that stale
  // profile forward into whatever the client typed next. Also clear the cached
  // decision response/compare/favorite selections (not just the questionnaire
  // itself) -- otherwise a stale recommendations payload from the previous case
  // can still surface on /results and its comparison/report links even after
  // the questionnaire state is clean, until a fresh fetch happens to overwrite it.
  useEffect(() => {
    clearSearchSession();
    clearCompareSelection();
    clearFavoriteFacilities();
    resetState();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function chooseRelationship(label: string, value: string): void {
    // "my husband" and "my wife" both map to the same "Spouse" relationship value
    // (matching the single "Spouse" option in the structured intake form), so the
    // gender implied by which one was picked would otherwise be discarded rather
    // than staying on record as Not provided/unknown for whatever might use it.
    const gender = label === "my mother" || label === "my wife" ? "Female" : label === "my father" || label === "my husband" ? "Male" : "";
    setState((current) => ({ ...current, relationship: value, gender }));
    setRelationshipLabel(personCopy(label));
    setHeroStep("age");
  }

  function chooseAge(label: string): void {
    const ageGroup = label.replaceAll("–", "-");
    const nextState = { ...state, ageGroup };
    flushSync(() => setState((current) => ({ ...current, ageGroup })));
    saveSessionJson(QUESTIONNAIRE_SESSION_KEY, nextState);
    router.push("/intake");
  }

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <section className="mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-lg font-semibold text-[#934b38]">Welcome</p>
          <h1 className="mt-4 text-[2.65rem] font-semibold leading-[1.1] tracking-[-0.04em] sm:text-6xl">Find a place that feels like home.</h1>
          <p className="mt-6 text-xl leading-8 text-muted">Tell us about the person, the life they want and the support they need. We’ll help you understand the choices and take the next step at your own pace.</p>
          <p className="mt-5 text-lg leading-8 text-muted">Starting in the Las Vegas Valley. Your needs guide the recommendations.</p>
        </div>
        <div id="start-search" className="mx-auto mt-10 max-w-3xl scroll-mt-40 rounded-3xl border border-line bg-white p-6 shadow-[0_12px_36px_-20px_rgba(26,29,32,0.24)] sm:p-8 oomnik-panel">
          <p className="text-base font-medium text-muted">Let’s start with the person · {heroStep === "relationship" ? "1" : "2"} of 2</p>
          {heroStep === "relationship" ? <>
            <h2 className="mt-4 text-3xl font-semibold leading-tight">Who are you looking for?</h2>
            <p className="mt-3 text-xl leading-8 text-muted">A few simple answers will help us get to know what matters.</p>
            <div className="mt-6 flex flex-wrap gap-3">{RELATIONSHIP_OPTIONS.map(option => <ChoiceLink key={option.label} label={option.label} onClick={() => chooseRelationship(option.label, option.value)} />)}</div>
          </> : <>
            <button type="button" onClick={() => setHeroStep("relationship")} className="mt-2 inline-flex min-h-12 items-center gap-2 text-lg font-medium text-forest"><JourneyIcon kind="back" />Change who this is for</button>
            <h2 className="mt-4 text-3xl font-semibold leading-tight">Thanks. About how old is {relationshipLabel}?</h2>
            <div className="mt-6 flex flex-wrap gap-3">{AGE_OPTIONS.map(option => <ChoiceLink key={option} label={option} onClick={() => chooseAge(option)} />)}</div>
          </>}
          <Link href="/intake" className="mt-7 inline-flex min-h-12 items-center text-lg font-medium text-forest underline underline-offset-4">Continue where I left off</Link>
        </div>
      </section>
      <section id="how-it-works" className="mx-auto max-w-6xl scroll-mt-40 px-5 pb-14 sm:px-8 sm:pb-20">
        <h2 className="text-3xl font-semibold tracking-tight">Life, in the moments that matter</h2>
        <p className="mt-4 max-w-3xl text-xl leading-8 text-muted">The familiar conversations, the music you love, the feeling of belonging. Tell us what makes a day feel like yours, and we’ll keep that in view alongside the support you need.</p>
        <div className="mt-7 grid gap-7 md:grid-cols-2">
          {[{ image: "/lifestyle/connection-v1.webp", alt: "Illustrative scene of older friends sharing a meal on a terrace", title: "Room for connection", text: "Good company and familiar routines can be part of what you’re looking for. We’ll explain what each place has evidence for, and what still needs a conversation." }, { image: "/lifestyle/music-v1.webp", alt: "Illustrative scene of an older couple enjoying live music", title: "More of what you love", text: "A new home should be considered in the context of your life. Your interests and preferences help shape the search, alongside care, location and the full family budget." }].map(panel => <article key={panel.title} className="overflow-hidden rounded-3xl border border-line bg-white shadow-[0_16px_40px_-24px_rgba(40,75,56,0.28)] oomnik-panel"><Image src={panel.image} alt={panel.alt} width={1536} height={1024} loading="eager" sizes="(max-width: 767px) 100vw, 50vw" className="aspect-[3/2] w-full object-cover" /><div className="p-6 sm:p-8"><h3 className="text-2xl font-semibold text-forest">{panel.title}</h3><p className="mt-3 text-xl leading-8 text-muted">{panel.text}</p></div></article>)}
        </div>
        <p className="mt-4 text-base leading-7 text-muted">AI-generated lifestyle illustrations for inspiration. These are not photographs of listed communities.</p>
        <div className="mt-10 max-w-3xl"><h3 className="text-2xl font-semibold">We’ll take it one step at a time</h3><p className="mt-4 text-xl leading-8 text-muted">First, we get to know what matters to you. Then we explain the places that match your confirmed needs and the questions still open. When a place feels promising, you can explore a visit or a complete service and price plan. The community will need to confirm the details.</p></div>
        <div className="mt-8 rounded-3xl bg-forest p-7 text-white sm:p-9"><p className="text-2xl font-semibold leading-9">Your life. Your choice. Guidance you can understand.</p><p className="mt-3 text-xl leading-8">No paid placement determines your recommendation. We explain what we know and what still needs checking, so you can decide with confidence.</p></div>
        <details className="mt-8 text-lg"><summary className="inline-flex min-h-12 cursor-pointer items-center font-medium text-forest underline underline-offset-4">Explore the Las Vegas market evidence</summary><p className="mt-3 leading-8 text-muted">Market facts give context; your personal needs guide the match.</p><div className="mt-5 grid gap-4 sm:grid-cols-2">{LAS_VEGAS_MARKET_FACTS.supply.map(fact => <p key={fact.label} className="rounded-xl border border-line bg-white p-5"><strong className="block text-2xl">{fact.value}</strong>{fact.label}</p>)}</div><Link href="/las-vegas-senior-living" className="mt-4 inline-flex min-h-12 items-center underline">Read definitions and sources</Link></details>
      </section>
      <footer className="bg-forest text-white"><div className="mx-auto flex max-w-6xl flex-col gap-5 px-5 py-9 sm:px-8 md:flex-row md:items-center md:justify-between"><OptimeStaticLogo variant="primary" height={72} /><p className="text-lg">© {new Date().getFullYear()} OOmnik. Finding You the Right Way.</p><div className="flex flex-wrap gap-x-6 gap-y-2 text-lg"><Link href="/guides" className="inline-flex min-h-12 items-center underline underline-offset-4">Family guides</Link><Link href="/workspace" className="inline-flex min-h-12 items-center underline underline-offset-4">Saved conversations</Link><Link href="/admin" prefetch={false} className="inline-flex min-h-12 items-center underline underline-offset-4">Admin</Link></div></div></footer>
    </main>
  );
}
