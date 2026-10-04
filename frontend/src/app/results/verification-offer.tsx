"use client";

import { FormEvent, useState } from "react";

export function VerificationOffer() {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim()) return;

    // This UI intentionally does not claim that outreach has been sent until the
    // governed Top-10 outreach backend is connected. Keep the address in-session
    // only; do not persist PII in localStorage or analytics.
    setSubmitted(true);
  };

  return (
    <section className="rounded-3xl border border-line bg-sand p-6 shadow-[0_16px_50px_-34px_rgba(69,58,43,0.25)]">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-forest">Before you review your top recommendations</p>
      <h2 className="mt-2 text-xl font-semibold text-ink">Would you like OPTIME to verify the missing details for you?</h2>
      <p className="mt-3 max-w-4xl text-sm leading-6 text-muted">
        These recommendations are based on the information you provided and the information currently available in the OPTIME system. Some details that may affect your personal match are still awaiting confirmation.
      </p>
      <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">
        We can contact the relevant communities to verify the missing information and return to you within 24 hours with an updated comparison. Newly verified information may change the order of the recommendations.
      </p>
      <p className="mt-2 max-w-4xl text-xs leading-5 text-muted">
        In the background, OPTIME will verify the full set of case-relevant known and unknown details across the Top 10 candidates. Communities are not told their ranking. Commercial offers may be shown to you, but do not improve organic ranking by themselves.
      </p>

      {!isOpen ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="mt-5 rounded-full bg-forest px-6 py-3 text-sm font-semibold text-white transition hover:bg-forest-hover"
        >
          SEND
        </button>
      ) : (
        <div className="mt-5 rounded-2xl border border-line bg-white p-5 oomnik-panel">
          {!submitted ? (
            <form onSubmit={submit} className="max-w-xl">
              <label htmlFor="verification-email" className="text-sm font-semibold text-ink">
                Where should we send your updated results?
              </label>
              <p className="mt-1 text-xs text-muted">Enter the email address where you want to receive the 24-hour verification update.</p>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                <input
                  id="verification-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="min-w-0 flex-1 rounded-full border border-line px-4 py-3 text-sm text-ink outline-none focus:border-forest"
                />
                <button type="submit" className="rounded-full bg-forest px-6 py-3 text-sm font-semibold text-white hover:bg-forest-hover">
                  Confirm
                </button>
              </div>
              <p className="mt-3 text-xs text-[#8a6330]">
                The outreach workflow is being connected. Your request will not be represented as sent until the Top-10 verification backend confirms dispatch.
              </p>
            </form>
          ) : (
            <div>
              <p className="font-semibold text-ink">Email captured for this verification request.</p>
              <p className="mt-2 text-sm text-muted">
                OPTIME will only mark the request as sent after the governed Top-10 outreach workflow confirms dispatch. No ranking changes occur from this request itself.
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
