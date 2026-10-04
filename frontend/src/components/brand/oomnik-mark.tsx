import { ApprovedLogo } from "./approved-logo";

/** The approved double-OO artwork, decorative beside an action's text label. */
export function OomnikMark({ className = "", size = 28 }: { className?: string; size?: number }) {
  return <ApprovedLogo variant="double-o" width={size} decorative className={className} />;
}
