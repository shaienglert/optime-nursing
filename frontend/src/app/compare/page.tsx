import { Suspense } from "react";

import { ComparePageClient } from "@/components/compare/compare-page-client";

export default function ComparePage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-canvas px-6 py-12 text-muted">Loading compare view...</main>}>
      <ComparePageClient />
    </Suspense>
  );
}