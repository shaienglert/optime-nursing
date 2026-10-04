import Link from "next/link";
import { ApprovedLogo } from "./approved-logo";

type OptimeStaticLogoProps = {
  href?: string;
  className?: string;
  variant?: "compact" | "primary";
  height?: number;
};

export function OptimeStaticLogo({ href = "/", className = "", variant = "compact", height = 38 }: OptimeStaticLogoProps) {
  const ratio = variant === "primary" ? 450 / 155 : 449 / 109;
  return <Link href={href} className={`inline-flex min-w-0 max-w-full items-center ${className}`.trim()} aria-label="OOmnik Home"><ApprovedLogo variant={variant} width={Math.round(height * ratio)} decorative /></Link>;
}
