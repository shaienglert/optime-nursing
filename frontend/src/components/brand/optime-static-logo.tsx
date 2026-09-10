import Link from "next/link";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  subtitle?: string;
};

export function OptimeStaticLogo({
  href = "/",
  className = "",
  subtitle = "Finding You the Right Way",
}: OptimeStaticLogoProps) {
  return (
    <Link href={href} className={`inline-flex items-center gap-3 ${className}`.trim()} aria-label="Oomnik Home">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-[#bdd5cc] bg-white shadow-[0_10px_24px_-16px_rgba(30,84,70,0.42)]">
        <svg viewBox="0 0 64 64" className="h-6 w-6" role="img" aria-hidden="true">
          <circle cx="22" cy="27" r="10" fill="none" stroke="#2f7f6d" strokeWidth="4" />
          <circle cx="42" cy="27" r="10" fill="none" stroke="#2f7f6d" strokeWidth="4" />
          <path d="M32 27h0" stroke="#2f7f6d" strokeWidth="4" strokeLinecap="round" />
          <path d="M18 44c4 6 24 6 28 0" fill="none" stroke="#57a18f" strokeWidth="4" strokeLinecap="round" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className="block text-xl font-semibold tracking-[-0.06em] text-[#204d43]"><span className="text-2xl">OO</span>mnik</span>
        <span className="block text-[11px] text-[#5e786f]">{subtitle}</span>
      </span>
    </Link>
  );
}
