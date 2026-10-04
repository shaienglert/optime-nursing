import Link from "next/link";
import { Suspense } from "react";

import { ResultsPageClient } from "@/app/results/results-page-client";

export default function DetailedResultsPage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-5 sm:px-8 lg:px-12">
        <Link
          href="/results"
          className="inline-flex rounded-2xl border border-line bg-white px-5 py-3 text-lg font-semibold text-muted shadow-sm hover:bg-sand oomnik-panel"
        >
          Back to simple results
        </Link>
      </div>
      <Suspense fallback={<main className="min-h-screen bg-canvas px-6 py-12 text-xl text-muted">Loading detailed comparison…</main>}>
        <ResultsPageClient />
      </Suspense>
    </>
  );
}
