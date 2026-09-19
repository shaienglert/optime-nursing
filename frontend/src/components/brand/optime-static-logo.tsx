import Image from "next/image";
import Link from "next/link";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  /** "compact" is the wordmark alone, for tight spaces (headers, inline nav).
   *  "primary" also carries the "Finding You the Right Way" tagline baked into
   *  the artwork, for large, uncontested spaces (hero sections, footers). */
  variant?: "compact" | "primary";
  /** Rendered height in pixels; width is derived from the source aspect ratio. */
  height?: number;
};

const VARIANTS = {
  compact: { src: "/brand/oomnik-compact.png", width: 2066, height: 595 },
  primary: { src: "/brand/oomnik-primary.png", width: 2058, height: 651 },
};

export function OptimeStaticLogo({ href = "/", className = "", variant = "compact", height = 32 }: OptimeStaticLogoProps) {
  const { src, width, height: naturalHeight } = VARIANTS[variant];
  const renderedWidth = Math.round((width / naturalHeight) * height);
  return (
    <Link href={href} className={`inline-flex items-center ${className}`.trim()} aria-label="Oomnik Home">
      <Image src={src} alt="Oomnik — Finding You the Right Way" width={renderedWidth} height={height} priority />
    </Link>
  );
}
