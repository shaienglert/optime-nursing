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
      <div className="mx-auto flex min-h-24 w-full max-w-[1800px] items-center justify-between gap-8 px-6 sm:px-10 lg:px-14">
        <nav aria-label="Primary" className="hidden flex-1 items-center justify-between gap-6 md:flex">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-2 py-3 text-[1.3rem] font-medium text-[#31554a] transition hover:bg-[#eef7f3] hover:text-[#1e4339]"
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
