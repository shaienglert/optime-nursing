"use client";

import { useEffect, useState } from "react";

import {
  FacilityOutreachPublicStatus,
  RoomSubmission,
  fetchFacilityOutreachPublicStatus,
  submitFacilityOutreachResponse,
} from "@/lib/api";

type DraftRoom = {
  room_type_name: string;
  description: string;
  monthly_price: string;
  availability_status: RoomSubmission["availability_status"];
  photo_urls: string;
};

function emptyRoom(): DraftRoom {
  return { room_type_name: "", description: "", monthly_price: "", availability_status: "AVAILABLE", photo_urls: "" };
}

export function FacilityOutreachResponseClient({ responseToken }: { responseToken: string }) {
  const [status, setStatus] = useState<FacilityOutreachPublicStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [rooms, setRooms] = useState<DraftRoom[]>([emptyRoom()]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchFacilityOutreachPublicStatus(responseToken)
      .then((value) => {
        if (active) setStatus(value);
      })
      .catch(() => {
        if (active) setNotFound(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [responseToken]);

  function updateRoom(index: number, patch: Partial<DraftRoom>) {
    setRooms((prev) => prev.map((room, i) => (i === index ? { ...room, ...patch } : room)));
  }

  async function handleSubmit() {
    setSubmitError(null);
    const validRooms = rooms.filter((r) => r.room_type_name.trim());
    if (validRooms.length === 0) {
      setSubmitError("Add at least one room type before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      const payload: RoomSubmission[] = validRooms.map((r) => ({
        room_type_name: r.room_type_name.trim(),
        description: r.description.trim(),
        monthly_price_cents: r.monthly_price.trim() ? Math.round(parseFloat(r.monthly_price) * 100) : null,
        availability_status: r.availability_status,
        photo_urls: r.photo_urls.split(",").map((u) => u.trim()).filter(Boolean),
      }));
      await submitFacilityOutreachResponse(responseToken, payload);
      setSubmitted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Something went wrong submitting this. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]"><div className="mx-auto max-w-2xl text-lg">Loading…</div></main>;
  }

  if (notFound) {
    return (
      <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]">
        <div className="mx-auto max-w-2xl rounded-3xl border border-rose-200 bg-white p-8 text-lg">
          This link isn&apos;t valid or has expired. Please contact OPTIME directly if you believe this is an error.
        </div>
      </main>
    );
  }

  if (submitted) {
    return (
      <main className="min-h-screen bg-[#fffaf2] px-5 py-12 text-[#22332d]">
        <div className="mx-auto max-w-2xl rounded-3xl border border-[#ded6c9] bg-white p-8">
          <h1 className="text-2xl font-semibold">Thank you</h1>
          <p className="mt-3 text-lg text-[#53635d]">
            We&apos;ve received your room, pricing, and availability details for {status?.facility_name}. This will be shared
            with the family who asked us to follow up.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#fffaf2] px-5 py-8 text-[#22332d] sm:px-8 lg:px-12">
      <div className="mx-auto max-w-3xl">
        <section className="rounded-[2rem] border border-[#e1d8c9] bg-white p-7 shadow-sm sm:p-9">
          <p className="text-base font-semibold uppercase tracking-[0.14em] text-[#437667]">OPTIME · Facility response</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight">Room details for {status?.facility_name}</h1>
          <p className="mt-4 text-lg leading-7 text-[#53635d]">
            A family currently considering your community asked OPTIME to check on your current room types, pricing, and
            availability. Add as many room types as apply below -- no account needed.
          </p>
          {status?.status === "RESPONDED" ? (
            <p className="mt-4 rounded-2xl bg-[#eef7f2] p-4 text-base text-[#214d40]">
              You&apos;ve submitted details for this request before. Submitting again will update what we have on file.
            </p>
          ) : null}
        </section>

        <section className="mt-6 space-y-5">
          {rooms.map((room, index) => (
            <div key={index} className="rounded-3xl border border-[#ded6c9] bg-white p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Room type {index + 1}</h2>
                {rooms.length > 1 ? (
                  <button
                    type="button"
                    onClick={() => setRooms((prev) => prev.filter((_, i) => i !== index))}
                    className="text-sm font-medium text-[#8b3d2e] hover:underline"
                  >
                    Remove
                  </button>
                ) : null}
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-medium text-[#53635d]">
                  Room type name
                  <input
                    type="text"
                    value={room.room_type_name}
                    onChange={(e) => updateRoom(index, { room_type_name: e.target.value })}
                    placeholder="e.g. Private Suite"
                    className="mt-1 w-full rounded-xl border border-[#d9cfbf] px-3 py-2 text-base text-[#22332d]"
                  />
                </label>
                <label className="block text-sm font-medium text-[#53635d]">
                  Monthly price ($)
                  <input
                    type="number"
                    value={room.monthly_price}
                    onChange={(e) => updateRoom(index, { monthly_price: e.target.value })}
                    placeholder="e.g. 5200"
                    className="mt-1 w-full rounded-xl border border-[#d9cfbf] px-3 py-2 text-base text-[#22332d]"
                  />
                </label>
                <label className="block text-sm font-medium text-[#53635d] sm:col-span-2">
                  Description
                  <textarea
                    value={room.description}
                    onChange={(e) => updateRoom(index, { description: e.target.value })}
                    rows={2}
                    className="mt-1 w-full rounded-xl border border-[#d9cfbf] px-3 py-2 text-base text-[#22332d]"
                  />
                </label>
                <label className="block text-sm font-medium text-[#53635d]">
                  Availability
                  <select
                    value={room.availability_status}
                    onChange={(e) => updateRoom(index, { availability_status: e.target.value as DraftRoom["availability_status"] })}
                    className="mt-1 w-full rounded-xl border border-[#d9cfbf] px-3 py-2 text-base text-[#22332d]"
                  >
                    <option value="AVAILABLE">Available now</option>
                    <option value="WAITLIST">Waitlist</option>
                    <option value="UNAVAILABLE">Not available</option>
                  </select>
                </label>
                <label className="block text-sm font-medium text-[#53635d]">
                  Photo URLs (comma-separated, optional)
                  <input
                    type="text"
                    value={room.photo_urls}
                    onChange={(e) => updateRoom(index, { photo_urls: e.target.value })}
                    placeholder="https://..."
                    className="mt-1 w-full rounded-xl border border-[#d9cfbf] px-3 py-2 text-base text-[#22332d]"
                  />
                </label>
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={() => setRooms((prev) => [...prev, emptyRoom()])}
            className="rounded-full border-2 border-[#315f53] px-5 py-2.5 text-base font-semibold text-[#315f53]"
          >
            + Add another room type
          </button>

          {submitError ? <p className="text-base font-medium text-[#8b3d2e]">{submitError}</p> : null}

          <div>
            <button
              type="button"
              disabled={submitting}
              onClick={() => void handleSubmit()}
              className="rounded-2xl bg-[#2F5D46] px-6 py-3.5 text-lg font-semibold text-white hover:bg-[#254a38] disabled:opacity-60"
            >
              {submitting ? "Submitting…" : "Submit details"}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
