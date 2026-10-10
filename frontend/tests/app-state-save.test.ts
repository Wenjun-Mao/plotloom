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

  it("creates a complete canonical prefix when saving a teaching sample brief", async () => {
      const incoming = creationResponse("sample-project", demoProject.brief.title, {
        story_bible: demoProject.storyBible,
        story_graph: demoProject.storyGraph,
        scene_beats: demoProject.sceneBeats,
        storyboard: demoProject.storyboard,
      });
      const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: incoming.stages });

      await renderSample(root);
      await act(async () => button("保存并继续到来源").click());
      await flush();
      expect(window.location.search).toContain("stage=source");
      await act(async () => button("故事圣经").click());

      expect(create).toHaveBeenCalledWith({
        brief: demoProject.brief,
        initialStages: [
          { stage: "story_bible", payload: demoProject.storyBible },
          { stage: "story_graph", payload: demoProject.storyGraph },
          { stage: "scene_beats", payload: demoProject.sceneBeats },
          { stage: "storyboard", payload: demoProject.storyboard },
        ],
      }, expect.any(String));
      const logline = document.querySelector(".form-card textarea") as HTMLTextAreaElement;
      expect(logline.value).toBe(demoProject.storyBible.logline);
      expect(document.querySelectorAll(".character-card")).not.toHaveLength(0);
      expect(plotloomApi.getProject).toHaveBeenCalledWith("sample-project", expect.any(AbortSignal));
      expect(plotloomApi.getStages).toHaveBeenCalledWith("sample-project", expect.any(AbortSignal));
    });

  it("does not let delayed first-save Gate hydration retire a newer stage save", async () => {
      const created = creationResponse("gate-race-project", demoProject.brief.title, {
        story_bible: demoProject.storyBible,
        story_graph: demoProject.storyGraph,
        scene_beats: demoProject.sceneBeats,
        storyboard: demoProject.storyboard,
      });
      const delayedReview = deferred<never>();
      const delayedPatch = deferred<StageEnvelope["head"]>();
      vi.spyOn(plotloomApi, "createProject").mockResolvedValue(created);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(created);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: created.stages });
      vi.spyOn(plotloomApi, "getStoryboardReview")
        .mockReturnValueOnce(delayedReview.promise)
        .mockResolvedValue(null as never);
      vi.spyOn(plotloomApi, "patchStage").mockReturnValue(delayedPatch.promise);

      await renderSample(root);
      await act(async () => button("分镜工作台").click());
      await act(async () => button("保存分镜").click());
      await flush();
      window.history.pushState(null, "", "/?project=gate-race-project&stage=bible");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();
      const logline = document.querySelector(".form-card textarea") as HTMLTextAreaElement;
      await act(async () => setInput(logline, "新路由中的未完成保存"));
      await act(async () => button("保存故事圣经").click());
      expect(plotloomApi.patchStage).toHaveBeenCalledOnce();
      await flush();
      expect(button("正在保存…").disabled).toBe(true);

      await act(async () => delayedReview.resolve({} as never));
      await flush();

      expect(window.location.search).toContain("project=gate-race-project");
      expect(window.location.search).toContain("stage=bible");
      expect((document.querySelector(".form-card textarea") as HTMLTextAreaElement).value).toBe("新路由中的未完成保存");
      expect(button("正在保存…").disabled).toBe(true);
      await act(async () => delayedPatch.resolve(created.stages[0]!.head));
    });

  it("creates a clean source-first project without initial stages and loads its canonical route", async () => {
      const created = creationResponse("brief-project", "干净简报");
      const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(created);
      const loadProject = vi.spyOn(plotloomApi, "getProject").mockResolvedValue(created);
      const loadStages = vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: created.stages });

      await renderBlank(root);
      const title = document.querySelector(".form-card input") as HTMLInputElement;
      await act(async () => setInput(title, "干净简报"));
      await act(async () => setInput(document.querySelector(".form-card textarea") as HTMLTextAreaElement, "干净项目的可编辑梗概。"));
      await act(async () => button("保存并继续到来源").click());
      await flush();

      expect(create).toHaveBeenCalledWith({ brief: expect.objectContaining({ title: "干净简报" }) }, expect.any(String));
      expect(loadProject).toHaveBeenCalledWith("brief-project", expect.any(AbortSignal));
      expect(loadStages).toHaveBeenCalledWith("brief-project", expect.any(AbortSignal));
      expect(window.location.search).toBe("?project=brief-project&stage=source");
      expect(window.location.hash).toBe("#source");
      expect(document.body.textContent).toContain("brief-project");
    });

  it("creates the canonical prefix when a stage is saved before the brief", async () => {
      const stagedBible = { ...demoProject.storyBible, logline: "本地编辑的圣经草稿" };
      const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(creationResponse("stage-project", demoProject.brief.title, { story_bible: stagedBible }));
      const loadProject = vi.spyOn(plotloomApi, "getProject");
      const loadStages = vi.spyOn(plotloomApi, "getStages");

      await renderSample(root);
      await act(async () => button("故事圣经").click());
      await flush();
      const logline = document.querySelector(".form-card textarea") as HTMLTextAreaElement;
      await act(async () => setInput(logline, stagedBible.logline));
      await act(async () => button("保存故事圣经").click());
      await flush();

      expect(create).toHaveBeenCalledWith({
        brief: demoProject.brief,
        initialStages: [{ stage: "story_bible", payload: stagedBible }],
      }, expect.any(String));
      expect(loadProject).not.toHaveBeenCalled();
      expect(loadStages).not.toHaveBeenCalled();
    });

  it("allows only one synchronous first-save flight and exposes saving state", async () => {
      const pending = deferred<ProjectCreationResponse>();
      const create = vi.spyOn(plotloomApi, "createProject").mockReturnValue(pending.promise);

      await renderSample(root);
      await act(async () => {
        button("保存并继续到来源").click();
        button("保存并继续到来源").click();
      });

      expect(create).toHaveBeenCalledOnce();
      const savingButton = button("保存中…");
      expect(savingButton.disabled).toBe(true);
      await act(async () => pending.resolve(creationResponse("single-flight", demoProject.brief.title)));
      await flush();
    });

  it("reuses an idempotency key for an identical failed first-save body and changes it with the draft", async () => {
      const create = vi.spyOn(plotloomApi, "createProject")
        .mockRejectedValueOnce(new TypeError("network unavailable"))
        .mockRejectedValueOnce(new TypeError("network unavailable"))
        .mockRejectedValueOnce(new TypeError("network unavailable"));

      await renderBlank(root);
      const title = document.querySelector(".form-card input") as HTMLInputElement;
      await act(async () => setInput(title, "相同请求"));
      await act(async () => setInput(document.querySelector(".form-card textarea") as HTMLTextAreaElement, "幂等请求梗概。"));
      await act(async () => button("保存并继续到来源").click());
      await flush();
      const firstKey = create.mock.calls[0][1];

      await act(async () => button("保存并继续到来源").click());
      await flush();
      expect(create.mock.calls[1][1]).toBe(firstKey);

      await act(async () => setInput(title, "已修改的请求"));
      await act(async () => button("保存并继续到来源").click());
      await flush();
      expect(create.mock.calls[2][1]).not.toBe(firstKey);
      expect(create.mock.calls[2][0]).toEqual({ brief: expect.objectContaining({ title: "已修改的请求" }) });
    });

  it("keeps a failed first-save draft, URL, and retry affordance intact", async () => {
      const create = vi.spyOn(plotloomApi, "createProject")
        .mockRejectedValueOnce(new TypeError("offline"))
        .mockResolvedValueOnce(creationResponse("retry-project", "保留草稿"));

      await renderSample(root);
      const title = document.querySelector(".form-card input") as HTMLInputElement;
      await act(async () => setInput(title, "保留草稿"));
      await act(async () => button("保存并继续到来源").click());
      await flush();

      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("保留草稿");
      expect(window.location.search).toBe("?stage=brief");
      expect(document.body.textContent).toContain("尚未保存的项目草稿");
      expect(button("保存并继续到来源").disabled).toBe(false);

      await act(async () => button("保存并继续到来源").click());
      await flush();
      expect(create).toHaveBeenCalledTimes(2);
      expect(window.location.search).toBe("?project=retry-project&stage=source");
      expect(window.location.hash).toBe("#source");
    });

  it("retains the same creation key until the canonical response is installed", async () => {
      const incomplete = {
        ...resource("incomplete-response", demoProject.brief.title),
        stages: undefined,
      } as unknown as ProjectCreationResponse;
      const create = vi.spyOn(plotloomApi, "createProject")
        .mockResolvedValueOnce(incomplete)
        .mockResolvedValueOnce(creationResponse("replayed-project", demoProject.brief.title));

      await renderSample(root);
      await act(async () => button("保存并继续到来源").click());
      await flush();

      expect(window.location.search).toBe("?stage=brief");
      const firstKey = create.mock.calls[0][1];
      await act(async () => button("保存并继续到来源").click());
      await flush();

      expect(create.mock.calls[1][1]).toBe(firstKey);
      expect(window.location.search).toBe("?project=replayed-project&stage=source");
      expect(window.location.hash).toBe("#source");
    });

  it("keeps existing-project PATCH revisions and 409 conflict feedback unchanged", async () => {
      window.history.replaceState(null, "", "/?project=existing-project");
      const incoming = resource("existing-project", "现有项目", 7);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      const patch = vi.spyOn(plotloomApi, "patchProject").mockRejectedValue(new ApiError("revision changed", 409, { code: "revision_conflict" }));
      const create = vi.spyOn(plotloomApi, "createProject");

      await act(async () => root.render(createElement(App)));
      await flush();
      const title = document.querySelector(".form-card input") as HTMLInputElement;
      await act(async () => setInput(title, "本地冲突修改"));
      await act(async () => button("保存修改").click());
      await flush();

      expect(create).not.toHaveBeenCalled();
      expect(patch).toHaveBeenCalledWith("existing-project", 7, expect.objectContaining({ title: "本地冲突修改" }));
      expect(document.body.textContent).toContain("项目版本冲突：revision changed");
    });

  it("keeps a canonical stage save live while entity focus only changes the URL", async () => {
      window.history.replaceState(null, "", "/?project=entity-save-project&stage=beats");
      const incoming = resource("entity-save-project", "实体焦点保存", 7);
      const pending = deferred<StageEnvelope["head"]>();
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes({ scene_beats: demoProject.sceneBeats }) });
      const patch = vi.spyOn(plotloomApi, "patchStage").mockReturnValue(pending.promise);

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => setInput(document.querySelector(".beat-card textarea") as HTMLTextAreaElement, "实体焦点不应取消保存"));
      await act(async () => button("保存节拍").click());
      await act(async () => button("诊断双重故障").click());
      expect(new URLSearchParams(window.location.search).get("entity")).toBe("scene:scene_diagnose");

      await act(async () => pending.resolve({ ...stageEnvelopes({ scene_beats: demoProject.sceneBeats })[2].head, stage: "scene_beats", revision: 2, status: "ready" }));
      await flush();

      expect(patch).toHaveBeenCalledWith("entity-save-project", "scene_beats", 1, expect.objectContaining({ beats: expect.any(Array) }));
      expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain("entity-save-project:scene_beats:1");
      expect(button("保存节拍").disabled).toBe(false);
    });

});
