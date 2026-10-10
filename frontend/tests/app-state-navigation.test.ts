import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { fallbackProfiles } from "../src/app/workspace/useTextProviderProfiles";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject, demoRun } from "../src/demo";
import type { MediaTask, ProjectCreationResponse, ProjectListItem, ProjectResource, RunProgress, RunTrace, ServerStageName, StageEnvelope } from "../src/types";
import { button, creationResponse, deferred, flush, mediaTask, renderBlank, renderSample, resource, setInput, stageEnvelopes } from "./app-state-fixtures";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("App project/editor rehydration", () => {

  let root: Root;

  beforeEach(() => {
      vi.restoreAllMocks();
      window.sessionStorage.clear();
      window.history.replaceState(null, "", "/");
      document.body.innerHTML = '<div id="test-root"></div>';
      root = createRoot(document.getElementById("test-root")!);
      vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [] });
      vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [] });
      vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue(fallbackProfiles());
      vi.spyOn(plotloomApi, "getRuntimeCapabilities").mockResolvedValue({
        durableProjectDrafts: false, durableMediaDrafts: false, explicitProjectClose: false,
        portableSnapshots: false, apiTextPipeline: true,
      });
    });

  afterEach(async () => {
      await act(async () => root.unmount());
    });

  it("does not substitute the latest run when the URL requests a missing run", async () => {
      window.history.replaceState(null, "", "/?project=run-project&stage=trace&run=foreign-run");
      const incoming = resource("run-project", "运行选择");
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [{ ...demoRun, id: "latest-run", projectId: incoming.id, status: "succeeded" }] });
      const trace = vi.spyOn(plotloomApi, "getTrace");

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("运行 foreign-run 不属于当前项目或已不存在");
      expect(document.body.textContent).not.toContain("latest-run");
      expect(trace).not.toHaveBeenCalled();
    });

  it("clears an accepted old-stage draft without repainting a workspace selected mid-save", async () => {
      window.history.replaceState(null, "", "/?project=old-stage-project&stage=beats");
      const source = resource("old-stage-project", "旧节拍项目", 7);
      const destination = resource("new-stage-project", "新工作台", 3);
      const pending = deferred<StageEnvelope["head"]>();
      vi.spyOn(plotloomApi, "getProject").mockImplementation(async (id) => id === source.id ? source : destination);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes({ scene_beats: demoProject.sceneBeats }) });
      vi.spyOn(plotloomApi, "patchStage").mockReturnValue(pending.promise);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".beat-card textarea") as HTMLTextAreaElement, "服务端会接受的旧保存"));
      await act(async () => button("保存节拍").click());
      window.history.replaceState(null, "", "/?project=new-stage-project&stage=brief");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      await act(async () => button("丢弃").click());
      await flush();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("新工作台");

      await act(async () => pending.resolve({ ...stageEnvelopes({ scene_beats: demoProject.sceneBeats })[2].head, stage: "scene_beats", revision: 2, status: "ready" }));
      await flush();

      expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain("old-stage-project:scene_beats:1");
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("新工作台");
    });

  it("reloads canonical stage data when returning to the same project after a stale accepted save", async () => {
      window.history.replaceState(null, "", "/?project=refresh-stage-project&stage=beats");
      const incoming = resource("refresh-stage-project", "回访刷新", 7);
      const pending = deferred<StageEnvelope["head"]>();
      const canonicalPlan = { ...demoProject.sceneBeats, beats: demoProject.sceneBeats.beats.map((beat) => beat.id === "b1" ? { ...beat, description: "服务器 revision 2" } : beat) };
      const firstStages = stageEnvelopes({ scene_beats: demoProject.sceneBeats });
      const refreshedStages = stageEnvelopes({ scene_beats: canonicalPlan });
      refreshedStages[2] = { ...refreshedStages[2], head: { ...refreshedStages[2].head, revision: 2 } };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      const getStages = vi.spyOn(plotloomApi, "getStages").mockResolvedValueOnce({ stages: firstStages }).mockResolvedValueOnce({ stages: refreshedStages });
      vi.spyOn(plotloomApi, "patchStage").mockReturnValue(pending.promise);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".beat-card textarea") as HTMLTextAreaElement, "旧路由中的保存"));
      await act(async () => button("保存节拍").click());
      await act(async () => button("故事圣经").click());
      await flush();
      await act(async () => button("丢弃").click());
      await flush();
      await act(async () => pending.resolve({ ...firstStages[2].head, revision: 2, status: "ready" }));
      await flush();

      await act(async () => button("场景节拍").click());
      await flush();

      expect(getStages).toHaveBeenCalledTimes(2);
      expect((document.querySelector(".beat-card textarea") as HTMLTextAreaElement).value).toBe("服务器 revision 2");
      expect(button("保存节拍").disabled).toBe(false);
    });

  it("immediately refreshes when a user returns to the source project before its accepted save resolves", async () => {
      window.history.replaceState(null, "", "/?project=reverse-source&stage=beats");
      const source = resource("reverse-source", "返回源项目", 7);
      const destination = resource("reverse-destination", "中转项目", 3);
      const pending = deferred<StageEnvelope["head"]>();
      const canonicalPlan = { ...demoProject.sceneBeats, beats: demoProject.sceneBeats.beats.map((beat) => beat.id === "b1" ? { ...beat, description: "回访后的服务器 revision 2" } : beat) };
      const firstStages = stageEnvelopes({ scene_beats: demoProject.sceneBeats });
      const returnedBeforeSave = stageEnvelopes({ scene_beats: demoProject.sceneBeats });
      const canonicalStages = stageEnvelopes({ scene_beats: canonicalPlan });
      canonicalStages[2] = { ...canonicalStages[2], head: { ...canonicalStages[2].head, revision: 2 } };
      vi.spyOn(plotloomApi, "getProject").mockImplementation(async (id) => id === source.id ? source : destination);
      const getStages = vi.spyOn(plotloomApi, "getStages")
        .mockResolvedValueOnce({ stages: firstStages })
        .mockResolvedValueOnce({ stages: stageEnvelopes() })
        .mockResolvedValueOnce({ stages: returnedBeforeSave })
        .mockResolvedValueOnce({ stages: canonicalStages });
      vi.spyOn(plotloomApi, "patchStage").mockReturnValue(pending.promise);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".beat-card textarea") as HTMLTextAreaElement, "延迟接受的保存"));
      await act(async () => button("保存节拍").click());
      window.history.replaceState(null, "", "/?project=reverse-destination&stage=brief");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      await act(async () => button("丢弃").click());
      await flush();
      window.history.replaceState(null, "", "/?project=reverse-source&stage=beats");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      await act(async () => pending.resolve({ ...firstStages[2].head, revision: 2, status: "ready" }));
      await flush();

      expect(getStages).toHaveBeenCalledTimes(4);
      expect((document.querySelector(".beat-card textarea") as HTMLTextAreaElement).value).toBe("回访后的服务器 revision 2");
      expect(button("保存节拍").disabled).toBe(false);
    });

  it("does not let a delayed PATCH repaint a project selected after the save began", async () => {
      window.history.replaceState(null, "", "/?project=save-source");
      const source = resource("save-source", "保存来源", 7);
      const destination = resource("save-destination", "切换后的项目", 3);
      const pendingPatch = deferred<ProjectResource>();
      vi.spyOn(plotloomApi, "getProject").mockImplementation(async (id) => id === source.id ? source : destination);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "listProjects").mockResolvedValue({ projects: [destination], nextCursor: null });
      vi.spyOn(plotloomApi, "patchProject").mockReturnValue(pendingPatch.promise);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".form-card input") as HTMLInputElement, "旧项目的延迟保存"));
      await act(async () => button("保存修改").click());
      await act(async () => button("当前项目").click());
      await flush();
      await act(async () => button("切换后的项目").click());
      await flush();
      expect(document.body.textContent).toContain("保存当前草稿？");
      await act(async () => button("丢弃").click());
      await flush();
      expect(window.location.search).toContain("stage=creator");
      expect(document.body.textContent).toContain("切换后的项目");

      await act(async () => pendingPatch.resolve({ ...source, revision: 8, brief: { ...source.brief, title: "旧项目的延迟保存" } }));
      await flush();
      await act(async () => button("项目简报与创作设置").click());
      await flush();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("切换后的项目");
      expect(window.location.search).toContain("project=save-destination");
    });

  it("requires a dirty-draft decision before archiving the current project", async () => {
      window.history.replaceState(null, "", "/?project=archive-project");
      const incoming = resource("archive-project", "待归档项目", 7);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "listProjects").mockResolvedValue({ projects: [incoming], nextCursor: null });
      const archive = vi.spyOn(plotloomApi, "archiveProject").mockResolvedValue({ ...incoming, lifecycleRevision: 2, lifecycleStatus: "archived", archivedAt: "2026-09-03T00:00:00Z" });

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".form-card input") as HTMLInputElement, "未保存的归档前修改"));
      await flush();
      expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain("未保存的归档前修改");
      expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain("archive-project:brief:7");
      await act(async () => button("当前项目").click());
      await flush();
      const archiveButton = [...document.querySelectorAll("button")].find((candidate) => candidate.textContent === "归档") as HTMLButtonElement;
      await act(async () => archiveButton.click());
      await flush();

      expect(document.body.textContent).toContain("归档前保存当前修改？");
      expect(document.body.textContent).toContain("已保存的草稿仍保留");
      expect(archive).not.toHaveBeenCalled();
      await act(async () => button("丢弃本页修改并归档").click());
      await flush();
      expect(archive).toHaveBeenCalledWith("archive-project", 1);
    });

  it("restores the visible route when a dirty popstate navigation is cancelled", async () => {
      await renderSample(root);
      await act(async () => setInput(document.querySelector(".form-card input") as HTMLInputElement, "保留当前路由的草稿"));
      await flush();

      window.history.pushState(null, "", "/?stage=bible");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      expect(document.body.textContent).toContain("保存当前草稿？");
      await act(async () => button("取消").click());
      await flush();

      expect(window.location.search).toBe("?stage=brief");
      expect(document.body.textContent).toContain("项目简报");
    });

  it("restores quarantined work-unit status without loading evidence until the trace page opens", async () => {
      window.history.replaceState(null, "", "/?project=restore-project");
      const incoming = resource("restore-project", "恢复项目");
      const run = { ...demoRun, id: "run-restored", projectId: incoming.id, status: "quarantined" as const, requestedStages: ["story_bible" as const] };
      const trace: RunTrace = {
        run,
        attempts: [{ id: "attempt-restored", runId: run.id, workUnitId: null, stage: "story_bible", attemptNumber: 1, attemptKind: "primary", sourceAttemptId: null, status: "failed", provider: null, model: null, error: "刷新后仍可见的合同错误", dispatchedAt: null, responsePersistedAt: null, providerRequestId: null, outcomeUnknown: false, outcomeCode: "schema_invalid", startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z" }],
        artifacts: [
          { id: "response-restored", runId: run.id, attemptId: "attempt-restored", workUnitId: null, sourceArtifactId: null, stage: "story_bible", kind: "response", mediaType: "application/json", content: { rawResponse: "original response" }, contentHash: "response", createdAt: "2026-08-30T00:00:00Z" },
          { id: "validation-restored", runId: run.id, attemptId: "attempt-restored", workUnitId: null, sourceArtifactId: null, stage: "story_bible", kind: "validation", mediaType: "application/json", content: { issue: "missing premise" }, contentHash: "abc", createdAt: "2026-08-30T00:00:01Z" },
        ],
        snapshotIsCurrent: true,
      };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [run] });
      const progress: RunProgress = {
        runId: run.id, status: "quarantined", failureCode: "schema_invalid", failedStage: "story_bible", stageProgress: [],
        workUnits: [{
          workUnitId: "unit-restored", stage: "story_bible", sequence: 1, status: "quarantined", maxAttempts: 3,
          latestAttempt: { attemptId: "attempt-restored", attemptNumber: 3, attemptKind: "correction", sourceAttemptId: "attempt-2", status: "failed", outcomeCode: "schema_invalid", outcomeUnknown: false, startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z", inputTokens: 10, outputTokens: 20, durationMs: 1000 },
          sealed: false, repairEligible: true, repairReasonCode: null,
        }],
        actions: { canResume: false, canCancel: false, canRebuildStage: true, repairEligible: true },
      };
      vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue(progress);
      const getTrace = vi.spyOn(plotloomApi, "getTrace").mockResolvedValue(trace);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("隔离修复").click());

      expect(getTrace).not.toHaveBeenCalled();
      expect(document.body.textContent).toContain("unit-restored");
      expect(document.body.textContent).toContain("重新执行此子任务");
      await act(async () => button("运行轨迹").click());
      await flush();
      expect(getTrace).toHaveBeenCalledWith("run-restored");
      expect(document.body.textContent).toContain("run-restored");
      await act(async () => button("事件数据").click());
      expect(document.body.textContent).toContain("missing premise");
    });

  it("reloads the run selected by same-project browser history", async () => {
      window.history.replaceState(null, "", "/?project=history-project&stage=trace&run=run-one");
      const incoming = resource("history-project", "运行历史项目");
      const runOne = { ...demoRun, id: "run-one", projectId: incoming.id, status: "succeeded" as const };
      const runTwo = { ...demoRun, id: "run-two", projectId: incoming.id, status: "quarantined" as const };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [runTwo, runOne] });
      vi.spyOn(plotloomApi, "getRunProgress").mockImplementation(async (runId) => ({
        runId,
        status: runId === runOne.id ? "succeeded" : "quarantined",
        failureCode: null,
        failedStage: null,
        stageProgress: [],
        workUnits: [],
        actions: { canResume: false, canCancel: false, canRebuildStage: false, repairEligible: false },
      }));
      const getTrace = vi.spyOn(plotloomApi, "getTrace").mockImplementation(async (runId) => ({
        run: runId === runOne.id ? runOne : runTwo,
        attempts: [], artifacts: [], snapshotIsCurrent: true,
      }));

      await act(async () => root.render(createElement(App)));
      await flush();
      expect(document.body.textContent).toContain("run-one");
      expect(getTrace).toHaveBeenCalledTimes(1);
      await flush();
      // A valid but empty provenance response is still a loaded response.
      // Do not spin on it merely because the rendered event list has length 0.
      expect(getTrace).toHaveBeenCalledTimes(1);

      window.history.replaceState(null, "", "/?project=history-project&stage=trace&run=run-two");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      expect(getTrace).toHaveBeenCalledWith("run-two");
      expect(document.body.textContent).toContain("run-two");
    });

  it("loads latest-run provenance when a trace URL omits an explicit run id", async () => {
      window.history.replaceState(null, "", "/?project=implicit-run-project&stage=trace");
      const incoming = resource("implicit-run-project", "默认运行项目");
      const latest = { ...demoRun, id: "latest-run", projectId: incoming.id, status: "succeeded" as const };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [latest] });
      vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({
        runId: latest.id, status: "succeeded", failureCode: null, failedStage: null, stageProgress: [], workUnits: [],
        actions: { canResume: false, canCancel: false, canRebuildStage: false, repairEligible: false },
      });
      const getTrace = vi.spyOn(plotloomApi, "getTrace").mockResolvedValue({ run: latest, attempts: [], artifacts: [], snapshotIsCurrent: true });

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(getTrace).toHaveBeenCalledWith("latest-run");
      expect(document.body.textContent).toContain("latest-run");
    });

});
