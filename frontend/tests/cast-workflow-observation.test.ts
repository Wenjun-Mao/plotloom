import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { CastPanel } from "../src/pages/CastPanel";
import { CharactersPage } from "../src/pages/CharactersPage";
import { ReviewWorkflowReadProvider, useReviewWorkflowRead } from "../src/app/workspace/ReviewWorkflowReadContext";
import { castWorkflowNextText } from "../src/app/workspace/recommendedCastWorkflow";
import type { CastReviewState } from "../src/types";

vi.mock("../src/pages/CharacterReferenceGalleryPage", () => ({ CharacterReferenceReviewPanel: () => null }));

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const missing: CastReviewState = { status: "missing", candidate: null, acceptedCast: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } };

it("observes the CastPanel owner and selection without adding reads, and clears on exit", async () => {
  const get = vi.spyOn(plotloomApi, "getCast");
  const host = document.createElement("div"), root = createRoot(host);
  let enabled = true, loadError = "";
  function Guide() { const read = useReviewWorkflowRead(); return createElement("p", { "data-hint": true }, castWorkflowNextText(read?.stage === "characters" ? read : undefined).text); }
  const refresh = vi.fn(async () => true);
  const render = () => act(async () => root.render(createElement(ReviewWorkflowReadProvider, { projectId: "one", revision: 1, stage: enabled ? "characters" : undefined,
    children: [createElement(Guide, { key: "guide" }), enabled ? createElement(CastPanel, { key: "panel", projectId: "one", readOnly: false, state: missing, loadError, onState: vi.fn(), onRefresh: refresh, onInvalidate: vi.fn(), onTransitionComplete: vi.fn() }) : null] })));
  const hint = () => host.querySelector("[data-hint]")?.textContent;
  try {
    await render(); expect(hint()).toContain("先选择「角色图像风格」");
    const select = host.querySelector('select[aria-label="角色图像风格"]')! as HTMLSelectElement;
    await act(async () => { select.value = "live-action"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(hint()).toContain("角色图像风格已选择");
    expect(get).not.toHaveBeenCalled(); expect(refresh).not.toHaveBeenCalled();
    loadError = "HTTP 503"; await render(); expect(hint()).toContain("重试加载角色设定");
    enabled = false; await render(); expect(hint()).toContain("正在读取");
    loadError = ""; enabled = true; await render(); expect(hint()).toContain("先选择「角色图像风格」");
  } finally { await act(async () => root.unmount()); }
});

it("revalidates the Role owner on workspace refresh, retaining edits but rejecting obsolete reads", async () => {
  const binding = { sourceRevision: 1, sourceContentHash: "source", outlineRevision: 1, outlineContentHash: "outline", sectionMapRevision: 1, sectionMapContentHash: "sections", graphRevision: 1, graphContentHash: "graph", sectionIds: ["opening"] };
  const accepted: CastReviewState = { ...missing, status: "accepted", acceptedReviewState: { status: "current", staleReasons: [] }, acceptedCast: { revision: 1, candidateJobId: "cast-job", binding, contentHash: "cast", cast: { characters: [{ id: "keeper", name: "Mira", persona: { personality: ["Careful"], appearance: "Blue coat" } }] }, consumerMappings: [], reportAvailable: false, differsFromDelivery: null, acceptedAt: "2026-10-11T00:00:00Z" } };
  const reopened: CastReviewState = { ...accepted, status: "reopened" };
  const get = vi.spyOn(plotloomApi, "getCast").mockResolvedValue(accepted);
  vi.spyOn(plotloomApi, "reopenCast").mockResolvedValue(reopened);
  const host = document.createElement("div"), root = createRoot(host);
  let revision = 1;
  function Guide() { const read = useReviewWorkflowRead(); return createElement("p", { "data-hint": true }, castWorkflowNextText(read?.stage === "characters" ? read : undefined).text); }
  const render = () => act(async () => root.render(createElement(ReviewWorkflowReadProvider, { projectId: "one", revision, stage: "characters", children: [createElement(Guide, { key: "guide" }), createElement(CharactersPage, { key: "page", projectId: "one", refreshToken: revision, readOnly: false, onContinue: vi.fn() })] })));
  const hint = () => host.querySelector("[data-hint]")?.textContent;
  const button = (text: string) => [...host.querySelectorAll("button")].find(item => item.textContent === text)!;
  let resolveOld!: (state: CastReviewState) => void;
  let rejectCurrent!: (error: Error) => void;
  try {
    await render(); expect(hint()).toContain("继续：美术参考"); expect(get).toHaveBeenCalledTimes(1);
    await act(async () => button("编辑角色设定").click());
    const input = [...host.querySelectorAll("textarea")].find(item => item.value === "Blue coat")!;
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(input, "Red coat draft"); input.dispatchEvent(new Event("input", { bubbles: true })); });
    get.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
    revision += 1; await render();
    expect(hint()).toContain("正在读取"); expect(button("保存角色修改").disabled).toBe(true);
    expect(button("继续：美术参考").disabled).toBe(true);
    expect(input.value).toBe("Red coat draft"); expect(get).toHaveBeenCalledTimes(2);
    get.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectCurrent = reject; }));
    revision += 1; await render();
    await act(async () => { resolveOld(accepted); });
    expect(hint()).toContain("正在读取"); expect(button("保存角色修改").disabled).toBe(true);
    await act(async () => { rejectCurrent(new Error("HTTP 503")); });
    expect(hint()).toContain("重试加载角色设定"); expect(button("保存角色修改").disabled).toBe(true);
    get.mockResolvedValueOnce(reopened);
    await act(async () => button("重试加载角色设定").click());
    expect(hint()).toContain("保存角色修改"); expect(button("保存角色修改").disabled).toBe(false);
    expect(input.value).toBe("Red coat draft"); expect(get).toHaveBeenCalledTimes(4);
  } finally { await act(async () => root.unmount()); }
});
