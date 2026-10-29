import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { RejectedTakeReplacement } from "../src/features/video-batch/RejectedTakeReplacement";
import { batchApi } from "../src/features/video-batch/api";
import { readyProductionBatch } from "./h3-production-fixtures";
import type { Review } from "../src/features/video-batch/contracts";
import type { VideoJobPrepareBody } from "../src/api";

it("single replacement preserves original settings, uses one stable new operation key and reads lost results without resending", async () => {
  const request: VideoJobPrepareBody = { approvalId: "approval", shotId: "shot", storyboardRevision: 1, expectedSelectionRevision: 1,
    idempotencyKey: "original-request-key", seed: 42, profileId: "h3_vertical_8", aspectPolicy: "cover_center_crop", allowCenterCrop: true,
    requestedDurationSeconds: 15, playbackIntent: "segment_required", resolution: "576x1024", audio: true };
  const batch = readyProductionBatch(request); batch.state = "cancelled";
  const review: Review = { batchId: batch.id, reviewHash: "f".repeat(64), ready: false, readyCount: 0, blockedCount: 0,
    kept: [], errors: [], proposals: [{ shotId: "shot", title: "守灯人", jobId: "original-job", segmentId: "segment", error: null, segment: null,
      job: { id: "original-job", state: "ingested", selected: false, selectionRevision: 1, reviews: [{ decision: "reject", note: "保持原构图，收紧表演。" }] } as never }] };
  let current = batch;
  vi.spyOn(batchApi, "current").mockImplementation(async () => current);
  vi.spyOn(batchApi, "review").mockResolvedValue(review);
  const send = vi.spyOn(batchApi, "command").mockImplementation(async (_project, name, body) => {
    expect(name).toBe("replace-rejected");
    const setup = (body as { setup: { singleRequest: VideoJobPrepareBody } }).setup;
    expect(setup.singleRequest).toEqual({ ...request, idempotencyKey: `video-replacement-${batch.id}-original-job` });
    current = { ...batch, id: "successor", state: "setup", execution: {}, manifest: { ...batch.manifest, replacement: { batchId: batch.id, rejectedJobIds: ["original-job"] } } };
    throw new Error("successor response lost");
  });
  const host = document.createElement("div"), root = createRoot(host), success = vi.fn(); document.body.append(host);
  const mount = () => act(async () => root.render(createElement(RejectedTakeReplacement, { projectId: "project", batch, review, disabled: false,
    actor: null, onRead: vi.fn(), onPending: vi.fn(), onSuccess: success })));
  try {
    await mount(); await act(async () => [...host.querySelectorAll("button")].find(button => button.textContent === "仅重做这些镜头")!.click());
    expect(send).toHaveBeenCalledOnce(); expect(success).toHaveBeenCalledWith(current);
    await act(async () => root.render(null)); await mount();
    await act(async () => [...host.querySelectorAll("button")].find(button => button.textContent === "仅重做这些镜头")!.click());
    expect(send).toHaveBeenCalledOnce(); expect(success).toHaveBeenLastCalledWith(current);
  } finally { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); }
});
