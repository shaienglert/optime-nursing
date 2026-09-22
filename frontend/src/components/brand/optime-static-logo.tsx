import Link from "next/link";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  variant?: "compact" | "primary";
  height?: number;
};

export function OptimeStaticLogo({ href = "/", className = "", variant = "compact", height = 32 }: OptimeStaticLogoProps) {
  const scale = height / 32;
  const wordSize = Math.max(22, Math.round(36.3 * scale));
  const ring = Math.max(24, Math.round(37.5 * scale));
  const stroke = Math.max(4, Math.round(6.05 * scale));
  const gap = Math.max(4, Math.round(7.56 * scale));

  return (
    <Link
      href={href}
      className={`inline-flex flex-col items-center leading-none ${className}`.trim()}
      aria-label="OOmnik Home"
    >
      <span className="inline-flex items-center font-semibold text-[#079ff2]" style={{ gap }}>
        <span className="inline-flex items-center" aria-hidden="true">
          <span className="inline-block rounded-full border-current" style={{ width: ring, height: ring, borderWidth: stroke }} />
          <span className="inline-block rounded-full border-current" style={{ width: ring, height: ring, borderWidth: stroke, marginLeft: -stroke }} />
        </span>
        <span className="inline-flex items-baseline" style={{ gap, fontSize: wordSize, letterSpacing: "0.0375em" }}>
          <span>m</span><span>n</span>
          <span className="relative inline-block">ı<span aria-hidden="true" className="absolute left-1/2 -translate-x-1/2 rounded-full bg-orange-500" style={{ width: Math.max(5, Math.round(4.75*scale)), height: Math.max(5, Math.round(4.75*scale)), top: Math.round(5.4*scale) }} /></span>
          <span>k</span>
        </span>
      </span>
      {variant === "primary" ? (
        <span className="mt-1 whitespace-nowrap font-light text-[#168fe0]" style={{ fontSize: Math.max(9, Math.round(10*scale)), letterSpacing: "0.125em" }}>
          Finding You the Right Way
        </span>
      ) : null}
    </Link>
  );
}
