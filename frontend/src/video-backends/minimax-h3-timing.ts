/** The current gateway requests 5–15 seconds on the 24 fps, 17k+5 frame grid. */
export function h3RequestFrameCount(seconds: number): number | undefined {
  if (!Number.isInteger(seconds) || seconds < 5 || seconds > 15) return undefined;
  return 17 * Math.ceil((seconds * 24 - 5) / 17) + 5;
}

export function h3Timing(targetMs: number, seconds: number, qualified: readonly number[] | undefined) {
  const requestFrames = qualified?.includes(seconds) ? h3RequestFrameCount(seconds) : undefined;
  const playbackIntent = requestFrames && Number.isSafeInteger(targetMs) && targetMs > 0 ? "whole_take" as const : undefined;
  return { requestFrames, playbackIntent };
}

export function closestH3Request(targetMs: number, qualified: readonly number[] | undefined) {
  return qualified?.map(seconds => ({ seconds, ...h3Timing(targetMs, seconds, qualified) }))
    .filter(item => item.playbackIntent)
    .sort((a, b) => Math.abs(a.requestFrames! * 1000 - targetMs * 24) - Math.abs(b.requestFrames! * 1000 - targetMs * 24)
      || a.seconds - b.seconds)[0];
}

/** Compare the measured original with the target before rounding the percentage for display. */
export function durationDeviationNotice(targetMs: number, actualSeconds: number): string | undefined {
  if (!(targetMs > 0 && actualSeconds > 0)) return undefined;
  const targetUs = targetMs * 1000;
  const delta = Math.round(actualSeconds * 1_000_000) - targetUs;
  if (Math.abs(delta) * 100 <= targetUs * 15) return undefined;
  return `时长偏差较大 · 目标 ${targetMs / 1000} 秒 · 原片 ${actualSeconds.toFixed(2)} 秒（${delta > 0 ? "+" : ""}${(100 * delta / targetUs).toFixed(1)}%）`;
}
