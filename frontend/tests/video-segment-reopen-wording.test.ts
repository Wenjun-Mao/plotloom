import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { VideoSegmentReview } from "../src/video-segment-review";
import type { VideoJob, VideoSegment } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("keeps reopen guidance true after preparing and selecting a playback segment", async () => {
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  const segment: VideoSegment = { id: "segment", videoJobId: "job", shotId: "shot", inFrame: 0, outFrame: 120, authoredDurationUnits: 5_000, sourceProbe: { frameCount: 124, fps: "24/1" }, derivativeProbe: { frameCount: 120, fps: "24/1" }, derivativeHash: "a".repeat(64), current: true, selected: false, selectedRevision: null, createdAt: "now" };
  const job: VideoJob = { id: "job", projectId: "project", state: "ingested", current: true, selected: false, selectionRevision: 1, requestedSeconds: 5, providerPredictionId: "provider", cancelRequestedAt: null, outputHash: "b".repeat(64), error: null, snapshot: { sourceTiming: { durationUnits: 5_000 } }, observed: { durationSeconds: 5.167, width: 832, height: 480, videoCodec: "h264", audioCodec: "aac", frameCount: 124 }, reviews: [
    { id: "reject", decision: "reject", reviewer: "QA", note: "technical only", createdAt: "earlier" },
    { id: "reopen", decision: "reopen", reviewer: "QA", note: "technical reconsideration", createdAt: "now" },
  ] };
  try {
    for (const segments of [[], [segment], [{ ...segment, selected: true }]]) {
      await act(async () => root.render(createElement(VideoSegmentReview, { projectId: "project", job: { ...job, segments }, readOnly: false, onRefresh: async () => {} })));
      expect(host.textContent).toContain("重新开放本身不会准备片段或将视频用于故事");
      expect(host.textContent).not.toContain("尚未准备片段或选择故事播放");
      if (segments.length) expect(host.textContent).toContain(segment.selected || segments[0].selected ? "已选择片段 · 正用于故事" : "待审片段 · 尚未用于故事");
    }
  } finally { await act(async () => root.unmount()); host.remove(); }
});
