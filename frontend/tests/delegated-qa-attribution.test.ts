import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { humanReviewLabel } from "../src/human-review-attribution";
import { BranchingVideoPreview } from "../src/branching-video-preview";
import { branchingFixture } from "./video-pilot-fixtures";
import { batchApi } from "../src/features/video-batch/api";
import { VideoBatchPanel } from "../src/features/video-batch/VideoBatchPanel";
import { plotloomApi } from "../src/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const attribution = { kind: "agent_operated_qa", scopeId: "synthetic-test-scope" } as const;

it("distinguishes agent QA, unnamed human confirmation and retained actual names", () => {
  expect(humanReviewLabel({ reviewer: "@plotloom:agent-qa:synthetic-test-scope", attribution })).toBe("代理 QA 审阅（经用户授权）");
  expect(humanReviewLabel({ reviewer: "", attribution: { kind: "unnamed_creator" } })).toBe("创作者确认（未署名）");
  expect(humanReviewLabel({ reviewer: "Retained actual reviewer" })).toBe("Retained actual reviewer");
});

it("shows delegated QA on the selected story clip without asserting human review", async () => {
  const fixture = branchingFixture();
  fixture.selected[0].playbackSegment!.attribution = attribution;
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
  try {
    await act(async () => root.render(createElement(BranchingVideoPreview, {
      projectId: "project", jobs: fixture.selected, storyboard: fixture.storyboard, sceneBeats: fixture.sceneBeats, graph: fixture.graph,
    })));
    expect(host.querySelector("video")).not.toBeNull();
    expect(host.textContent).toContain("代理 QA 审阅（经用户授权） · 一次性测试素材");
    expect(host.textContent).not.toContain("创作者确认");
    expect(host.textContent).not.toContain("@plotloom:agent-qa");
  } finally {
    await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  }
});

it("attributes an approved QA batch heading and saved status to the agent", async () => {
  vi.spyOn(batchApi, "current").mockResolvedValue({ id: "qa-batch", projectId: "project", revision: 1,
    controlRevision: 1, state: "approved", manifestHash: "a".repeat(64), execution: { reviewAttribution: attribution },
    manifest: { scopeShotIds: ["SH01", "SH02"], kept: [], targets: [], blockers: [], newJobs: 2, requestedSeconds: 10,
      setup: { profileId: "test-profile", aspectPolicy: "cover_center_crop", maxJobs: 2, maxRequestedSeconds: 10 } } });
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false } as never);
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(VideoBatchPanel, { projectId: "project", disabled: false, dirty: false })));
    expect(host.querySelector("h3")?.textContent).toBe("全部视频已保存代理 QA 确认");
    expect(host.textContent).toContain("代理 QA 审阅（经用户授权） · 一次性测试批次");
    expect(host.textContent).not.toContain("已保存人工确认");
    expect(host.textContent).not.toContain("整包人工确认");
  } finally {
    await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  }
});

it.each(["running", "paused"])("labels frozen planned work truthfully while %s with a submitted job", async state => {
  const batch = { id: "qa-batch", projectId: "project", revision: 4,
    controlRevision: 3, state, manifestHash: "a".repeat(64),
    execution: { reviewAttribution: attribution, authorizedManifestHash: "a".repeat(64),
      jobs: { SH01: "already-submitted-job" }, segments: {} },
    progress: { total: 2, ready: 0, failed: 0, blocked: 0 },
    manifest: { scopeShotIds: ["SH01", "SH02"], kept: [], targets: [], blockers: [], newJobs: 2, requestedSeconds: 10,
      setup: { profileId: "test-profile", aspectPolicy: "cover_center_crop", maxJobs: 2, maxRequestedSeconds: 10 } } };
  vi.spyOn(batchApi, "current").mockResolvedValue(batch);
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: false } as never);
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(VideoBatchPanel, { projectId: "project", disabled: false, dirty: false })));
    expect(host.querySelector("h3")?.textContent).toBe(state === "paused" ? "已暂停新派发" : "正在制作全部缺失视频");
    expect(host.textContent).toContain("计划新作业 2 项");
    expect(host.textContent).not.toContain("待派发任务");
    expect(host.textContent).toContain("播放提案就绪 0/2");
    expect(batchApi.current).toHaveBeenCalledTimes(1);
  } finally {
    await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks();
  }
});
