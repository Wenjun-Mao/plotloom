import { expect, it } from "vitest";
import { demoProject } from "../src/demo";
import { shotWorkflowNextText } from "../src/app/workspace/recommendedShotWorkflow";
import { selectedJob } from "./video-pilot-fixtures";
import { hasCurrentStoryboardApproval } from "../src/features/media/current-storyboard-approval";
import type { StoryboardReview } from "../src/types";

const shot = { ...demoProject.storyboard.shots[0], durationUnits: 6_000 };
const ready: Parameters<typeof shotWorkflowNextText>[0] = {
  videoReady: true, videoError: false, mediaPhase: "ready", shot, availableShots: 1, readOnly: false,
  approvalCurrent: true, keyframeReady: true, identityReviewed: true,
  backendEnabled: true, h3: true, jobs: [], allRoutesReady: false,
};
const text = (change: Partial<typeof ready> = {}) => shotWorkflowNextText({ ...ready, ...change });

it("prioritizes unknown, failed and read-only owner state over retained readiness", () => {
  expect(text({ videoReady: false, allRoutesReady: true })).toContain("正在读取镜头视频状态");
  expect(text({ videoReady: false, videoError: true })).toContain("重新读取镜头视频状态");
  expect(text({ mediaPhase: "error", allRoutesReady: true })).toContain("重试媒体读取");
  expect(text({ mediaPhase: "loading" })).toContain("正在读取当前镜头的媒体证据");
  expect(text({ readOnly: true, allRoutesReady: true })).toContain("不要准备或提交新任务");
});
it("names each missing prerequisite and never equates installed shots with videos", () => {
  expect(text({ approvalCurrent: false })).toContain("前往分镜审核");
  expect(text({ keyframeReady: false })).toContain("查看关键帧");
  expect(text({ identityReviewed: false })).toContain("记录视觉复核");
  expect(text({ backendEnabled: false })).toContain("不能准备或提交新视频");
  expect(text({ backendEnabled: undefined })).toContain("尚未核实");
  expect(text({ availableShots: 0, shot: undefined })).toContain("当前分镜没有镜头");
  expect(text({ availableShots: 0, shot: undefined })).not.toContain("下拉框选择");
  expect(text()).toContain("审阅英文生成说明");
  expect(text({ h3: false })).toContain("准备新视频任务（冻结当前审核关键帧）");
});
it("requires a matching ready review and subject revision, not a retained approval ID", () => {
  const review = { head: { status: "ready", revision: 2 }, activeApproval: { id: "retained", subjectRevision: 2 } } as StoryboardReview;
  expect(hasCurrentStoryboardApproval(review, 2, false)).toBe(true);
  for (const [value, revision, dirty] of [[review, 3, false], [review, 2, true], [{ ...review, head: { ...review.head, status: "stale" } }, 2, false]] as const) {
    const current = hasCurrentStoryboardApproval(value as StoryboardReview, revision, dirty);
    expect(current).toBe(false);
    expect(text({ approvalCurrent: current })).toContain("前往分镜审核");
    expect(text({ approvalCurrent: current })).not.toContain("读取当前来源");
  }
});
it.each(["outcome_unknown", "dispatching", "submitted", "retrieve_needed", "prepared"] as const)("names the next %s action without duplicate preparation", state => {
  const job = selectedJob("request", 1, { state, selected: false, playbackSegment: null });
  const hint = text({ jobs: [job] });
  expect(hint).toContain(state === "prepared" ? "提交一次" : state === "submitted" || state === "retrieve_needed" ? "获取结果" : "不要重新提交");
  expect(hint).not.toContain("读取当前来源");
});
it("keeps original, preview, selected shot and complete routes distinct", () => {
  const job = selectedJob("request", 1, { selected: false, playbackSegment: null, segments: [] });
  expect(text({ jobs: [job] })).toContain("准备播放片段");
  expect(text({ jobs: [{ ...job, segments: [selectedJob("request", 1).playbackSegment!] }] })).toContain("预览片段");
  const selected = selectedJob("selected", 1);
  expect(text({ jobs: [selected] })).toContain("完整路线仍缺少已选片段");
  expect(text({ jobs: [{ ...selected, inputStatus: "stale", current: false }] })).toContain("旧选择不会进入故事播放");
  expect(text({ allRoutesReady: true })).toContain("实际核对问题、选项与每个结局");
  expect(text({ allRoutesReady: true })).toContain("不代表播放已验收");
});
