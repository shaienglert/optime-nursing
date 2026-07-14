"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";

const relationshipOptions = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Myself", "Relative", "Friend"];

const ageGroupOptions = ["60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"];

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

const memoryOptions = ["No", "Occasionally forgetful", "Mild memory issues", "Significant memory issues", "Not sure"];

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

const distanceOptions = ["Under 10 minutes", "Under 20 minutes", "Under 30 minutes", "Under 1 hour", "Anywhere"];

function OptionChip({ label, isActive, onClick }: { label: string; isActive: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
        isActive
          ? "border-[#7f9f88] bg-[#7f9f88] text-white shadow-[0_10px_24px_-12px_rgba(90,120,98,0.65)]"
          : "border-[#ddd2bf] bg-white text-[#5e5346] hover:border-[#97a89a] hover:text-[#516c5a]"
      }`}
    >
      {label}
    </button>
  );
}

function toggleOption(current: string[], option: string): string[] {
  return current.includes(option) ? current.filter((item) => item !== option) : [...current, option];
}

export default function Home() {
  const router = useRouter();
  const { setState } = useQuestionnaire();

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
      return { label: "Not enough information yet", style: "border-slate-200 bg-slate-100 text-slate-600" };
    }
    if (answeredCount <= 4) {
      return { label: "Good understanding", style: "border-amber-200 bg-amber-100 text-amber-800" };
    }
    if (answeredCount <= 6) {
      return { label: "Strong understanding", style: "border-emerald-200 bg-emerald-100 text-emerald-800" };
    }
    return { label: "Ready to match", style: "border-green-300 bg-green-100 text-green-900" };
  }, [answeredCount]);

  const relationshipLabel = relationship || "your loved one";

  const ctaText = useMemo(() => {
    return `Find the right home for ${relationshipLabel}`;
  }, [relationshipLabel]);

  const handleFindHome = () => {
    setState({
      relationship,
      ageGroup,
      assistanceLevel,
      memoryStatus,
      happinessPreferences,
      budget,
      distanceFromFamily,
      notes,
    });

    const params = new URLSearchParams();
    if (relationship) params.set("relationship", relationship);
    if (ageGroup) params.set("age", ageGroup);
    if (assistanceLevel) params.set("care", assistanceLevel);
    if (memoryStatus) params.set("memory", memoryStatus);
    if (happinessPreferences.length > 0) params.set("activities", happinessPreferences.join(","));
    params.set("budget", String(budget));
    if (distanceFromFamily) params.set("distance", distanceFromFamily);
    if (notes.trim()) params.set("notes", notes.trim());

    router.push(`/results?${params.toString()}`);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f3eee1_0%,#fffaf2_36%,#ffffff_74%)] px-6 py-10 sm:px-10 lg:px-16">
      <section className="mx-auto max-w-6xl">
        <div className="rounded-3xl border border-[#e8dcc9] bg-white/92 p-6 shadow-[0_24px_80px_-38px_rgba(96,80,56,0.38)] backdrop-blur sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#5d7f6b]">OPTIME Nursing</p>
          <h1 className="mt-4 max-w-4xl text-3xl font-semibold leading-tight text-[#2f2a24] sm:text-5xl">Find the right home, not just the best-rated one.</h1>
          <p className="mt-5 max-w-3xl text-lg text-[#6b6257]">A simple, family-friendly questionnaire built for clear decisions with less stress.</p>

          <div className={`mt-8 rounded-2xl border px-4 py-3 text-sm font-semibold sm:px-6 ${understanding.style}`}>{understanding.label}</div>

          <div className="mt-8 grid gap-5">
            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">1. Who are you searching for?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {relationshipOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={relationship === option} onClick={() => setRelationship(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">2. Age Group</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {ageGroupOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={ageGroup === option} onClick={() => setAgeGroup(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">3. How much daily assistance is needed?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {assistanceOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={assistanceLevel === option} onClick={() => setAssistanceLevel(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">4. Are there memory or confusion issues?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {memoryOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={memoryStatus === option} onClick={() => setMemoryStatus(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">5. What would make them happiest?</h3>
              <p className="mt-1 text-sm text-[#6c6358]">Select all that apply.</p>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {happinessOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={happinessPreferences.includes(option)}
                    onClick={() => setHappinessPreferences((current) => toggleOption(current, option))}
                  />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">6. Monthly budget</h3>
              <p className="mt-1 text-sm text-[#6c6358]">$3,000 - $15,000</p>
              <div className="mt-5">
                <input
                  type="range"
                  min={3000}
                  max={15000}
                  step={100}
                  value={budget}
                  onChange={(event) => setBudget(Number(event.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-[#e7ddd0] accent-[#6f8fb1]"
                />
                <p className="mt-3 text-base font-semibold text-[#5b7d9f]">${budget.toLocaleString()}</p>
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">7. Maximum distance from family</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {distanceOptions.map((option) => (
                  <OptionChip key={option} label={option} isActive={distanceFromFamily === option} onClick={() => setDistanceFromFamily(option)} />
                ))}
              </div>
            </article>

            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">8. Anything else we should know?</h3>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Anything important to your family or loved one that we should consider during matching."
                className="mt-4 min-h-32 w-full resize-y rounded-xl border border-[#dfd4c3] px-4 py-3 text-base text-[#52483d] outline-none ring-[#87a79b] transition placeholder:text-[#9f9384] focus:ring-2"
              />
              <p className="mt-3 text-xs text-[#8b7f71]">Examples: Loves old movies, Must have Hebrew speaking staff, Wants a Jewish community, Doesn't like noisy environments, Loves gardening</p>
            </article>
          </div>

          <div className="mt-8">
            <button
              type="button"
              onClick={handleFindHome}
              className="w-full rounded-full bg-[#7a9d87] px-6 py-4 text-base font-semibold text-white transition hover:bg-[#6b8b76] sm:w-auto"
            >
              {ctaText}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
