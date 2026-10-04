import Link from "next/link";
import { FontSizeControl } from "@/components/brand/font-size-control";
import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";
import { JourneyIcon } from "@/components/brand/journey-icon";

const SECONDARY_LINKS = [
  { href: "/results", label: "Your results" }, { href: "/facilities", label: "Explore communities" },
  { href: "/compare", label: "Compare saved places" }, { href: "/las-vegas-senior-living", label: "Las Vegas evidence" },
  { href: "/guides", label: "Family guides" }, { href: "/admin", label: "Admin" },
];

export function SiteHeader() {
  return <>
    <a href="#main-content" className="sr-only z-[60] rounded-xl bg-white p-4 text-lg text-[#284b38] focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Skip to content</a>
    <header className="sticky top-0 z-50 border-b border-[#e4ded4] bg-[#fdfbf7]/95 backdrop-blur">
      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 px-5 py-4 sm:px-8 xl:flex xl:gap-6">
        <OptimeStaticLogo height={26} />
        <nav aria-label="Primary" className="hidden flex-1 items-center justify-center gap-6 text-lg font-medium xl:flex">
          <Link href="/#how-it-works" className="inline-flex min-h-12 items-center hover:text-[#284b38]">How it works</Link>
          <Link href="/workspace" className="inline-flex min-h-12 items-center hover:text-[#284b38]">Saved conversations</Link>
          <details className="relative"><summary className="flex min-h-12 cursor-pointer items-center hover:text-[#284b38]">Explore</summary><nav aria-label="More pages" className="absolute right-0 top-full mt-3 w-72 rounded-xl border border-[#e4ded4] bg-white p-3 shadow-lg">{SECONDARY_LINKS.map(item => <Link key={item.href} href={item.href} prefetch={item.href === "/admin" ? false : undefined} className="flex min-h-12 items-center rounded-lg px-3 hover:bg-[#f1f0e8]">{item.label}</Link>)}</nav></details>
        </nav>
        <FontSizeControl />
        <details className="relative xl:hidden"><summary className="flex min-h-12 cursor-pointer items-center text-lg font-medium">Menu</summary><nav aria-label="Mobile navigation" className="absolute left-0 top-full mt-2 max-h-[65vh] w-[min(19rem,85vw)] overflow-y-auto rounded-xl border border-[#e4ded4] bg-white p-3 text-lg shadow-lg"><Link href="/#how-it-works" className="flex min-h-12 items-center rounded-lg px-3 hover:bg-[#f1f0e8]">How it works</Link><Link href="/workspace" className="flex min-h-12 items-center rounded-lg px-3 hover:bg-[#f1f0e8]">Saved conversations</Link>{SECONDARY_LINKS.map(item => <Link key={item.href} href={item.href} prefetch={item.href === "/admin" ? false : undefined} className="flex min-h-12 items-center rounded-lg px-3 hover:bg-[#f1f0e8]">{item.label}</Link>)}</nav></details>
        <Link href="/#start-search" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#284b38] px-4 py-3 text-lg font-semibold text-white transition hover:bg-[#1c3527]">Start here<JourneyIcon kind="forward" /></Link>
      </div>
    </header>
  </>;
}
