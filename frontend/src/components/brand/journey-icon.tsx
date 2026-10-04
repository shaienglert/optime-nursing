export function JourneyIcon({ kind, size = 24 }: { kind: "conversation" | "home" | "forward" | "back"; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="shrink-0">
    {kind === "conversation" ? <><path d="M21 11a8 8 0 0 1-8 8H7l-4 3v-7a8 8 0 0 1 8-12h2a8 8 0 0 1 8 8Z" /><path d="M8 9h8M8 13h5" /></> : kind === "home" ? <><path d="m3 10 9-7 9 7M5 9v12h14V9" /><path d="M9 21v-8h6v8" /></> : kind === "back" ? <path d="m11 5-7 7 7 7M4 12h16" /> : <path d="M4 12h16m-7-7 7 7-7 7" />}
  </svg>;
}
