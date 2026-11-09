"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import {
  AnswerState,
  Completeness,
  ProfileSnapshot,
  QuestionnaireDetails,
  addFacilityPhoto,
  ensureOpticareDemo,
  fetchProfileSnapshot,
  formatPercent,
  isDerived,
  removeFacilityPhoto,
  saveCapabilities,
} from "@/lib/provider-api";

const PROVIDER_USER_KEY = "optime_provider_user_id";

/**
 * The verified provider session is browser state owned outside React, so it is read as an
 * external store rather than copied into state by an effect. The server snapshot is null,
 * which is also the correct answer during SSR: nobody is signed in until the browser says so.
 */
function subscribeToProviderSession(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function readProviderUserId(): number | null {
  try {
    const stored = window.localStorage.getItem(PROVIDER_USER_KEY);
    const parsed = stored ? Number(stored) : Number.NaN;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
}

const ANSWER_CHOICES: { value: AnswerState; label: string }[] = [
  { value: "YES", label: "Yes" },
  { value: "LIMITED", label: "Limited" },
  { value: "NO", label: "No" },
  { value: "UNKNOWN", label: "Not sure" },
];

/**
 * The profile editor.
 *
 * Two things drive the layout. The provider is correcting a pre-filled table rather than
 * filling a blank form, so what we already hold is shown first and plainly. And an unknown
 * is drawn as a gap rather than a fault -- the incentive to answer is that a blank cannot
 * match, not that a blank looks bad.
 *
 * The user id is read from the identity session the claim flow establishes. Until that flow
 * is wired to this page, an unverified visitor sees the profile read-only rather than a
 * broken save.
 */
export default function ProviderProfilePage({
  params,
}: {
  params: Promise<{ facilityId: string }>;
}) {
  const { facilityId: rawId } = use(params);
  const facilityId = Number(rawId);

  const [snapshot, setSnapshot] = useState<ProfileSnapshot | null>(null);
  const [draft, setDraft] = useState<Record<string, AnswerState>>({});
  const [detailDraft, setDetailDraft] = useState<Record<string, QuestionnaireDetails>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [photoUrl, setPhotoUrl] = useState("");
  const [photoCaption, setPhotoCaption] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  // Established by the identity/claim flow (provider_identity register + verify).
  const userId = useSyncExternalStore(subscribeToProviderSession, readProviderUserId, () => null);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);

  useEffect(() => {
    if (!Number.isFinite(facilityId)) return;
    let isMounted = true;

    async function loadProfile() {
      setIsLoading(true);
      setError(null);
      try {
        const next = await fetchProfileSnapshot(facilityId);
        if (isMounted) {
          setSnapshot(next);
          setDraft({});
          setDetailDraft({});
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "This profile could not be loaded.");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    void loadProfile();
    return () => {
      isMounted = false;
    };
  }, [facilityId, reloadToken]);

  const pendingCount = Object.keys(draft).length;
  const canEdit = userId !== null;

  const answerOf = useCallback(
    (key: string, saved: AnswerState): AnswerState => draft[key] ?? saved,
    [draft],
  );

  const onSave = async () => {
    if (!canEdit || pendingCount === 0) return;
    setIsSaving(true);
    setError(null);
    setNotice(null);
    try {
      const result = await saveCapabilities(facilityId, userId, draft, Object.fromEntries(Object.keys(draft).map((key) => {
        const saved = snapshot?.sections.flatMap((section) => section.questions).find((question) => question.key === key);
        return [key, detailDraft[key] ?? saved?.details ?? {}];
      })));
      setNotice(
        result.updated === 0
          ? "Nothing changed — those answers were already recorded."
          : `Saved ${result.updated} ${result.updated === 1 ? "answer" : "answers"}.`,
      );
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setIsSaving(false);
    }
  };

  const onAddPhoto = async () => {
    if (!canEdit || !photoUrl.trim()) return;
    setError(null);
    setNotice(null);
    try {
      await addFacilityPhoto(facilityId, userId, {
        url: photoUrl.trim(),
        caption: photoCaption.trim() || undefined,
      });
      setPhotoUrl("");
      setPhotoCaption("");
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The photograph could not be added.");
    }
  };

  const onRemovePhoto = async (photoId: number) => {
    if (!canEdit) return;
    setError(null);
    try {
      await removeFacilityPhoto(facilityId, userId, photoId);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The photograph could not be removed.");
    }
  };

  const enterDemoWorkspace = async () => {
    setError(null);
    try {
      const demo = await ensureOpticareDemo();
      if (demo.facility_id !== facilityId) {
        throw new Error("This practice access is only available for the OPTICARE demonstration profile.");
      }
      window.localStorage.setItem(PROVIDER_USER_KEY, String(demo.user_id));
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The practice workspace could not be opened.");
    }
  };

  if (isLoading) {
    return <main className="mx-auto max-w-4xl px-6 py-14 text-muted">Loading profile&hellip;</main>;
  }

  if (!snapshot) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-14">
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          {error ?? "Profile not found."}
        </p>
        <Link href="/provider" className="mt-4 inline-block text-forest underline">
          Back to search
        </Link>
      </main>
    );
  }

  if (!canEdit) {
    return (
      <main className="min-h-screen bg-canvas px-4 py-8 text-ink sm:px-8 sm:py-12">
        <section className="mx-auto max-w-3xl">
          <Link href="/provider" className="text-base font-semibold text-forest">← Back to community search</Link>
          <div className="mt-6 rounded-[2rem] border border-line bg-sand px-6 py-10 shadow-[0_18px_60px_-40px_rgba(29,29,31,.38)] sm:px-12 sm:py-14">
            <p className="text-sm font-semibold uppercase tracking-[.18em] text-forest">Step 2 of 3 · secure access</p>
            <h1 className="mt-5 text-4xl font-semibold leading-[1.05] tracking-[-.045em] sm:text-5xl">Confirm that you represent {snapshot.name}.</h1>
            <p className="mt-5 max-w-2xl text-xl leading-8 text-muted">We will verify a work email before anyone can update the public listing. Every change remains linked to the person who made it.</p>
            <div className="mt-8 rounded-2xl border border-line bg-white/85 p-5 text-base leading-7 text-muted oomnik-panel">
              <p className="font-semibold text-ink">What happens next</p>
              <p className="mt-2">After email verification, complete your profile section by section so families can understand which needs your community supports. Information you enter is clearly labelled as provider-supplied and does not improve organic ranking by itself.</p>
            </div>
            {snapshot.is_demo ? (
              <div className="mt-8 rounded-2xl border border-line bg-sand p-5">
                <p className="font-semibold text-forest">OPTICARE is a fictitious practice profile.</p>
                <p className="mt-2 text-base leading-7 text-muted">Email delivery is not connected yet, so use the practice workspace to review editing, saving, photographs and audit history without claiming a real community.</p>
                <button type="button" onClick={() => void enterDemoWorkspace()} className="mt-5 min-h-12 rounded-full bg-forest px-6 py-3 text-base font-semibold text-white shadow-[0_5px_14px_rgba(22,113,94,.2)] transition hover:bg-forest-hover">Open OPTICARE practice workspace</button>
              </div>
            ) : (
              <div className="mt-8 rounded-2xl border border-line bg-white p-5 text-base text-muted oomnik-panel">Email verification will be available here once the OOmnik mail service is connected.</div>
            )}
            {error ? <p className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-base text-red-800">{error}</p> : null}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href="/provider" className="text-sm text-forest underline">
        &larr; All communities
      </Link>
      <h1 className="mt-3 text-3xl font-semibold text-ink">{snapshot.name}</h1>

      <CompletenessPanel completeness={snapshot.completeness} />

      {error ? (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>
      ) : null}
      {notice ? (
        <p className="mt-6 rounded-md border border-line bg-sand px-4 py-3 text-sm text-forest">{notice}</p>
      ) : null}

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">What we already hold</h2>
        <p className="mt-1 text-sm text-muted">
          Read from public records. Tell us if any of it is wrong.
        </p>
        <dl className="mt-4 grid grid-cols-1 gap-px overflow-hidden rounded-md border border-line bg-sand sm:grid-cols-2">
          {snapshot.known_from_public_record.map((field) => (
            <div key={field.key} className="bg-white px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-muted">{field.label}</dt>
              <dd className="mt-1 text-ink">
                {field.value === null || field.value === "" ? (
                  <span className="text-muted">Not on file</span>
                ) : (
                  String(field.value)
                )}
                <span className="ml-2 text-xs text-muted">{field.source}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-12">
        <h2 className="text-lg font-semibold text-ink">
          What only you can tell us
          <span className="ml-2 text-sm font-normal text-muted">
            {snapshot.completeness.total_questions - snapshot.completeness.unanswered_count} of{" "}
            {snapshot.completeness.total_questions} answered
          </span>
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          &ldquo;Not sure&rdquo; is a real answer and costs you nothing in ranking. It just
          cannot prove that you meet a family’s request. Describe conditions, service delivery and supporting sources so we can check the specific need.
        </p>
        {snapshot.sections.some((section) => section.prefilled_from_public_record > 0) ? (
          <p className="mt-2 max-w-2xl text-sm text-muted">
            A few are already answered. We read those off your licence or your Medicare
            certification &mdash; hover to see which. Change any of them and your answer replaces
            ours permanently.
          </p>
        ) : null}

        <fieldset disabled={isSaving} className="mt-6 space-y-8">
          {snapshot.sections.map((section) => (
            <details key={section.section} className="rounded-xl border border-line p-4">
              <summary className="flex items-baseline justify-between border-b border-line pb-2">
                <h3 className="font-semibold text-ink">{section.section}</h3>
                <span className="text-xs text-muted">
                  {section.answered}/{section.total}
                  {section.prefilled_from_public_record > 0
                    ? ` · ${section.prefilled_from_public_record} from public record`
                    : ""}
                </span>
              </summary>
              <ul className="mt-2 divide-y divide-line">
                {section.questions.map((question) => {
                  const current = answerOf(question.key, question.value);
                  const isDirty = draft[question.key] !== undefined;
                  const details = detailDraft[question.key] ?? question.details ?? {};
                  const editDetail = (field: keyof QuestionnaireDetails, value: string) => {
                    setDraft((previous) => ({ ...previous, [question.key]: current }));
                    setDetailDraft((previous) => ({ ...previous, [question.key]: { ...details, [field]: value } }));
                  };
                  return (
                    <li
                      key={question.key}
                      className="flex flex-wrap items-center justify-between gap-3 py-2.5"
                    >
                      <span className="text-ink">
                        {question.label}
                        {isDirty ? <span className="ml-2 text-xs text-forest">unsaved</span> : null}
                        {!isDirty && isDerived(question) ? (
                          <span
                            className="ml-2 cursor-help text-xs text-muted underline decoration-dotted"
                            title={question.note ?? undefined}
                          >
                            from public record
                          </span>
                        ) : null}
                      </span>
                      <div className="flex gap-1" role="group" aria-label={question.label}>
                        {ANSWER_CHOICES.map((choice) => {
                          const selected = current === choice.value;
                          return (
                            <button
                              key={choice.value}
                              type="button"
                              disabled={!canEdit || isSaving}
                              aria-pressed={selected}
                              onClick={() =>
                                setDraft((previous) => ({ ...previous, [question.key]: choice.value }))
                              }
                              className={[
                                "min-h-11 rounded border px-3 py-2 text-sm font-medium transition",
                                selected
                                  ? "border-forest bg-forest text-white"
                                  : "border-line bg-white text-muted hover:border-line",
                                canEdit ? "" : "cursor-not-allowed opacity-60",
                              ].join(" ")}
                            >
                              {choice.label}
                            </button>
                          );
                        })}
                      </div>
                      <div className="w-full space-y-2">
                        {question.hint ? <p className="text-sm text-muted">{question.hint}</p> : null}
                        {question.response_kind && question.response_kind !== "state" && (current === "YES" || current === "LIMITED") ? (
                          <label className="block text-sm text-muted">
                            Value
                            <input type={question.response_kind === "number" ? "number" : question.response_kind === "date" ? "date" : "text"}
                              min={question.response_kind === "number" ? 0 : undefined}
                              step={question.response_kind === "number" ? "any" : undefined}
                              maxLength={4000}
                              value={details.value ?? ""}
                              onChange={(event) => editDetail("value", event.target.value)}
                              className="mt-1 block min-h-11 w-full rounded border border-line bg-white px-3 text-ink" />
                          </label>
                        ) : null}
                        <details className="text-sm">
                          <summary className="cursor-pointer text-forest">Conditions and supporting information{current === "LIMITED" ? " (required)" : ""}</summary>
                          <div className="mt-3 grid gap-3 sm:grid-cols-2">
                            <label className="sm:col-span-2">Conditions, limitations and relevant unit or program
                              <textarea maxLength={4000} value={details.conditions ?? ""} onChange={(event) => editDetail("conditions", event.target.value)}
                                className="mt-1 block w-full rounded border border-line bg-white p-3" />
                            </label>
                            <label>Applies to
                              <select value={details.scope ?? ""} onChange={(event) => editDetail("scope", event.target.value)} className="mt-1 block min-h-11 w-full rounded border border-line bg-white px-3">
                                <option value="">Not specified</option>
                                <option value="FACILITY">Whole community</option><option value="UNIT">Specific unit</option>
                                <option value="PROGRAM">Specific program</option><option value="SERVICE">Specific service</option>
                              </select>
                            </label>
                            <label>Service delivery
                              <select value={details.delivery ?? ""} onChange={(event) => editDetail("delivery", event.target.value)} className="mt-1 block min-h-11 w-full rounded border border-line bg-white px-3">
                                <option value="">Not specified</option><option value="ON_SITE">On site</option>
                                <option value="THIRD_PARTY">External provider</option><option value="TRANSPORT">Transport to service</option>
                                <option value="UNKNOWN">Not sure</option>
                              </select>
                            </label>
                            <label>Supporting policy or source URL
                              <input type="url" maxLength={4000} value={details.evidence_url ?? ""} onChange={(event) => editDetail("evidence_url", event.target.value)} className="mt-1 block min-h-11 w-full rounded border border-line bg-white px-3" />
                            </label>
                            <label>Date information was checked
                              <input type="date" value={details.observed_on ?? ""} onChange={(event) => editDetail("observed_on", event.target.value)} className="mt-1 block min-h-11 w-full rounded border border-line bg-white px-3" />
                            </label>
                          </div>
                          <p className="mt-2 text-xs text-muted">Recorded as information supplied by your community. Supporting information is reviewed separately.</p>
                        </details>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </details>
          ))}
        </fieldset>

        {canEdit ? (
          <div className="sticky bottom-4 mt-8 flex items-center justify-between rounded-md border border-line bg-white px-4 py-3 shadow-sm">
            <span className="text-sm text-muted">
              {pendingCount === 0
                ? "No unsaved changes"
                : `${pendingCount} unsaved ${pendingCount === 1 ? "answer" : "answers"}`}
            </span>
            <button
              type="button"
              onClick={onSave}
              disabled={pendingCount === 0 || isSaving}
              className="rounded-md bg-forest px-5 py-2 text-sm font-medium text-white hover:bg-forest-hover disabled:cursor-not-allowed disabled:bg-sand"
            >
              {isSaving ? "Saving…" : "Save answers"}
            </button>
          </div>
        ) : null}
      </section>

      <section className="mt-12">
        <h2 className="text-lg font-semibold text-ink">
          Photographs
          <span className="ml-2 text-sm font-normal text-muted">
            {snapshot.completeness.photo_count} of {snapshot.photo_target}
          </span>
        </h2>
        <p className="mt-1 text-sm text-muted">
          Yours, rather than whatever a directory site scraped some years ago.
        </p>

        {snapshot.photos.length > 0 ? (
          <ul className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {snapshot.photos.map((photo) => (
              <li key={photo.id} className="overflow-hidden rounded-md border border-line">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.url} alt={photo.caption ?? "Community photograph"} className="h-32 w-full object-cover" />
                <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                  <span className="truncate text-xs text-muted">{photo.caption ?? photo.category}</span>
                  {canEdit ? (
                    <button
                      type="button"
                      onClick={() => void onRemovePhoto(photo.id)}
                      className="text-xs text-red-700 underline"
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 rounded-md border border-dashed border-line px-4 py-6 text-center text-sm text-muted">
            No photographs yet.
          </p>
        )}

        {canEdit ? (
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={photoUrl}
              onChange={(event) => setPhotoUrl(event.target.value)}
              placeholder="https://…/photo.jpg"
              aria-label="Photograph URL"
              className="flex-1 rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-forest"
            />
            <input
              value={photoCaption}
              onChange={(event) => setPhotoCaption(event.target.value)}
              placeholder="Caption (optional)"
              aria-label="Photograph caption"
              className="rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-forest"
            />
            <button
              type="button"
              onClick={() => void onAddPhoto()}
              disabled={!photoUrl.trim()}
              className="rounded-md border border-line px-4 py-2 text-sm font-medium text-muted hover:border-line disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add
            </button>
          </div>
        ) : null}
      </section>

      <section className="mt-12 rounded-md border border-line bg-white p-6">
        <h2 className="text-lg font-semibold text-ink">Activity calendar</h2>
        {snapshot.activity_calendar_connected ? (
          <p className="mt-2 text-sm text-forest">
            Connected. We are reading your published schedule and keeping the categories below
            current.
          </p>
        ) : (
          <p className="mt-2 max-w-2xl text-sm text-muted">
            A daughter looking for her mother does not ask for &ldquo;assisted living&rdquo;.
            She asks whether there is a garden, whether services are held on Saturday, whether
            anyone still plays bridge. Connect the weekly or monthly schedule you already
            publish and we learn what actually runs here, rather than guessing from a brochure.
          </p>
        )}

        {snapshot.activities.length > 0 ? (
          <ul className="mt-4 flex flex-wrap gap-2">
            {snapshot.activities.map((activity) => (
              <li
                key={activity.category}
                className={[
                  "rounded border px-2.5 py-1 text-xs",
                  activity.availability === "UNKNOWN"
                    ? "border-line bg-canvas text-muted"
                    : "border-line bg-sand text-forest",
                ].join(" ")}
              >
                {activity.category}
                {activity.availability === "UNKNOWN" ? " · not sure" : ""}
              </li>
            ))}
          </ul>
        ) : null}

        <p className="mt-4 text-xs text-muted">
          Calendar connection is handled by the activities import endpoint; ask us and we will
          set it up against whichever calendar you publish.
        </p>
      </section>
    </main>
  );
}

function CompletenessPanel({ completeness }: { completeness: Completeness }) {
  const buckets = useMemo(
    () => [
      { label: "Medical", value: completeness.medical },
      { label: "Lifestyle", value: completeness.lifestyle },
      { label: "Dining", value: completeness.dining },
      { label: "Photos", value: completeness.photos },
      { label: "Activities", value: completeness.activity },
    ],
    [completeness],
  );

  return (
    <div className="mt-6 rounded-md border border-line bg-white p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-ink">Profile completeness</h2>
        <span className="text-2xl font-semibold tabular-nums text-forest">
          {formatPercent(completeness.overall)}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {buckets.map((bucket) => (
          <div key={bucket.label}>
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-muted">{bucket.label}</span>
              <span className="text-xs tabular-nums text-muted">{formatPercent(bucket.value)}</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-sand">
              <div
                className="h-full rounded-full bg-forest"
                style={{ width: `${Math.round(bucket.value * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {completeness.unanswered_count > 0 ? (
        <p className="mt-4 text-sm text-muted">
          {completeness.unanswered_count} of {completeness.total_questions} questions are still
          unanswered. Each one is a family conversation you are not currently part of.
        </p>
      ) : (
        <p className="mt-4 text-sm text-forest">Every question answered.</p>
      )}
    </div>
  );
}
