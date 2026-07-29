"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { OptimeDynamicLogo } from "@/components/brand/optime-dynamic-logo";
import { useQuestionnaire } from "@/context/questionnaire-context";
import { fetchPatientDecisionRecommendations, fetchPatientNeedsProfile } from "@/lib/api";

type SavedSearch = {
  id: string;
  title: string;
  naturalLanguageQuery: string;
  questionnaireState: Record<string, unknown>;
  createdAt: string;
};

type PatientProfileRecord = {
  id: string;
  label: string;
  version: number;
  updatedAt: string;
  state: Record<string, unknown>;
};

type QuestionnaireSectionKey =
  | "careNeeds"
  | "memoryCognitive"
  | "lifestyle"
  | "location"
  | "budget"
  | "languages"
  | "otherInterests";

type QuestionnaireSection = {
  key: QuestionnaireSectionKey;
  title: string;
};

const PATIENT_CASE_ID_SESSION_KEY = "optime.patient.case.id";
const RECENT_SEARCHES_STORAGE_KEY = "optime.recent.searches";
const SAVED_SEARCHES_STORAGE_KEY = "optime.saved.searches";
const PATIENT_PROFILES_STORAGE_KEY = "optime.patient.profiles";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

function loadSessionNumber(key: string): number | null {
  if (!hasWindow()) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = Number(JSON.parse(raw));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

function saveSessionNumber(key: string, value: number): void {
  if (!hasWindow()) return;
  if (!Number.isFinite(value) || value <= 0) return;
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Best effort only.
  }
}

function loadLocalRows<T extends { id: string }>(key: string): T[] {
  if (!hasWindow()) return [];
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return [];
    const rows = JSON.parse(raw) as T[];
    if (!Array.isArray(rows)) return [];
    const seen = new Set<string>();
    const deduped: T[] = [];
    for (const row of rows) {
      const id = String(row?.id || "").trim();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      deduped.push(row);
    }
    return deduped;
  } catch {
    return [];
  }
}

function saveLocalRows<T>(key: string, rows: T[]): void {
  if (!hasWindow()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(rows));
  } catch {
    // Best effort only.
  }
}

function loadRecentSearches(): SavedSearch[] {
  return loadLocalRows<SavedSearch>(RECENT_SEARCHES_STORAGE_KEY);
}

function saveRecentSearch(search: SavedSearch): void {
  const next = [search, ...loadRecentSearches().filter((item) => item.id !== search.id)].slice(0, 20);
  saveLocalRows(RECENT_SEARCHES_STORAGE_KEY, next);
}

function loadSavedSearches(): SavedSearch[] {
  return loadLocalRows<SavedSearch>(SAVED_SEARCHES_STORAGE_KEY);
}

function saveSavedSearch(search: SavedSearch): void {
  const next = [search, ...loadSavedSearches().filter((item) => item.id !== search.id)].slice(0, 50);
  saveLocalRows(SAVED_SEARCHES_STORAGE_KEY, next);
}

function loadPatientProfiles(): PatientProfileRecord[] {
  return loadLocalRows<PatientProfileRecord>(PATIENT_PROFILES_STORAGE_KEY);
}

function uid(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

const EXAMPLE_QUERY = "My mother is 82, has early dementia, enjoys music and social activities, speaks Hebrew and English, and our budget is $8,000 per month.";

const WORKFLOW_MESSAGES = [
  "Understanding care needs...",
  "Learning lifestyle preferences...",
  "Analyzing cognitive profile...",
  "Reviewing budget...",
  "Matching communities...",
  "Checking evidence...",
  "Preparing recommendations...",
  "Recommendation Ready.",
];

const QUESTIONNAIRE_SECTIONS: QuestionnaireSection[] = [
  { key: "careNeeds", title: "Care Needs" },
  { key: "memoryCognitive", title: "Memory & Cognitive Status" },
  { key: "lifestyle", title: "Lifestyle" },
  { key: "location", title: "Location" },
  { key: "budget", title: "Budget" },
  { key: "languages", title: "Languages" },
  { key: "otherInterests", title: "Other Interests" },
];

const CARE_NEEDS_OPTIONS = [
  "Fully independent",
  "Light assistance",
  "Help with bathing",
  "Help with dressing",
  "Help with medications",
  "24/7 support required",
  "Skilled nursing care",
];

const MEMORY_STATUS_OPTIONS = [
  "No",
  "Occasionally forgetful",
  "Mild memory issues",
  "Significant memory issues",
  "Not sure",
];

const LIFESTYLE_OPTIONS = [
  "Social activities",
  "Fitness & wellness",
  "Quiet environment",
  "Outdoor spaces",
  "Cultural programs",
  "Faith-based community",
];

const DISTANCE_STRATEGY_OPTIONS = [
  "Closest to resident",
  "Closest to family",
  "Balanced location",
  "Emergency priority",
  "Family visit maximization",
];

export default function HomePage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();

  const [query, setQuery] = useState(state.notes || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [liveSummary, setLiveSummary] = useState<string>("");
  const [workflowMessageIndex, setWorkflowMessageIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState<SavedSearch[]>(() => loadRecentSearches());
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(() => loadSavedSearches());
  const [patientProfiles] = useState<PatientProfileRecord[]>(() => loadPatientProfiles());
  const [isQuestionnaireOpen, setIsQuestionnaireOpen] = useState(false);
  const [questionnaireStep, setQuestionnaireStep] = useState(0);

  const assistanceLevelValue = String(state.assistanceLevel || "").trim();
  const memoryStatusValue = String(state.memoryStatus || "").trim();
  const locationValue = String(state.referenceAddress || state.distanceFromFamily || state.locationImportant || "").trim();
  const languagesValue = [
    state.humanIntelligenceV2.languageProfile.preferredSpokenLanguage,
    ...state.humanIntelligenceV2.languageProfile.languagesUnderstood,
  ]
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index)
    .join(", ");
  const lifestyleValue = state.happinessPreferences.length > 0 ? state.happinessPreferences.join(", ") : "";
  const interestsValue = String(state.otherInterests || "").trim() || state.humanIntelligenceV2.interestsProfile.join(", ");

  const missingRequirements = useMemo(() => {
    const missing: string[] = [];
    if (!assistanceLevelValue) missing.push("Care needs");
    if (!memoryStatusValue) missing.push("Cognitive status");
    if (!state.budget || state.budget <= 0) missing.push("Budget");
    if (!locationValue) missing.push("Preferred location");
    if (!lifestyleValue) missing.push("Lifestyle");
    if (!interestsValue) missing.push("Other interests");
    return missing;
  }, [assistanceLevelValue, interestsValue, lifestyleValue, locationValue, memoryStatusValue, state.budget]);

  const recommendationReady = query.trim().length > 0 && missingRequirements.length === 0;
  const currentQuestionnaireSection = QUESTIONNAIRE_SECTIONS[Math.min(questionnaireStep, QUESTIONNAIRE_SECTIONS.length - 1)];

  function updateQuestionnaireField<K extends keyof typeof state>(field: K, value: (typeof state)[K]): void {
    setState({ ...state, [field]: value });
  }

  function updateLanguageValues(value: string): void {
    const languages = value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    setState({
      ...state,
      humanIntelligenceV2: {
        ...state.humanIntelligenceV2,
        languageProfile: {
          ...state.humanIntelligenceV2.languageProfile,
          preferredSpokenLanguage: languages[0] || "",
          languagesUnderstood: languages,
        },
      },
    });
  }

  function updateOtherInterests(value: string): void {
    const items = value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    setState({
      ...state,
      otherInterests: value,
      humanIntelligenceV2: {
        ...state.humanIntelligenceV2,
        interestsProfile: items,
      },
    });
  }

  function toggleLifestyleOption(option: string): void {
    const next = state.happinessPreferences.includes(option)
      ? state.happinessPreferences.filter((item) => item !== option)
      : [...state.happinessPreferences, option];
    updateQuestionnaireField("happinessPreferences", next);
  }

  function isQuestionnaireSectionComplete(section: QuestionnaireSection): boolean {
    switch (section.key) {
      case "careNeeds":
        return assistanceLevelValue.length > 0;
      case "memoryCognitive":
        return memoryStatusValue.length > 0;
      case "lifestyle":
        return state.happinessPreferences.length > 0;
      case "location":
        return locationValue.length > 0;
      case "budget":
        return state.budget > 0;
      case "languages":
        return languagesValue.length > 0;
      case "otherInterests":
        return interestsValue.length > 0;
      default:
        return false;
    }
  }

  function goToNextQuestionnaireSection(): void {
    setQuestionnaireStep((current) => Math.min(current + 1, QUESTIONNAIRE_SECTIONS.length - 1));
  }

  function goToPreviousQuestionnaireSection(): void {
    setQuestionnaireStep((current) => Math.max(current - 1, 0));
  }

  const activeMessages = useMemo(() => {
    if (recommendationReady) {
      return WORKFLOW_MESSAGES;
    }

    const answeredSignals = [
      state.assistanceLevel,
      state.memoryStatus,
      String(state.budget > 0),
      locationValue,
      state.happinessPreferences.length > 0 ? "lifestyle" : "",
    ].filter((value) => String(value).trim().length > 0).length;

    const count = Math.min(WORKFLOW_MESSAGES.length - 1, Math.max(1, answeredSignals + 1));
    return WORKFLOW_MESSAGES.slice(0, count);
  }, [locationValue, recommendationReady, state.assistanceLevel, state.budget, state.happinessPreferences.length, state.memoryStatus]);

  const currentWorkflowMessage = activeMessages[Math.min(workflowMessageIndex, activeMessages.length - 1)] || WORKFLOW_MESSAGES[0];
  const aiProgress = recommendationReady
    ? 100
    : Math.round((Math.max(0, activeMessages.length - 1) / (WORKFLOW_MESSAGES.length - 1)) * 100);

  useEffect(() => {
    setWorkflowMessageIndex((current) => (current >= activeMessages.length ? 0 : current));
    const timer = window.setInterval(() => {
      setWorkflowMessageIndex((current) => {
        const next = current + 1;
        return next >= activeMessages.length ? 0 : next;
      });
    }, 1700);
    return () => window.clearInterval(timer);
  }, [activeMessages]);

  async function runSearch(inputQuery: string, saveAsFavorite = false): Promise<void> {
    const normalized = inputQuery.trim();
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

      const currentPatientCaseId = loadSessionNumber(PATIENT_CASE_ID_SESSION_KEY) || undefined;
      const canonicalQuestionnaire = nextQuestionnaire as Record<string, unknown>;
      const canonicalNaturalLanguage = normalized;
      setLiveSummary(normalized);

      const [, recommendations] = await Promise.all([
        fetchPatientNeedsProfile({
          questionnaire_state: canonicalQuestionnaire,
          natural_language_query: canonicalNaturalLanguage,
        }),
        fetchPatientDecisionRecommendations({
          patient_case_id: currentPatientCaseId,
          questionnaire_state: canonicalQuestionnaire,
          natural_language_query: canonicalNaturalLanguage,
          limit: 50,
        }),
      ]);

      if (typeof recommendations.patient_case_id === "number" && recommendations.patient_case_id > 0) {
        saveSessionNumber(PATIENT_CASE_ID_SESSION_KEY, recommendations.patient_case_id);
      }

      const searchRecord: SavedSearch = {
        id: uid("search"),
        title: normalized.slice(0, 72) || "Untitled search",
        naturalLanguageQuery: normalized,
        questionnaireState: nextQuestionnaire,
        createdAt: new Date().toISOString(),
      };
      saveRecentSearch(searchRecord);
      setRecentSearches(loadRecentSearches());
      if (saveAsFavorite) {
        saveSavedSearch(searchRecord);
        setSavedSearches(loadSavedSearches());
      }

      const params = new URLSearchParams();
      if (normalized) params.set("notes", normalized);
      if (state.relationship) params.set("relationship", state.relationship);
      if (state.ageGroup) params.set("age", state.ageGroup);
      if (state.assistanceLevel) params.set("care", state.assistanceLevel);
      if (state.memoryStatus) params.set("memory", state.memoryStatus);
      if (state.budget) params.set("budget", String(state.budget));
      if (state.distanceFromFamily) params.set("distanceStrategy", state.distanceFromFamily);
      router.push(`/results?${params.toString()}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to run AI search at the moment.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function startVoiceInput(): void {
    const windowWithSpeech = window as unknown as {
      webkitSpeechRecognition?: new () => {
        lang: string;
        interimResults: boolean;
        maxAlternatives: number;
        onresult: ((event: { results?: ArrayLike<ArrayLike<{ transcript?: string }>> }) => void) | null;
        onerror: (() => void) | null;
        onend: (() => void) | null;
        start: () => void;
      };
      SpeechRecognition?: new () => {
        lang: string;
        interimResults: boolean;
        maxAlternatives: number;
        onresult: ((event: { results?: ArrayLike<ArrayLike<{ transcript?: string }>> }) => void) | null;
        onerror: (() => void) | null;
        onend: (() => void) | null;
        start: () => void;
      };
    };
    const SpeechRecognitionCtor = windowWithSpeech.webkitSpeechRecognition || windowWithSpeech.SpeechRecognition;

    if (!SpeechRecognitionCtor) {
      setError("Voice capture is not available in this browser. You can still type your case in natural language.");
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      if (transcript) setQuery((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onerror = () => {
      setError("Voice input encountered an issue. Please continue by typing.");
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);
    recognition.start();
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void runSearch(query, false);
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(1200px_circle_at_15%_-10%,#d2efe5_0%,transparent_50%),radial-gradient(900px_circle_at_85%_0%,#ffe7c8_0%,transparent_45%),linear-gradient(180deg,#f8f7f3_0%,#fffefe_100%)] px-4 py-8 sm:px-8 lg:px-14">
      <section className="mx-auto max-w-7xl space-y-8">
        <header className="rounded-[2rem] border border-[#dce8e2] bg-white/90 p-8 shadow-[0_28px_90px_-54px_rgba(22,36,27,0.48)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#2f6c5f]">OPTIME AI Decision Engine</p>
          <h1 className="mt-3 max-w-4xl text-3xl font-semibold leading-tight text-[#1f2a24] sm:text-5xl">
            Find the Right Senior Living Community - Not Just the Highest Rated One.
          </h1>
          <p className="mt-4 max-w-4xl text-base leading-7 text-[#43534c] sm:text-lg">
            OPTIME evaluates hundreds of verified care, lifestyle, quality, and evidence parameters to build a patient needs profile and ranked recommendations with confidence.
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4" aria-label="AI search">
            <label htmlFor="ai-case-input" className="block text-sm font-semibold text-[#2b3632]">Describe your family case in natural language</label>
            <textarea
              id="ai-case-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              rows={5}
              placeholder={EXAMPLE_QUERY}
              className="w-full rounded-3xl border border-[#c7d7cf] bg-white px-5 py-4 text-base leading-7 text-[#26312d] outline-none ring-[#78b9a5] transition focus:ring-2"
            />
            <div className="flex flex-wrap gap-3">
              <button type="submit" disabled={isSubmitting} className="rounded-full bg-[#1f7a67] px-6 py-3 text-sm font-semibold text-white hover:bg-[#186251] disabled:cursor-not-allowed disabled:opacity-70">
                {isSubmitting ? "Building your recommendations..." : "Run AI Recommendation"}
              </button>
              <button type="button" onClick={() => setQuery(EXAMPLE_QUERY)} className="rounded-full border border-[#c7d7cf] bg-white px-5 py-3 text-sm font-semibold text-[#33544a] hover:bg-[#f3faf7]">
                Use Example
              </button>
              <button type="button" onClick={startVoiceInput} className="rounded-full border border-[#c7d7cf] bg-white px-5 py-3 text-sm font-semibold text-[#33544a] hover:bg-[#f3faf7]" aria-pressed={isListening}>
                {isListening ? "Listening..." : "Voice Capture"}
              </button>
              <button type="button" onClick={() => void runSearch(query, true)} disabled={isSubmitting || !query.trim()} className="rounded-full border border-[#d8cba9] bg-[#fff6e7] px-5 py-3 text-sm font-semibold text-[#6a4f1f] hover:bg-[#ffeed2] disabled:cursor-not-allowed disabled:opacity-60">
                Save Search
              </button>
              <button
                type="button"
                onClick={() => setIsQuestionnaireOpen((current) => !current)}
                className="rounded-full border border-[#d6ddf0] bg-[#eff4ff] px-5 py-3 text-sm font-semibold text-[#22436a] hover:bg-[#dfe9fb]"
                aria-expanded={isQuestionnaireOpen}
                aria-controls="homepage-questionnaire"
              >
                {isQuestionnaireOpen ? "Hide Conversational Questionnaire" : "Conversational Questionnaire"}
              </button>
            </div>
          </form>

          {error ? <p className="mt-4 rounded-2xl border border-[#f3c8bc] bg-[#fff1ed] px-4 py-3 text-sm text-[#8b3d2e]">{error}</p> : null}

          <div
            id="homepage-questionnaire"
            className="overflow-hidden transition-all duration-500 ease-in-out"
            style={{
              maxHeight: isQuestionnaireOpen ? "1200px" : "0px",
              opacity: isQuestionnaireOpen ? 1 : 0,
              marginTop: isQuestionnaireOpen ? "1.5rem" : "0rem",
            }}
          >
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-5">
              <div className="flex flex-wrap items-center gap-3 text-sm text-[#35544b]" aria-label="Questionnaire sections progress">
                {QUESTIONNAIRE_SECTIONS.map((section, index) => {
                  const isCurrent = currentQuestionnaireSection?.key === section.key;
                  const isComplete = isQuestionnaireSectionComplete(section);
                  return (
                    <div key={section.key} className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setQuestionnaireStep(index)}
                        className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${isCurrent ? "border-[#2f7e69] bg-[#eaf7f2] text-[#205245]" : isComplete ? "border-[#bed8ce] bg-white text-[#2c5a4d]" : "border-[#d6e4de] bg-white text-[#5b776d]"}`}
                      >
                        {section.title}
                      </button>
                      {index < QUESTIONNAIRE_SECTIONS.length - 1 ? <span aria-hidden>↓</span> : null}
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 rounded-2xl border border-[#d9e7e1] bg-white/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5c7b71]">{currentQuestionnaireSection?.title}</p>

                {currentQuestionnaireSection?.key === "careNeeds" ? (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {CARE_NEEDS_OPTIONS.map((option) => {
                      const selected = state.assistanceLevel === option;
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => updateQuestionnaireField("assistanceLevel", option)}
                          className={`rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${selected ? "border-[#2f7e69] bg-[#eaf7f2] text-[#215445]" : "border-[#d6e5df] bg-white text-[#34534a] hover:bg-[#f3faf7]"}`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                ) : null}

                {currentQuestionnaireSection?.key === "memoryCognitive" ? (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {MEMORY_STATUS_OPTIONS.map((option) => {
                      const selected = state.memoryStatus === option;
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => updateQuestionnaireField("memoryStatus", option)}
                          className={`rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${selected ? "border-[#2f7e69] bg-[#eaf7f2] text-[#215445]" : "border-[#d6e5df] bg-white text-[#34534a] hover:bg-[#f3faf7]"}`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                ) : null}

                {currentQuestionnaireSection?.key === "lifestyle" ? (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {LIFESTYLE_OPTIONS.map((option) => {
                      const selected = state.happinessPreferences.includes(option);
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => toggleLifestyleOption(option)}
                          className={`rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${selected ? "border-[#2f7e69] bg-[#eaf7f2] text-[#215445]" : "border-[#d6e5df] bg-white text-[#34534a] hover:bg-[#f3faf7]"}`}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                ) : null}

                {currentQuestionnaireSection?.key === "location" ? (
                  <div className="mt-3 space-y-3">
                    <input
                      type="text"
                      value={state.locationImportant}
                      onChange={(event) => {
                        const value = event.target.value;
                        setState({
                          ...state,
                          locationImportant: value,
                          referenceAddress: value,
                        });
                      }}
                      placeholder="Preferred location or city"
                      className="w-full rounded-2xl border border-[#c9ddd5] bg-white px-4 py-3 text-sm text-[#28433b] outline-none ring-[#8fcbb8] focus:ring-2"
                    />
                    <select
                      value={state.distanceFromFamily}
                      onChange={(event) => updateQuestionnaireField("distanceFromFamily", event.target.value)}
                      className="w-full rounded-2xl border border-[#c9ddd5] bg-white px-4 py-3 text-sm text-[#28433b] outline-none ring-[#8fcbb8] focus:ring-2"
                    >
                      <option value="">Select distance strategy</option>
                      {DISTANCE_STRATEGY_OPTIONS.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>
                ) : null}

                {currentQuestionnaireSection?.key === "budget" ? (
                  <div className="mt-3 space-y-2">
                    <input
                      type="number"
                      min={1000}
                      step={100}
                      value={state.budget || 0}
                      onChange={(event) => updateQuestionnaireField("budget", Number(event.target.value) || 0)}
                      className="w-full rounded-2xl border border-[#c9ddd5] bg-white px-4 py-3 text-sm text-[#28433b] outline-none ring-[#8fcbb8] focus:ring-2"
                    />
                    <p className="text-sm text-[#4d675f]">
                      We&apos;ll also search approximately 20% above and below your preferred budget to avoid missing an excellent match.
                    </p>
                  </div>
                ) : null}

                {currentQuestionnaireSection?.key === "languages" ? (
                  <input
                    type="text"
                    value={languagesValue}
                    onChange={(event) => updateLanguageValues(event.target.value)}
                    placeholder="English, Hebrew"
                    className="mt-3 w-full rounded-2xl border border-[#c9ddd5] bg-white px-4 py-3 text-sm text-[#28433b] outline-none ring-[#8fcbb8] focus:ring-2"
                  />
                ) : null}

                {currentQuestionnaireSection?.key === "otherInterests" ? (
                  <div className="mt-3 space-y-2">
                    <textarea
                      rows={3}
                      value={state.otherInterests}
                      onChange={(event) => updateOtherInterests(event.target.value)}
                      placeholder="Gardening, Music, Reading"
                      className="w-full rounded-2xl border border-[#c9ddd5] bg-white px-4 py-3 text-sm text-[#28433b] outline-none ring-[#8fcbb8] focus:ring-2"
                    />
                    <p className="text-sm text-[#4d675f]">Examples: Gardening, Music, Reading, Movies, Art, Cooking, Walking, Pets</p>
                  </div>
                ) : null}

                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={goToPreviousQuestionnaireSection}
                    disabled={questionnaireStep === 0}
                    className="rounded-full border border-[#c9ddd5] bg-white px-5 py-2.5 text-sm font-semibold text-[#35574d] hover:bg-[#f3faf7] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    onClick={goToNextQuestionnaireSection}
                    disabled={!currentQuestionnaireSection || !isQuestionnaireSectionComplete(currentQuestionnaireSection)}
                    className="rounded-full bg-[#1f7a67] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[#186251] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {questionnaireStep >= QUESTIONNAIRE_SECTIONS.length - 1 ? "Questionnaire Complete" : "Next"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div id="ai-workspace" className="mt-6 rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-5">
            <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <div className="space-y-4 rounded-2xl border border-[#d9e7e1] bg-white/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[#5c7b71]">AI Workflow Status</p>
                <OptimeDynamicLogo progress={aiProgress} ready={recommendationReady} />
                <p className="min-h-[1.25rem] text-sm font-medium text-[#315148]">{currentWorkflowMessage}</p>
              </div>

              <div className="rounded-2xl border border-[#d9e7e1] bg-white/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5c7b71]">Patient Profile Summary</p>
                <ul className="mt-3 space-y-2 text-sm text-[#2b3b35]">
                  <li>{assistanceLevelValue ? `✓ Care Needs: ${assistanceLevelValue}` : "Care Needs: Needed"}</li>
                  <li>{memoryStatusValue ? `✓ Cognitive Status: ${memoryStatusValue}` : "Cognitive Status: Needed"}</li>
                  <li>{state.budget > 0 ? `✓ Budget: $${Number(state.budget).toLocaleString()}` : "Budget: Needed"}</li>
                  <li>{locationValue ? `✓ Preferred Location: ${locationValue}` : "Preferred Location: Needed"}</li>
                  <li>{languagesValue ? `✓ Languages: ${languagesValue}` : "Languages: Needed"}</li>
                  <li>{lifestyleValue ? `✓ Lifestyle: ${lifestyleValue}` : "Lifestyle: Needed"}</li>
                  <li>{interestsValue ? `✓ Other Interests: ${interestsValue}` : "Other Interests: Needed"}</li>
                </ul>

                <div className="mt-4 rounded-xl border border-[#dce8e2] bg-[#f8fcfa] p-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#5c7b71]">Recommendation Status</p>
                  {recommendationReady ? (
                    <p className="mt-2 text-sm font-semibold text-[#2b6c5d]">Recommendation Ready</p>
                  ) : (
                    <div className="mt-2 space-y-2 text-sm text-[#3b534a]">
                      <p className="font-semibold">Almost Ready</p>
                      <p>Still needed:</p>
                      <ul className="list-disc pl-5">
                        {missingRequirements.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {liveSummary ? (
            <div className="mt-4 rounded-2xl border border-[#cfe0d9] bg-[#f6fcf9] px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#3b6c5f]">Live Patient Summary</p>
              <p className="mt-1 text-sm text-[#335149]">{liveSummary}</p>
            </div>
          ) : null}
        </header>

        <section className="grid gap-6 lg:grid-cols-3">
          <article className="rounded-3xl border border-[#dce8e2] bg-white p-6 shadow-[0_16px_54px_-42px_rgba(24,46,37,0.4)]">
            <h2 className="text-lg font-semibold text-[#21342d]">Recent Searches</h2>
            <ul className="mt-4 space-y-3">
              {recentSearches.slice(0, 5).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setQuery(item.naturalLanguageQuery);
                      void runSearch(item.naturalLanguageQuery, false);
                    }}
                    className="w-full rounded-2xl border border-[#e1ece7] bg-[#f8fcfa] px-4 py-3 text-left text-sm text-[#365148] hover:bg-[#edf8f3]"
                  >
                    <p className="line-clamp-2 font-medium">{item.title}</p>
                    <p className="mt-1 text-xs text-[#6a837a]">{new Date(item.createdAt).toLocaleString()}</p>
                  </button>
                </li>
              ))}
              {recentSearches.length === 0 ? <li className="text-sm text-[#688076]">No recent searches yet.</li> : null}
            </ul>
          </article>

          <article className="rounded-3xl border border-[#e8decb] bg-white p-6 shadow-[0_16px_54px_-42px_rgba(60,45,19,0.35)]">
            <h2 className="text-lg font-semibold text-[#3f321e]">Saved Searches</h2>
            <ul className="mt-4 space-y-3">
              {savedSearches.slice(0, 5).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setQuery(item.naturalLanguageQuery);
                      void runSearch(item.naturalLanguageQuery, false);
                    }}
                    className="w-full rounded-2xl border border-[#efe2cc] bg-[#fffaef] px-4 py-3 text-left text-sm text-[#5e4923] hover:bg-[#fff4df]"
                  >
                    <p className="line-clamp-2 font-medium">{item.title}</p>
                    <p className="mt-1 text-xs text-[#8d7242]">{new Date(item.createdAt).toLocaleString()}</p>
                  </button>
                </li>
              ))}
              {savedSearches.length === 0 ? <li className="text-sm text-[#8d7242]">No saved searches yet.</li> : null}
            </ul>
            <Link href="/workspace" className="mt-4 inline-flex rounded-full border border-[#e6d7bb] px-4 py-2 text-sm font-semibold text-[#6c5427] hover:bg-[#fff5df]">
              Open Saved Workspace
            </Link>
          </article>

          <article className="rounded-3xl border border-[#d8def0] bg-white p-6 shadow-[0_16px_54px_-42px_rgba(33,45,77,0.35)]">
            <h2 className="text-lg font-semibold text-[#223960]">Patient Profiles</h2>
            <ul className="mt-4 space-y-3">
              {patientProfiles.slice(0, 5).map((profile) => (
                <li key={profile.id}>
                  <button
                    type="button"
                    onClick={() => {
                      const profileState = profile.state;
                      const mergedState = {
                        ...state,
                        ...(profileState as Partial<typeof state>),
                        locationImportant: String((profileState as Partial<typeof state>).locationImportant ?? state.locationImportant ?? ""),
                        referenceAddress: String((profileState as Partial<typeof state>).referenceAddress ?? state.referenceAddress ?? ""),
                        maximumDistanceMiles: String((profileState as Partial<typeof state>).maximumDistanceMiles ?? state.maximumDistanceMiles ?? ""),
                        customDistanceMiles: String((profileState as Partial<typeof state>).customDistanceMiles ?? state.customDistanceMiles ?? ""),
                        otherInterests: String((profileState as Partial<typeof state>).otherInterests ?? state.otherInterests ?? ""),
                      };
                      setState(mergedState);
                      const profileNotes = typeof profileState.notes === "string" ? profileState.notes : "";
                      setQuery(profileNotes);
                    }}
                    className="w-full rounded-2xl border border-[#dde4f7] bg-[#f5f8ff] px-4 py-3 text-left text-sm text-[#27446f] hover:bg-[#eaf1ff]"
                  >
                    <p className="font-medium">{profile.label}</p>
                    <p className="mt-1 text-xs text-[#5f7395]">Version {profile.version} | {new Date(profile.updatedAt).toLocaleString()}</p>
                  </button>
                </li>
              ))}
              {patientProfiles.length === 0 ? <li className="text-sm text-[#6178a0]">No saved patient profiles yet.</li> : null}
            </ul>
            <Link href="/profiles" className="mt-4 inline-flex rounded-full border border-[#cad8f5] px-4 py-2 text-sm font-semibold text-[#2e4d7d] hover:bg-[#edf3ff]">
              Manage Profiles
            </Link>
          </article>
        </section>

        <section className="rounded-3xl border border-[#d9e6de] bg-white p-6">
          <h2 className="text-xl font-semibold text-[#20322b]">How OPTIME 2.0 works</h2>
          <div className="mt-4 grid gap-3 text-sm text-[#41564e] sm:grid-cols-2 lg:grid-cols-4">
            <p className="rounded-2xl border border-[#e4eee9] bg-[#f8fcfa] px-4 py-3">Natural language or conversational questionnaire intake</p>
            <p className="rounded-2xl border border-[#e4eee9] bg-[#f8fcfa] px-4 py-3">AI-generated patient needs profile with weighted parameters</p>
            <p className="rounded-2xl border border-[#e4eee9] bg-[#f8fcfa] px-4 py-3">Evidence-driven ranking with confidence and runtime versioning</p>
            <p className="rounded-2xl border border-[#e4eee9] bg-[#f8fcfa] px-4 py-3">Save comparisons, profiles, and recommendation sessions in workspace</p>
          </div>
        </section>
      </section>
    </main>
  );
}
