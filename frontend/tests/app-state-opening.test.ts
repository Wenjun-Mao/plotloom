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

  it("shows an explicit welcome instead of installing the sample project by default", async () => {
      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("从一个项目开始");
      expect(document.body.textContent).not.toContain(demoProject.brief.title);
      expect(document.querySelector(".form-card")).toBeNull();

      await act(async () => button("打开示例项目").click());
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe(demoProject.brief.title);
    });

  it("clears inherited entity and run query state when opening sample or blank workspaces", async () => {
      window.history.replaceState(null, "", "/?stage=bible&entity=old-entity&run=old-run");
      vi.spyOn(plotloomApi, "listProjects").mockResolvedValue({ projects: [], nextCursor: null });

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("打开示例项目").click());
      expect(window.location.search).toBe("?stage=bible");
      await act(async () => button("当前项目").click());
      await flush();
      await act(async () => button("新建空白项目").click());
      expect(window.location.search).toBe("?stage=bible");
    });

  it("selects a Story Bible entity from any character-card focus", async () => {
      window.history.replaceState(null, "", "/?stage=bible");
      await renderSample(root);

      await act(async () => button("查看此角色").click());
      expect(new URLSearchParams(window.location.search).get("entity")).toBe("bible:character:char_ruanxing");
    });

  it("appends stable directory pages using the server cursor", async () => {
      const statuses = { story_bible: "missing" as const, story_graph: "missing" as const, scene_beats: "missing" as const, storyboard: "missing" as const };
      const first = { ...resource("directory-one", "目录项目一"), stageStatuses: statuses, latestRun: null };
      const second = { ...resource("directory-two", "目录项目二"), stageStatuses: statuses, latestRun: null };
      const list = vi.spyOn(plotloomApi, "listProjects")
        .mockResolvedValueOnce({ projects: [first], nextCursor: "after-one" })
        .mockResolvedValueOnce({ projects: [second], nextCursor: null });

      await act(async () => root.render(createElement(App)));
      await flush();
      await act(async () => button("打开项目目录").click());
      await flush();
      expect(document.body.textContent).toContain("目录项目一");
      await act(async () => button("加载更多项目").click());
      await flush();

      expect(document.body.textContent).toContain("目录项目一");
      expect(document.body.textContent).toContain("目录项目二");
      expect(list).toHaveBeenNthCalledWith(1, false, 50, undefined);
      expect(list).toHaveBeenNthCalledWith(2, false, 50, "after-one");
    });

  it("installs a recovered session draft into the editor after the user confirms restore", async () => {
      const restoredTitle = "恢复到编辑器的草稿标题";
      window.history.replaceState(null, "", "/?project=recovery-project");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "recovery-project:brief:1": {
          key: "recovery-project:brief:1", projectId: "recovery-project", scope: "brief", baseRevision: 1,
          payload: { ...demoProject.brief, title: restoredTitle }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      const incoming = resource("recovery-project", "服务器标题", 1);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

      await act(async () => root.render(createElement(App)));
      await flush();
      expect(document.body.textContent).toContain("发现可恢复草稿");

      await act(async () => button("恢复草稿").click());
      await flush();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe(restoredTitle);
    });

  it("shows a discard-only notice for a draft from an older server revision", async () => {
      window.history.replaceState(null, "", "/?project=conflict-project");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "conflict-project:brief:6": {
          key: "conflict-project:brief:6", projectId: "conflict-project", scope: "brief", baseRevision: 6,
          payload: { ...demoProject.brief, title: "不可恢复的旧草稿" }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      const incoming = resource("conflict-project", "服务器新版本", 7);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("草稿版本已过期");
      expect(document.body.textContent).not.toContain("恢复草稿");
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("服务器新版本");
    });

  it("keeps archived drafts inspectable without restore authority", async () => {
      window.history.replaceState(null, "", "/?project=archived-draft-project");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "archived-draft-project:brief:7": {
          key: "archived-draft-project:brief:7", projectId: "archived-draft-project", scope: "brief", baseRevision: 7,
          payload: { ...demoProject.brief, title: "归档时的草稿" }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      const incoming = { ...resource("archived-draft-project", "已归档项目", 7), lifecycleStatus: "archived" as const, archivedAt: "2026-09-03T00:00:00Z" };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("归档项目草稿不可恢复");
      expect(document.body.textContent).not.toContain("恢复草稿");
    });

  it("routes archived-draft popstate through discard-only instead of save-and-switch", async () => {
      window.history.replaceState(null, "", "/?project=archived-pop-project&stage=brief");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "archived-pop-project:brief:7": {
          key: "archived-pop-project:brief:7", projectId: "archived-pop-project", scope: "brief", baseRevision: 7,
          payload: { ...demoProject.brief, title: "归档草稿" }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      const incoming = { ...resource("archived-pop-project", "归档 popstate", 7), lifecycleStatus: "archived" as const, archivedAt: "2026-09-03T00:00:00Z" };
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

      await act(async () => root.render(createElement(App)));
      await flush();
      window.history.replaceState(null, "", "/?project=archived-pop-project&stage=bible");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      expect(document.body.textContent).toContain("归档项目草稿不可恢复");
      expect(document.body.textContent).not.toContain("保存并切换");
      await act(async () => button("丢弃不可用草稿").click());
      await flush();
      expect(document.body.textContent).toContain("故事圣经");
    });

  it("does not silently substitute the teaching sample when a requested project cannot load", async () => {
      window.history.replaceState(null, "", "/?project=missing-project");
      vi.spyOn(plotloomApi, "getProject").mockRejectedValue(new Error("not found"));

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("本次读取未完成");
      expect(document.body.textContent).toContain("没有回退到示例");
      expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).not.toBeNull();
      expect(document.querySelector(".editor-host")).toBeNull();
      expect(document.body.textContent).not.toContain("尚未保存的项目草稿");
    });

  it("retains inspectable drafts when project authority is temporarily unavailable", async () => {
      window.history.replaceState(null, "", "/?project=deleted-project");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "deleted-project:brief:4": {
          key: "deleted-project:brief:4", projectId: "deleted-project", scope: "brief", baseRevision: 4,
          payload: { ...demoProject.brief, title: "已删除项目的草稿" }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      vi.spyOn(plotloomApi, "getProject").mockRejectedValue(new Error("not found"));

      await act(async () => root.render(createElement(App)));
      await flush();

      expect(document.body.textContent).toContain("暂时无法核实项目，草稿已保留");
      expect(document.body.textContent).not.toContain("恢复草稿");
      await act(async () => button("丢弃不可用草稿").click());
      expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain("deleted-project:brief:4");
    });

  it("allows explicit discard of unavailable drafts before popstate", async () => {
      window.history.replaceState(null, "", "/?project=unavailable-pop&stage=brief");
      window.sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({
        "unavailable-pop:brief:4": {
          key: "unavailable-pop:brief:4", projectId: "unavailable-pop", scope: "brief", baseRevision: 4,
          payload: { ...demoProject.brief, title: "无法加载的草稿" }, updatedAt: "2026-09-03T00:00:00Z",
        },
      }));
      vi.spyOn(plotloomApi, "getProject").mockRejectedValue(new Error("not found"));

      await act(async () => root.render(createElement(App)));
      await flush();
      window.history.replaceState(null, "", "/?stage=bible");
      await act(async () => window.dispatchEvent(new PopStateEvent("popstate")));
      await flush();

      expect(document.body.textContent).toContain("暂时无法核实项目，草稿已保留");
      expect(document.body.textContent).not.toContain("保存并切换");
      await act(async () => button("丢弃不可用草稿").click());
      await flush();
      expect(document.body.textContent).toContain("故事圣经");
    });

  it("remounts a demo-initialized editor with the asynchronously loaded project and preserves later unsaved edits", async () => {
      window.history.replaceState(null, "", "/?project=real-project");
      const incoming = resource("real-project", "服务器项目", 7);
      vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
      vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
      const patch = vi.spyOn(plotloomApi, "patchProject").mockImplementation(async (_id, _revision, brief) => ({ ...incoming, brief, revision: 8 }));

      await act(async () => root.render(createElement(App)));
      await flush();

      const title = document.querySelector(".form-card input") as HTMLInputElement;
      expect(title.value).toBe("服务器项目");
      await act(async () => setInput(title, "尚未保存的用户修改"));
      await act(async () => button("供应商与会话密钥").click());
      await flush();
      expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("尚未保存的用户修改");

      await act(async () => button("保存修改").click());
      await flush();
      expect(patch).toHaveBeenCalledWith("real-project", 7, expect.objectContaining({ title: "尚未保存的用户修改" }));
    });

});
