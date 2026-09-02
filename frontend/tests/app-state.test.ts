import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { ApiError, plotloomApi } from "../src/api";
import { defaultProviderSettings, demoProject, demoRun } from "../src/demo";
import type { MediaTask, ProjectCreationResponse, ProjectResource, RunTrace, ServerStageName, StageEnvelope } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function resource(id: string, title: string, revision = 1): ProjectResource {
  return {
    id,
    revision,
    brief: { ...demoProject.brief, title },
    createdAt: "2026-08-30T00:00:00Z",
    updatedAt: "2026-08-30T00:00:00Z",
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

    await act(async () => root.render(createElement(App)));
    await flush();
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

    await act(async () => root.render(createElement(App)));
    await flush();
    const title = document.querySelector(".form-card input") as HTMLInputElement;
    await act(async () => setInput(title, "干净简报"));
    await act(async () => button("保存简报").click());
    await flush();

    expect(create).toHaveBeenCalledWith({ brief: expect.objectContaining({ title: "干净简报" }) }, expect.any(String));
    expect(loadProject).not.toHaveBeenCalled();
    expect(loadStages).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?project=brief-project");
    expect(document.body.textContent).toContain("brief-project");
  });

  it("creates the canonical prefix when a stage is saved before the brief", async () => {
    const stagedBible = { ...demoProject.storyBible, logline: "本地编辑的圣经草稿" };
    const create = vi.spyOn(plotloomApi, "createProject").mockResolvedValue(creationResponse("stage-project", demoProject.brief.title, { story_bible: stagedBible }));
    const loadProject = vi.spyOn(plotloomApi, "getProject");
    const loadStages = vi.spyOn(plotloomApi, "getStages");

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => button("故事圣经").click());
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

    await act(async () => root.render(createElement(App)));
    await flush();
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

    await act(async () => root.render(createElement(App)));
    await flush();
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

    await act(async () => root.render(createElement(App)));
    await flush();
    const title = document.querySelector(".form-card input") as HTMLInputElement;
    await act(async () => setInput(title, "保留草稿"));
    await act(async () => button("保存简报").click());
    await flush();

    expect((document.querySelector(".form-card input") as HTMLInputElement).value).toBe("保留草稿");
    expect(window.location.search).toBe("");
    expect(document.body.textContent).toContain("unsaved teaching draft");
    expect(button("保存简报").disabled).toBe(false);

    await act(async () => button("保存简报").click());
    await flush();
    expect(create).toHaveBeenCalledTimes(2);
    expect(window.location.search).toBe("?project=retry-project");
  });

  it("retains the same creation key until the canonical response is installed", async () => {
    const incomplete = {
      ...resource("incomplete-response", demoProject.brief.title),
      stages: undefined,
    } as unknown as ProjectCreationResponse;
    const create = vi.spyOn(plotloomApi, "createProject")
      .mockResolvedValueOnce(incomplete)
      .mockResolvedValueOnce(creationResponse("replayed-project", demoProject.brief.title));

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => button("保存简报").click());
    await flush();

    expect(window.location.search).toBe("");
    const firstKey = create.mock.calls[0][1];
    await act(async () => button("保存简报").click());
    await flush();

    expect(create.mock.calls[1][1]).toBe(firstKey);
    expect(window.location.search).toBe("?project=replayed-project");
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

  it("restores the newest quarantined run, its trace evidence, and repair context after refresh", async () => {
    window.history.replaceState(null, "", "/?project=restore-project");
    const incoming = resource("restore-project", "恢复项目");
    const run = { ...demoRun, id: "run-restored", projectId: incoming.id, status: "quarantined" as const, requestedStages: ["story_bible" as const] };
    const trace: RunTrace = {
      run,
      attempts: [{ id: "attempt-restored", runId: run.id, stage: "story_bible", attemptNumber: 1, status: "failed", provider: null, model: null, error: "刷新后仍可见的合同错误", startedAt: "2026-08-30T00:00:00Z", finishedAt: "2026-08-30T00:00:01Z" }],
      artifacts: [
        { id: "response-restored", runId: run.id, attemptId: "attempt-restored", sourceArtifactId: null, stage: "story_bible", kind: "response", mediaType: "application/json", content: { rawResponse: "original response" }, contentHash: "response", createdAt: "2026-08-30T00:00:00Z" },
        { id: "validation-restored", runId: run.id, attemptId: "attempt-restored", sourceArtifactId: null, stage: "story_bible", kind: "validation", mediaType: "application/json", content: { issue: "missing premise" }, contentHash: "abc", createdAt: "2026-08-30T00:00:01Z" },
      ],
      snapshotIsCurrent: true,
    };
    vi.spyOn(plotloomApi, "getProject").mockResolvedValue(incoming);
    vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: stageEnvelopes() });
    vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [run] });
    vi.spyOn(plotloomApi, "getTrace").mockResolvedValue(trace);

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => button("隔离修复").click());

    expect(document.body.textContent).toContain("刷新后仍可见的合同错误");
    expect(document.body.textContent).toContain("提交修复");
    await act(async () => button("运行轨迹").click());
    expect(document.body.textContent).toContain("run-restored");
    await act(async () => button("Payload").click());
    expect(document.body.textContent).toContain("missing premise");
  });

  it("rehydrates a succeeded keyframe and passes it as the required video source", async () => {
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
    const startMedia = vi.spyOn(plotloomApi, "startMediaTask").mockResolvedValue(mediaTask({ id: "video-task", kind: "video", status: "succeeded", outputUri: "https://assets.example/shot-01.mp4", startedAt: "2026-08-30T00:00:01Z", finishedAt: "2026-08-30T00:00:02Z" }));

    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => button("分镜工作台").click());
    await act(async () => button("生成视频").click());
    await flush();

    expect(startMedia).toHaveBeenCalledWith("media-project", "shot_01", "video", { sourceUri: "https://assets.example/shot-01.png" });
  });

  it("blocks video generation with a clear error until a keyframe succeeds", async () => {
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
    await act(async () => button("生成视频").click());

    expect(startMedia).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("请先为这个镜头生成成功的关键帧");
  });

  it("explains when a server key is available and a session key is only an override", async () => {
    vi.mocked(plotloomApi.getProviderSettings).mockResolvedValue({ ...defaultProviderSettings, textKeyAvailable: true });
    await act(async () => root.render(createElement(App)));
    await flush();
    await act(async () => button("供应商与会话 Key").click());
    await flush();

    expect(document.body.textContent).toContain("服务器已配置文本密钥");
    expect(document.body.textContent).toContain("填写则仅覆盖当前标签页");
  });
});
