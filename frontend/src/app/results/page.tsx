import { Suspense } from "react";

import { ResultsPageClient } from "@/app/results/results-page-client";

export default function ResultsPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#fffaf2] px-6 py-12 text-[#5d5548]">Loading results...</main>}>
      <ResultsPageClient />
    </Suspense>
  );
}
