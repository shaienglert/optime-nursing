import { ApprovedLogo } from "./approved-logo";

export function OptimeDynamicLogo({ progress, ready }: { progress: number; ready: boolean }) {
  return <div className="rounded-3xl border border-line bg-white p-6"><ApprovedLogo variant="primary" width={260} /><div role="progressbar" aria-label="Preparing your options" aria-valuemin={0} aria-valuemax={100} aria-valuenow={ready ? 100 : Math.round(Math.max(0, Math.min(100, progress)))} className="mt-5 h-1.5 overflow-hidden rounded-full bg-sand"><div className="h-full rounded-full bg-forest" style={{ width: `${ready ? 100 : Math.max(0, Math.min(100, progress))}%` }} /></div></div>;
}
