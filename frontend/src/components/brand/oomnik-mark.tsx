import { ApprovedLogo } from "./approved-logo";

/** The approved double-OO artwork, decorative beside an action's text label. */
export function OomnikMark({ className = "", size = 28 }: { className?: string; size?: number }) {
  return <span aria-hidden="true" className={`inline-flex shrink-0 items-center justify-center rounded-lg bg-cream px-1.5 py-1 align-middle ${className}`}><ApprovedLogo variant="double-o" width={size} decorative /></span>;
}
