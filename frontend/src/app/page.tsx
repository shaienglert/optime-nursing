"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { LAS_VEGAS_MARKET_FACTS } from "@/content/public-market-content";
import { QUESTIONNAIRE_SESSION_KEY, clearCompareSelection, clearFavoriteFacilities, clearSearchSession, saveSessionJson } from "@/lib/search-session";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";
import { OomnikMark as OOmnikMark } from "@/components/brand/oomnik-mark";

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
      className={`group relative mr-4 mt-4 inline-flex min-h-12 max-w-full items-center text-left text-2xl font-medium transition sm:mr-7 sm:mt-5 sm:min-h-14 sm:text-4xl ${
        selected ? "text-[#302940]" : "text-[#675088] hover:text-[#302940]"
      }`}
    >
      <span className={`border-b pb-1 transition ${selected ? "border-[#302940]" : "border-[#816d96] group-hover:border-[#675088]"}`}>
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
    <main className="min-h-screen bg-[#f8f5ef] text-[#302940]">
      <section className="relative overflow-hidden border-b border-[#e4d8e8] bg-[radial-gradient(circle_at_12%_8%,rgba(219,239,229,0.88),transparent_33%),radial-gradient(circle_at_90%_0%,rgba(255,232,202,0.72),transparent_36%),linear-gradient(180deg,#fbfaf7_0%,#f7f4ee_100%)]">
        <div className="mx-auto w-full max-w-[1600px] px-5 pb-24 pt-6 sm:px-10 lg:px-16 lg:pb-32">
          <nav className="flex items-center justify-end" aria-label="Main navigation">
            <div className="flex max-w-full items-center gap-2 text-base font-medium sm:gap-5 sm:text-2xl">
              <Link href="/workspace" className="hidden px-3 py-2 text-[#675088] hover:text-[#302940] md:inline-flex">My workspace</Link>
              <Link href="/intake" className="max-w-[80vw] border-b border-[#816d96] px-1 py-2 text-right text-[#675088] transition hover:border-[#302940] hover:text-[#302940] sm:max-w-none">Continue where I left off</Link>
            </div>
          </nav>

          <div className="pt-10 sm:pt-14">
            <p className="text-4xl font-semibold tracking-[-0.03em] text-[#302940] sm:text-5xl">Welcome</p>
            <h1 className="mt-5 max-w-none text-[2.25rem] font-semibold leading-[1.12] tracking-[-0.05em] text-[#302940] sm:text-[3.5rem] lg:text-[4.4rem]">
              A difficult decision deserves time, care, and the right guidance.
            </h1>
            <div className="flex w-full justify-center overflow-visible py-10 sm:py-16"><div className="flex w-full justify-center sm:hidden"><OptimeStaticLogo variant="primary" height={64} className="items-center" /></div><div className="hidden justify-center sm:flex"><OptimeStaticLogo variant="primary" height={112} className="items-center" /></div></div>
            <p className="max-w-none text-3xl font-medium leading-tight tracking-[-0.04em] text-[#675088] sm:text-4xl">
              Choosing senior living has many important dimensions. Answer a few questions, and <span className="whitespace-nowrap"><span>OOmn</span><span className="relative inline-block">ı<span aria-hidden="true" className="absolute left-1/2 -translate-x-1/2 rounded-full bg-orange-500" style={{ width: "0.18em", height: "0.18em", top: "0.30em" }} /></span><span>k</span></span> will understand the case, research the options, explain what is still unknown, and help you move forward with confidence.
            </p>

            <div className="mt-14 max-w-none">
              {heroStep === "relationship" && (
                <div>
                  <p className="text-3xl font-medium text-[#675088]">Let&apos;s begin naturally. A few simple answers will help us understand the person before we compare any community.</p>
                  <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[#302940] sm:text-6xl">First, tell us who this decision is for.</h2>
                  <p className="mt-5 text-4xl font-medium text-[#675088]">Who are you looking for?</p>
                  <div className="mt-3">
                    {RELATIONSHIP_OPTIONS.map((option) => (
                      <ChoiceLink key={option.label} label={option.label} onClick={() => chooseRelationship(option.label, option.value)} />
                    ))}
                  </div>
                </div>
              )}

              {heroStep === "age" && (
                <div>
                  <button type="button" onClick={() => setHeroStep("relationship")} className="text-sm text-[#675088] hover:text-[#675088]">← Change who this is for</button>
                  <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#302940] sm:text-6xl">Thanks. About how old is {relationshipLabel}?</h2>
                  <div className="mt-3">
                    {AGE_OPTIONS.map((option) => <ChoiceLink key={option} label={option} onClick={() => chooseAge(option)} />)}
                  </div>
                </div>
              )}

            </div>
            <p className="mt-12 max-w-none text-3xl font-medium leading-tight tracking-[-0.04em] text-[#302940] sm:text-4xl">No paid placement determines your recommendation. Uncertainty is shown, not hidden.</p>
          </div>
        </div>
      </section>\n\n      <section className="border-y border-[#e4d8e8] bg-[#f6edf4]">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#675088]">Las Vegas market transparency</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#302940] sm:text-5xl">Know the market. Then find the right fit.</h2>
            <p className="mt-5 text-lg leading-8 text-[#675088]">We publish the evidence-backed market facts we have, with definitions and sources. Market data is context — it never replaces a person-specific recommendation.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[...LAS_VEGAS_MARKET_FACTS.supply, ...LAS_VEGAS_MARKET_FACTS.skilledNursing.slice(0, 2)].map((fact) => (
              <div key={fact.label} className="rounded-3xl border border-[#e4d8e8] bg-white p-6">
                <p className="text-3xl font-semibold tracking-[-0.04em] text-[#302940]">{fact.value}</p>
                <p className="mt-2 text-sm font-medium leading-6 text-[#302940]">{fact.label}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold">
            <Link href="/las-vegas-senior-living" className="text-[#675088] underline underline-offset-4">See definitions and sources →</Link>
            <Link href="/guides" className="text-[#675088] underline underline-offset-4">Read family research guides →</Link>
          </div>
        </div>
      </section>

      <footer className="bg-[#f4f1eb]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-[#675088] sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12">
          <p>© {new Date().getFullYear()} OOmnik. Finding You the Right Way.</p>
          <div className="flex flex-wrap gap-5">
            <Link href="/workspace" className="hover:text-[#302940]">Workspace</Link>
            <Link href="/profiles" className="hover:text-[#302940]">Saved profiles</Link>
            <Link href="/admin" prefetch={false} className="hover:text-[#302940]">Admin</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
