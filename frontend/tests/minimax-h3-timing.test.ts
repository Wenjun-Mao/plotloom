import { expect, it } from "vitest";
import { closestH3Request, durationDeviationNotice, h3RequestFrameCount, h3Timing } from "../src/video-backends/minimax-h3-timing";

// Independent vectors from the qualified backend catalog, including negative-JS-remainder cases.
const catalog = [[5, 124], [6, 158], [7, 175], [8, 192], [9, 226], [10, 243], [11, 277], [12, 294], [13, 328], [14, 345], [15, 362]];
const qualified = catalog.map(([seconds]) => seconds);

it.each(catalog)("matches the backend %s-second request's %s frames", (seconds, frames) => {
  expect(h3RequestFrameCount(seconds)).toBe(frames);
});

it.each([4, 16, 5.5, NaN, Infinity])( "rejects a noncatalog request %s", (seconds) => {
  expect(h3RequestFrameCount(seconds)).toBeUndefined();
});

it.each([1001, 2500, 6000, 11300, 16000])("admits a supported whole take with target %s", target => {
  expect(h3Timing(target, 5, qualified)).toEqual({ requestFrames: 124, playbackIntent: "whole_take" });
});

it("refuses missing catalog, unsupported request or invalid target", () => {
  for (const values of [undefined, [], [5]]) expect(h3Timing(2500, 6, values).playbackIntent).toBeUndefined();
  for (const ms of [0, -1, 1.5]) expect(h3Timing(ms, 5, qualified).playbackIntent).toBeUndefined();
});

it("chooses the closest qualified playback time even if shorter than the target", () => {
  expect(closestH3Request(11300, qualified)?.requestFrames).toBe(277);
  expect(closestH3Request(6000, [5, 8])?.seconds).toBe(5);
  expect(closestH3Request(16000, qualified)?.seconds).toBe(15);
});

it.each([[8.5, false], [11.5, false], [8.499, true], [11.501, true], [10, false]])(
  "only flags measured %s s outside the inclusive 15%% tolerance", (seconds, flagged) => {
    expect(Boolean(durationDeviationNotice(10000, Number(seconds)))).toBe(flagged);
  },
);
