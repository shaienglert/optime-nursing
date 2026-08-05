import Link from "next/link";
import Image from "next/image";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  subtitle?: string;
};

export function OptimeStaticLogo({
  href = "/",
  className = "",
  subtitle: _subtitle,
}: OptimeStaticLogoProps) {
  return (
    <Link href={href} className={`inline-flex h-16 items-center ${className}`.trim()} aria-label="OPTIME Home">
      <Image
        src="/branding/optime-logo-header.png"
        alt="OPTIME"
        width={900}
        height={220}
        priority
        className="h-[54px] w-auto max-w-none object-contain"
      />
    </Link>
  );
}
