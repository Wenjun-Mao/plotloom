import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { StoryboardReviewPanel } from "../src/pages/StoryboardReviewPanel";
import { ReviewWorkflowReadProvider, useReviewWorkflowRead, useBridgeWorkflowRead } from "../src/app/workspace/ReviewWorkflowReadContext";
import { storyboardWorkflowNextText } from "../src/app/workspace/recommendedStoryboardWorkflow";
import type { StoryboardReviewState } from "../src/types";
import { workflowProductionFixture } from "./workflow-production-fixture";
import { bridgeState } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const missing: StoryboardReviewState = { status: "missing", candidate: null, acceptedReview: null, staleReasons: [], acceptedReviewState: { status: "missing", staleReasons: [] } };
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }

async function harness(initial = missing) {
  const api = vi.spyOn(plotloomApi, "getStoryboardSourceReview").mockResolvedValue(initial);
  const bridgeApi = vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(bridgeState());
  const host = document.createElement("div"), root = createRoot(host);
  let projectId = "one", active = true, token = 1;
  function Guide() { const read = useReviewWorkflowRead(), bridge = useBridgeWorkflowRead(); return createElement("p", { "data-hint": true }, storyboardWorkflowNextText(read?.stage === "storyboard-review" ? read : undefined, bridge).text); }
  const render = () => act(async () => root.render(createElement(ReviewWorkflowReadProvider, { projectId, revision: 1, stage: active ? "storyboard-review" : undefined,
    children: [createElement(Guide, { key: "guide" }), active ? createElement(StoryboardReviewPanel, { key: "panel", projectId, readOnly: false, refreshToken: token, onInstalled: async () => undefined }) : null] })));
  await render();
  return { api, bridgeApi, host, render, get text() { return host.querySelector("[data-hint]")?.textContent; },
    activate: async (value: boolean) => { active = value; await render(); }, project: async (value: string) => { projectId = value; await render(); },
    refresh: async () => { token++; await render(); }, close: () => act(async () => root.unmount()) };
}

it("observes the existing Storyboard read once, including busy and delivered transitions", async () => {
  const view = await harness();
  try {
    expect(view.api).toHaveBeenCalledOnce(); expect(view.bridgeApi).not.toHaveBeenCalled(); expect(view.text).toContain("准备分镜任务");
    await view.render(); expect(view.api).toHaveBeenCalledOnce();
    const operation = deferred<Awaited<ReturnType<typeof plotloomApi.prepareStoryboardSourceReviewCandidate>>>();
    vi.spyOn(plotloomApi, "prepareStoryboardSourceReviewCandidate").mockReturnValue(operation.promise);
    view.api.mockResolvedValue({ ...missing, status: "candidate_ready", candidate: { status: "ready", jobId: "job", binding: {} } } as never);
    await act(async () => [...view.host.querySelectorAll("button")].find(button => button.textContent === "准备分镜任务")!.click());
    expect(view.text).toContain("正在处理分镜评审任务");
    await act(async () => operation.resolve({ assignment: "task" } as never));
    expect(view.text).toContain("确认此分镜评审方案"); expect(view.api).toHaveBeenCalledTimes(2);
  } finally { await view.close(); }
});
it("observes the nested bridge without duplicating or replacing the Storyboard owner", async () => {
  const current = workflowProductionFixture({ graphAdmission: {} } as never).storyboardSource!;
  const view = await harness(current);
  try {
    expect(view.api).toHaveBeenCalledOnce(); expect(view.bridgeApi).toHaveBeenCalledOnce();
    expect(view.text).toContain("点击下方「准备投产提案」");
    await view.render(); expect(view.api).toHaveBeenCalledOnce(); expect(view.bridgeApi).toHaveBeenCalledOnce();
    view.api.mockRejectedValueOnce(new Error("HTTP 503")); await view.refresh();
    expect(view.text).toContain("重试加载分镜评审"); expect(view.text).not.toContain("点击下方「准备投产提案」");
  } finally { await view.close(); }
});
it("suppresses old observations across page exit and project A-B-A", async () => {
  const view = await harness(), late = deferred<StoryboardReviewState>(), current = deferred<StoryboardReviewState>();
  try {
    await view.activate(false); expect(view.text).toContain("正在读取");
    await view.activate(true);
    view.api.mockReturnValueOnce(late.promise); await view.project("two");
    view.api.mockReturnValueOnce(current.promise); await view.project("one");
    await act(async () => late.resolve(missing)); expect(view.text).toContain("正在读取");
    await act(async () => current.resolve(missing)); expect(view.text).toContain("准备分镜任务");
  } finally { await view.close(); }
});
