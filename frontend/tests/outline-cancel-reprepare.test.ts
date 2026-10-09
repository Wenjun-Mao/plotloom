import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture } from "./graph-workbench-fixture";
import { SourceOutlinePage } from "../src/pages/SourceOutlinePage";
import { specialistsApi } from "../src/features/specialists/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());

it.each([
  { sourceRevision: 1, candidateStatus: null, guidance: "返回保留的有效大纲" },
  { sourceRevision: 2, candidateStatus: null, guidance: "来源已变化，旧大纲只保留供阅读" },
  { sourceRevision: 2, candidateStatus: "prepared", guidance: "大纲任务尚未交付" },
  { sourceRevision: 2, candidateStatus: "ready", guidance: "先阅读候选大纲，再确认使用" },
])("binds revision guidance to source and candidate state: $sourceRevision/$candidateStatus", async ({ sourceRevision, candidateStatus, guidance }) => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getSourceOutline").mockResolvedValue({
    source: { revision: sourceRevision, material: { kind: "synopsis", title: "Confirmed", text: "current source", adaptationIntent: "" } },
    candidate: candidateStatus ? { jobId: "next", status: candidateStatus, sourceRevision, expectedOutlineRevision: 1 } : null,
    acceptedOutline: { revision: 1, sourceRevision: 1, candidateJobId: "retained", contentHash: "outline", outline: {} },
    outlineStatus: "reopened", sectionMapStaleReasons: [],
  } as never);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: "prepared", configured: true });
  const restore = vi.spyOn(plotloomApi, "returnToAcceptedOutline");
  try {
    await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: graphControllerFixture(), children: createElement(SourceOutlinePage, { projectId: "project", briefSeed: demoProject.brief, readOnly: false, onProductionInstalled: async () => undefined }) })));
    const guide = host.querySelector(".source-workflow-source .stage-guide")!;
    expect(guide.textContent).toContain(guidance);
    if (sourceRevision === 2) expect(guide.textContent).not.toContain("返回保留的有效大纲");
    const card = host.querySelector('[data-testid="source-outline-accepted"]')!;
    const button = [...card.querySelectorAll("button")].find(item => item.textContent === "返回保留的已确认大纲")!;
    expect(button.disabled).toBe(sourceRevision === 2);
    expect(restore).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it.each(["prepared", "queued", "outcome_unknown"] as const)("does not infer dispatch from a prepared outline candidate: %s", async taskState => {
  const host = document.createElement("div"); const root = createRoot(host);
  vi.spyOn(plotloomApi, "getSourceOutline").mockResolvedValue({ source: { revision: 1, material: { kind: "synopsis", title: "Confirmed", text: "unchanged source", adaptationIntent: "" } }, candidate: { jobId: "pending", status: "prepared", sourceRevision: 1, expectedOutlineRevision: 0 }, acceptedOutline: null, outlineStatus: "missing", sectionMapStaleReasons: [] } as never);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(specialistsApi, "status").mockResolvedValue({ state: taskState, configured: true });
  const send = vi.spyOn(specialistsApi, "send");
  try {
    await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: graphControllerFixture(), children: createElement(SourceOutlinePage, { projectId: "project", briefSeed: demoProject.brief, readOnly: false, onProductionInstalled: async () => undefined }) })));
    const card = host.querySelector('[data-testid="source-outline-candidate"]')!;
    expect(card.querySelector("header")?.textContent).toContain("任务尚未交付");
    expect(card.querySelector("header")?.textContent).not.toContain("等待助手交付");
    const labels = { prepared: "任务已准备，尚未发送", queued: "已发送，等待助手返回结果", outcome_unknown: "发送结果不确定" };
    expect(card.textContent).toContain(labels[taskState]);
    expect([...card.querySelectorAll("button")].some(button => button.textContent === "发送给文字创作助手")).toBe(taskState === "prepared");
    expect(send).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it.each([false, true])("exposes explicit first-candidate cancel recovery with readOnly=%s", async readOnly => {
  const host = document.createElement("div"); const root = createRoot(host);
  const state = { source: { revision: 1, material: { kind: "synopsis", title: "Confirmed", text: "unchanged source", adaptationIntent: "" } }, candidate: { jobId: "old", status: "cancelled", sourceRevision: 1, expectedOutlineRevision: 0 }, acceptedOutline: null, outlineStatus: "missing", sectionMapStaleReasons: [] };
  const get = vi.spyOn(plotloomApi, "getSourceOutline").mockResolvedValue(state as never);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  const prepare = vi.spyOn(plotloomApi, "prepareOutlineCandidate").mockRejectedValue(new Error("ordinary admission refused"));
  const saveSource = vi.spyOn(plotloomApi, "saveSourceMaterial");
  const show = () => act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: graphControllerFixture(), children: createElement(SourceOutlinePage, { projectId: "project", briefSeed: demoProject.brief, readOnly, onProductionInstalled: async () => undefined }) })));
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
