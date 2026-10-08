import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { PlayView } from "../src/play/PlayView";
import { plotloomApi } from "../src/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); window.history.replaceState({}, "", "/"); });

it("retries failed playback reads without admitting missing stages or changing content", async () => {
  window.history.replaceState({}, "", "/?view=play&project=project");
  const host = document.createElement("div"); const root = createRoot(host);
  const getProject = vi.spyOn(plotloomApi, "getProject").mockRejectedValueOnce(new Error("offline"));
  const stages = vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] } as Awaited<ReturnType<typeof plotloomApi.getStages>>);
  const videos = vi.spyOn(plotloomApi, "getVideoJobs").mockResolvedValue({ jobs: [] });
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
