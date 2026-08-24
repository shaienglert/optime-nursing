import { Suspense } from "react";

import { SimpleResultsPageClient } from "@/app/results/simple-results-page-client";

export default function ResultsPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#fffaf2] px-6 py-12 text-xl text-[#5d5548]">Preparing your results…</main>}>
      <SimpleResultsPageClient />
    </Suspense>
  );
}
