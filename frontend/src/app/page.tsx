"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useQuestionnaire } from "@/context/questionnaire-context";

const relationshipOptions = ["Mom", "Dad", "Grandma", "Grandpa", "Spouse", "Myself", "Couple", "Relative", "Friend"];

const genderOptions = ["Male", "Female", "Prefer not to say"];

const coupleAssistanceOptions = ["Husband", "Wife", "Both equally"];

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

function relationshipCopy(relationship: string): string {
  if (relationship === "Myself") return "You";
  if (relationship === "Couple") return "You both";
  return relationship || "your loved one";
}

function ctaCopy(relationship: string): string {
  if (relationship === "Myself") return "Find the right home for me";
  if (relationship === "Couple") return "Find the right home for us";
  if (relationship) return `Find the right home for ${relationship}`;
  return "Find the right home";
}

export default function Home() {
  const router = useRouter();
  const { setState } = useQuestionnaire();

  const [relationship, setRelationship] = useState("");
  const [gender, setGender] = useState("");
  const [coupleAssistance, setCoupleAssistance] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [assistanceLevel, setAssistanceLevel] = useState("");
  const [memoryStatus, setMemoryStatus] = useState("");
  const [happinessPreferences, setHappinessPreferences] = useState<string[]>([]);
  const [budget, setBudget] = useState(7000);
  const [distanceFromFamily, setDistanceFromFamily] = useState("");
  const [referenceLocationType, setReferenceLocationType] = useState("");
  const [referenceLocationValue, setReferenceLocationValue] = useState("");
  const [maxDistanceMiles, setMaxDistanceMiles] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  const relationshipLabel = relationshipCopy(relationship);

  const ctaText = useMemo(() => ctaCopy(relationship), [relationship]);

  const handleFindHome = () => {
    setState({
      relationship,
      gender,
      coupleAssistance,
      ageGroup,
      assistanceLevel,
      memoryStatus,
      happinessPreferences,
      budget,
      distanceFromFamily,
      referenceLocationType: referenceLocationType || "",
      referenceLocationValue: referenceLocationValue || "",
      maxDistanceMiles: maxDistanceMiles || null,
      notes,
    });

    const params = new URLSearchParams();
    if (relationship) params.set("relationship", relationship);
    if (gender) params.set("gender", gender);
    if (coupleAssistance) params.set("coupleAssistance", coupleAssistance);
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
        <div className="rounded-3xl border border-[#e8dcc9] bg-white/92 p-4 shadow-[0_24px_80px_-38px_rgba(96,80,56,0.38)] backdrop-blur sm:p-6">
          <section className="relative overflow-hidden rounded-3xl border border-[#e7dcc9] bg-[#f8f3e8]">
            <img
              src="/hero-reference.png"
              alt="OPTIME hero reference image"
              className="h-[420px] w-full object-cover object-[62%_center] sm:h-[470px]"
            />
            <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(246,241,232,0.9)_0%,rgba(246,241,232,0.66)_42%,rgba(246,241,232,0.2)_70%,rgba(246,241,232,0.06)_100%)]" />
            <div className="absolute inset-y-0 left-0 z-10 w-full rounded-3xl bg-[rgba(255,251,244,0.76)] backdrop-blur-[1.5px] sm:w-[64%]" />

            <div className="absolute inset-y-0 left-0 z-20 flex w-full items-center px-6 py-6 sm:w-[64%] sm:px-10 lg:px-12">
              <div className="w-full max-w-2xl">
                <div className="flex items-center gap-3 text-[#62816c]">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#a6bea8] bg-white/85 text-lg">✤</span>
                  <div>
                    <p className="text-2xl font-semibold tracking-[0.16em]">OPTIME</p>
                    <p className="text-sm text-[#70856f]">Better choices. Better lives.</p>
                  </div>
                </div>

                <h1 className="mt-5 text-4xl font-semibold leading-[1.05] text-[#1f392a] sm:text-6xl">
                  Find the right home,
                  <br />
                  not just the best-rated one.
                </h1>

                <div className="mt-5 h-1 w-16 rounded-full bg-[#c9a15d]" />

                <p className="mt-5 text-lg leading-relaxed text-[#4f5d4d]">
                  A simple, family-friendly questionnaire built for clear decisions with less stress.
                </p>

                <div className="mt-7 flex flex-wrap gap-2.5 text-sm">
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Personalized Matching</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Transparent Scoring</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ Family First</p>
                  <p className="rounded-full bg-[#6d8f72] px-4 py-2 font-semibold text-white">✓ AI Assisted Decisions</p>
                </div>
              </div>
            </div>
          </section>

          <div className="mt-6 grid gap-5">
            <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
              <h3 className="text-lg font-semibold text-[#2f2a24]">1. Who are you searching for?</h3>
              <div className="mt-4 flex flex-wrap gap-2.5">
                {relationshipOptions.map((option) => (
                  <OptionChip
                    key={option}
                    label={option}
                    isActive={relationship === option}
                    onClick={() => {
                      setRelationship(option);
                      if (option !== "Myself") setGender("");
                      if (option !== "Couple") setCoupleAssistance("");
                    }}
                  />
                ))}
              </div>
            </article>

            {relationship === "Myself" ? (
              <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
                <h3 className="text-lg font-semibold text-[#2f2a24]">Gender</h3>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  {genderOptions.map((option) => (
                    <OptionChip key={option} label={option} isActive={gender === option} onClick={() => setGender(option)} />
                  ))}
                </div>
              </article>
            ) : null}

            {relationship === "Couple" ? (
              <article className="rounded-2xl border border-[#e7ddcd] bg-[#fffefb] p-5">
                <h3 className="text-lg font-semibold text-[#2f2a24]">Who needs more assistance?</h3>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  {coupleAssistanceOptions.map((option) => (
                    <OptionChip
                      key={option}
                      label={option}
                      isActive={coupleAssistance === option}
                      onClick={() => setCoupleAssistance(option)}
                    />
                  ))}
                </div>
              </article>
            ) : null}

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
              <h3 className="text-lg font-semibold text-[#2f2a24]">5. What would make {relationshipLabel} happiest?</h3>
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
