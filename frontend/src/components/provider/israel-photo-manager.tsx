"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchProfileSnapshot,
  photoSrc,
  removeFacilityPhoto,
  uploadFacilityPhoto,
  type ProfilePhoto,
} from "@/lib/provider-api";
import { shrinkImage } from "@/lib/shrink-image";

/** Hebrew photo upload for an Israeli facility's own page. Photos never affect matching. */
export function IsraelPhotoManager({ facilityId, userId }: { facilityId: number; userId: number | null }) {
  const [photos, setPhotos] = useState<ProfilePhoto[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    try {
      const snapshot = await fetchProfileSnapshot(facilityId);
      setPhotos(snapshot.photos);
    } catch {
      setError("לא ניתן לטעון את התמונות כרגע.");
    }
  }, [facilityId]);

  useEffect(() => {
    let cancelled = false;
    fetchProfileSnapshot(facilityId)
      .then((snapshot) => {
        if (!cancelled) setPhotos(snapshot.photos);
      })
      .catch(() => {
        if (!cancelled) setError("לא ניתן לטעון את התמונות כרגע.");
      });
    return () => {
      cancelled = true;
    };
  }, [facilityId]);

  async function onFiles(files: FileList | null) {
    if (!files?.length || !userId) return;
    setBusy(true);
    setError(null);
    const list = Array.from(files);
    let failed = 0;
    for (const [index, file] of list.entries()) {
      setProgress(`מעלה ${index + 1} מתוך ${list.length}…`);
      try {
        await uploadFacilityPhoto(facilityId, userId, await shrinkImage(file));
      } catch (uploadError) {
        failed += 1;
        setError(`${file.name}: ${uploadError instanceof Error ? uploadError.message : "ההעלאה נכשלה."}`);
      }
    }
    setProgress(failed ? null : `הועלו ${list.length} תמונות.`);
    if (input.current) input.current.value = "";
    await reload();
    setBusy(false);
  }

  async function remove(photoId: number) {
    if (!userId) return;
    try {
      await removeFacilityPhoto(facilityId, userId, photoId);
      await reload();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "המחיקה נכשלה.");
    }
  }

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold">תמונות המוסד</h2>
      <p className="mt-1 text-sm">התמונות יוצגו בדף הבית של המוסד. אפשר לבחור כמה תמונות בבת אחת, גם ישר מהמצלמה בטלפון.</p>

      <label className="mt-3 inline-flex cursor-pointer items-center rounded-xl border px-4 py-2 font-medium">
        {busy ? "מעלה…" : "בחירת תמונות"}
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          disabled={!userId || busy}
          className="sr-only"
          onChange={(event) => void onFiles(event.target.files)}
        />
      </label>
      {progress ? <p role="status" className="mt-2 text-sm">{progress}</p> : null}
      {error ? <p role="alert" className="mt-2 text-sm">{error}</p> : null}

      {photos.length ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {photos.map((photo) => (
            <figure key={photo.id} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photoSrc(photo.url)} alt={photo.caption ?? "תמונת המוסד"} className="aspect-[4/3] w-full rounded-xl object-cover" />
              <button
                type="button"
                onClick={() => void remove(photo.id)}
                disabled={!userId}
                className="absolute left-2 top-2 rounded-lg bg-white/90 px-2 py-1 text-xs text-black"
              >
                הסרה
              </button>
            </figure>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm">עוד לא הועלו תמונות.</p>
      )}
    </section>
  );
}
