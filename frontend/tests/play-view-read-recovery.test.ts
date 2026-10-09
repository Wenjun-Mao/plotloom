import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { PlayView } from "../src/play/PlayView";
import { plotloomApi } from "../src/api";
import { bridgeState, installedProduction } from "./production-bridge-fixture";
import { demoProject } from "../src/demo";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

it("retries failed playback reads without admitting missing stages or changing content", async () => {
  window.history.replaceState({}, "", "/?view=play&project=project");
  const host = document.createElement("div"); const root = createRoot(host);
  const getProject = vi.spyOn(plotloomApi, "getProject").mockRejectedValueOnce(new Error("offline"));
  const stages = vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] } as Awaited<ReturnType<typeof plotloomApi.getStages>>);
  const videos = vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState());
  try {
    await act(async () => root.render(createElement(PlayView)));
    expect(host.textContent).toContain("offline");
    expect(host.textContent).toContain("返回工作台");
    getProject.mockResolvedValue({ brief: { title: "雨停以后" } } as Awaited<ReturnType<typeof plotloomApi.getProject>>);
    await act(async () => host.querySelector("button")!.click());
    expect(getProject).toHaveBeenCalledTimes(2);
    expect(stages).toHaveBeenCalledTimes(2);
    expect(videos).toHaveBeenCalledTimes(2);
    expect(host.textContent).toContain("故事尚未准备好");
    expect(host.textContent).toContain("尚未建立可播放的故事路线、场景内容、分镜内容");
    expect(host.querySelector('[role="alert"]')).toBeNull();
    expect(host.textContent).not.toContain("重新读取播放内容");
    expect(host.querySelector('a[href="?project=project&stage=source#storyboard-review"]')?.textContent).toBe("前往分镜评审与制作");
    expect(host.textContent).not.toContain("offline");
    expect(host.querySelector("video")).toBeNull();
  } finally { await act(async () => root.unmount()); }
});

it.each(["installation", "canonical"])("directs %s staleness to rebuilding rather than missing clips", async (authority) => {
  window.history.replaceState({}, "", "/?view=play&project=project");
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ brief: { title: "渡口" } } as Awaited<ReturnType<typeof plotloomApi.getProject>>);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [{ head: { stage: "storyboard", status: authority === "canonical" ? "stale" : "ready" }, payload: {} }] } as Awaited<ReturnType<typeof plotloomApi.getStages>>);
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState({ installation: authority === "installation" ? installedProduction({ status: "outdated" }) : null }));
  try {
    await act(async () => root.render(createElement(PlayView)));
    expect(host.textContent).toContain("故事已修改，需要重新建立制作内容");
    expect(host.textContent).toContain("旧视频仍保留");
    expect(host.textContent).not.toContain("缺少当前已确认的播放片段");
    expect(host.querySelector('[data-testid="branching-video-preview"]')).toBeNull();
    expect(host.querySelector('a[href="?project=project&stage=source#storyboard-review"]')).not.toBeNull();
  } finally { await act(async () => root.unmount()); }
});

it("keeps playback closed when installation authority cannot be read and permits a read-only retry", async () => {
  window.history.replaceState({}, "", "/?view=play&project=project");
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ brief: { title: "渡口" } } as Awaited<ReturnType<typeof plotloomApi.getProject>>);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  const read = vi.spyOn(plotloomApi, "getProductionBridge").mockRejectedValueOnce(new Error("production unavailable")).mockResolvedValue(bridgeState({ installation: installedProduction({ status: "outdated" }) }));
  try {
    await act(async () => root.render(createElement(PlayView)));
    expect(host.textContent).toContain("production unavailable");
    expect(host.textContent).not.toContain("故事尚未准备好");
    expect(host.querySelector("video")).toBeNull();
    await act(async () => host.querySelector("button")!.click());
    expect(read).toHaveBeenCalledTimes(2);
    expect(host.textContent).toContain("故事已修改，需要重新建立制作内容");
  } finally { await act(async () => root.unmount()); }
});

it("admits ready canonical content without an installation record", async () => {
  window.history.replaceState({}, "", "/?view=play&project=project");
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ brief: { title: "直接编排的故事" } } as Awaited<ReturnType<typeof plotloomApi.getProject>>);
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState({ installation: null }));
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [
    { head: { stage: "story_graph", status: "ready" }, payload: demoProject.storyGraph },
    { head: { stage: "scene_beats", status: "ready" }, payload: demoProject.sceneBeats },
    { head: { stage: "storyboard", status: "ready" }, payload: demoProject.storyboard },
  ] } as Awaited<ReturnType<typeof plotloomApi.getStages>>);
  try {
    await act(async () => root.render(createElement(PlayView)));
    expect(host.textContent).toContain("直接编排的故事");
    expect(host.querySelector('[data-testid="branching-video-preview"]')).not.toBeNull();
    expect(host.textContent).not.toContain("需要重新建立制作内容");
  } finally { await act(async () => root.unmount()); }
});

it("ignores an abandoned project's late authority response", async () => {
  window.history.replaceState({}, "", "/?view=play&project=old");
  const host = document.createElement("div"); const root = createRoot(host);
  let resolveOld!: (value: Awaited<ReturnType<typeof plotloomApi.getProductionBridge>>) => void;
  const oldRead = new Promise<Awaited<ReturnType<typeof plotloomApi.getProductionBridge>>>(resolve => { resolveOld = resolve; });
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue({ brief: { title: "渡口" } } as Awaited<ReturnType<typeof plotloomApi.getProject>>);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
  const bridge = vi.spyOn(plotloomApi, "getProductionBridge").mockReturnValueOnce(oldRead).mockResolvedValue(bridgeState({ installation: installedProduction({ status: "outdated" }) }));
  try {
    await act(async () => root.render(createElement(PlayView)));
    const oldSignal = bridge.mock.calls[0][1]!;
    window.history.replaceState({}, "", "/?view=play&project=current");
    await act(async () => root.render(createElement(PlayView)));
    expect(oldSignal.aborted).toBe(true);
    expect(host.textContent).toContain("故事已修改，需要重新建立制作内容");
    await act(async () => resolveOld(bridgeState({ installation: null })));
    expect(host.textContent).toContain("故事已修改，需要重新建立制作内容");
    expect(host.textContent).not.toContain("故事尚未准备好");
    expect(host.querySelector('a[href="?project=current&stage=source#storyboard-review"]')).not.toBeNull();
  } finally { await act(async () => root.unmount()); }
});
