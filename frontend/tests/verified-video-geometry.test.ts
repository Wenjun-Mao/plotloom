import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { verifiedVideoGeometry } from "../src/features/media/verified-video-geometry";
import { VideoSegmentReview } from "../src/video-segment-review";
import type { VideoJob, VideoSegment } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("reserves portrait and landscape probe geometry without waiting for browser metadata", () => {
  expect(verifiedVideoGeometry({ width: 576, height: 1024 })).toEqual({ aspectRatio: "576 / 1024", objectFit: "contain" });
  expect(verifiedVideoGeometry({ width: 1280, height: 704 })).toEqual({ aspectRatio: "1280 / 704", objectFit: "contain" });
});

it("does not invent dimensions when probe geometry is absent or invalid", () => {
  for (const observed of [null, undefined, { width: 0, height: 1 }, { width: 1, height: NaN }, { width: 1.2, height: 2 }]) {
    expect(verifiedVideoGeometry(observed)).toBeUndefined();
  }
});

it("reserves a retained segment's review player before any metadata event", async () => {
  const segment: VideoSegment = {
    id: "segment", videoJobId: "take", shotId: "shot", inFrame: 0, outFrame: 144,
    authoredDurationUnits: 6000, sourceProbe: { frameCount: 192, fps: "24/1" },
    derivativeProbe: { frameCount: 144, fps: "24/1" }, derivativeHash: "hash",
    current: true, selected: false, selectedRevision: null, createdAt: "2026-10-04T00:00:00Z",
  };
  const job: VideoJob = {
    id: "take", projectId: "project", state: "ingested", current: true, selected: false,
    selectionRevision: 1, requestedSeconds: 8, cancelRequestedAt: null,
    providerPredictionId: null, outputHash: "hash", error: null, reviews: [], segments: [segment],
    observed: { durationSeconds: 8, width: 576, height: 1024, videoCodec: "h264", audioCodec: "aac", frameCount: 192 },
    snapshot: { sourceTiming: { durationUnits: 6000 } },
  };
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(VideoSegmentReview, {
      projectId: "project", job, readOnly: false, onRefresh: async () => undefined,
    })));
    const player = host.querySelector<HTMLVideoElement>("video")!;
    expect(player.readyState).toBe(0);
    expect(player.style.aspectRatio).toBe("576 / 1024");
    expect(player.style.objectFit).toBe("contain");
  } finally {
    await act(async () => root.unmount()); host.remove();
  }
});
