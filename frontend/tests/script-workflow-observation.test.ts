import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ScriptPanel } from "../src/pages/ScriptPanel";
import { ScriptWorkflowReadProvider, useScriptWorkflowRead } from "../src/app/workspace/ScriptWorkflowReadContext";
import { scriptWorkflowNextText } from "../src/app/workspace/recommendedScriptWorkflow";
import type { ScriptReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
const missing: ScriptReviewState = { status: "missing", candidate: null, acceptedScript: null, staleReasons: [],
  acceptedReviewState: { status: "missing", staleReasons: [] } };
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }

async function harness() {
  const api = vi.spyOn(plotloomApi, "getScript").mockResolvedValue(missing);
  const host = document.createElement("div"), root = createRoot(host);
  let projectId = "one", active = true, token = 1;
  function Guide() { const read = useScriptWorkflowRead(); return createElement("p", { "data-hint": true }, scriptWorkflowNextText(read).text); }
  const render = () => act(async () => root.render(createElement(ScriptWorkflowReadProvider, { projectId, revision: 1, active,
    children: [createElement(Guide, { key: "guide" }), active ? createElement(ScriptPanel, { key: "panel", projectId, readOnly: false, refreshToken: token }) : null] })));
  await render();
  return { api, host, render, get text() { return host.querySelector("[data-hint]")?.textContent; },
    activate: async (value: boolean) => { active = value; await render(); },
    project: async (value: string) => { projectId = value; await render(); },
    refresh: async () => { token++; await render(); }, close: () => act(async () => root.unmount()) };
}

it("observes ScriptPanel without adding another API read", async () => {
  const view = await harness();
  try {
    expect(view.api).toHaveBeenCalledOnce();
    expect(view.text).toContain("准备剧本任务");
    await view.render();
    expect(view.api).toHaveBeenCalledOnce();
    const operation = deferred<Awaited<ReturnType<typeof plotloomApi.prepareScriptCandidate>>>();
    vi.spyOn(plotloomApi, "prepareScriptCandidate").mockReturnValue(operation.promise);
    const prepared = { ...missing, status: "prepared", candidate: { status: "prepared", jobId: "job" } } as ScriptReviewState;
    view.api.mockResolvedValue(prepared);
    await act(async () => [...view.host.querySelectorAll("button")].find(button => button.textContent === "准备剧本任务")!.click());
    expect(view.text).toContain("正在处理剧本任务");
    await act(async () => operation.resolve({ assignment: "task" } as never));
    expect(view.text).toContain("剧本任务已准备，尚未交付");
    expect(view.api).toHaveBeenCalledTimes(2);
  } finally { await view.close(); }
});
it("does not revive advice on page re-entry while its new read is pending", async () => {
  const view = await harness(), held = deferred<ScriptReviewState>();
  try {
    await view.activate(false);
    expect(view.text).toContain("正在读取");
    view.api.mockReturnValueOnce(held.promise);
    await view.activate(true);
    expect(view.text).not.toContain("当前没有剧本候选");
    await act(async () => held.resolve(missing));
    expect(view.text).toContain("准备剧本任务");
  } finally { await view.close(); }
});
it("suppresses late reads across project one → two → one", async () => {
  const view = await harness(), late = deferred<ScriptReviewState>(), current = deferred<ScriptReviewState>();
  try {
    view.api.mockReturnValueOnce(late.promise); await view.project("two");
    view.api.mockReturnValueOnce(current.promise); await view.project("one");
    await act(async () => late.resolve(missing));
    expect(view.text).toContain("正在读取");
    await act(async () => current.resolve(missing));
    expect(view.text).toContain("准备剧本任务");
  } finally { await view.close(); }
});
it("keeps failed refreshes unknown even when the old script state remains visible", async () => {
  const view = await harness();
  try {
    view.api.mockRejectedValueOnce(new Error("HTTP 503")); await view.refresh();
    expect(view.text).toContain("重试加载剧本");
    expect(view.text).not.toContain("准备剧本任务");
    await act(async () => [...view.host.querySelectorAll("button")].find(button => button.textContent === "重试加载剧本")!.click());
    expect(view.text).toContain("准备剧本任务");
  } finally { await view.close(); }
});
