"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ClaimSearchResult, searchClaimableFacilities } from "@/lib/provider-api";

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

  useEffect(() => {
    const timer = setTimeout(() => {
      void runSearch(query, state);
    }, 250);
    return () => clearTimeout(timer);
  }, [query, state, runSearch]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <p className="text-xs font-semibold uppercase tracking-widest text-teal-700">
        For senior living providers
      </p>
      <h1 className="mt-3 text-3xl font-semibold text-slate-900">Find your community</h1>
      <p className="mt-4 max-w-xl text-slate-600">
        Your community is most likely already on OPTIME. We built its profile from public
        records &mdash; CMS quality data, state licensing, bed counts, inspection history.
        That covers what the government publishes about you and almost nothing about what
        living there is like. Find yourself below and complete the rest.
      </p>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Community name"
          aria-label="Community name"
          className="flex-1 rounded-md border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
        />
        <select
          value={state}
          onChange={(event) => setState(event.target.value)}
          aria-label="State"
          className="rounded-md border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
        >
          <option value="">All states</option>
          <option value="NV">Nevada</option>
          <option value="FL">Florida</option>
        </select>
      </div>

      {error ? (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      {isSearching ? <p className="mt-6 text-sm text-slate-500">Searching&hellip;</p> : null}

      {!isSearching && hasSearched && results.length === 0 ? (
        <div className="mt-6 rounded-md border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
          <p className="font-medium text-slate-900">No match under that name.</p>
          <p className="mt-1">
            Communities are listed under the name on their CMS certification, which is not
            always the name on the sign. Try a shorter fragment, or reply to our email and we
            will find it for you.
          </p>
        </div>
      ) : null}

      {results.length > 0 ? (
        <ul className="mt-6 divide-y divide-slate-200 rounded-md border border-slate-200">
          {results.map((facility) => (
            <li key={facility.facility_id} className="flex flex-wrap items-center gap-3 px-4 py-4">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-slate-900">{facility.name}</p>
                <p className="text-sm text-slate-600">
                  {facility.address}, {facility.city}, {facility.state} {facility.zip_code}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  CMS {facility.cms_id}
                  {facility.beds ? ` · ${facility.beds} certified beds` : ""}
                  {facility.overall_rating ? ` · CMS rating ${facility.overall_rating}/5` : ""}
                </p>
              </div>
              {facility.already_claimed ? (
                <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                  Already claimed
                </span>
              ) : null}
              <Link
                href={`/provider/${facility.facility_id}`}
                className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
              >
                This is us
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <section className="mt-12 rounded-md border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Why completing this matters</h2>
        <p className="mt-3 text-slate-700">
          Where we have no answer, we record it as unknown. It is never held against you
          &mdash; we do not rank a community down for silence, and we do not invent an answer
          to fill the gap. But an unknown cannot win you a family either. If a family needs
          kosher dining and your entry is blank, you are not ranked low; you are simply not in
          that conversation.
        </p>
        <p className="mt-3 text-slate-700">
          Match accuracy is a direct function of how complete your profile is. The listing is
          free and always will be.
        </p>
      </section>
    </main>
  );
}
