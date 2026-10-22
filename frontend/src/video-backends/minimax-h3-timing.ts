/** The current gateway requests 5–15 seconds on the 24 fps, 17k+5 frame grid. */
export function h3RequestFrameCount(seconds: number): number | undefined {
  if (!Number.isInteger(seconds) || seconds < 5 || seconds > 15) return undefined;
  return 17 * Math.ceil((seconds * 24 - 5) / 17) + 5;
}

export function h3SourceFrameCount(milliseconds: number): number | undefined {
  const scaled = milliseconds * 24;
  if (!Number.isSafeInteger(milliseconds) || milliseconds <= 0
    || !Number.isSafeInteger(scaled) || scaled % 1000 !== 0) return undefined;
  return scaled / 1000;
}

/** Catalog, source frame grid and request capacity are independent requirements. */
export function h3Timing(
  sourceMilliseconds: number,
  requestedSeconds: number,
  qualifiedSeconds: readonly number[] | undefined,
): {
  sourceFrames: number | undefined;
  requestFrames: number | undefined;
  playbackIntent: "source_exact" | "segment_required" | undefined;
} {
  const sourceFrames = h3SourceFrameCount(sourceMilliseconds);
  const requestFrames = qualifiedSeconds?.includes(requestedSeconds)
    ? h3RequestFrameCount(requestedSeconds) : undefined;
  const playbackIntent = sourceFrames !== undefined && requestFrames !== undefined && sourceFrames <= requestFrames
    ? sourceFrames === requestFrames ? "source_exact" : "segment_required"
    : undefined;
  return { sourceFrames, requestFrames, playbackIntent };
}
