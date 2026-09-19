import Image from "next/image";

type OomnikMarkProps = {
  className?: string;
  /** Rendered width in pixels; height is derived from the source aspect ratio (510x340). */
  size?: number;
};

/** The "OO" double-ring mark alone, for dropping into buttons and other small,
 *  cluttered spots where the full wordmark wouldn't fit or would compete with
 *  the button's own label. */
export function OomnikMark({ className = "", size = 20 }: OomnikMarkProps) {
  const height = Math.round((340 / 510) * size);
  return (
    <Image
      src="/brand/oomnik-doubleo.png"
      alt=""
      width={size}
      height={height}
      className={className}
      aria-hidden="true"
    />
  );
}
