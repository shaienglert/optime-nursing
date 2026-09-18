"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientNeedsProfile } from "@/lib/api";
import { LAS_VEGAS_MARKET_FACTS } from "@/content/public-market-content";
import { QUESTIONNAIRE_SESSION_KEY, clearCompareSelection, clearFavoriteFacilities, clearSearchSession, saveSessionJson } from "@/lib/search-session";

const EXAMPLE_QUERY =
  "My mother is 82, has early memory changes, enjoys music and social activities, speaks Hebrew and English, and our budget is $8,000 per month.";

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

const ASSISTANCE_OPTIONS = [
  "fully independent",
  "a little support",
  "help with bathing",
  "help with dressing",
  "help with medications",
  "daytime supervision",
  "support around the clock",
  "skilled nursing care",
] as const;

const ASSISTANCE_VALUE_MAP: Record<string, string> = {
  "fully independent": "Fully independent",
  "a little support": "Light assistance",
  "help with bathing": "Help with bathing",
  "help with dressing": "Help with dressing",
  "help with medications": "Help with medications",
  "daytime supervision": "Daytime supervision",
  "support around the clock": "24/7 support required",
  "skilled nursing care": "Skilled nursing care",
};

const MEMORY_OPTIONS = [
  { label: "no memory concerns", value: "No" },
  { label: "occasional forgetfulness", value: "Occasionally forgetful" },
  { label: "mild memory changes", value: "Mild memory issues" },
  { label: "significant memory concerns", value: "Significant memory issues" },
  { label: "I am not sure yet", value: "Not sure" },
] as const;

type HeroStep = "relationship" | "age" | "assistance" | "memory";

function extractExplicitMonthlyBudget(text: string): number | null {
  const patterns = [
    /(?:budget|afford|spend|pay)[^.$\n]{0,60}\$\s*([\d,]+)/i,
    /\$\s*([\d,]+)[^.$\n]{0,60}(?:per month|monthly|budget)/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    const amount = Number(match[1].replaceAll(",", ""));
    if (Number.isFinite(amount) && amount > 0) return amount;
  }
  return null;
}

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
      className={`group relative mr-5 mt-4 inline-flex min-h-12 items-center text-left text-2xl font-medium transition ${
        selected ? "text-[#183f35]" : "text-[#315f53] hover:text-[#183f35]"
      }`}
    >
      <span className={`border-b pb-1 transition ${selected ? "border-[#183f35]" : "border-[#8fb4a8] group-hover:border-[#315f53]"}`}>
        {selected ? "✓ " : ""}{label}
      </span>
    </button>
  );
}

export default function HomePage() {
  const router = useRouter();
  const { state, setState, resetState } = useQuestionnaire();
  const [query, setQuery] = useState("");
  const [heroStep, setHeroStep] = useState<HeroStep>("relationship");
  const [relationshipLabel, setRelationshipLabel] = useState("your loved one");
  const [selectedAssistance, setSelectedAssistance] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    setState({ ...state, relationship: value, gender });
    setRelationshipLabel(personCopy(label));
    setHeroStep("age");
  }

  function chooseAge(label: string): void {
    setState({ ...state, ageGroup: label.replaceAll("–", "-") });
    setHeroStep("assistance");
  }

  function toggleAssistance(label: string): void {
    setSelectedAssistance((current) =>
      current.includes(label) ? current.filter((item) => item !== label) : [...current, label],
    );
  }

  function continueAfterAssistance(): void {
    if (selectedAssistance.length === 0) return;

    const primaryLabel = [...selectedAssistance].sort(
      (left, right) => ASSISTANCE_OPTIONS.indexOf(right as (typeof ASSISTANCE_OPTIONS)[number]) - ASSISTANCE_OPTIONS.indexOf(left as (typeof ASSISTANCE_OPTIONS)[number]),
    )[0];
    const supportSummary = selectedAssistance.map((item) => ASSISTANCE_VALUE_MAP[item]).join(", ");
    const existingNotes = state.notes?.trim() || "";
    const notes = [existingNotes, `Support needs selected: ${supportSummary}.`].filter(Boolean).join(" ");

    setState({
      ...state,
      assistanceLevel: ASSISTANCE_VALUE_MAP[primaryLabel],
      notes,
    });
    setHeroStep("memory");
  }

  function chooseMemory(value: string): void {
    setState({ ...state, memoryStatus: value });
    router.push("/intake");
  }

  async function runSearch(inputQuery: string): Promise<void> {
    const normalized = inputQuery.trim();
    if (!normalized) {
      setError("Please tell us a little more about the person and the situation.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const explicitBudget = extractExplicitMonthlyBudget(normalized);
      const nextQuestionnaire = {
        ...state,
        // The untouched slider default is not a client statement. A budget written
        // in the story is authoritative; otherwise leave it unknown until AI asks.
        budget: explicitBudget ?? (state.questionnaireCompletion?.mandatoryComplete ? state.budget : 0),
        notes: normalized,
        locationImportant: state.locationImportant || "",
        referenceAddress: state.referenceAddress || "",
        maximumDistanceMiles: state.maximumDistanceMiles || "",
        customDistanceMiles: state.customDistanceMiles || "",
        otherInterests: state.otherInterests || "",
      };
      // Persist before navigation. React state updates can otherwise lose a race
      // with the adaptive page mounting and make a valid story look empty.
      saveSessionJson(QUESTIONNAIRE_SESSION_KEY, nextQuestionnaire);
      flushSync(() => setState(nextQuestionnaire));

      const params = new URLSearchParams();
      params.set("notes", normalized);
      if (nextQuestionnaire.relationship) params.set("relationship", nextQuestionnaire.relationship);
      if (nextQuestionnaire.ageGroup) params.set("age", nextQuestionnaire.ageGroup);
      if (nextQuestionnaire.assistanceLevel) params.set("care", nextQuestionnaire.assistanceLevel);
      if (nextQuestionnaire.memoryStatus) params.set("memory", nextQuestionnaire.memoryStatus);
      if (nextQuestionnaire.budget) params.set("budget", String(nextQuestionnaire.budget));
      if (nextQuestionnaire.distanceFromFamily) params.set("distanceStrategy", nextQuestionnaire.distanceFromFamily);

      const resultsUrl = `/results?${params.toString()}`;

      // Do not hold the user's navigation hostage to recommendation generation.
      // The governed adaptive interview owns the next-question decision and can
      // continue while profile/recommendation warming runs in the background.
      router.push(`/adaptive-interview?next=${encodeURIComponent(resultsUrl)}`);

      const canonicalQuestionnaire = nextQuestionnaire as Record<string, unknown>;
      // Warm only the light profile endpoint here. The results page owns the single
      // recommendation request; sending the same ranking request from both screens
      // caused concurrent work and could exhaust the production web worker.
      void fetchPatientNeedsProfile({ questionnaire_state: canonicalQuestionnaire, natural_language_query: normalized });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "We could not continue right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void runSearch(query);
  }

  return (
    <main className="min-h-screen bg-[#f8f5ef] text-[#21312b]">
      <section className="relative overflow-hidden border-b border-[#dbe4df] bg-[radial-gradient(circle_at_12%_8%,rgba(219,239,229,0.88),transparent_33%),radial-gradient(circle_at_90%_0%,rgba(255,232,202,0.72),transparent_36%),linear-gradient(180deg,#fbfaf7_0%,#f7f4ee_100%)]">
        <div className="mx-auto max-w-6xl px-5 pb-24 pt-6 sm:px-8 lg:px-12 lg:pb-32">
          <nav className="flex items-center justify-between" aria-label="Main navigation">
            <Link href="/" className="text-xl font-semibold tracking-[-0.03em] text-[#1e4f43]">Oomnik</Link>
            <div className="flex items-center gap-3 text-sm font-medium">
              <Link href="/workspace" className="hidden px-3 py-2 text-[#486057] hover:text-[#234f43] sm:inline-flex">My workspace</Link>
              <Link href="/intake" className="border-b border-[#6c9c8e] px-1 py-2 text-[#315f53] transition hover:border-[#244f43] hover:text-[#244f43]">Continue where I left off</Link>
            </div>
          </nav>

          <div className="pt-20 sm:pt-28">
            <p className="text-2xl font-semibold tracking-[-0.03em] text-[#1e4f43]">Welcome to Oomnik</p>
            <h1 className="mt-5 max-w-5xl text-5xl font-semibold leading-[1.03] tracking-[-0.05em] text-[#1e2e28] sm:text-7xl lg:text-[5.5rem]">
              A difficult decision deserves time, care, and the right guidance.
            </h1>
            <p className="mt-7 max-w-4xl text-xl leading-9 text-[#52645d] sm:text-2xl sm:leading-10">
              Choosing senior living has many important dimensions. Answer a few questions, and Oomnik will understand the case, research the options, explain what is still unknown, and help you move forward with confidence.
            </p>

            <div className="mt-14 max-w-4xl border-l-2 border-[#a9c7bd] pl-6 sm:pl-9">
              {heroStep === "relationship" && (
                <div>
                  <p className="text-xl font-medium text-[#52645d]">Let&apos;s begin naturally. A few simple answers will help us understand the person before we compare any community.</p>
                  <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[#22332d] sm:text-6xl">First, tell us who this decision is for.</h2>
                  <p className="mt-5 text-2xl font-medium text-[#315f53]">Who are you looking for?</p>
                  <div className="mt-3">
                    {RELATIONSHIP_OPTIONS.map((option) => (
                      <ChoiceLink key={option.label} label={option.label} onClick={() => chooseRelationship(option.label, option.value)} />
                    ))}
                  </div>
                </div>
              )}

              {heroStep === "age" && (
                <div>
                  <button type="button" onClick={() => setHeroStep("relationship")} className="text-sm text-[#648077] hover:text-[#315f53]">← Change who this is for</button>
                  <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-4xl">How old is {relationshipLabel}?</h2>
                  <div className="mt-3">
                    {AGE_OPTIONS.map((option) => <ChoiceLink key={option} label={option} onClick={() => chooseAge(option)} />)}
                  </div>
                </div>
              )}

              {heroStep === "assistance" && (
                <div>
                  <button type="button" onClick={() => setHeroStep("age")} className="text-sm text-[#648077] hover:text-[#315f53]">← Change the age</button>
                  <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-4xl">What kind of help is needed today?</h2>
                  <p className="mt-3 max-w-2xl text-base leading-7 text-[#60716a]">Choose every answer that applies, then continue.</p>
                  <div className="mt-3">
                    {ASSISTANCE_OPTIONS.map((option) => (
                      <ChoiceLink key={option} label={option} selected={selectedAssistance.includes(option)} onClick={() => toggleAssistance(option)} />
                    ))}
                  </div>
                  <button
                    type="button"
                    disabled={selectedAssistance.length === 0}
                    onClick={continueAfterAssistance}
                    className="mt-8 inline-flex items-center border-b-2 border-[#4c8b7b] pb-1 text-lg font-semibold text-[#285f51] transition hover:border-[#183f35] hover:text-[#183f35] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Next <span className="ml-2">→</span>
                  </button>
                </div>
              )}

              {heroStep === "memory" && (
                <div>
                  <button type="button" onClick={() => setHeroStep("assistance")} className="text-sm text-[#648077] hover:text-[#315f53]">← Change the support needed</button>
                  <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-4xl">Are there any memory concerns?</h2>
                  <div className="mt-3">
                    {MEMORY_OPTIONS.map((option) => (
                      <ChoiceLink key={option.label} label={option.label} onClick={() => chooseMemory(option.value)} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button type="button" onClick={() => document.getElementById("describe")?.scrollIntoView({ behavior: "smooth" })} className="mt-12 text-2xl font-medium text-[#315f53] underline decoration-[#a8beb6] underline-offset-4 hover:text-[#183f35]">
              Or tell the story in your own words
            </button>
            <p className="mt-12 max-w-5xl text-3xl font-medium leading-tight tracking-[-0.04em] text-[#20342c] sm:text-4xl">No paid placement determines your recommendation. Uncertainty is shown, not hidden.</p>
            <p className="mt-6 text-4xl font-semibold tracking-[-0.05em] text-[#1e4f43] sm:text-5xl">Oomnik — Finding You the Right Way.</p>
          </div>
        </div>
      </section>

      <section id="describe" className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:px-12">
        <div className="max-w-4xl">
          <p className="text-xl font-semibold tracking-[-0.02em] text-[#3a7969]">Your story matters</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#22332d] sm:text-6xl">Tell us anything the questions may not capture.</h2>
          <p className="mt-5 max-w-2xl text-xl leading-9 text-[#5a6d65]">Use your own words. Oomnik will combine the story with the answers already saved.</p>
          <form onSubmit={submit} className="mt-10 max-w-4xl">
            <label htmlFor="family-case" className="sr-only">Describe your family situation</label>
            <textarea id="family-case" value={query} onChange={(event) => setQuery(event.target.value)} rows={6} placeholder={EXAMPLE_QUERY} className="w-full resize-none border-0 border-b-2 border-[#a8beb6] bg-transparent px-0 py-5 text-xl leading-9 text-[#273630] outline-none transition placeholder:text-[#8b9a94] focus:border-[#315f53] focus:ring-0" />
            {error && <p className="mt-4 text-sm text-[#8a4434]">{error}</p>}
            <button type="submit" disabled={isSubmitting} className="mt-6 inline-flex items-center border-b-2 border-[#4c8b7b] pb-1 text-lg font-semibold text-[#285f51] transition hover:border-[#183f35] hover:text-[#183f35] disabled:opacity-60">
              {isSubmitting ? "Opening the AI interview..." : "See options that may fit"} <span className="ml-2">→</span>
            </button>
          </form>
        </div>
      </section>

      <section className="border-y border-[#dbe4df] bg-[#edf6f1]">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8 lg:px-12">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#3a7969]">Las Vegas market transparency</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#22332d] sm:text-5xl">Know the market. Then find the right fit.</h2>
            <p className="mt-5 text-lg leading-8 text-[#52645d]">We publish the evidence-backed market facts we have, with definitions and sources. Market data is context — it never replaces a person-specific recommendation.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[...LAS_VEGAS_MARKET_FACTS.supply, ...LAS_VEGAS_MARKET_FACTS.skilledNursing.slice(0, 2)].map((fact) => (
              <div key={fact.label} className="rounded-3xl border border-[#d2e2dc] bg-white p-6">
                <p className="text-3xl font-semibold tracking-[-0.04em] text-[#1e4f43]">{fact.value}</p>
                <p className="mt-2 text-sm font-medium leading-6 text-[#42554d]">{fact.label}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold">
            <Link href="/las-vegas-senior-living" className="text-[#285f51] underline underline-offset-4">See definitions and sources →</Link>
            <Link href="/guides" className="text-[#285f51] underline underline-offset-4">Read family research guides →</Link>
          </div>
        </div>
      </section>

      <footer className="bg-[#f4f1eb]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-[#66766f] sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12">
          <p>© {new Date().getFullYear()} Oomnik. Finding You the Right Way.</p>
          <div className="flex flex-wrap gap-5">
            <Link href="/workspace" className="hover:text-[#254d42]">Workspace</Link>
            <Link href="/profiles" className="hover:text-[#254d42]">Saved profiles</Link>
            <Link href="/admin" className="hover:text-[#254d42]">Admin</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
