import type { Metadata } from "next";
import { ExternalRatings } from "@/components/facility/external-ratings";

export const metadata: Metadata = {
  title: "The Heights of Summerlin | External Ratings Check",
  robots: { index: false, follow: false },
};

export default function SummerlinExternalRatingsCheckPage() {
  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-5 py-10">
      <header className="space-y-3">
        <p className="text-sm font-semibold text-muted">External ratings check</p>
        <h1 className="text-3xl font-semibold">The Heights of Summerlin</h1>
        <p>10550 W Park Run Dr., Las Vegas, NV 89144</p>
        <p className="text-sm text-muted">This verification page is separate from the Oomnik matching catalog.</p>
        <nav aria-label="Facility verification sources" className="flex flex-wrap gap-4 text-sm">
          <a className="underline" href="https://theheightsofsummerlin.com/">Facility website</a>
          <a className="underline" href="https://www.medicare.gov/care-compare/details/nursing-home/295083">Medicare Care Compare</a>
          <a className="underline" href="https://maps.app.goo.gl/8DiLgPgU1ZktWa81A">View this facility on Google Maps</a>
        </nav>
      </header>
      <ExternalRatings canonicalFacilityId="verification-summerlin-295083" />
    </main>
  );
}
