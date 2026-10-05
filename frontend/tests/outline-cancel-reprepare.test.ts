import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { SourceOutlinePage } from "../src/pages/SourceOutlinePage";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());

it.each([false, true])("exposes explicit first-candidate cancel recovery with readOnly=%s", async readOnly => {
  const host = document.createElement("div"); const root = createRoot(host);
  const state = { source: { revision: 1, material: { kind: "synopsis", title: "Confirmed", text: "unchanged source", adaptationIntent: "" } }, candidate: { jobId: "old", status: "cancelled", sourceRevision: 1, expectedOutlineRevision: 0 }, acceptedOutline: null, outlineStatus: "missing", sectionMapStaleReasons: [] };
  const get = vi.spyOn(plotloomApi, "getSourceOutline").mockResolvedValue(state as never);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  const prepare = vi.spyOn(plotloomApi, "prepareOutlineCandidate").mockRejectedValue(new Error("ordinary admission refused"));
  const saveSource = vi.spyOn(plotloomApi, "saveSourceMaterial");
  const show = () => act(async () => root.render(createElement(SourceOutlinePage, { projectId: "project", briefSeed: demoProject.brief, readOnly })));
  try {
    await show();
    const button = [...host.querySelectorAll("button")].find(item => item.textContent === "重新准备大纲任务")!;
    expect(button.disabled).toBe(readOnly);
    if (!readOnly) {
      await act(async () => button.click());
      expect(host.textContent).toContain("ordinary admission refused");
      expect(host.textContent).toContain("已取消");
      expect(prepare).toHaveBeenCalledExactlyOnceWith("project");
      get.mockRejectedValue(new Error("failed currentness read"));
      await act(async () => [...host.querySelectorAll("button")].find(item => item.textContent === "刷新")!.click());
      expect(button.disabled).toBe(true);
    } else expect(prepare).not.toHaveBeenCalled();
    expect(saveSource).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});
