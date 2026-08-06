"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientDecisionRecommendations, fetchPatientNeedsProfile } from "@/lib/api";

const EXAMPLE_QUERY =
  "My mother is 82, has early memory changes, enjoys music and social activities, speaks Hebrew and English, and our budget is $8,000 per month.";

const PATIENT_CASE_ID_SESSION_KEY = "optime.patient.case.id";

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

function loadPatientCaseId(): number | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = window.sessionStorage.getItem(PATIENT_CASE_ID_SESSION_KEY);
    if (!raw) return undefined;
    const value = Number(JSON.parse(raw));
    return Number.isFinite(value) && value > 0 ? value : undefined;
  } catch {
    return undefined;
  }
}

function savePatientCaseId(value: number): void {
  if (typeof window === "undefined" || !Number.isFinite(value) || value <= 0) return;
  try {
    window.sessionStorage.setItem(PATIENT_CASE_ID_SESSION_KEY, JSON.stringify(value));
  } catch {
    // Best-effort continuity only.
  }
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
      className={`group relative mr-5 mt-3 inline-flex items-center text-left text-lg font-medium transition ${
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
  const { state, setState } = useQuestionnaire();
  const [query, setQuery] = useState(state.notes || "");
  const [heroStep, setHeroStep] = useState<HeroStep>(state.relationship ? "age" : "relationship");
  const [relationshipLabel, setRelationshipLabel] = useState("your loved one");
  const [selectedAssistance, setSelectedAssistance] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function chooseRelationship(label: string, value: string): void {
    setState({ ...state, relationship: value });
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
      const nextQuestionnaire = {
        ...state,
        notes: normalized,
        locationImportant: state.locationImportant || "",
        referenceAddress: state.referenceAddress || "",
        maximumDistanceMiles: state.maximumDistanceMiles || "",
        customDistanceMiles: state.customDistanceMiles || "",
        otherInterests: state.otherInterests || "",
      };
      setState(nextQuestionnaire);

      const canonicalQuestionnaire = nextQuestionnaire as Record<string, unknown>;
      const currentPatientCaseId = loadPatientCaseId();

      const [, recommendations] = await Promise.all([
        fetchPatientNeedsProfile({ questionnaire_state: canonicalQuestionnaire, natural_language_query: normalized }),
        fetchPatientDecisionRecommendations({
          patient_case_id: currentPatientCaseId,
          questionnaire_state: canonicalQuestionnaire,
          natural_language_query: normalized,
          limit: 50,
        }),
      ]);

      if (typeof recommendations.patient_case_id === "number") savePatientCaseId(recommendations.patient_case_id);

      const params = new URLSearchParams();
      params.set("notes", normalized);
      if (state.relationship) params.set("relationship", state.relationship);
      if (state.ageGroup) params.set("age", state.ageGroup);
      if (state.assistanceLevel) params.set("care", state.assistanceLevel);
      if (state.memoryStatus) params.set("memory", state.memoryStatus);
      if (state.budget) params.set("budget", String(state.budget));
      if (state.distanceFromFamily) params.set("distanceStrategy", state.distanceFromFamily);
      router.push(`/results?${params.toString()}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "We could not complete the search right now. Please try again.");
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
            <Link href="/" className="text-xl font-semibold tracking-[-0.03em] text-[#1e4f43]">OPTIME</Link>
            <div className="flex items-center gap-3 text-sm font-medium">
              <Link href="/workspace" className="hidden px-3 py-2 text-[#486057] hover:text-[#234f43] sm:inline-flex">My workspace</Link>
              <Link href="/intake" className="border-b border-[#6c9c8e] px-1 py-2 text-[#315f53] transition hover:border-[#244f43] hover:text-[#244f43]">Continue where I left off</Link>
            </div>
          </nav>

          <div className="pt-20 sm:pt-28">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#3a7969]">Finding You the Right Way</p>
            <h1 className="mt-5 max-w-5xl text-5xl font-semibold leading-[1.03] tracking-[-0.05em] text-[#1e2e28] sm:text-7xl lg:text-[5.5rem]">
              The right senior living decision starts with understanding the person.
            </h1>
            <p className="mt-7 max-w-3xl text-lg leading-8 text-[#52645d] sm:text-xl">
              Let&apos;s begin naturally. A few simple answers will help us understand the person before we compare any community.
            </p>

            <div className="mt-14 max-w-4xl border-l-2 border-[#a9c7bd] pl-6 sm:pl-9">
              {heroStep === "relationship" && (
                <div>
                  <p className="text-sm font-medium text-[#648077]">First, tell us who this decision is for.</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-4xl">Who are you looking for?</h2>
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

            <button type="button" onClick={() => document.getElementById("describe")?.scrollIntoView({ behavior: "smooth" })} className="mt-12 text-sm font-medium text-[#5a756c] underline decoration-[#a8beb6] underline-offset-4 hover:text-[#315f53]">
              Or tell the story in your own words
            </button>
            <p className="mt-8 max-w-3xl text-sm leading-6 text-[#64766f]">No paid placement determines your recommendation. Uncertainty is shown, not hidden.</p>
          </div>
        </div>
      </section>

      <section id="describe" className="mx-auto max-w-6xl px-5 py-24 sm:px-8 lg:px-12">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#3a7969]">Your story matters</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#22332d] sm:text-6xl">Tell us anything the questions may not capture.</h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[#5a6d65]">Use your own words. OPTIME will combine the story with the answers already saved.</p>
          <form onSubmit={submit} className="mt-10 max-w-4xl">
            <label htmlFor="family-case" className="sr-only">Describe your family situation</label>
            <textarea id="family-case" value={query} onChange={(event) => setQuery(event.target.value)} rows={6} placeholder={EXAMPLE_QUERY} className="w-full resize-none border-0 border-b-2 border-[#a8beb6] bg-transparent px-0 py-5 text-xl leading-9 text-[#273630] outline-none transition placeholder:text-[#8b9a94] focus:border-[#315f53] focus:ring-0" />
            {error && <p className="mt-4 text-sm text-[#8a4434]">{error}</p>}
            <button type="submit" disabled={isSubmitting} className="mt-6 inline-flex items-center border-b-2 border-[#4c8b7b] pb-1 text-lg font-semibold text-[#285f51] transition hover:border-[#183f35] hover:text-[#183f35] disabled:opacity-60">
              {isSubmitting ? "Understanding your needs..." : "See options that may fit"} <span className="ml-2">→</span>
            </button>
          </form>
        </div>
      </section>

      <footer className="bg-[#f4f1eb]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-[#66766f] sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12">
          <p>© {new Date().getFullYear()} OPTIME. Finding You the Right Way.</p>
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
