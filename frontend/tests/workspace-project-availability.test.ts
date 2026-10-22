import {act, createElement} from "react";
import {createRoot, type Root} from "react-dom/client";
import {afterEach, beforeEach, expect, it, vi} from "vitest";
import App from "../src/App";
import {ApiError, plotloomApi} from "../src/api";
import {demoProject, demoRun} from "../src/demo";
import {fallbackProfiles} from "../src/app/workspace/useTextProviderProfiles";
import type {ProjectResource, RunProgress, ServerStageName, StageEnvelope} from "../src/types";

(globalThis as typeof globalThis & {IS_REACT_ACT_ENVIRONMENT: boolean}).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
const project: ProjectResource = {id: "a", revision: 3, brief: {...demoProject.brief, title: "已保存的项目"},
  lifecycleRevision: 1, lifecycleStatus: "active", archivedAt: null, createdAt: "2026-10-08", updatedAt: "2026-10-08"};
const closed = () => new ApiError("project is closed", 409, {code: "project_closed"});
const button = (name: string) => {
  const found = [...document.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent?.trim() === name);
  if (!found) throw new Error(`Missing button ${name}`);
  return found;
};
const flush = async () => {await act(async () => {await new Promise(resolve => window.setTimeout(resolve, 0));});};
const render = async (url: string) => {
  window.history.replaceState(null, "", url);
  await act(async () => root.render(createElement(App)));
  await flush();
};
const envelopes = (): StageEnvelope[] => (["story_bible", "story_graph", "scene_beats", "storyboard"] as ServerStageName[]).map(stage => ({
  head: {stage, revision: 1, status: "ready", entityRevisionId: `${stage}-r1`, contentHash: `${stage}-hash`,
    schemaVersion: 2, inputRevisions: {}, staleReasons: [], updatedAt: "2026-10-08"},
  payload: stage === "story_bible" ? demoProject.storyBible : stage === "story_graph" ? demoProject.storyGraph
    : stage === "scene_beats" ? demoProject.sceneBeats : demoProject.storyboard,
}));
beforeEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
  document.body.innerHTML = '<div id="test-root"></div>';
  root = createRoot(document.getElementById("test-root")!);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(project);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({stages: []});
  vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({runs: []});
  vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({tasks: []});
  vi.spyOn(plotloomApi, "getStoryboardReview").mockRejectedValue(new ApiError("No storyboard review", 404));
  vi.spyOn(plotloomApi, "getRuntimeCapabilities").mockResolvedValue({durableProjectDrafts: false, explicitProjectClose: true, portableSnapshots: true, durableMediaDrafts: true, apiTextPipeline: true});
  vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue(fallbackProfiles());
  vi.spyOn(plotloomApi, "listProjects").mockResolvedValue({projects: [], nextCursor: null});
});
afterEach(async () => {await act(async () => root.unmount()); vi.restoreAllMocks();});

it("does not expose or request API profiles when the service explicitly omits them", async () => {
  vi.mocked(plotloomApi.getRuntimeCapabilities).mockResolvedValue({
    durableProjectDrafts: false, durableMediaDrafts: false, explicitProjectClose: true,
    portableSnapshots: true, apiTextPipeline: false,
  });
  await render("/?project=a&stage=brief");
  expect(document.body.textContent).toContain("API 文本供应商未启用");
  expect([...document.querySelectorAll("button")].some(item => item.textContent === "供应商与会话密钥")).toBe(false);
  expect(document.body.textContent).not.toContain("readiness.not_checked");
  expect(plotloomApi.getTextProviderProfiles).not.toHaveBeenCalled();
  expect(button("生成助手设置")).toBeTruthy();
  expect([...document.querySelectorAll("button")].some(item => item.textContent === "生成故事提案")).toBe(false);
  expect(document.body.textContent).toContain("请在来源与大纲中使用生成助手");
});

it.each(["failed", "running"] as const)("retains the native %s run on Trace without generic run/progress/profile requests", async status => {
  vi.mocked(plotloomApi.getRuntimeCapabilities).mockResolvedValue({durableProjectDrafts: false, durableMediaDrafts: false,
    explicitProjectClose: true, portableSnapshots: true, apiTextPipeline: false});
  const run = {...demoRun, projectId: "a", status};
  vi.mocked(plotloomApi.getProjectRuns).mockResolvedValue({runs: [run]});
  const progress = vi.spyOn(plotloomApi, "getRunProgress"), trace = vi.spyOn(plotloomApi, "getTrace");
  const execution = vi.spyOn(plotloomApi, "getRunExecutionTrace"), resume = vi.spyOn(plotloomApi, "resumeRun");
  const save = vi.spyOn(plotloomApi, "patchProject");
  await render(`/?project=a&stage=trace&run=${run.id}`);
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.querySelector(".run-console")?.textContent).toContain(run.id);
  expect(document.body.textContent).toContain("保留的 API 运行仅显示摘要");
  for (const request of [progress, trace, execution, resume, save, plotloomApi.getTextProviderProfiles]) expect(request).not.toHaveBeenCalled();
  for (const label of ["运行所选阶段", "继续排队运行", "取消运行", "从失败阶段完整重建"])
    expect([...document.querySelectorAll("button")].some(item => item.textContent === label)).toBe(false);
});

it("keeps failed capabilities unknown and retries explicitly without a provider fallback", async () => {
  const capabilities = vi.mocked(plotloomApi.getRuntimeCapabilities).mockRejectedValueOnce(new ApiError("offline", 503));
  await render("/?project=a&stage=brief");
  expect(document.body.textContent).toContain("暂时无法读取服务功能");
  expect(document.body.textContent).not.toContain("API 文本供应商未启用");
  expect(plotloomApi.getTextProviderProfiles).not.toHaveBeenCalled();
  expect(capabilities).toHaveBeenCalledTimes(1);
  capabilities.mockResolvedValue({ durableProjectDrafts: false, durableMediaDrafts: false,
    explicitProjectClose: true, portableSnapshots: true, apiTextPipeline: true });
  await act(async () => button("重新读取服务功能").click());
  await flush();
  await act(async () => button("供应商与会话密钥").click());
  await flush();
  expect(capabilities).toHaveBeenCalledTimes(2);
  expect(plotloomApi.getTextProviderProfiles).toHaveBeenCalledTimes(1);
  expect(document.querySelector("dialog[open]")).not.toBeNull();
});

it("keeps a closed shot link unavailable without claiming a missing shot or unsaved draft", async () => {
  vi.mocked(plotloomApi.getProject).mockRejectedValue(closed());
  const open = vi.spyOn(plotloomApi, "openProjectFolder");
  const create = vi.spyOn(plotloomApi, "createProject");
  const patch = vi.spyOn(plotloomApi, "patchProject");
  const url = "/?project=a&stage=storyboard&entity=shot%3Aone#shot-workbench";
  await render(url);
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).not.toBeNull();
  expect(document.querySelector(".editor-host")).toBeNull();
  expect(document.body.textContent).toContain("项目已关闭");
  for (const text of ["尚未保存的项目草稿", "请求的镜头不属于当前分镜", "先保存项目", "未命名项目"]) expect(document.body.textContent).not.toContain(text);
  expect(location.search + location.hash).toBe(url.slice(1));
  await act(async () => document.querySelector<HTMLButtonElement>('[aria-label="关闭错误"]')!.click());
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).not.toBeNull();
  await act(async () => button("打开项目目录").click());
  await flush();
  expect(document.body.textContent).toContain("项目目录");
  expect(open).not.toHaveBeenCalled();
  expect(create).not.toHaveBeenCalled();
  expect(patch).not.toHaveBeenCalled();
});

it.each([404, 503])("distinguishes authoritative HTTP%s without showing a blank editor", async status => {
  vi.mocked(plotloomApi.getProject).mockRejectedValue(new ApiError("read evidence", status));
  await render("/?project=a&stage=brief");
  expect(document.querySelector(".editor-host")).toBeNull();
  expect(document.body.textContent).toContain(status === 404 ? "找不到这个项目" : "暂时无法读取项目");
  expect(document.body.textContent).toContain("当前链接与页面位置仍保留");
  expect(document.body.textContent).not.toContain("镜头位置");
  if (status === 503) expect(document.body.textContent).not.toContain("服务器确认当前项目目录中没有");
});

it("retry reads the same exact deep-linked shot without automatically opening or saving", async () => {
  const shot = demoProject.storyboard.shots[0]!;
  vi.mocked(plotloomApi.getProject).mockRejectedValueOnce(closed());
  vi.mocked(plotloomApi.getStages).mockResolvedValue({stages: envelopes()});
  const open = vi.spyOn(plotloomApi, "openProjectFolder"), patch = vi.spyOn(plotloomApi, "patchProject");
  const url = `/?project=a&stage=storyboard&entity=${encodeURIComponent(`shot:${shot.id}`)}#shot-workbench`;
  await render(url);
  await act(async () => button("重新读取项目").click());
  await flush();
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.querySelector(".editor-host")).not.toBeNull();
  const shotSelect = [...document.querySelectorAll<HTMLSelectElement>("select")].find(item => [...item.options].some(option => option.value === shot.id));
  expect(shotSelect?.value).toBe(shot.id);
  expect(document.querySelector('[data-testid="unknown-storyboard-entity"]')).toBeNull();
  expect(location.search + location.hash).toBe(url.slice(1));
  expect(open).not.toHaveBeenCalled(); expect(patch).not.toHaveBeenCalled();
});

it.each(["queued", "running"] as const)("explicit reread does not resume a %s generation run", async status => {
  vi.mocked(plotloomApi.getProject).mockRejectedValueOnce(new ApiError("read unavailable", 503));
  vi.mocked(plotloomApi.getProjectRuns).mockResolvedValue({runs: [{...demoRun, projectId: "a", status}]});
  vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({
    runId: demoRun.id, status, failureCode: null, failedStage: null, stageProgress: [], workUnits: [],
    actions: {canResume: true, canCancel: true, canRebuildStage: false, repairEligible: false},
  } satisfies RunProgress);
  const resume = vi.spyOn(plotloomApi, "resumeRun");
  await render("/?project=a&stage=brief");
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).not.toBeNull();
  await act(async () => button("重新读取项目").click());
  await flush();
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.querySelector(".editor-host")).not.toBeNull();
  expect(plotloomApi.getRunProgress).toHaveBeenCalledWith(demoRun.id);
  expect(resume).not.toHaveBeenCalled();
});

it("still reports a genuinely missing shot after successful authoritative load", async () => {
  vi.mocked(plotloomApi.getStages).mockResolvedValue({stages: envelopes()});
  await render("/?project=a&stage=storyboard&entity=shot%3Areally-missing#shot-workbench");
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.querySelector('[data-testid="unknown-storyboard-entity"]')).not.toBeNull();
});

it("keeps the same accepted editor mounted during a pending and failed refresh", async () => {
  await render("/?project=a&stage=brief");
  const input = document.querySelector<HTMLInputElement>(".form-card input")!;
  expect(input.value).toBe("已保存的项目");
  let reject!: (error: Error) => void;
  vi.mocked(plotloomApi.getProject).mockReturnValueOnce(new Promise((_, fail) => {reject = fail;}));
  await act(async () => button("刷新服务器版本").click());
  await flush();
  expect(document.querySelector(".form-card input")).toBe(input);
  expect(document.querySelector<HTMLFieldSetElement>(".editor-host")?.disabled).toBe(true);
  await act(async () => reject(new ApiError("refresh unavailable", 503)));
  await flush();
  expect(document.querySelector(".form-card input")).toBe(input);
  expect(input.value).toBe("已保存的项目");
  expect(document.querySelector<HTMLFieldSetElement>(".editor-host")?.disabled).toBe(true);
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.body.textContent).toContain("本次读取未完成");
  expect(document.body.textContent).not.toContain("项目未加载");
  expect(document.querySelector("#workspace-main details pre")?.textContent).toBe("refresh unavailable");
});

it("preserves a real unsaved editor buffer when the late capability reread fails", async () => {
  type Capability = Awaited<ReturnType<typeof plotloomApi.getRuntimeCapabilities>>;
  let resolveCapability!: (capability: Capability) => void;
  vi.mocked(plotloomApi.getRuntimeCapabilities).mockReturnValue(new Promise(resolve => {resolveCapability = resolve;}));
  vi.spyOn(plotloomApi, "getAuthoringDrafts").mockResolvedValue([]);
  const save = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const patch = vi.spyOn(plotloomApi, "patchProject");
  await render("/?project=a&stage=brief");
  const input = document.querySelector<HTMLInputElement>(".form-card input")!;
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "本页尚未保存的修改");
    input.dispatchEvent(new Event("input", {bubbles: true}));
  });
  expect(input.value).toBe("本页尚未保存的修改");
  let reject!: (error: Error) => void;
  vi.mocked(plotloomApi.getProject).mockReturnValueOnce(new Promise((_, fail) => {reject = fail;}));
  await act(async () => resolveCapability({durableProjectDrafts: true, explicitProjectClose: true, portableSnapshots: true, durableMediaDrafts: true, apiTextPipeline: true}));
  await flush();
  expect(document.querySelector(".form-card input")).toBe(input);
  expect(document.querySelector<HTMLFieldSetElement>(".editor-host")?.disabled).toBe(true);
  await act(async () => reject(new ApiError("capability reread unavailable", 503)));
  await flush();
  expect(document.querySelector(".form-card input")).toBe(input);
  expect(input.value).toBe("本页尚未保存的修改");
  expect(document.querySelector<HTMLFieldSetElement>(".editor-host")?.disabled).toBe(true);
  expect(document.body.textContent).toContain("本次读取未完成");
  expect(save).not.toHaveBeenCalled();
  expect(patch).not.toHaveBeenCalled();
});

it("permits an explicit real blank draft after an unavailable project", async () => {
  vi.mocked(plotloomApi.getProject).mockRejectedValue(closed());
  await render("/?project=a&stage=brief");
  await act(async () => button("打开项目目录").click());
  await flush();
  await act(async () => button("新建空白项目").click());
  await flush();
  expect(document.querySelector('[data-testid="workspace-project-unavailable"]')).toBeNull();
  expect(document.querySelector(".form-card input")).not.toBeNull();
  expect(document.body.textContent).toContain("尚未保存的项目草稿");
  expect(new URLSearchParams(location.search).has("project")).toBe(false);
});
