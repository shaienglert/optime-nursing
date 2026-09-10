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
      <span className="leading-tight text-[#0b2850]">
        <span className="flex items-end font-black tracking-tight" aria-label="Oomnik">
          <span className="relative mr-[1px] inline-flex items-center">
            <span className="inline-block h-[22px] w-[22px] rounded-full border-[5px] border-current" />
            <span className="absolute -left-[2px] -top-[5px] h-[8px] w-[14px] rotate-[-18deg] rounded-full border-t-[4px] border-current" />
          </span>
          <span className="relative mr-[2px] inline-flex items-center">
            <span className="inline-block h-[22px] w-[22px] rounded-full border-[5px] border-current" />
            <span className="absolute -right-[3px] -top-[5px] h-[8px] w-[14px] rotate-[18deg] rounded-full border-t-[4px] border-current" />
          </span>
          <span className="text-[25px] font-black leading-[22px] tracking-[-0.055em]">mnik</span>
        </span>
        <span className="mt-1 block text-[11px] font-medium tracking-[0.01em] text-[#0b2850]">{subtitle}</span>
      </span>
    </Link>
  );
}
