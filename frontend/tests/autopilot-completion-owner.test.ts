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
  return createElement("button", { id: "start", onClick: () => void owner.start({ styleAuthority: "brief", maxImages: 80, maxJobs: 96 }) }, "start");
}
async function render() {
  await act(async () => root.render(createElement(AutopilotWorkspace, { projectId: "disposable", revision: 1,
    readOnly: false, onChanged: async () => undefined, onVideo: vi.fn(), children: createElement(Start) })));
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
