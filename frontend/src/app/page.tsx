"use client";

import { useMemo, useState } from "react";

const careNeedsOptions = [
  "Independent",
  "Help with bathing",
  "Help with dressing",
  "Help with medication",
  "Wheelchair",
  "Memory care",
  "Dementia care",
  "Nursing care",
];

const socialPreferencesOptions = [
  "Loves social activities",
  "Loves movies",
  "Loves music",
  "Loves games",
  "Loves outdoor activities",
  "Loves quiet environments",
  "Religious activities",
];

const biggestConcernsOptions = [
  "Poor care quality",
  "Staff shortages",
  "Falls and safety",
  "Loneliness",
  "Hidden costs",
  "Medical emergencies",
  "Loss of independence",
  "Memory decline",
];

const cognitiveConditionOptions = [
  "No memory issues",
  "Mild memory loss",
  "Early dementia",
  "Moderate dementia",
  "Advanced dementia",
];

const distanceOptions = [
  "Under 10 miles",
  "Under 25 miles",
  "Under 50 miles",
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
  const [aiDescription, setAiDescription] = useState(
    "My mother is 82 years old, needs help with showering and dressing, loves movies and social activities, speaks English and Hebrew and has a budget of $7,000 per month.",
  );
  const [careNeeds, setCareNeeds] = useState<string[]>([]);
  const [cognitiveCondition, setCognitiveCondition] = useState(
    cognitiveConditionOptions[0],
  );
  const [socialPreferences, setSocialPreferences] = useState<string[]>([]);
  const [biggestConcerns, setBiggestConcerns] = useState<string[]>([]);
  const [budget, setBudget] = useState(7000);
  const [distanceFromFamily, setDistanceFromFamily] = useState(distanceOptions[1]);

  const selectedSummary = useMemo(() => {
    return `${careNeeds.length} care need(s), ${socialPreferences.length} social preference(s), ${biggestConcerns.length} concern(s)`;
  }, [careNeeds, socialPreferences, biggestConcerns]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#cffafe_0%,#f8fafc_32%,#ffffff_65%)] px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl">
        <div className="rounded-3xl border border-cyan-100 bg-white/90 p-6 shadow-[0_24px_80px_-32px_rgba(14,116,144,0.55)] backdrop-blur sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-700">
            OPTIME Nursing AI
          </p>
          <h1 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-slate-900 sm:text-5xl">
            Find the right home, not just the best-rated one.
          </h1>
          <p className="mt-5 max-w-3xl text-lg text-slate-600">
            Describe your loved one in your own words and OPTIME will find the best matches.
          </p>

          <div className="mt-8 rounded-2xl border border-cyan-100 bg-cyan-50/40 p-4 sm:p-6">
            <label htmlFor="ai-search" className="mb-3 block text-sm font-semibold text-cyan-900">
              AI Search Prompt
            </label>
            <textarea
              id="ai-search"
              value={aiDescription}
              onChange={(event) => setAiDescription(event.target.value)}
              placeholder="My mother is 82 years old, needs help with showering and dressing, loves movies and social activities, speaks English and Hebrew and has a budget of $7,000 per month."
              className="min-h-40 w-full resize-y rounded-xl border border-cyan-200 bg-white px-4 py-3 text-base text-slate-700 outline-none ring-cyan-300 transition placeholder:text-slate-400 focus:ring-2"
            />
            <button
              type="button"
              className="mt-4 inline-flex items-center rounded-full bg-cyan-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-cyan-800"
            >
              Find Matching Communities
            </button>
          </div>

          <div className="mt-12">
            <h2 className="text-2xl font-semibold text-slate-900">Prefer a guided search?</h2>
            <p className="mt-2 text-slate-600">Answer a few questions and we&apos;ll do the rest.</p>
          </div>

          <div className="mt-8 grid gap-5">
            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">1. Care Needs</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {careNeedsOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={careNeeds.includes(option)}
                    onClick={() => setCareNeeds((current) => toggleOption(current, option))}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">2. Cognitive Condition</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {cognitiveConditionOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={cognitiveCondition === option}
                    onClick={() => setCognitiveCondition(option)}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">3. Social Preferences</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {socialPreferencesOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={socialPreferences.includes(option)}
                    onClick={() =>
                      setSocialPreferences((current) => toggleOption(current, option))
                    }
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">4. Biggest Concerns</h3>
              <p className="mt-1 text-sm text-slate-600">What worries you the most?</p>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {biggestConcernsOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={biggestConcerns.includes(option)}
                    onClick={() =>
                      setBiggestConcerns((current) => toggleOption(current, option))
                    }
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">5. Budget</h3>
              <p className="mt-1 text-sm text-slate-600">$3,000 - $15,000/month</p>
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
                <p className="mt-3 text-sm font-semibold text-cyan-800">${budget.toLocaleString()}/month</p>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold text-slate-900">6. Distance from family</h3>
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
          </div>

          <div className="mt-8 rounded-2xl border border-cyan-100 bg-cyan-50/50 p-4 text-sm text-slate-700">
            <p className="font-semibold text-cyan-900">Current draft profile</p>
            <p className="mt-1">{selectedSummary}</p>
            <p className="mt-1">Cognitive condition: {cognitiveCondition}</p>
            <p className="mt-1">Distance preference: {distanceFromFamily}</p>
          </div>
        </div>
      </section>
    </main>
  );
}
