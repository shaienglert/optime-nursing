"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ClaimSearchResult, ensureOpticareDemo, searchClaimableFacilities } from "@/lib/provider-api";

/**
 * Step one of the provider portal: find your own community.
 *
 * The outreach letter tells an operator their community is already listed, so this page has
 * one job -- let them recognise it. Everything shown here is public record, which is why it
 * needs no sign-in; proving the claim happens after they pick the right row.
 */
export default function ProviderLandingPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState("NV");
  const [results, setResults] = useState<ClaimSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isPreparingDemo, setIsPreparingDemo] = useState(false);

  const runSearch = useCallback(async (term: string, stateFilter: string) => {
    if (term.trim().length < 2) {
      setResults([]);
      setHasSearched(false);
      return;
    }
    setIsSearching(true);
    setError(null);
    try {
      const found = await searchClaimableFacilities(term, { state: stateFilter || undefined });
      setResults(found);
      setHasSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search is unavailable right now.");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const prepareOpticare = async () => {
    setIsPreparingDemo(true);
    setError(null);
    try {
      await ensureOpticareDemo();
      setState("NV");
      setQuery("OPTICARE");
      await runSearch("OPTICARE", "NV");
    } catch (err) {
      setError(err instanceof Error ? err.message : "The demonstration profile could not be prepared.");
    } finally {
      setIsPreparingDemo(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      void runSearch(query, state);
    }, 250);
    return () => clearTimeout(timer);
  }, [query, state, runSearch]);

  return (
    <main className="min-h-screen bg-[#f5f5f7] px-4 py-8 text-[#1d1d1f] sm:px-8 sm:py-12">
      <section className="mx-auto max-w-5xl">
        <div className="rounded-[2rem] border border-[#e5e5ea] bg-[radial-gradient(circle_at_92%_4%,#e3f1eb_0,transparent_31%),linear-gradient(135deg,#ffffff_0%,#fbfbfc_100%)] px-6 py-10 shadow-[0_18px_60px_-40px_rgba(29,29,31,.38)] sm:px-12 sm:py-14">
          <p className="text-sm font-semibold uppercase tracking-[.18em] text-[#26715d]">Oomnik for communities</p>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-.045em] text-[#1d1d1f] sm:text-6xl">Make sure families see the full picture.</h1>
          <p className="mt-6 max-w-2xl text-xl leading-8 text-[#4b4b4f]">Find your community, confirm your work email, and update the information only your team can provide.</p>
          <div className="mt-8 grid gap-3 text-base text-[#3d4b46] sm:grid-cols-3">
            <p className="rounded-2xl bg-white/80 px-4 py-4"><span className="font-semibold text-[#1d1d1f]">1.</span> Find your listing</p>
            <p className="rounded-2xl bg-white/80 px-4 py-4"><span className="font-semibold text-[#1d1d1f]">2.</span> Verify your work email</p>
            <p className="rounded-2xl bg-white/80 px-4 py-4"><span className="font-semibold text-[#1d1d1f]">3.</span> A short questionnaire places your community correctly</p>
          </div>
          <button
            type="button"
            onClick={() => void prepareOpticare()}
            disabled={isPreparingDemo}
            className="mt-6 min-h-12 rounded-full border border-[#26715d] bg-white px-5 py-3 text-base font-semibold text-[#17624f] transition hover:bg-[#edf8f3] disabled:opacity-60"
          >
            {isPreparingDemo ? "Preparing OPTICARE…" : "Try the OPTICARE demonstration profile"}
          </button>
          <p className="mt-2 text-sm text-[#52645d]">Fictitious data for portal review only — never used in family results.</p>
        </div>

      <div className="mt-8 rounded-[1.75rem] border border-[#e5e5ea] bg-white p-5 shadow-[0_12px_36px_-30px_rgba(29,29,31,.4)] sm:p-7">
        <label htmlFor="community-search" className="text-xl font-semibold tracking-[-.02em]">Find your community</label>
        <p className="mt-2 text-base text-[#4b4b4f]">Use the name shown on your license or public listing.</p>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          id="community-search"
          placeholder="Start typing your community name"
          aria-label="Community name"
          className="min-h-14 flex-1 rounded-2xl border border-[#c9d4cf] px-5 text-lg text-[#1d1d1f] outline-none focus:border-[#26715d] focus:ring-4 focus:ring-[#def0e8]"
        />
        <select
          value={state}
          onChange={(event) => setState(event.target.value)}
          aria-label="State"
          className="min-h-14 rounded-2xl border border-[#c9d4cf] px-5 text-lg text-[#1d1d1f] outline-none focus:border-[#26715d] focus:ring-4 focus:ring-[#def0e8]"
        >
          <option value="">All states</option>
          <option value="NV">Nevada</option>
          <option value="FL">Florida</option>
        </select>
        </div>
      </div>

      {error ? (
        <p className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-base text-red-800">
          {error}
        </p>
      ) : null}

      {isSearching ? <p className="mt-6 text-base text-[#52645d]">Searching communities&hellip;</p> : null}

      {!isSearching && hasSearched && results.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-[#e5e5ea] bg-white px-5 py-5 text-base text-[#4b4b4f]">
          <p className="font-medium text-slate-900">No match under that name.</p>
          <p className="mt-1">
            Communities are listed under the name on their CMS certification, which is not
            always the name on the sign. Try a shorter fragment, or reply to our email and we
            will find it for you.
          </p>
        </div>
      ) : null}

      {results.length > 0 ? (
        <ul className="mt-6 space-y-4">
          {results.map((facility) => (
            <li key={facility.facility_id} className="flex flex-wrap items-center gap-5 rounded-[1.5rem] border border-[#e5e5ea] bg-white px-5 py-5 shadow-[0_10px_30px_-26px_rgba(29,29,31,.45)] sm:px-6">
              <div className="min-w-0 flex-1">
                <p className="text-xl font-semibold tracking-[-.02em] text-[#1d1d1f]">{facility.name}</p>
                <p className="mt-1 text-base text-[#4b4b4f]">
                  {facility.address}, {facility.city}, {facility.state} {facility.zip_code}
                </p>
                <p className="mt-2 text-sm text-[#65706b]">
                  CMS {facility.cms_id}
                  {facility.beds ? ` · ${facility.beds} certified beds` : ""}
                  {facility.overall_rating ? ` · CMS rating ${facility.overall_rating}/5` : ""}
                </p>
              </div>
              {facility.already_claimed ? (
                <span className="rounded-full bg-[#f1f3f2] px-3 py-2 text-sm font-medium text-[#52645d]">
                  Already claimed
                </span>
              ) : null}
              <Link
                href={`/provider/${facility.facility_id}`}
                className="min-h-12 rounded-full bg-[#16715e] px-6 py-3 text-base font-semibold text-white shadow-[0_5px_14px_rgba(22,113,94,.2)] transition hover:bg-[#105c4d]"
              >
                This is us
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <section className="mt-12 rounded-[1.75rem] border border-[#e5e5ea] bg-white p-7 shadow-[0_12px_36px_-30px_rgba(29,29,31,.4)]">
        <h2 className="text-2xl font-semibold tracking-[-.025em] text-[#1d1d1f]">Why completing this matters</h2>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-[#4b4b4f]">
          Where we have no answer, we record it as unknown. It is never held against you
          &mdash; we do not rank a community down for silence, and we do not invent an answer
          to fill the gap. But an unknown cannot win you a family either. If a family needs
          kosher dining and your entry is blank, you are not ranked low; you are simply not in
          that conversation.
        </p>
        <p className="mt-4 text-lg leading-8 text-[#4b4b4f]">
          Match accuracy is a direct function of how complete your profile is. The listing is
          free and always will be.
        </p>
      </section>
      </section>
    </main>
  );
}
