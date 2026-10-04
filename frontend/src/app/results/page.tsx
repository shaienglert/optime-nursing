import { Suspense } from "react";

import { SimpleResultsPageClient } from "@/app/results/simple-results-page-client";

export default function ResultsPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-canvas px-6 py-12 text-xl text-muted">Preparing your results…</main>}>
      <SimpleResultsPageClient />
    </Suspense>
  );
}
