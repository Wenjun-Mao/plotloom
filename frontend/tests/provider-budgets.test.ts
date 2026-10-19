import { act, createElement, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AggregateBudget, budgetSummary, parseBudget, type BudgetInput } from "../src/components/AggregateBudget";
import { AutopilotWorkspace, AutopilotLaunch } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { VideoBatchPanel } from "../src/features/video-batch/VideoBatchPanel";
import { batchApi } from "../src/features/video-batch/api";
import { plotloomApi } from "../src/api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
const button = (label: string) => [...host.querySelectorAll<HTMLButtonElement>("button")].find(node => node.textContent === label)!;
async function select(index: number, value: string) {
  await act(async () => { const node = host.querySelectorAll("select")[index]; node.value = value; node.dispatchEvent(new Event("change", { bubbles: true })); });
}
async function input(index: number, value: string) {
  await act(async () => { const node = host.querySelectorAll("input")[index];
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(node, value);
    node.dispatchEvent(new Event("input", { bubbles: true })); });
}

it.each(["", "0", "-1", "NaN", "Infinity", "true", "12.5", "1e3", " 10", "9007199254740992"])("rejects finite raw text %s", value => {
  expect(parseBudget(value, 1)).toBeUndefined();
});
it("represents unlimited explicitly and accepts finite values beyond retired ceilings", () => {
  expect(parseBudget(null, 1)).toBeNull(); expect(parseBudget("10000", 1)).toBe(10000);
  expect(parseBudget("8", 9)).toBeUndefined();
  expect(budgetSummary(null, "项")).toBe("不限"); expect(budgetSummary(10, "秒")).toBe("10 秒");
});
it("keeps blank finite mode invalid instead of treating it as unlimited", async () => {
  function Harness() { const [value, setValue] = useState<BudgetInput>(null);
    return createElement(AggregateBudget, { label: "任务", value, minimum: 1, onChange: setValue }); }
  await act(async () => root.render(createElement(Harness)));
  expect(host.querySelector("input")).toBeNull();
  await select(0, "finite"); expect(host.querySelector("input")!.getAttribute("aria-invalid")).toBe("true");
  await input(0, "300"); expect(host.querySelector("input")!.value).toBe("300");
  expect(host.querySelector("input")!.getAttribute("aria-invalid")).toBe("false");
  await select(0, "unlimited"); expect(host.querySelector("input")).toBeNull();
});

const frozen = (jobs: number | null, seconds: number | null) => ({ id: "test-batch", projectId: "project", revision: 1,
  controlRevision: 1, state: "cancelled", manifestHash: "a".repeat(64), execution: {},
  manifest: { scopeShotIds: [], kept: [], targets: [], blockers: [], newJobs: 0, requestedSeconds: 0,
    setup: { profileId: "test-profile", aspectPolicy: "reject_mismatch", maxJobs: jobs, maxRequestedSeconds: seconds } } });
function backend() {
  vi.spyOn(plotloomApi, "getVideoBackend").mockResolvedValue({ enabled: true, defaultProfileId: "test-profile", profiles: [
    { id: "test-profile", label: "Test profile", provider: "minimax_h3_gateway", quality: "8" },
  ] } as never);
}
it.each([[null, null, "任务上限 不限 / 源秒上限 不限"], [2, 10, "任务上限 2 项 / 源秒上限 10 秒"]] as const)(
  "shows the actual frozen caps %s/%s and resets the next setup to unlimited", async (jobs, seconds, summary) => {
    vi.spyOn(batchApi, "current").mockResolvedValue(frozen(jobs, seconds)); backend();
    const send = vi.spyOn(batchApi, "command").mockResolvedValue(frozen(null, null));
    await act(async () => root.render(createElement(VideoBatchPanel, { projectId: "project", disabled: false, dirty: false })));
    expect(host.textContent).toContain(summary);
    await act(async () => button("准备新的缺失视频清单").click());
    expect([...host.querySelectorAll("select")].filter(node => node.value === "unlimited")).toHaveLength(2);
    await act(async () => button("批量生成缺失视频").click());
    expect(send).toHaveBeenCalledWith("project", "setup", { profileId: "test-profile", aspectPolicy: "reject_mismatch", maxJobs: null, maxRequestedSeconds: null });
  });
it("project switches reset finite budget drafts and invalid drafts cannot submit", async () => {
  vi.spyOn(batchApi, "current").mockResolvedValue(null); backend();
  const send = vi.spyOn(batchApi, "command").mockResolvedValue(frozen(300, null));
  const render = async (projectId: string) => act(async () => root.render(createElement(VideoBatchPanel, { projectId, disabled: false, dirty: false })));
  await render("first");
  // Locate budget selects after the existing profile/aspect controls.
  const index = [...host.querySelectorAll("select")].findIndex(node => node.options[0]?.value === "unlimited");
  await select(index, "finite"); expect(button("批量生成缺失视频").disabled).toBe(true);
  await input(0, "0"); expect(button("批量生成缺失视频").disabled).toBe(true);
  await input(0, "300"); expect(button("批量生成缺失视频").disabled).toBe(false);
  await act(async () => button("批量生成缺失视频").click());
  expect(send).toHaveBeenCalledWith("first", "setup", expect.objectContaining({ maxJobs: 300, maxRequestedSeconds: null }));
  await render("second");
  expect([...host.querySelectorAll("select")].filter(node => node.value === "unlimited")).toHaveLength(2);
  expect(host.querySelector("input")).toBeNull();
});

it("autopilot project changes clear finite drafts and restore explicit unlimited defaults", async () => {
  vi.spyOn(autopilotApi, "current").mockResolvedValue(null);
  vi.spyOn(autopilotApi, "launchContext").mockResolvedValue({ eligible: true, briefRevision: 1 });
  const render = async (projectId: string) => act(async () => root.render(createElement(AutopilotWorkspace, {
    projectId, revision: 1, readOnly: false, onChanged: async () => undefined, onVideo: () => undefined,
    children: createElement(AutopilotLaunch, { saved: true, dirty: false, disabled: false }),
  })));
  await render("first"); await act(async () => button("自动准备素材").click());
  await select(0, "finite"); expect(button("开始准备已保存简报的素材").disabled).toBe(true);
  await input(0, "300"); expect(button("开始准备已保存简报的素材").disabled).toBe(false);
  await render("second"); await act(async () => button("自动准备素材").click());
  expect(host.querySelector("input")).toBeNull();
  expect([...host.querySelectorAll("select")].map(node => node.value)).toEqual(["unlimited", "unlimited"]);
});
