import type { CSSProperties } from "react";

/** Reserve review layout from the admitted probe, before browser metadata loads. */
export function verifiedVideoGeometry(
  observed: { width: number; height: number } | null | undefined,
): CSSProperties | undefined {
  if (!observed || !Number.isInteger(observed.width) || !Number.isInteger(observed.height)
    || observed.width <= 0 || observed.height <= 0) return undefined;
  return { aspectRatio: `${observed.width} / ${observed.height}`, objectFit: "contain" };
}
