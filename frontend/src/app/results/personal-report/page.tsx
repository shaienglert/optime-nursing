import { Suspense } from "react";

import { PersonalReportPageClient } from "@/app/results/personal-report/personal-report-page-client";

export default function PersonalReportPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#fffaf2] px-6 py-12 text-xl text-[#5d5548]">Preparing your personal report…</main>}>
      <PersonalReportPageClient />
    </Suspense>
  );
}
