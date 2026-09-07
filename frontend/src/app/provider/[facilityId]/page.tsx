"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import {
  AnswerState,
  Completeness,
  ProfileSnapshot,
  addFacilityPhoto,
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
      const result = await saveCapabilities(facilityId, userId, draft);
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

  if (isLoading) {
    return <main className="mx-auto max-w-4xl px-6 py-14 text-slate-500">Loading profile&hellip;</main>;
  }

  if (!snapshot) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-14">
        <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          {error ?? "Profile not found."}
        </p>
        <Link href="/provider" className="mt-4 inline-block text-teal-700 underline">
          Back to search
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href="/provider" className="text-sm text-teal-700 underline">
        &larr; All communities
      </Link>
      <h1 className="mt-3 text-3xl font-semibold text-slate-900">{snapshot.name}</h1>

      <CompletenessPanel completeness={snapshot.completeness} />

      {!canEdit ? (
        <p className="mt-6 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          You are viewing this profile read-only. Verify your work email against this
          community to make changes &mdash; every edit is recorded against the person who made
          it, which is what lets us tell your answers apart from a government file.
        </p>
      ) : null}

      {error ? (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>
      ) : null}
      {notice ? (
        <p className="mt-6 rounded-md border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900">{notice}</p>
      ) : null}

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">What we already hold</h2>
        <p className="mt-1 text-sm text-slate-600">
          Read from public records. Tell us if any of it is wrong.
        </p>
        <dl className="mt-4 grid grid-cols-1 gap-px overflow-hidden rounded-md border border-slate-200 bg-slate-200 sm:grid-cols-2">
          {snapshot.known_from_public_record.map((field) => (
            <div key={field.key} className="bg-white px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">{field.label}</dt>
              <dd className="mt-1 text-slate-900">
                {field.value === null || field.value === "" ? (
                  <span className="text-slate-400">Not on file</span>
                ) : (
                  String(field.value)
                )}
                <span className="ml-2 text-xs text-slate-400">{field.source}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-12">
        <h2 className="text-lg font-semibold text-slate-900">
          What only you can tell us
          <span className="ml-2 text-sm font-normal text-slate-500">
            {snapshot.completeness.total_questions - snapshot.completeness.unanswered_count} of{" "}
            {snapshot.completeness.total_questions} answered
          </span>
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          &ldquo;Not sure&rdquo; is a real answer and costs you nothing in ranking. It just
          cannot match a family who asked for that thing.
        </p>
        {snapshot.sections.some((section) => section.prefilled_from_public_record > 0) ? (
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            A few are already answered. We read those off your licence or your Medicare
            certification &mdash; hover to see which. Change any of them and your answer replaces
            ours permanently.
          </p>
        ) : null}

        <div className="mt-6 space-y-8">
          {snapshot.sections.map((section) => (
            <div key={section.section}>
              <div className="flex items-baseline justify-between border-b border-slate-200 pb-2">
                <h3 className="font-semibold text-slate-900">{section.section}</h3>
                <span className="text-xs text-slate-500">
                  {section.answered}/{section.total}
                  {section.prefilled_from_public_record > 0
                    ? ` · ${section.prefilled_from_public_record} from public record`
                    : ""}
                </span>
              </div>
              <ul className="mt-2 divide-y divide-slate-100">
                {section.questions.map((question) => {
                  const current = answerOf(question.key, question.value);
                  const isDirty = draft[question.key] !== undefined;
                  return (
                    <li
                      key={question.key}
                      className="flex flex-wrap items-center justify-between gap-3 py-2.5"
                    >
                      <span className="text-slate-800">
                        {question.label}
                        {isDirty ? <span className="ml-2 text-xs text-teal-700">unsaved</span> : null}
                        {!isDirty && isDerived(question) ? (
                          <span
                            className="ml-2 cursor-help text-xs text-slate-500 underline decoration-dotted"
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
                              disabled={!canEdit}
                              aria-pressed={selected}
                              onClick={() =>
                                setDraft((previous) => ({ ...previous, [question.key]: choice.value }))
                              }
                              className={[
                                "rounded border px-2.5 py-1 text-xs font-medium transition",
                                selected
                                  ? "border-teal-700 bg-teal-700 text-white"
                                  : "border-slate-300 bg-white text-slate-600 hover:border-slate-400",
                                canEdit ? "" : "cursor-not-allowed opacity-60",
                              ].join(" ")}
                            >
                              {choice.label}
                            </button>
                          );
                        })}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {canEdit ? (
          <div className="sticky bottom-4 mt-8 flex items-center justify-between rounded-md border border-slate-300 bg-white px-4 py-3 shadow-sm">
            <span className="text-sm text-slate-600">
              {pendingCount === 0
                ? "No unsaved changes"
                : `${pendingCount} unsaved ${pendingCount === 1 ? "answer" : "answers"}`}
            </span>
            <button
              type="button"
              onClick={onSave}
              disabled={pendingCount === 0 || isSaving}
              className="rounded-md bg-teal-700 px-5 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isSaving ? "Saving…" : "Save answers"}
            </button>
          </div>
        ) : null}
      </section>

      <section className="mt-12">
        <h2 className="text-lg font-semibold text-slate-900">
          Photographs
          <span className="ml-2 text-sm font-normal text-slate-500">
            {snapshot.completeness.photo_count} of {snapshot.photo_target}
          </span>
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Yours, rather than whatever a directory site scraped some years ago.
        </p>

        {snapshot.photos.length > 0 ? (
          <ul className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {snapshot.photos.map((photo) => (
              <li key={photo.id} className="overflow-hidden rounded-md border border-slate-200">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.url} alt={photo.caption ?? "Community photograph"} className="h-32 w-full object-cover" />
                <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                  <span className="truncate text-xs text-slate-600">{photo.caption ?? photo.category}</span>
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
          <p className="mt-4 rounded-md border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500">
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
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
            />
            <input
              value={photoCaption}
              onChange={(event) => setPhotoCaption(event.target.value)}
              placeholder="Caption (optional)"
              aria-label="Photograph caption"
              className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-600"
            />
            <button
              type="button"
              onClick={() => void onAddPhoto()}
              disabled={!photoUrl.trim()}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Add
            </button>
          </div>
        ) : null}
      </section>

      <section className="mt-12 rounded-md border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Activity calendar</h2>
        {snapshot.activity_calendar_connected ? (
          <p className="mt-2 text-sm text-teal-800">
            Connected. We are reading your published schedule and keeping the categories below
            current.
          </p>
        ) : (
          <p className="mt-2 max-w-2xl text-sm text-slate-700">
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
                    ? "border-slate-200 bg-slate-50 text-slate-500"
                    : "border-teal-200 bg-teal-50 text-teal-900",
                ].join(" ")}
              >
                {activity.category}
                {activity.availability === "UNKNOWN" ? " · not sure" : ""}
              </li>
            ))}
          </ul>
        ) : null}

        <p className="mt-4 text-xs text-slate-500">
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
    <div className="mt-6 rounded-md border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-slate-900">Profile completeness</h2>
        <span className="text-2xl font-semibold tabular-nums text-teal-700">
          {formatPercent(completeness.overall)}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {buckets.map((bucket) => (
          <div key={bucket.label}>
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-slate-600">{bucket.label}</span>
              <span className="text-xs tabular-nums text-slate-500">{formatPercent(bucket.value)}</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-teal-600"
                style={{ width: `${Math.round(bucket.value * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {completeness.unanswered_count > 0 ? (
        <p className="mt-4 text-sm text-slate-600">
          {completeness.unanswered_count} of {completeness.total_questions} questions are still
          unanswered. Each one is a family conversation you are not currently part of.
        </p>
      ) : (
        <p className="mt-4 text-sm text-teal-800">Every question answered.</p>
      )}
    </div>
  );
}
