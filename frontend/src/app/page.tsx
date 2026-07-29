"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

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

export default function HomePage() {
  const router = useRouter();
  const { state, setState } = useQuestionnaire();

  const [query, setQuery] = useState(state.notes || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [estimatedMatches, setEstimatedMatches] = useState<number | null>(null);
  const [profilePreviewCount, setProfilePreviewCount] = useState<number | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [liveSummary, setLiveSummary] = useState<string>("");
  const [recentSearches, setRecentSearches] = useState<SavedSearch[]>(() => loadRecentSearches());
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>(() => loadSavedSearches());
  const [patientProfiles] = useState<PatientProfileRecord[]>(() => loadPatientProfiles());

  const confidencePreview = useMemo(() => {
    if (profilePreviewCount === null) return "Pending";
    if (profilePreviewCount >= 12) return "High";
    if (profilePreviewCount >= 6) return "Medium";
    return "Low";
  }, [profilePreviewCount]);

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

      const [needs, recommendations] = await Promise.all([
        fetchPatientNeedsProfile({
          patient_case_id: currentPatientCaseId,
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

      setProfilePreviewCount(needs.needs.length);
      setEstimatedMatches(recommendations.total_candidates_scored || recommendations.result_count);

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
              <Link href="/questionnaire" className="rounded-full border border-[#d6ddf0] bg-[#eff4ff] px-5 py-3 text-sm font-semibold text-[#22436a] hover:bg-[#dfe9fb]">Conversational Questionnaire</Link>
            </div>
          </form>

          {error ? <p className="mt-4 rounded-2xl border border-[#f3c8bc] bg-[#fff1ed] px-4 py-3 text-sm text-[#8b3d2e]">{error}</p> : null}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-4">
              <p className="text-xs uppercase tracking-[0.15em] text-[#5c7b71]">Patient Needs Profile</p>
              <p className="mt-2 text-2xl font-semibold text-[#234139]">{profilePreviewCount ?? "--"}</p>
              <p className="mt-1 text-xs text-[#577168]">scored need signals</p>
            </div>
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-4">
              <p className="text-xs uppercase tracking-[0.15em] text-[#5c7b71]">Estimated Match Count</p>
              <p className="mt-2 text-2xl font-semibold text-[#234139]">{estimatedMatches ?? "--"}</p>
              <p className="mt-1 text-xs text-[#577168]">candidate communities</p>
            </div>
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-4">
              <p className="text-xs uppercase tracking-[0.15em] text-[#5c7b71]">Confidence Preview</p>
              <p className="mt-2 text-2xl font-semibold text-[#234139]">{confidencePreview}</p>
              <p className="mt-1 text-xs text-[#577168]">evidence confidence band</p>
            </div>
            <div className="rounded-2xl border border-[#dce8e2] bg-[#f8fcfa] p-4">
              <p className="text-xs uppercase tracking-[0.15em] text-[#5c7b71]">Voice Architecture</p>
              <p className="mt-2 text-2xl font-semibold text-[#234139]">Ready</p>
              <p className="mt-1 text-xs text-[#577168]">Web Speech adapter enabled</p>
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
