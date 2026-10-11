import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ArtPanel } from "../src/pages/ArtPanel";
import { ReviewWorkflowReadProvider, useReviewWorkflowRead } from "../src/app/workspace/ReviewWorkflowReadContext";
import { artWorkflowNextText } from "../src/app/workspace/recommendedArtWorkflow";
import type { ArtReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const missing: ArtReviewState = { status: "missing", candidate: null, acceptedArt: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } };

it("shares existing Art reads and style selection, invalidating observations across Art/Script switches", async () => {
  const art = vi.spyOn(plotloomApi, "getArt").mockResolvedValue(missing);
  const proposals = vi.spyOn(plotloomApi, "getArtReferenceProposals").mockResolvedValue({ configured: false, proposals: [] });
  const decisions = vi.spyOn(plotloomApi, "getArtReferenceDecisions").mockResolvedValue({ decisions: [], states: [] });
  const host = document.createElement("div"), root = createRoot(host);
  let stage: "art" | "script" = "art";
  function Guide() { const read = useReviewWorkflowRead(); return createElement("p", { "data-hint": true }, artWorkflowNextText(read?.stage === "art" ? read : undefined).text); }
  const render = () => act(async () => root.render(createElement(ReviewWorkflowReadProvider, { projectId: "project", revision: 1, stage,
    children: [createElement(Guide, { key: "guide" }), createElement(ArtPanel, { key: "panel", projectId: "project", active: stage === "art", readOnly: false })] })));
  const hint = () => host.querySelector("[data-hint]")?.textContent;
  try {
    await render();
    expect(hint()).toContain("先选择「美术风格」");
    for (const api of [art, proposals, decisions]) expect(api).toHaveBeenCalledOnce();
    const select = host.querySelector('select[aria-label="美术风格"]')! as HTMLSelectElement;
    await act(async () => { select.value = "live-action"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(hint()).toContain("美术风格已选择");
    for (const api of [art, proposals, decisions]) expect(api).toHaveBeenCalledOnce();
    stage = "script"; await render();
    expect(hint()).toContain("正在读取");
    let release!: (state: ArtReviewState) => void;
    art.mockReturnValueOnce(new Promise(resolve => { release = resolve; }));
    stage = "art"; await render();
    expect(hint()).toContain("正在读取");
    expect(hint()).not.toContain("美术风格已选择");
    stage = "script"; await render();
    await act(async () => release(missing));
    expect(hint()).toContain("正在读取");
    expect(hint()).not.toContain("美术风格已选择");
  } finally { await act(async () => root.unmount()); }
});
