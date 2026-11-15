/**
 * Line icons for the Hebrew intake tiles. Original drawings on a 32×32 grid,
 * 1.6px strokes, round caps, using currentColor.
 */
import type { ReactElement } from "react";

const paths: Record<string, ReactElement> = {
  // people
  mother: (
    <>
      <circle cx="16" cy="10" r="4.5" />
      <path d="M11.5 9.5c0-4 2-6 4.5-6s4.5 2 4.5 6c1.2 1.6 1.4 3.4.6 5" />
      <path d="M7.5 27.5c.8-5.6 4.2-8.5 8.5-8.5s7.7 2.9 8.5 8.5" />
    </>
  ),
  father: (
    <>
      <circle cx="16" cy="10.5" r="4.5" />
      <path d="M12 8.5c1.6.4 3.4-.4 4.6-2 .8 1.4 2.2 2.2 3.4 2.3" />
      <path d="M7.5 27.5c.8-5.6 4.2-8.5 8.5-8.5s7.7 2.9 8.5 8.5" />
    </>
  ),
  grandparent: (
    <>
      <circle cx="14" cy="10.5" r="4.5" />
      <path d="M6.5 27.5c.7-5.3 3.6-8.3 7.5-8.3 2.5 0 4.6 1.2 6 3.4" />
      <path d="M24 16.5v11M24 16.5c0-1.6 2.6-1.6 2.6 0" />
    </>
  ),
  couple: (
    <>
      <circle cx="11" cy="11" r="3.8" />
      <circle cx="21" cy="11" r="3.8" />
      <path d="M4.5 26.5c.6-4.6 3.2-7 6.5-7 2 0 3.7.9 5 2.6 1.3-1.7 3-2.6 5-2.6 3.3 0 5.9 2.4 6.5 7" />
    </>
  ),
  self: (
    <>
      <circle cx="16" cy="10" r="4.5" />
      <path d="M7.5 27.5c.8-5.6 4.2-8.5 8.5-8.5s7.7 2.9 8.5 8.5" />
      <path d="M13.5 23.5l2 2 3.5-4" />
    </>
  ),
  relative: (
    <>
      <circle cx="12" cy="11" r="4" />
      <path d="M5 26.5c.7-4.8 3.4-7.4 7-7.4s6.3 2.6 7 7.4" />
      <path d="M22 9v8M18 13h8" />
    </>
  ),
  // priorities
  medical: (
    <>
      <rect x="5.5" y="5.5" width="21" height="21" rx="6" />
      <path d="M16 11v10M11 16h10" />
    </>
  ),
  social: (
    <>
      <circle cx="10" cy="12" r="3" />
      <circle cx="22" cy="12" r="3" />
      <circle cx="16" cy="9" r="3" />
      <path d="M4.5 24c.4-3.4 2.6-5.2 5.5-5.2M27.5 24c-.4-3.4-2.6-5.2-5.5-5.2M10.5 26c.5-4.2 2.8-6.4 5.5-6.4s5 2.2 5.5 6.4" />
    </>
  ),
  shield: (
    <>
      <path d="M16 4.5l9.5 3.5v7.2c0 6-4 10.4-9.5 12.3-5.5-1.9-9.5-6.3-9.5-12.3V8z" />
      <path d="M12 16l3 3 5.5-6" />
    </>
  ),
  heart: <path d="M16 26.5S5.5 20.3 5.5 12.6c0-3.6 2.6-6.1 5.7-6.1 2.2 0 4 1.2 4.8 3 .8-1.8 2.6-3 4.8-3 3.1 0 5.7 2.5 5.7 6.1 0 7.7-10.5 13.9-10.5 13.9z" />,
  // surroundings and style
  city: (
    <>
      <path d="M4.5 27.5h23M7 27.5V13.5l6-3v17M13 27.5V7.5l8 3.5v16.5M21 27.5V15.5l4.5 2v10" />
      <path d="M16 13v1.5M16 17.5V19M16 22v1.5M9.5 17v1.5M9.5 21.5V23" />
    </>
  ),
  village: (
    <>
      <path d="M4.5 27.5h23" />
      <path d="M8 27.5v-8l5-4.5 5 4.5v8M11.5 27.5v-4.5h3v4.5" />
      <path d="M23.5 27.5v-6M23.5 21.5c-3 0-4.2-2.4-3-5 .6-1.4 1.8-2.3 3-4 1.2 1.7 2.4 2.6 3 4 1.2 2.6 0 5-3 5z" />
    </>
  ),
  luxury: (
    <>
      <path d="M9 6.5h14l4 6-11 13.5L5 12.5z" />
      <path d="M5 12.5h22M13 6.5l3 6 3-6M16 12.5v13.5" />
    </>
  ),
  modern: (
    <>
      <rect x="6.5" y="5.5" width="19" height="21" rx="2" />
      <path d="M6.5 12.5h19M6.5 19.5h19M16 5.5v21" />
    </>
  ),
  boutique: (
    <>
      <path d="M6.5 13.5h19v13h-19z" />
      <path d="M5 13.5l2.5-7h17l2.5 7M13 26.5v-6h6v6" />
      <path d="M9.5 13.5c0 1.6 1.2 2.6 2.4 2.6s2.4-1 2.4-2.6c0 1.6 1.2 2.6 2.4 2.6s2.4-1 2.4-2.6c0 1.6 1.2 2.6 2.4 2.6" />
    </>
  ),
  homey: (
    <>
      <path d="M5.5 15L16 6l10.5 9M8.5 12.5v14h15v-14" />
      <path d="M16 23s-4-2.4-4-5c0-1.3 1-2.2 2-2.2.8 0 1.6.5 2 1.2.4-.7 1.2-1.2 2-1.2 1 0 2 .9 2 2.2 0 2.6-4 5-4 5z" />
    </>
  ),
  // day rhythm
  privateSpace: (
    <>
      <path d="M8.5 27.5V6.5h15v21" />
      <path d="M4.5 27.5h23M19.5 17.5h.01" />
    </>
  ),
  structured: (
    <>
      <circle cx="16" cy="16" r="10.5" />
      <path d="M16 10v6l4 2.5" />
    </>
  ),
  flexible: (
    <>
      <path d="M5 21c3-6 5-6 8 0s5 6 8 0 4-5 6-2" />
      <path d="M5 12c3-5 5-5 8 0s5 5 8 0 4-4 6-1.5" />
    </>
  ),
  // activities
  gardening: (
    <>
      <path d="M16 27.5v-11" />
      <path d="M16 18.5c-5.5 0-8-3.5-8-8.5 5 0 8 2.5 8 8.5zM16 16c0-5 2.5-8 8-8 0 5-2.5 8-8 8z" />
      <path d="M9.5 27.5h13" />
    </>
  ),
  crafts: (
    <>
      <circle cx="12" cy="20" r="6.5" />
      <path d="M8 16.5c3 1 5.5 3.5 6.5 7.5M6.5 21c3-.5 7 .5 9.5 3M21 4.5l6.5 6.5-8.5 8.5" />
    </>
  ),
  games: (
    <>
      <rect x="5.5" y="9.5" width="21" height="14" rx="7" />
      <path d="M11.5 13.5v6M8.5 16.5h6M21 15h.01M23.5 18h.01" />
    </>
  ),
  music: (
    <>
      <path d="M12.5 23V8.5l13-3V20" />
      <circle cx="9.5" cy="23" r="3" />
      <circle cx="22.5" cy="20" r="3" />
    </>
  ),
  lectures: (
    <>
      <path d="M16 9c-3-2.2-7-2.6-10.5-1.6v17c3.5-1 7.5-.6 10.5 1.6 3-2.2 7-2.6 10.5-1.6v-17C23 6.4 19 6.8 16 9zM16 9v17" />
    </>
  ),
  movement: (
    <>
      <circle cx="18.5" cy="6.5" r="2.5" />
      <path d="M11 13.5l5-3 4 3.5 4.5 1M16 10.5l-2 8 5 3.5v5.5M14 18.5l-4.5 7" />
    </>
  ),
  outings: (
    <>
      <path d="M4.5 25.5l8-12 5 7 3-4 7 9z" />
      <circle cx="22.5" cy="8.5" r="2.5" />
    </>
  ),
  spiritual: (
    <>
      <path d="M16 27.5c-4.5 0-7.5-3-7.5-7.5 0-5 4.5-7.5 7.5-14 3 6.5 7.5 9 7.5 14 0 4.5-3 7.5-7.5 7.5z" />
      <path d="M16 27.5c-2 0-3.5-1.5-3.5-3.6 0-2.3 2-3.4 3.5-6.4 1.5 3 3.5 4.1 3.5 6.4 0 2.1-1.5 3.6-3.5 3.6z" />
    </>
  ),
  check: <path d="M8 16.5l5 5 11-11" />,
};

export type IntakeIconName = keyof typeof paths;

export function IntakeIcon({ name, size = 32 }: { name: string; size?: number }) {
  const drawing = paths[name];
  if (!drawing) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {drawing}
    </svg>
  );
}
