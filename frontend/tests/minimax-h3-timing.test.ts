import { expect, it } from "vitest";
import { h3RequestFrameCount, h3SourceFrameCount, h3Timing } from "../src/video-backends/minimax-h3-timing";

// Independent vectors from the qualified backend catalog, including negative-JS-remainder cases.
const catalog = [[5, 124], [6, 158], [7, 175], [8, 192], [9, 226], [10, 243], [11, 277], [12, 294], [13, 328], [14, 345], [15, 362]];
const qualified = catalog.map(([seconds]) => seconds);

it.each(catalog)("matches the backend %s-second request's %s frames", (seconds, frames) => {
  expect(h3RequestFrameCount(seconds)).toBe(frames);
});

it.each([4, 16, 5.5, NaN, Infinity])( "rejects a noncatalog request %s", (seconds) => {
  expect(h3RequestFrameCount(seconds)).toBeUndefined();
});

it("separates exact-source playback from a covering request needing a reviewed segment", () => {
  expect(h3Timing(8000, 8, qualified)).toEqual({ sourceFrames: 192, requestFrames: 192, playbackIntent: "source_exact" });
  expect(h3Timing(2500, 5, qualified)).toEqual({ sourceFrames: 60, requestFrames: 124, playbackIntent: "segment_required" });
  expect(h3Timing(6000, 6, qualified)).toEqual({ sourceFrames: 144, requestFrames: 158, playbackIntent: "segment_required" });
});

it("refuses an off-grid source, insufficient capacity and missing or unqualified requests", () => {
  expect(h3Timing(1001, 5, qualified).playbackIntent).toBeUndefined();
  expect(h3Timing(6000, 5, qualified)).toEqual({ sourceFrames: 144, requestFrames: 124, playbackIntent: undefined });
  expect(h3Timing(16000, 15, qualified).playbackIntent).toBeUndefined();
  expect(h3Timing(2500, 5, undefined).requestFrames).toBeUndefined();
  expect(h3Timing(2500, 5, []).requestFrames).toBeUndefined();
  expect(h3Timing(2500, 6, [5]).requestFrames).toBeUndefined();
  expect(h3SourceFrameCount(0)).toBeUndefined();
  expect(h3SourceFrameCount(-125)).toBeUndefined();
  expect(h3SourceFrameCount(2500.1)).toBeUndefined();
});
