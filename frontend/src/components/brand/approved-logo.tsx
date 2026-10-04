import Image from "next/image";

const ARTWORK = {
  compact: { file: "Oomnik_Compact_Transparent.png", sourceWidth: 512, sourceHeight: 341, x: 36, y: 145, width: 449, height: 109 },
  primary: { file: "Oomnik_Primary_Transparent.png", sourceWidth: 512, sourceHeight: 286, x: 36, y: 97, width: 450, height: 155 },
  "double-o": { file: "Oomnik_DoubleO_Transparent.png", sourceWidth: 512, sourceHeight: 342, x: 109, y: 86, width: 293, height: 158 },
} as const;

/** Approved, unmodified artwork. The viewport hides only the export's empty margins. */
export function ApprovedLogo({ variant = "compact", width = 160, decorative = false, className = "" }: { variant?: keyof typeof ARTWORK; width?: number; decorative?: boolean; className?: string }) {
  const art = ARTWORK[variant];
  return <span aria-hidden={decorative || undefined} className={`relative inline-block max-w-full shrink-0 overflow-hidden align-middle ${className}`} style={{ width, aspectRatio: `${art.width} / ${art.height}` }}>
    <Image src={`/brand/approved/${art.file}`} alt={decorative ? "" : variant === "primary" ? "OOmnik — Finding You the Right Way" : "OOmnik"} width={art.sourceWidth} height={art.sourceHeight} sizes={`${Math.ceil(width * art.sourceWidth / art.width)}px`} loading="eager" className="absolute max-w-none" style={{ width: `${100 * art.sourceWidth / art.width}%`, height: "auto", left: `${-100 * art.x / art.width}%`, top: `${-100 * art.y / art.height}%` }} />
  </span>;
}
