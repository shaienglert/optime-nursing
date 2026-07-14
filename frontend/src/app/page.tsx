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
          <section className="relative overflow-hidden rounded-3xl border border-[#e7dcc9]">
            <img
              src="https://images.unsplash.com/photo-1516307365426-bea591f05011?auto=format&fit=crop&w=1800&q=80"
              alt="Warm senior living community with gardens and outdoor seating"
              className="h-[540px] w-full object-cover object-center sm:h-[640px]"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[rgba(255,251,243,0.98)] via-[rgba(255,251,243,0.85)] to-[rgba(255,251,243,0.08)]" />
            <div className="absolute inset-y-0 left-0 z-10 flex w-full items-center p-6 sm:w-[78%] sm:p-10 lg:w-[56%] lg:p-12">
              <div className="rounded-3xl bg-[rgba(255,252,246,0.55)] p-4 backdrop-blur-[2px] sm:p-6">
                <div className="flex items-center gap-3 text-[#62816c]">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[#a6bea8] bg-white/70 text-xl">✿</span>
                  <div>
                    <p className="text-2xl font-semibold tracking-[0.16em]">OPTIME</p>
                    <p className="text-sm text-[#70856f]">Better choices. Better lives.</p>
                  </div>
                </div>

                <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-[1.05] text-[#1f392a] sm:text-6xl">
                  Find the right home,
                  <br />
                  not just the best-rated one.
                </h1>

                <div className="mt-5 h-1 w-16 rounded-full bg-[#c9a15d]" />

                <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[#4f5d4d]">
                  A simple, family-friendly questionnaire built for clear decisions with less stress.
                </p>

                <button
                  type="button"
                  onClick={() => window.scrollTo({ top: 720, behavior: "smooth" })}
                  className="mt-7 inline-flex items-center gap-3 rounded-2xl bg-[#6d8f72] px-7 py-3 text-lg font-semibold text-white shadow-[0_10px_24px_-14px_rgba(57,85,58,0.55)] transition hover:bg-[#5f8065]"
                >
                  Let&apos;s get started
                  <span aria-hidden="true">→</span>
                </button>

                <div className="mt-7 grid grid-cols-2 gap-3 text-sm text-[#4a5547] sm:grid-cols-4">
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/72 px-3 py-2 text-center">Trusted Information</p>
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/72 px-3 py-2 text-center">Personalized Matches</p>
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/72 px-3 py-2 text-center">Family Focused</p>
                  <p className="rounded-xl border border-[#d8d3c7] bg-white/72 px-3 py-2 text-center">Private &amp; Secure</p>
                </div>
              </div>
            </div>
          </section>

          <div className="mt-8 grid gap-5">
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
