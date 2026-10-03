import Link from "next/link";

import { FontSizeControl } from "@/components/brand/font-size-control";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/results", label: "Results" },
  { href: "/facilities", label: "Facilities" },
  { href: "/las-vegas-senior-living", label: "Las Vegas data" },
  { href: "/guides", label: "Guides" },
  { href: "/compare", label: "Compare" },
  { href: "/workspace", label: "Saved Cases" },
  { href: "/admin", label: "Admin" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#d8e7e1] bg-white/92 backdrop-blur">
      <div className="mx-auto flex min-h-20 w-full max-w-[1800px] items-center gap-3 overflow-x-auto px-3 sm:min-h-24 sm:gap-8 sm:px-10 lg:px-14">
        <nav aria-label="Primary" className="flex min-w-max flex-1 items-center gap-1 sm:gap-3 md:justify-between md:gap-6">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              prefetch={item.href.startsWith("/admin") ? false : undefined}
              className="rounded-full px-2 py-3 text-sm font-medium whitespace-nowrap text-[#31554a] transition hover:bg-[#eef7f3] hover:text-[#1e4339] sm:text-base md:text-[1.3rem]"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <FontSizeControl />
      </div>
    </header>
  );
}
