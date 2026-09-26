import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { ScriptPanel } from "../src/pages/ScriptPanel";
import type { ScriptReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

function preparedState(): ScriptReviewState {
  return { candidate: null, acceptedScript: null, status: "missing", staleReasons: [] };
}

function awaitingDeliveryState(): ScriptReviewState {
  return {
    candidate: {
      jobId: "script-job", expectedScriptRevision: 0, binding: {}, status: "prepared", deliveryId: null, manifestHash: null,
      script: null, reportAvailable: false, createdAt: "2026-09-26T00:00:00Z", deliveredAt: null,
    } as ScriptReviewState["candidate"],
    acceptedScript: null, status: "prepared", staleReasons: [],
  };
}

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("settles a held F4 preparation after unmount without publishing assignment, error, or refresh", async () => {
  const prepared = deferred<{ assignment: string }>();
  const getScript = vi.spyOn(plotloomApi, "getScript").mockResolvedValue(preparedState());
  vi.spyOn(plotloomApi, "prepareScriptCandidate").mockReturnValue(prepared.promise as ReturnType<typeof plotloomApi.prepareScriptCandidate>);

  await act(async () => { root.render(createElement(ScriptPanel, { projectId: "old", readOnly: false })); });
  const prepare = [...host.querySelectorAll("button")].find(button => button.textContent === "准备剧本任务");
  expect(prepare).toBeDefined();
  await act(async () => prepare?.click());
  const callsBeforeUnmount = getScript.mock.calls.length;
  await act(async () => root.unmount());

  await act(async () => {
    prepared.resolve({ assignment: "stale script assignment" });
    await prepared.promise;
  });

  expect(getScript).toHaveBeenCalledTimes(callsBeforeUnmount);
  expect(host.textContent).not.toContain("stale script assignment");
  expect(host.querySelector('[role="alert"]')).toBeNull();
});

it("settles a held F4 preparation after a project switch without crossing into the new project", async () => {
  const prepared = deferred<{ assignment: string }>();
  const getScript = vi.spyOn(plotloomApi, "getScript").mockImplementation(async () => preparedState());
  vi.spyOn(plotloomApi, "prepareScriptCandidate").mockReturnValue(prepared.promise as ReturnType<typeof plotloomApi.prepareScriptCandidate>);

  await act(async () => { root.render(createElement(ScriptPanel, { projectId: "old", readOnly: false })); });
  const prepare = [...host.querySelectorAll("button")].find(button => button.textContent === "准备剧本任务");
  await act(async () => prepare?.click());
  await act(async () => { root.render(createElement(ScriptPanel, { projectId: "new", readOnly: false })); });
  const callsAfterSwitch = getScript.mock.calls.length;

  await act(async () => {
    prepared.resolve({ assignment: "old project assignment" });
    await prepared.promise;
  });

  expect(getScript).toHaveBeenCalledTimes(callsAfterSwitch);
  expect(host.textContent).not.toContain("old project assignment");
  expect(host.querySelector('[role="alert"]')).toBeNull();
});

it("restores the recovered script assignment without claiming it was copied", async () => {
  const state = awaitingDeliveryState();
  vi.spyOn(plotloomApi, "getScript").mockResolvedValue(state);
  vi.spyOn(plotloomApi, "recoverScriptHandoff").mockResolvedValue({ assignment: "Recovered script task" } as ReturnType<typeof plotloomApi.recoverScriptHandoff> extends Promise<infer Result> ? Result : never);
  const writeText = vi.fn();
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  await act(async () => { root.render(createElement(ScriptPanel, { projectId: "project", readOnly: false })); });
  const recover = [...host.querySelectorAll("button")].find(button => button.textContent === "恢复剧本任务");
  await act(async () => recover?.click());
  expect(host.querySelector("textarea")?.value).toBe("Recovered script task");
  expect(host.textContent).toContain("完整任务（可复制）");
  expect(host.textContent).not.toContain("已复制完整任务");
  expect(writeText).not.toHaveBeenCalled();
});
