import { Suspense } from "react";

import { PersonalReportPageClient } from "@/app/results/personal-report/personal-report-page-client";

export default function PersonalReportPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-canvas px-6 py-12 text-xl text-muted">Preparing your personal report…</main>}>
      <PersonalReportPageClient />
    </Suspense>
  );
}
