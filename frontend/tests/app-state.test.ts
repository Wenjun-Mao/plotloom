import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { ApiError, plotloomApi } from "../src/api";
import { defaultProviderSettings, demoProject, demoRun } from "../src/demo";
import type { MediaTask, ProjectCreationResponse, ProjectListItem, ProjectResource, RunProgress, RunTrace, ServerStageName, StageEnvelope } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function resource(id: string, title: string, revision = 1): ProjectListItem {
  return {
    id,
    revision,
    brief: { ...demoProject.brief, title },
    lifecycleRevision: 1,
    lifecycleStatus: "active",
    archivedAt: null,
    createdAt: "2026-08-30T00:00:00Z",
    updatedAt: "2026-08-30T00:00:00Z",
    stageStatuses: { story_bible: "missing", story_graph: "missing", scene_beats: "missing", storyboard: "missing" },
    latestRun: null,
  };
}

function mediaTask(overrides: Partial<MediaTask>): MediaTask {
  return {
    id: "task",
    projectId: "media-project",
    shotId: "shot_01",
    storyboardRevision: 1,
    kind: "image",
    status: "queued",
    derivedPrompt: "prompt",
    promptComponents: {},
    provider: "fixture",
    publicSettings: {},
    providerTaskId: null,
    outputUri: null,
    error: null,
    createdAt: "2026-08-30T00:00:00Z",
    updatedAt: "2026-08-30T00:00:00Z",
    startedAt: null,
    finishedAt: null,
    ...overrides,
  };
}

function stageEnvelopes(payloads: Partial<Record<ServerStageName, unknown>> = {}): StageEnvelope[] {
  return (["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map((stage) => ({
    head: {
      stage,
      revision: payloads[stage] == null ? 0 : 1,
      status: payloads[stage] == null ? "missing" : "ready",
      entityRevisionId: payloads[stage] == null ? null : `${stage}-r1`,
      contentHash: payloads[stage] == null ? null : `${stage}-hash`,
      schemaVersion: 2,
      inputRevisions: {},
      staleReasons: [],
      updatedAt: "2026-08-30T00:00:00Z",
    },
    payload: payloads[stage] ?? null,
  }));
}

function creationResponse(
  id: string,
  title: string,
  payloads: Partial<Record<ServerStageName, unknown>> = {},
  revision = 1,
): ProjectCreationResponse {
  return { ...resource(id, title, revision), stages: stageEnvelopes(payloads) };
}

function button(label: string): HTMLButtonElement {
  const found = [...document.querySelectorAll("button")].find((candidate) => candidate.textContent?.includes(label));
  if (!found) throw new Error(`Button not found: ${label}`);
  return found as HTMLButtonElement;
}

function setInput(input: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => window.setTimeout(resolve, 0));
  });
}

async function renderSample(root: Root): Promise<void> {
  await act(async () => root.render(createElement(App)));
  await flush();
  await act(async () => button("打开示例项目").click());
  await flush();
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

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
    vi.spyOn(plotloomApi, "getProviderSettings").mockResolvedValue(defaultProviderSettings);
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

    await act(async () => (document.querySelector(".character-card textarea") as HTMLTextAreaElement).focus());
    expect(window.location.search).toContain("entity=char_ruanxing");
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
    expect(document.body.textContent).toContain("发现未保存草稿");

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

  it("offers only discard when an archived project still has a session draft", async () => {
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

    expect(document.body.textContent).toContain("项目未加载");
    expect(document.body.textContent).toContain("没有回退到示例");
    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("");
  });

  it("offers only safe discard for drafts whose project cannot be loaded", async () => {
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

    expect(document.body.textContent).toContain("项目不可用，草稿不可恢复");
    expect(document.body.textContent).not.toContain("恢复草稿");
    await act(async () => button("丢弃不可用草稿").click());
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain("deleted-project:brief:4");
  });

  it("routes unavailable-project popstate through discard-only", async () => {
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

    expect(document.body.textContent).toContain("项目不可用，草稿不可恢复");
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
    await act(async () => button("供应商与会话 Key").click());
    await flush();
    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("尚未保存的用户修改");

    await act(async () => button("保存简报").click());
    await flush();
    expect(patch).toHaveBeenCalledWith("real-project", 7, expect.objectContaining({ title: "尚未保存的用户修改" }));
  });

  it("replaces tutorial stages with empty contracts from an empty creation response", async () => {
    const incoming = creationResponse("empty-project", demoProject.brief.title);
    vi.spyOn(plotloomApi, "createProject").mockResolvedValue(incoming);
    vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
    vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });

    await renderSample(root);
    await act(async () => button("保存简报").click());
    await flush();
    await act(async () => button("故事圣经").click());

    const logline = document.querySelector(".form-card textarea") as HTMLTextAreaElement;
    expect(logline.value).toBe("");
    expect(document.querySelectorAll(".character-card")).toHaveLength(0);
    expect(plotloomApi.getProject).not.toHaveBeenCalled();
    expect(plotloomApi.getStages).not.toHaveBeenCalled();
  });

  it("creates a clean unsaved brief without initial stages and hydrates only from the create response", async () => {
    const created = creationResponse("brief-project", "干净简报");
    const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(created);
    const loadProject = vi.spyOn(plotloomApi, "getProject");
    const loadStages = vi.spyOn(plotloomApi, "getStages");

    await renderSample(root);
    const title = document.querySelector(".form-card input") as HTMLInputElement;
    await act(async () => setInput(title, "干净简报"));
    await act(async () => button("保存简报").click());
    await flush();

    expect(create).toHaveBeenCalledWith({ brief: expect.objectContaining({ title: "干净简报" }) }, expect.any(String));
    expect(loadProject).not.toHaveBeenCalled();
    expect(loadStages).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?stage=brief&project=brief-project");
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
      button("保存简报").click();
      button("保存简报").click();
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

    await renderSample(root);
    const title = document.querySelector(".form-card input") as HTMLInputElement;
    await act(async () => setInput(title, "相同请求"));
    await act(async () => button("保存简报").click());
    await flush();
    const firstKey = create.mock.calls[0][1];

    await act(async () => button("保存简报").click());
    await flush();
    expect(create.mock.calls[1][1]).toBe(firstKey);

    await act(async () => setInput(title, "已修改的请求"));
    await act(async () => button("保存简报").click());
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
    await act(async () => button("保存简报").click());
    await flush();

    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("保留草稿");
    expect(window.location.search).toBe("?stage=brief");
    expect(document.body.textContent).toContain("unsaved teaching draft");
    expect(button("保存简报").disabled).toBe(false);

    await act(async () => button("保存简报").click());
    await flush();
    expect(create).toHaveBeenCalledTimes(2);
    expect(window.location.search).toBe("?stage=brief&project=retry-project");
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
    await act(async () => button("保存简报").click());
    await flush();

    expect(window.location.search).toBe("?stage=brief");
    const firstKey = create.mock.calls[0][1];
    await act(async () => button("保存简报").click());
    await flush();

    expect(create.mock.calls[1][1]).toBe(firstKey);
    expect(window.location.search).toBe("?stage=brief&project=replayed-project");
  });

  it("keeps existing-project PATCH revisions and 409 conflict feedback unchanged", async () => {
    window.history.replaceState(null, "", "/?project=existing-project");
    const incoming = resource("existing-project", "现有项目", 7);
    vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
    vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
    const patch = vi.spyOn(plotloomApi, "patchProject").mockRejectedValue(new ApiError("revision changed", 409));
    const create = vi.spyOn(plotloomApi, "createProject");

    await act(async () => root.render(createElement(App)));
    await flush();
    const title = document.querySelector(".form-card input") as HTMLInputElement;
    await act(async () => setInput(title, "本地冲突修改"));
    await act(async () => button("保存简报").click());
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
    expect(window.location.search).toContain("entity=scene_diagnose");

    await act(async () => pending.resolve({ ...stageEnvelopes({ scene_beats: demoProject.sceneBeats })[2].head, stage: "scene_beats", revision: 2, status: "ready" }));
    await flush();

    expect(patch).toHaveBeenCalledWith("entity-save-project", "scene_beats", 1, expect.objectContaining({ beats: expect.any(Array) }));
    expect(window.sessionStorage.getItem("plotloom:workbench-drafts:v1")).not.toContain("entity-save-project:scene_beats:1");
    expect(button("保存节拍").disabled).toBe(false);
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
    await act(async () => button("保存简报").click());
    await act(async () => button("当前项目").click());
    await flush();
    await act(async () => button("切换后的项目").click());
    await flush();
    expect(document.body.textContent).toContain("保存当前草稿？");
    await act(async () => button("丢弃").click());
    await flush();
    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("切换后的项目");

    await act(async () => pendingPatch.resolve({ ...source, revision: 8, brief: { ...source.brief, title: "旧项目的延迟保存" } }));
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

    expect(document.body.textContent).toContain("保存当前草稿？");
    expect(archive).not.toHaveBeenCalled();
    await act(async () => button("丢弃").click());
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
    expect(document.body.textContent).toContain("修复这个 work unit");
    await act(async () => button("运行轨迹").click());
    await flush();
    expect(getTrace).toHaveBeenCalledWith("run-restored");
    expect(document.body.textContent).toContain("run-restored");
    await act(async () => button("Payload").click());
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
    expect(document.body.textContent).toContain("媒体生产尚未开放");
    expect(document.body.textContent).toContain("现有媒体结果保持可读");
    expect(button("视频生产未就绪").disabled).toBe(true);
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
    expect(button("图片生产未就绪").disabled).toBe(true);
    expect(button("视频生产未就绪").disabled).toBe(true);
    expect(startMedia).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("Approval");
    expect(document.body.textContent).toContain("ProductionSnapshot");
  });

  it("explains when a server key is available and a session key is only an override", async () => {
    vi.mocked(plotloomApi.getProviderSettings).mockResolvedValue({ ...defaultProviderSettings, textKeyAvailable: true });
    await renderSample(root);
    await act(async () => button("供应商与会话 Key").click());
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
      profileId: "default", displayName: "Default", revision: 1, createdAt: "", updatedAt: "", serverKeyAvailable: false,
      configuration: { profileId: "default", textModel: "model", textAuthMode: "bearer" },
    } as never;
    vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue({
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
      profileId: "default", displayName: "Default", revision: 1, createdAt: "", updatedAt: "", serverKeyAvailable: false,
      configuration: { profileId: "default", textModel: "model", textAuthMode: "none" },
    } as never;
    vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue({
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
});
