import { OptimeStaticLogo } from "@/components/brand/optime-static-logo";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#dedbd4] bg-[#faf8f3]/94 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-4xl items-center justify-between gap-4 px-5 sm:px-10">
        <OptimeStaticLogo />
        <p className="text-xs font-medium tracking-[0.08em] text-[#756f66]">A family decision document</p>
      </div>
    </header>
  );
}
