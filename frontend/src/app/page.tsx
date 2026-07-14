"use client";

import { useMemo, useState } from "react";

const relationshipOptions = [
  "Mom",
  "Dad",
  "Spouse",
  "Grandmother",
  "Grandfather",
  "Relative",
  "Friend",
  "Myself",
  "Other",
];

const ageGroupOptions = [
  "60-64",
  "65-69",
  "70-74",
  "75-79",
  "80-84",
  "85-89",
  "90-94",
  "95+",
];

const assistanceOptions = [
  "Fully independent",
  "Light assistance",
  "Help with bathing",
  "Help with dressing",
  "Help with medications",
  "Daytime supervision",
  "24/7 support required",
  "Skilled nursing care",
];

const memoryOptions = [
  "No",
  "Occasionally forgetful",
  "Mild memory issues",
  "Significant memory issues",
  "Not sure",
];

const happinessOptions = [
  "Social activities",
  "Movies",
  "Music",
  "Games",
  "Outdoor activities",
  "Quiet environment",
  "Religious community",
  "Exercise and wellness",
  "Good food",
  "Cultural activities",
];

const distanceOptions = [
  "Under 10 minutes",
  "Under 20 minutes",
  "Under 30 minutes",
  "Under 1 hour",
  "Anywhere",
];

function OptionChip({
  label,
  isActive,
  onClick,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
        isActive
          ? "border-cyan-600 bg-cyan-600 text-white shadow-[0_10px_24px_-12px_rgba(8,145,178,0.7)]"
          : "border-slate-200 bg-white text-slate-700 hover:border-cyan-400 hover:text-cyan-700"
      }`}
    >
      {label}
    </button>
  );
}

function toggleOption(current: string[], option: string): string[] {
  return current.includes(option)
    ? current.filter((item) => item !== option)
    : [...current, option];
}

export default function Home() {
  const [relationship, setRelationship] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [assistanceLevel, setAssistanceLevel] = useState("");
  const [memoryStatus, setMemoryStatus] = useState("");
  const [happinessPreferences, setHappinessPreferences] = useState<string[]>([]);
  const [budget, setBudget] = useState(7000);
  const [distanceFromFamily, setDistanceFromFamily] = useState("");
  const [notes, setNotes] = useState("");

  const answeredCount = useMemo(() => {
    let count = 0;
    if (relationship) count += 1;
    if (ageGroup) count += 1;
    if (assistanceLevel) count += 1;
    if (memoryStatus) count += 1;
    if (happinessPreferences.length > 0) count += 1;
    if (budget >= 3000) count += 1;
    if (distanceFromFamily) count += 1;
    if (notes.trim()) count += 1;
    return count;
  }, [relationship, ageGroup, assistanceLevel, memoryStatus, happinessPreferences, budget, distanceFromFamily, notes]);

  const understanding = useMemo(() => {
    if (answeredCount <= 2) {
      return {
        label: "Not enough information yet",
        style: "border-slate-200 bg-slate-100 text-slate-600",
      };
    }
    if (answeredCount <= 4) {
      return {
        label: "Good understanding",
        style: "border-amber-200 bg-amber-100 text-amber-800",
      };
    }
    if (answeredCount <= 6) {
      return {
        label: "Strong understanding",
        style: "border-emerald-200 bg-emerald-100 text-emerald-800",
      };
    }
    return {
      label: "Ready to match",
      style: "border-green-300 bg-green-100 text-green-900",
    };
  }, [answeredCount]);

  const ctaText = useMemo(() => {
    if (relationship === "Mom") return "Find the right home for Mom";
    if (relationship === "Dad") return "Find the right home for Dad";
    if (relationship === "Grandmother") return "Find the right home for Grandma";
    return "Find the right home";
  }, [relationship]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#cffafe_0%,#f8fafc_32%,#ffffff_65%)] px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl">
        <div className="rounded-3xl border border-cyan-100 bg-white/90 p-6 shadow-[0_24px_80px_-32px_rgba(14,116,144,0.55)] backdrop-blur sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-700">OPTIME Nursing</p>
          <h1 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-slate-900 sm:text-5xl">
            Find the right home, not just the best-rated one.
          </h1>
          <p className="mt-5 max-w-3xl text-lg text-slate-600">
            A simple, family-friendly questionnaire built for clear decisions with less stress.
          </p>

          <div className={`mt-8 rounded-2xl border px-4 py-3 text-sm font-semibold sm:px-6 ${understanding.style}`}>
            {understanding.label}
          </div>

          <div className="mt-8 grid gap-5">
            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">1. Who are you searching for?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {relationshipOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={relationship === option}
                    onClick={() => setRelationship(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">2. Age Group</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {ageGroupOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={ageGroup === option}
                    onClick={() => setAgeGroup(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">3. How much daily assistance is needed?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {assistanceOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={assistanceLevel === option}
                    onClick={() => setAssistanceLevel(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">4. Are there memory or confusion issues?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {memoryOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={memoryStatus === option}
                    onClick={() => setMemoryStatus(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">5. What would make them happiest?</h3>
              <p className="mt-1 text-sm text-slate-600">Select all that apply.</p>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {happinessOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={happinessPreferences.includes(option)}
                    onClick={() =>
                      setHappinessPreferences((current) => toggleOption(current, option))
                    }
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">6. Monthly budget</h3>
              <p className="mt-1 text-sm text-slate-600">$3,000 - $15,000</p>
              <div className="mt-5">
                <input
                  type="range"
                  min={3000}
                  max={15000}
                  step={100}
                  value={budget}
                  onChange={(event) => setBudget(Number(event.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-cyan-100 accent-cyan-700"
                />
                <p className="mt-3 text-base font-semibold text-cyan-800">${budget.toLocaleString()}</p>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">7. Maximum distance from family</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {distanceOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={distanceFromFamily === option}
                    onClick={() => setDistanceFromFamily(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">8. Anything else we should know?</h3>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Anything important to your family or loved one that we should consider during matching."
                className="mt-4 min-h-32 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-base text-slate-700 outline-none ring-cyan-300 transition placeholder:text-slate-400 focus:ring-2"
              />
              <p className="mt-3 text-xs text-slate-500">
                Examples: Loves old movies, Must have Hebrew speaking staff, Wants a Jewish community, Doesn&apos;t like noisy environments, Loves gardening
              </p>
            </article>
          </div>

          <div className="mt-8">
            <button
              type="button"
              className="w-full rounded-full bg-cyan-700 px-6 py-4 text-base font-semibold text-white transition hover:bg-cyan-800 sm:w-auto"
            >
              {ctaText}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
