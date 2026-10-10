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

  it("keeps historical media readable while disabling new production tasks", async () => {
      window.history.replaceState(null, "", "/?project=media-project");
      const incoming = resource("media-project", "媒体项目");
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes({
        story_bible: demoProject.storyBible,
        story_graph: demoProject.storyGraph,
        scene_beats: demoProject.sceneBeats,
        storyboard: demoProject.storyboard,
      }) });
      vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [mediaTask({ id: "image-task", status: "succeeded", outputUri: "https://assets.example/shot-01.png", startedAt: "2026-08-30T00:00:01Z", finishedAt: "2026-08-30T00:00:02Z" })] });
      const startMedia = vi.spyOn(plotloomApi, "startMediaTask");

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("分镜工作台").click());
      expect(document.body.textContent).toContain("媒体工作流");
      expect(document.body.textContent).toContain("未配置视频后端时仍可查看已有候选");
      expect(startMedia).not.toHaveBeenCalled();
    });

  it("does not expose a client-side media enqueue action without a ProductionSnapshot", async () => {
      window.history.replaceState(null, "", "/?project=no-source-project");
      const incoming = resource("no-source-project", "无关键帧项目");
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes({
        story_bible: demoProject.storyBible,
        story_graph: demoProject.storyGraph,
        scene_beats: demoProject.sceneBeats,
        storyboard: demoProject.storyboard,
      }) });
      const startMedia = vi.spyOn(plotloomApi, "startMediaTask");

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("分镜工作台").click());
      expect(document.body.textContent).toContain("图片：查看关键帧与参考素材");
      expect(document.body.textContent).toContain("视频：在上方工作台审核片段");
      expect(startMedia).not.toHaveBeenCalled();
      expect(document.body.textContent).toContain("覆盖检查与分镜批准");
      expect(document.body.textContent).toContain("尚无可查看的历史关键帧任务提示词");
    });

  it("explains when a server key is available and a session key is only an override", async () => {
      const catalog = fallbackProfiles(); catalog.profiles[0].serverKeyAvailable = true;
      vi.mocked(plotloomApi.getTextProviderProfiles).mockResolvedValue(catalog);
      await renderSample(root);
      await act(async () => button("供应商与会话密钥").click());
      await flush();

      expect(document.body.textContent).toContain("服务器已配置文本密钥");
      expect(document.body.textContent).toContain("填写则仅覆盖当前标签页");
    });

  it("flushes the selected profile before generating and never includes its session key in the save", async () => {
      window.history.replaceState(null, "", "/?project=profile-project");
      const incoming = resource("profile-project", "Profile save before generate");
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      const savedProfile = {
        ...fallbackProfiles().profiles[0],
        profileId: "default", displayName: "Default", revision: 1, createdAt: "", updatedAt: "", serverKeyAvailable: false,
        adapterId: "openai_compatible", adapterVersion: "1",
        configuration: { ...fallbackProfiles().profiles[0].configuration, profileId: "default", textModel: "model", textAuthMode: "bearer" },
      } as never;
      vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue({
        ...fallbackProfiles(),
        profiles: [savedProfile], activeProfileId: "default", selectionRevision: 0, presets: {},
      } as never);
      const saveProfile = vi.spyOn(plotloomApi, "updateTextProviderProfile").mockResolvedValue(savedProfile);
      const startRun = vi.spyOn(plotloomApi, "startRun").mockResolvedValue({ ...demoRun, id: "profile-run", projectId: "profile-project", status: "queued" });
      window.sessionStorage.setItem("plotloom:provider-session-keys", JSON.stringify({ default: "never-in-profile-json" }));

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("运行轨迹").click());
      await act(async () => button("运行所选阶段").click());
      await flush();

      expect(saveProfile).toHaveBeenCalledBefore(startRun);
      expect(saveProfile.mock.calls[0].some((value) => JSON.stringify(value).includes("never-in-profile-json"))).toBe(false);
      expect(startRun).toHaveBeenCalledWith("profile-project", ["story_bible", "story_graph", "scene_beats", "storyboard"], "default", true);
      expect(window.location.search).toBe("?project=profile-project&stage=trace&run=profile-run");
    });

  it("does not submit generation after navigation invalidates a pending profile save", async () => {
      window.history.replaceState(null, "", "/?project=source-project&stage=trace");
      const source = resource("source-project", "旧工作台");
      const destination = resource("destination-project", "新工作台");
      vi.spyOn(plotloomApi, "getProject").mockImplementation(async (id) => id === source.id ? source : destination);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      const savedProfile = {
        ...fallbackProfiles().profiles[0],
        profileId: "default", displayName: "Default", revision: 1, createdAt: "", updatedAt: "", serverKeyAvailable: false,
        adapterId: "openai_compatible", adapterVersion: "1",
        configuration: { ...fallbackProfiles().profiles[0].configuration, profileId: "default", textModel: "model", textAuthMode: "none" },
      } as never;
      vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue({
        ...fallbackProfiles(),
        profiles: [savedProfile], activeProfileId: "default", selectionRevision: 0, presets: {},
      } as never);
      const pendingProfileSave = deferred<Awaited<ReturnType<typeof plotloomApi.updateTextProviderProfile>>>();
      vi.spyOn(plotloomApi, "updateTextProviderProfile").mockReturnValue(pendingProfileSave.promise);
      const startRun = vi.spyOn(plotloomApi, "startRun");

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("运行所选阶段").click());
      window.history.replaceState(null, "", "/?project=destination-project&stage=brief");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      await act(async () => pendingProfileSave.resolve(savedProfile));
      await flush();

      expect(startRun).not.toHaveBeenCalled();
      expect(window.location.search).toContain("project=destination-project");
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("新工作台");
    });

  it("aborts and rejects a late aggregate hydration after navigation chooses another project", async () => {
      window.history.replaceState(null, "", "/?project=hydrate-source&stage=brief");
      const source = resource("hydrate-source", "过期加载来源");
      const destination = resource("hydrate-destination", "当前规范项目");
      const delayedSource = deferred<ProjectResource>();
      let sourceSignal: AbortSignal | undefined;
      vi.spyOn(plotloomApi, "getProject").mockImplementation((id, signal) => {
        if (id === source.id) {
          sourceSignal = signal;
          return delayedSource.promise;
        }
        return Promise.resolve(destination);
      });
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

      await act(async () => root.render(createElement(App)));
      await flush();
      expect(sourceSignal?.aborted).toBe(false);

      window.history.replaceState(null, "", "/?project=hydrate-destination&stage=brief");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      expect(sourceSignal?.aborted).toBe(true);
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("当前规范项目");

      await act(async () => delayedSource.resolve(source));
      await flush();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("当前规范项目");
      expect(document.body.textContent).not.toContain("过期加载来源");
    });

  it("clears an old selected run before deferred same-project trace history hydration", async () => {
      const projectId = "trace-history-project";
      const firstRun = { ...demoRun, id: "trace-run-one", projectId, status: "running" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const secondRun = { ...demoRun, id: "trace-run-two", projectId, status: "running" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const delayedRuns = deferred<Awaited<ReturnType<typeof plotloomApi.getProjectRuns>>>();
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace&run=${firstRun.id}`);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(resource(projectId, "运行历史项目"));
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns")
        .mockResolvedValueOnce({ runs: [firstRun, secondRun] })
        .mockReturnValueOnce(delayedRuns.promise);
      vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({
        runId: firstRun.id, status: "running", failureCode: null, failedStage: null,
        stageProgress: [], workUnits: [], actions: { canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false },
      });
      vi.spyOn(plotloomApi, "getTrace").mockResolvedValue({ run: firstRun, attempts: [], artifacts: [], snapshotIsCurrent: true });
      vi.spyOn(plotloomApi, "getRunExecutionTrace").mockResolvedValue(undefined as never);
      vi.spyOn(plotloomApi, "resumeRun").mockResolvedValue(firstRun);
      const cancel = vi.spyOn(plotloomApi, "cancelRun");

      await act(async () => root.render(createElement(App)));
      await flush();
      await flush();
      expect(document.body.textContent).toContain(firstRun.id);
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace&run=${secondRun.id}`);
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      expect(document.querySelector('[data-testid="workspace-hydrating"]')).not.toBeNull();
      expect([...document.querySelectorAll("button")].some((candidate) => candidate.textContent?.includes("取消运行"))).toBe(false);
      expect(cancel).not.toHaveBeenCalled();

      await act(async () => delayedRuns.resolve({ runs: [firstRun, secondRun] }));
      await flush();
      expect(document.body.textContent).toContain(secondRun.id);
      expect(cancel).not.toHaveBeenCalled();
    });

  it("cancels an abandoned trace selection before returning to an implicit trace route", async () => {
      const projectId = "abandoned-trace-history-project";
      const firstRun = { ...demoRun, id: "trace-run-a", projectId, status: "running" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const secondRun = { ...demoRun, id: "trace-run-b", projectId, status: "succeeded" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const initialRuns = deferred<Awaited<ReturnType<typeof plotloomApi.getProjectRuns>>>();
      const abandonedRuns = deferred<Awaited<ReturnType<typeof plotloomApi.getProjectRuns>>>();
      const returningRuns = deferred<Awaited<ReturnType<typeof plotloomApi.getProjectRuns>>>();
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace&run=${firstRun.id}`);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(resource(projectId, "放弃运行选择项目"));
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      const getRuns = vi.spyOn(plotloomApi, "getProjectRuns")
        .mockReturnValueOnce(initialRuns.promise)
        .mockReturnValueOnce(abandonedRuns.promise)
        .mockReturnValueOnce(returningRuns.promise);
      vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({
        runId: firstRun.id, status: "running", failureCode: null, failedStage: null,
        stageProgress: [], workUnits: [], actions: { canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false },
      });
      vi.spyOn(plotloomApi, "resumeRun").mockResolvedValue(firstRun);

      await act(async () => root.render(createElement(App)));
      await flush();
      expect(getRuns).toHaveBeenCalledOnce();
      await act(async () => initialRuns.resolve({ runs: [firstRun, secondRun] }));
      await flush();
      expect(document.querySelector(".context-panel")?.textContent).toContain("放弃运行选择项目");
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace&run=${secondRun.id}`);
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      expect(document.querySelector('[data-testid="workspace-hydrating"]')).not.toBeNull();

      window.history.replaceState(null, "", `/?project=${projectId}&stage=brief`);
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      expect(document.querySelector(".project-brief-navigation[aria-current=page]")?.textContent).toContain("项目简报");
      expect(document.querySelector(".context-panel")?.textContent).toContain("放弃运行选择项目");
      expect(document.querySelector('[data-testid="workspace-hydrating"]')).toBeNull();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("放弃运行选择项目");

      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace`);
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      expect(document.querySelector('[data-testid="workspace-hydrating"]')).not.toBeNull();

      await act(async () => abandonedRuns.resolve({ runs: [firstRun, secondRun] }));
      await flush();
      expect(document.querySelector('[data-testid="workspace-hydrating"]')).not.toBeNull();

      await act(async () => returningRuns.resolve({ runs: [secondRun, firstRun] }));
      await flush();
      expect(document.querySelector('[data-testid="workspace-hydrating"]')).toBeNull();
      expect(document.body.textContent).toContain(secondRun.id);
    });

  it("hydrates an implicit latest-run trace selection before allowing new run commands", async () => {
      const projectId = "implicit-trace-history-project";
      const firstRun = { ...demoRun, id: "explicit-history-run", projectId, status: "running" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const latestRun = { ...demoRun, id: "implicit-latest-run", projectId, status: "succeeded" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" as const } };
      const delayedRuns = deferred<Awaited<ReturnType<typeof plotloomApi.getProjectRuns>>>();
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace&run=${firstRun.id}`);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(resource(projectId, "隐式运行历史项目"));
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns")
        .mockResolvedValueOnce({ runs: [firstRun, latestRun] })
        .mockReturnValueOnce(delayedRuns.promise);
      vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({
        runId: firstRun.id, status: "running", failureCode: null, failedStage: null,
        stageProgress: [], workUnits: [], actions: { canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false },
      });
      vi.spyOn(plotloomApi, "getTrace").mockResolvedValue({ run: firstRun, attempts: [], artifacts: [], snapshotIsCurrent: true });
      vi.spyOn(plotloomApi, "getRunExecutionTrace").mockResolvedValue(undefined as never);
      vi.spyOn(plotloomApi, "resumeRun").mockResolvedValue(firstRun);
      const start = vi.spyOn(plotloomApi, "startRun");

      await act(async () => root.render(createElement(App)));
      await flush();
      window.history.replaceState(null, "", `/?project=${projectId}&stage=trace`);
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      expect(document.querySelector('[data-testid="workspace-hydrating"]')).not.toBeNull();
      expect([...document.querySelectorAll("button")].some((candidate) => candidate.textContent?.includes("运行所选阶段"))).toBe(false);
      expect(start).not.toHaveBeenCalled();

      await act(async () => delayedRuns.resolve({ runs: [latestRun, firstRun] }));
      await flush();
      expect(document.body.textContent).toContain(latestRun.id);
      expect(start).not.toHaveBeenCalled();
    });

  it("rejects a late run-poll projection after Back/Forward changes the project session", async () => {
      window.history.replaceState(null, "", "/?project=poll-source&stage=trace");
      const source = resource("poll-source", "轮询源项目");
      const destination = resource("poll-destination", "轮询目标项目");
      const activeRun = { ...demoRun, id: "late-poll-run", projectId: source.id, status: "running" as const, providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" } };
      const lateProgress = deferred<RunProgress>();
      vi.spyOn(plotloomApi, "getProject").mockImplementation(async (id) => id === source.id ? source : destination);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      vi.spyOn(plotloomApi, "getProjectRuns").mockImplementation(async (id) => ({ runs: id === source.id ? [activeRun] : [] }));
      vi.spyOn(plotloomApi, "getRunProgress")
        .mockResolvedValueOnce({ runId: activeRun.id, status: "running", failureCode: null, failedStage: null, stageProgress: [], workUnits: [], actions: { canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false } })
        .mockReturnValueOnce(lateProgress.promise);
      vi.spyOn(plotloomApi, "resumeRun").mockResolvedValue(activeRun);

      await act(async () => root.render(createElement(App)));
      await flush();
      await flush();
      window.history.replaceState(null, "", "/?project=poll-destination&stage=brief");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      await act(async () => lateProgress.resolve({ runId: activeRun.id, status: "quarantined", failureCode: "late.poll", failedStage: "story_bible", stageProgress: [], workUnits: [{ workUnitId: "late-unit", stage: "story_bible", sequence: 1, status: "quarantined", maxAttempts: 1, latestAttempt: null, sealed: false, repairEligible: false, repairReasonCode: null }], actions: { canResume: false, canCancel: false, canRebuildStage: false, repairEligible: false } }));
      await flush();

      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("轮询目标项目");
      expect(document.body.textContent).not.toContain("late-unit");
      expect(document.body.textContent).not.toContain("late.poll");
    });

});
