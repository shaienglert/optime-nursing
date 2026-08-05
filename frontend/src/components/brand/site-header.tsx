import Link from "next/link";

import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/results", label: "Results" },
  { href: "/facilities", label: "Facilities" },
  { href: "/compare", label: "Compare" },
  { href: "/workspace", label: "Saved Cases" },
  { href: "/admin/executive-intelligence", label: "Admin" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#d8e7e1] bg-white/92 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-8">
        <OptimeStaticLogo />
        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-3 py-2 text-sm font-medium text-[#31554a] transition hover:bg-[#eef7f3] hover:text-[#1e4339]"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
