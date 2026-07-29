import Link from "next/link";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  subtitle?: string;
};

export function OptimeStaticLogo({
  href = "/",
  className = "",
  subtitle = "Evidence-guided family decisions",
}: OptimeStaticLogoProps) {
  return (
    <Link href={href} className={`inline-flex items-center gap-3 ${className}`.trim()} aria-label="OPTIME Home">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-[#bdd5cc] bg-white shadow-[0_10px_24px_-16px_rgba(30,84,70,0.42)]">
        <svg viewBox="0 0 64 64" className="h-6 w-6" role="img" aria-hidden="true">
          <rect x="8" y="8" width="48" height="48" rx="12" fill="#f4fbf8" stroke="#7db5a3" strokeWidth="3" />
          <path d="M20 20 H44 V32 H32 V44 H20 Z" fill="none" stroke="#2f7f6d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M32 44 H44" fill="none" stroke="#57a18f" strokeWidth="4" strokeLinecap="round" />
          <path d="M44 44 L50 44" fill="none" stroke="#57a18f" strokeWidth="4" strokeLinecap="round" />
        </svg>
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold tracking-[0.18em] text-[#204d43]">OPTIME</span>
        <span className="block text-[11px] text-[#5e786f]">{subtitle}</span>
      </span>
    </Link>
  );
}
