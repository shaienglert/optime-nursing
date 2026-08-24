import Link from "next/link";
import { Suspense } from "react";

import { ResultsPageClient } from "@/app/results/results-page-client";

export default function DetailedResultsPage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-5 sm:px-8 lg:px-12">
        <Link
          href="/results"
          className="inline-flex rounded-2xl border border-[#d9cfbf] bg-white px-5 py-3 text-lg font-semibold text-[#534a3d] shadow-sm hover:bg-[#f6f2ea]"
        >
          Back to simple results
        </Link>
      </div>
      <Suspense fallback={<main className="min-h-screen bg-[#fffaf2] px-6 py-12 text-xl text-[#5d5548]">Loading detailed comparison…</main>}>
        <ResultsPageClient />
      </Suspense>
    </>
  );
}
