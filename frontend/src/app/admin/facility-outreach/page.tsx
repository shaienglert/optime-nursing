"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FacilityOutreachRequest, approveAndSendFacilityOutreach, fetchFacilityOutreachAwaitingApproval } from "@/lib/api";

const ADMIN_TOKEN_SESSION_KEY = "optime.admin.token";

export default function FacilityOutreachAdminPage() {
  const [adminToken, setAdminToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [requests, setRequests] = useState<FacilityOutreachRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sendingId, setSendingId] = useState<number | null>(null);

  useEffect(() => {
    // Deferred via a resolved promise (matching this codebase's convention of never
    // calling setState synchronously in an effect body) rather than a lazy useState
    // initializer, which would read sessionStorage during the server render pass and
    // risk a hydration mismatch between server and client.
    Promise.resolve().then(() => {
      try {
        const saved = window.sessionStorage.getItem(ADMIN_TOKEN_SESSION_KEY);
        if (saved) {
          setAdminToken(saved);
          setTokenInput(saved);
        }
      } catch {
        // sessionStorage unavailable -- the token input still works, it just won't persist.
      }
    });
  }, []);

  useEffect(() => {
    if (!adminToken) return;
    let active = true;
    fetchFacilityOutreachAwaitingApproval(adminToken)
      .then((rows) => {
        if (active) {
          setRequests(rows);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load outreach requests. Check your admin token.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [adminToken]);

  function handleUnlock() {
    const trimmed = tokenInput.trim();
    if (!trimmed) return;
    try {
      window.sessionStorage.setItem(ADMIN_TOKEN_SESSION_KEY, trimmed);
    } catch {
      // sessionStorage unavailable -- proceed with the in-memory token anyway.
    }
    setLoading(true);
    setAdminToken(trimmed);
  }

  async function handleApprove(requestId: number) {
    setSendingId(requestId);
    try {
      await approveAndSendFacilityOutreach(requestId, adminToken);
      setRequests((prev) => prev.filter((r) => r.id !== requestId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send.");
    } finally {
      setSendingId(null);
    }
  }

  if (!adminToken) {
    return (
      <main className="min-h-screen bg-canvas px-6 py-8 text-ink sm:px-10 lg:px-16">
        <section className="mx-auto max-w-md space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-forest">Admin · Facility Outreach</p>
          <h1 className="text-2xl font-semibold">Admin token required</h1>
          <p className="text-sm text-muted">This page reviews and sends real emails to facilities -- it requires the admin token.</p>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleUnlock()}
            placeholder="Admin token"
            className="w-full rounded-xl border border-line bg-surface px-4 py-2.5 text-ink"
          />
          <button
            type="button"
            onClick={handleUnlock}
            className="w-full rounded-xl bg-forest px-4 py-2.5 text-sm font-semibold text-white hover:bg-forest-hover"
          >
            Unlock
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-canvas px-6 py-8 text-ink sm:px-10 lg:px-16">
      <section className="mx-auto max-w-4xl space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-forest">Admin · Facility Outreach</p>
            <h1 className="mt-2 text-3xl font-semibold">Requests Awaiting Approval</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted">
              Each draft below was auto-composed after a client asked us to follow up with a facility. Review the recipient and
              wording, then approve to actually send -- nothing goes out automatically.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/partner-desk" className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover">
              Open Sales Copilot
            </Link>
            <Link href="/admin" className="rounded-full border border-line px-4 py-2 text-sm text-muted hover:border-line">
              Back to Admin
            </Link>
          </div>
        </header>

        {loading ? <p className="text-sm text-muted">Loading…</p> : null}
        {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p> : null}
        {!loading && requests.length === 0 && !error ? (
          <p className="rounded-2xl border border-line bg-surface/60 p-6 text-sm text-muted">
            Nothing is currently awaiting approval.
          </p>
        ) : null}

        <div className="space-y-4">
          {requests.map((request) => (
            <article key={request.id} className="rounded-3xl border border-line bg-surface/80 p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{request.facility_name}</h2>
                  <p className="mt-1 text-sm text-muted">To: {request.draft?.to || request.contact_email}</p>
                  <p className="text-xs text-muted">Canonical ID: {request.canonical_facility_id}</p>
                </div>
                <button
                  type="button"
                  disabled={sendingId === request.id}
                  onClick={() => void handleApprove(request.id)}
                  className="rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest-hover disabled:opacity-60"
                >
                  {sendingId === request.id ? "Sending…" : "Approve & Send"}
                </button>
              </div>
              {request.draft ? (
                <div className="mt-4 rounded-2xl border border-line bg-surface/60 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-muted">Subject</p>
                  <p className="mt-1 text-sm text-ink">{request.draft.subject}</p>
                  <p className="mt-3 text-xs uppercase tracking-[0.14em] text-muted">Body</p>
                  <pre className="mt-1 whitespace-pre-wrap font-sans text-sm text-muted">{request.draft.body_text}</pre>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
