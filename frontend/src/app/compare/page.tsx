import { Suspense } from "react";

import { ComparePageClient } from "@/components/compare/compare-page-client";

export default function ComparePage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#fffdf8] px-6 py-12 text-[#5d5548]">Loading compare view...</main>}>
      <ComparePageClient />
    </Suspense>
  );
}