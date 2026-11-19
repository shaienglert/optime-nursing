"use client";

import Image from "next/image";
import { useSyncExternalStore } from "react";

const PHOTOS = Array.from({ length: 5 }, (_, index) => `/pilot/photos/album-${index + 1}.webp`);
const ISRAEL_PHOTOS = Array.from({ length: 7 }, (_, index) => `/pilot/israel/photo-${index + 1}.webp`);
const ISRAEL_ROOM_PHOTOS = Array.from({ length: 9 }, (_, index) => `/pilot/israel/room-${index + 1}.webp`);
const ISRAEL_OUTDOOR_PHOTOS = Array.from({ length: 3 }, (_, index) => `/pilot/israel/outdoor-${index + 1}.webp`);
const assignedPhotos = new Map<string, number>();
const STORAGE_KEY = "oomnik.pilot-photo-assignments.v1";
const subscribe = () => () => {};
const serverSnapshot = () => null;

function assignedPhoto(facilityId: string): number {
  const cached = assignedPhotos.get(facilityId);
  if (cached !== undefined) return cached;
  let saved: Record<string, number> = {};
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) saved = parsed as Record<string, number>;
  } catch { /* In-memory assignment still keeps this page stable. */ }
  const previous = Object.hasOwn(saved, facilityId) ? saved[facilityId] : undefined;
  const index = typeof previous === "number" && Number.isInteger(previous) && previous >= 0 && previous < PHOTOS.length
    ? previous : Math.floor(Math.random() * PHOTOS.length);
  assignedPhotos.set(facilityId, index);
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ ...saved, [facilityId]: index })); } catch { /* Storage may be disabled. */ }
  return index;
}

export function PilotPhoto({ facilityId, gallery = false, locale = "en", rooms = false }: { facilityId: string; gallery?: boolean; locale?: "en" | "he"; rooms?: boolean }) {
  const isIsrael = locale === "he";
  const album = isIsrael ? (rooms ? ISRAEL_ROOM_PHOTOS : ISRAEL_PHOTOS) : PHOTOS;
  const assignedIndex = useSyncExternalStore(
    subscribe,
    () => isIsrael ? null : assignedPhoto(facilityId),
    serverSnapshot,
  );
  // Israeli pilot IDs end in a sequence number shared by results and facility pages.
  const sequence = Number(facilityId.match(/\d+$/)?.[0] ?? 0);
  const index = isIsrael ? sequence % album.length : assignedIndex;
  if (index === null) return null;
  const photos = gallery ? [0, 1, 2].map(offset => album[(index + offset) % album.length]) : [album[index]];
  if (gallery && isIsrael && !rooms) {
    photos[2] = ISRAEL_OUTDOOR_PHOTOS[sequence % ISRAEL_OUTDOOR_PHOTOS.length];
  }
  const caption = locale === "he"
    ? "תמונת המחשה לפיילוט"
    : "Pilot illustration: randomly selected from the owner-provided photo album. These are not photographs of this community or its rooms.";
  return (
    <figure data-testid="pilot-photo" className="mb-6 overflow-hidden rounded-xl border border-line bg-sand">
      <div className={gallery ? "grid gap-2 sm:grid-cols-3" : ""}>
        {photos.map((src, position) => <Image key={src} src={src} alt={locale === "he" ? "" : "Illustrative city and landscape photograph for the pilot — not this community"} width={1400} height={1000} sizes={gallery ? "(max-width: 640px) 100vw, 33vw" : "(max-width: 768px) 100vw, 850px"} className="h-64 w-full object-cover" loading={position === 0 && locale === "en" ? "eager" : "lazy"} />)}
      </div>
      <figcaption className="px-4 py-3 text-base leading-6 text-muted">{caption}</figcaption>
    </figure>
  );
}
