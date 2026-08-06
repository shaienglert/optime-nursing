"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientDecisionRecommendations, fetchPatientNeedsProfile } from "@/lib/api";

const EXAMPLE_QUERY =
  "My mother is 82, has early memory changes, enjoys music and social activities, speaks Hebrew and English, and our budget is $8,000 per month.";

const PATIENT_CASE_ID_SESSION_KEY = "optime.patient.case.id";

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

const TRUST_POINTS = [
  {
    title: "Built around your family",
    text: "Care needs, personality, routines, language, location and budget are considered together — not as separate filters.",
  },
  {
    title: "Evidence before claims",
    text: "Recommendations are based on verified information. Missing or uncertain information is shown clearly rather than guessed.",
  },
  {
    title: "Independent recommendations",
    text: "Commercial relationships do not determine rankings. The decision starts with what is right for your family.",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Tell us what matters",
    text: "Describe the person, the situation and the decision in your own words, or use the guided questionnaire.",
  },
  {
    number: "02",
    title: "We build the full picture",
    text: "OPTIME organizes needs, priorities, constraints and unknowns into one clear decision profile.",
  },
  {
    number: "03",
    title: "Receive explained options",
    text: "See which communities fit, why they fit, what may not fit and what still needs to be verified.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();
  const [query, setQuery] = useState(state.notes || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSearch(inputQuery: string): Promise<void> {
    const normalized = inputQuery.trim();
    if (!normalized) {
      setError("Please describe who you are helping and what matters most.");
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
        fetchPatientNeedsProfile({
          questionnaire_state: canonicalQuestionnaire,
          natural_language_query: normalized,
        }),
        fetchPatientDecisionRecommendations({
          patient_case_id: currentPatientCaseId,
          questionnaire_state: canonicalQuestionnaire,
          natural_language_query: normalized,
          limit: 50,
        }),
      ]);

      if (typeof recommendations.patient_case_id === "number") {
        savePatientCaseId(recommendations.patient_case_id);
      }

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
      setError(
        requestError instanceof Error
          ? requestError.message
          : "We could not complete the search right now. Please try again."
      );
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
      <section className="relative overflow-hidden border-b border-[#dbe4df] bg-[radial-gradient(circle_at_12%_10%,rgba(219,239,229,0.95),transparent_32%),radial-gradient(circle_at_90%_0%,rgba(255,232,202,0.9),transparent_34%),linear-gradient(180deg,#fbfaf7_0%,#f7f4ee_100%)]">
        <div className="mx-auto max-w-7xl px-5 pb-20 pt-6 sm:px-8 lg:px-12 lg:pb-28">
          <nav className="flex items-center justify-between" aria-label="Main navigation">
            <Link href="/" className="text-xl font-semibold tracking-[-0.03em] text-[#1e4f43]">
              OPTIME
            </Link>
            <div className="flex items-center gap-3 text-sm font-medium">
              <Link href="/workspace" className="hidden rounded-full px-4 py-2 text-[#486057] hover:bg-white/70 sm:inline-flex">
                My workspace
              </Link>
              <Link href="/questionnaire" className="rounded-full bg-[#1f6f5d] px-5 py-2.5 text-white shadow-sm transition hover:bg-[#185a4c]">
                Start guided process
              </Link>
            </div>
          </nav>

          <div className="grid items-center gap-12 pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:pt-24">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3a7969]">
                Finding You the Right Way
              </p>
              <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[1.06] tracking-[-0.045em] text-[#1e2e28] sm:text-6xl lg:text-7xl">
                The right senior living decision starts with understanding the person.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-[#52645d] sm:text-xl">
                OPTIME helps families compare care, lifestyle, location and evidence together — then explains which options fit, where the trade-offs are and what still needs checking.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/questionnaire" className="rounded-full bg-[#1f6f5d] px-6 py-3.5 text-sm font-semibold text-white shadow-[0_12px_30px_-16px_rgba(31,111,93,0.9)] transition hover:bg-[#185a4c]">
                  Begin with guided questions
                </Link>
                <a href="#tell-us" className="rounded-full border border-[#bdcdc5] bg-white/70 px-6 py-3.5 text-sm font-semibold text-[#31584e] transition hover:bg-white">
                  Describe the situation
                </a>
              </div>
              <p className="mt-5 text-sm text-[#64766f]">
                No paid placement determines your recommendation. Uncertainty is shown, not hidden.
              </p>
            </div>

            <div id="tell-us" className="rounded-[2rem] border border-white/90 bg-white/90 p-6 shadow-[0_36px_90px_-44px_rgba(47,71,61,0.5)] backdrop-blur sm:p-8">
              <p className="text-sm font-semibold text-[#2b5f52]">Tell us who you are helping</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#22332d]">
                Start in your own words
              </h2>
              <p className="mt-3 text-sm leading-6 text-[#60716a]">
                Include anything that matters: care needs, personality, routines, language, family location, budget and concerns.
              </p>

              <form onSubmit={submit} className="mt-6 space-y-4">
                <label htmlFor="family-case" className="sr-only">
                  Describe your family situation
                </label>
                <textarea
                  id="family-case"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  rows={7}
                  placeholder={EXAMPLE_QUERY}
                  className="w-full resize-none rounded-3xl border border-[#cfdad4] bg-[#fbfcfb] px-5 py-4 text-base leading-7 text-[#273630] outline-none transition placeholder:text-[#8b9a94] focus:border-[#75a797] focus:ring-4 focus:ring-[#dcefe8]"
                />
                {error ? (
                  <p className="rounded-2xl border border-[#ecc8bc] bg-[#fff4ef] px-4 py-3 text-sm text-[#8a4434]">
                    {error}
                  </p>
                ) : null}
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 rounded-full bg-[#1f6f5d] px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-[#185a4c] disabled:cursor-not-allowed disabled:opacity-65"
                  >
                    {isSubmitting ? "Understanding your needs..." : "See options that may fit"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setQuery(EXAMPLE_QUERY)}
                    className="rounded-full border border-[#cfdad4] px-5 py-3.5 text-sm font-semibold text-[#3f6057] transition hover:bg-[#f5faf7]"
                  >
                    Use an example
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-12">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3a7969]">How OPTIME works</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-5xl">
            One clear process for a complicated family decision.
          </h2>
        </div>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {STEPS.map((step) => (
            <article key={step.number} className="rounded-[1.75rem] border border-[#dde5e1] bg-white p-7 shadow-[0_20px_60px_-45px_rgba(33,49,43,0.55)]">
              <p className="text-sm font-semibold text-[#6d978a]">{step.number}</p>
              <h3 className="mt-8 text-xl font-semibold tracking-[-0.02em] text-[#253730]">{step.title}</h3>
              <p className="mt-3 leading-7 text-[#60716a]">{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[#dbe4df] bg-[#edf4f0]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:px-12">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#3a7969]">A decision you can trust</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-[#22332d] sm:text-5xl">
              Clear about what we know — and what we do not.
            </h2>
            <p className="mt-5 max-w-xl text-lg leading-8 text-[#5a6d65]">
              OPTIME is designed to act like a careful advisor: evidence-led, transparent about uncertainty and focused on your family rather than the loudest listing.
            </p>
          </div>
          <div className="grid gap-4">
            {TRUST_POINTS.map((point) => (
              <article key={point.title} className="rounded-[1.5rem] border border-white/80 bg-white/80 p-6">
                <h3 className="text-lg font-semibold text-[#29453c]">{point.title}</h3>
                <p className="mt-2 leading-7 text-[#60716a]">{point.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-12">
        <div className="rounded-[2.25rem] bg-[#214c41] px-6 py-12 text-white shadow-[0_32px_90px_-48px_rgba(25,57,49,0.9)] sm:px-10 lg:flex lg:items-center lg:justify-between lg:px-14">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#a8d5c8]">Ready when you are</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] sm:text-5xl">
              Start with what you know. We will help uncover what is missing.
            </h2>
          </div>
          <div className="mt-8 flex flex-wrap gap-3 lg:mt-0 lg:pl-8">
            <Link href="/questionnaire" className="rounded-full bg-white px-6 py-3.5 text-sm font-semibold text-[#214c41] transition hover:bg-[#eef6f2]">
              Start the guided process
            </Link>
            <a href="#tell-us" className="rounded-full border border-[#6e9b8e] px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-white/10">
              Describe the situation
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#dbe4df] bg-[#f4f1eb]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-sm text-[#66766f] sm:px-8 md:flex-row md:items-center md:justify-between lg:px-12">
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
