import Link from "next/link";
import { Suspense } from "react";

import { ResultsPageClient } from "@/app/results/results-page-client";

export default function ResultsPage() {
  return (
    <>
      <div className="mx-auto max-w-7xl px-4 pt-5 sm:px-8 lg:px-12">
        <Link
          href="/adaptive-interview?review=1&next=/results"
          className="inline-flex rounded-full border border-[#d9cfbf] bg-white px-4 py-2 text-sm font-semibold text-[#534a3d] shadow-sm hover:bg-[#f6f2ea]"
        >
          Change decision answers
        </Link>
      </div>
      <Suspense fallback={<main className="min-h-screen bg-[#fffaf2] px-6 py-12 text-[#5d5548]">Loading results...</main>}>
        <ResultsPageClient />
      </Suspense>
    </>
  );
}
