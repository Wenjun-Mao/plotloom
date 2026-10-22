import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AutopilotWorkspace, useAutopilot } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import type { AutopilotRun } from "../src/features/autopilot/contracts";
import { fixtureRun } from "./autopilot-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, host: HTMLDivElement, current: AutopilotRun | null;
let scroll: ReturnType<typeof vi.spyOn>;
const running = { ...fixtureRun, state: "running" as const, revision: 20 };
function Start() {
  const owner = useAutopilot()!;
  return createElement("button", { id: "start", disabled: owner.busy, "data-run": owner.run?.id || "", onClick: () => void owner.start({ styleAuthority: "brief", maxImages: 80, maxJobs: 96 }) }, "start");
}
async function render(projectId = "disposable", onChanged: () => Promise<void> = async () => undefined, revision = 1) {
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId, revision,
    readOnly: false, onChanged, onVideo: vi.fn(), children: createElement(Start) })));
}
async function poll(value: AutopilotRun | null) {
  current = value;
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
}
async function start() {
  await act(async () => host.querySelector<HTMLButtonElement>("#start")!.click());
}
beforeEach(() => {
  vi.useFakeTimers(); current = null;
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(autopilotApi, "current").mockImplementation(async () => current);
  vi.spyOn(autopilotApi, "start").mockImplementation(async () => { current = running; return running; });
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(callback => { callback(0); return 1; });
  scroll = vi.spyOn(window, "scrollBy").mockImplementation(() => undefined);
});
afterEach(async () => {
  await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); vi.useRealTimers();
});
it("binds the initial Start response without clearing the intended run's one reveal", async () => {
  await render(); await start();
  expect(scroll).not.toHaveBeenCalled();
  await poll({ ...fixtureRun, revision: 21 });
  expect(scroll).toHaveBeenCalledTimes(1);
  await poll({ ...fixtureRun, revision: 22 });
  expect(scroll).toHaveBeenCalledTimes(1);
});
it("an externally replaced run cannot consume the foreground Start intent", async () => {
  await render(); await start();
  await poll({ ...running, id: "other-run", revision: 1 });
  await poll({ ...fixtureRun, id: "other-run", revision: 2 });
  expect(host.textContent).toContain("等待你审阅");
  expect(scroll).not.toHaveBeenCalled();
});
it.each(["cancelled", "taken_over", "stale"] as const)("external %s permanently withdraws that run's completion intent", async state => {
  await render(); await start();
  await poll({ ...running, state, revision: 21 });
  await poll({ ...fixtureRun, revision: 22 });
  expect(scroll).not.toHaveBeenCalled();
});
it("a delayed resume ACK cannot restore intent after polling observes replacement", async () => {
  current = { ...running, state: "paused" };
  let release!: (value: AutopilotRun) => void;
  vi.spyOn(autopilotApi, "control").mockImplementation(() => new Promise(resolve => { release = resolve; }));
  await render();
  await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "继续原任务")!.click());
  await poll({ ...running, id: "replacement-run", revision: 1 });
  await act(async () => release(running));
  await poll({ ...fixtureRun, id: "replacement-run", revision: 2 });
  expect(scroll).not.toHaveBeenCalled();
});
it("Start releases busy after its own new run is observed and async refresh finishes", async () => {
  let release!: () => void;
  const changed = vi.fn(() => new Promise<void>(resolve => { release = resolve; }));
  await render("disposable", changed); await start();
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(true);
  expect(host.querySelector("#start")?.getAttribute("data-run")).toBe(running.id);
  await act(async () => release());
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(false);
});
it("Continue releases busy after the successor run and async refresh finish", async () => {
  current = { ...fixtureRun, state: "cancelled" };
  const successor = { ...running, id: "successor-run", revision: 1 };
  vi.spyOn(autopilotApi, "continuationContext").mockResolvedValue({ runId: current.id, runRevision: current.revision,
    materialClosure: "a".repeat(64), eligible: true, blockers: [], inheritedOperations: 1, lifetimeJobs: 2, lifetimeImages: 0 });
  vi.spyOn(autopilotApi, "continueMaterial").mockImplementation(async () => { current = successor; return successor; });
  let release!: () => void;
  await render("disposable", () => new Promise<void>(resolve => { release = resolve; }));
  await act(async () => [...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "继续剩余素材")!.click());
  await act(async () => [...document.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "确认继续剩余素材")!.click());
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(true);
  expect(host.querySelector("#start")?.getAttribute("data-run")).toBe(successor.id);
  await act(async () => release());
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(false);
});
it("keeps existing Resume for a non-content text availability blocker", async () => {
  current = { ...running, state: "blocked", phase: "outline", blocker: { code: "host_unavailable", message: "host offline" } };
  vi.spyOn(autopilotApi, "textFailure").mockResolvedValue(null);
  await render();
  expect([...host.querySelectorAll<HTMLButtonElement>("button")].find(button => button.textContent === "继续原任务")?.disabled).toBe(false);
});
it("a late Start ACK cannot write across project A-B-A navigation", async () => {
  let release!: (value: AutopilotRun) => void;
  vi.mocked(autopilotApi.start).mockImplementation(() => new Promise(resolve => { release = resolve; }));
  await render("a"); await start(); await render("b"); await render("a");
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(false);
  await act(async () => release(running));
  expect(host.querySelector("#start")?.getAttribute("data-run")).toBe("");
});
it("releases its busy ownership when async refresh observes a new Brief revision", async () => {
  let release!: () => void;
  const changed = () => new Promise<void>(resolve => { release = resolve; });
  await render("disposable", changed); await start();
  await render("disposable", changed, 2);
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(true);
  await act(async () => release());
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(false);
});
it("a stale finally cannot clear a newer project's pending operation", async () => {
  let releaseA!: (value: AutopilotRun) => void, releaseB!: (value: AutopilotRun) => void;
  vi.mocked(autopilotApi.start).mockImplementationOnce(() => new Promise(resolve => { releaseA = resolve; }))
    .mockImplementationOnce(() => new Promise(resolve => { releaseB = resolve; }));
  await render("a"); await start(); await render("b"); await start();
  await act(async () => releaseA(running));
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(true);
  await act(async () => releaseB({ ...running, id: "b-run" }));
  expect(host.querySelector<HTMLButtonElement>("#start")?.disabled).toBe(false);
});
