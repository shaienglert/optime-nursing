"use client";

import Image from "next/image";
import { useId } from "react";

const ARTWORK = {
  compact: { file: "Oomnik_Compact_Transparent.png", sourceWidth: 512, sourceHeight: 341, x: 36, y: 145, width: 449, height: 109 },
  primary: { file: "Oomnik_Primary_Transparent.png", sourceWidth: 512, sourceHeight: 286, x: 36, y: 97, width: 450, height: 155 },
  "double-o": { file: "Oomnik_DoubleO_Transparent.png", sourceWidth: 512, sourceHeight: 342, x: 109, y: 86, width: 293, height: 158 },
} as const;

/** Preserve the approved pixels; remove the export's neutral matte at display time. */
export function ApprovedLogo({ variant = "compact", width = 160, decorative = false, className = "" }: { variant?: keyof typeof ARTWORK; width?: number; decorative?: boolean; className?: string }) {
  const art = ARTWORK[variant];
  const matteFilterId = `oomnik-matte-${useId().replace(/:/g, "")}`;
  return <span aria-hidden={decorative || undefined} className={`relative inline-block max-w-full shrink-0 overflow-hidden align-middle ${className}`} style={{ width, aspectRatio: `${art.width} / ${art.height}` }}>
    <svg width="0" height="0" aria-hidden="true" className="absolute pointer-events-none">
      <defs>
        <filter id={matteFilterId} colorInterpolationFilters="sRGB">
          {/* The blue wordmark and warm dot have chroma; the gray/white matte does not. */}
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1.05 0 1.05 0 -0.025" result="blueMask" />
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  2.8 0 -2.8 0 -0.06" result="warmMask" />
          <feComposite in="blueMask" in2="warmMask" operator="arithmetic" k2="1" k3="1" result="colorMask" />
          {/* Subtract the white matte from edge colors as well as their alpha. */}
          <feFlood floodColor="white" result="white" />
          <feComposite in="white" in2="colorMask" operator="out" result="matte" />
          <feComposite in="SourceGraphic" in2="matte" operator="arithmetic" k2="1" k3="-1" />
        </filter>
      </defs>
    </svg>
    <Image src={`/brand/approved/${art.file}`} alt={decorative ? "" : variant === "primary" ? "OOmnik — Finding You the Right Way" : "OOmnik"} width={art.sourceWidth} height={art.sourceHeight} unoptimized loading="eager" className="absolute max-w-none" style={{ filter: `url(#${matteFilterId})`, width: `${100 * art.sourceWidth / art.width}%`, height: "auto", left: `${-100 * art.x / art.width}%`, top: `${-100 * art.y / art.height}%` }} />
  </span>;
}
