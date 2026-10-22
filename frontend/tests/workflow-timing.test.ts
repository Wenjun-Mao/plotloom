import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { WorkflowTiming, type TimingFacts } from "../src/components/WorkflowTiming";

let host: HTMLDivElement; let root: Root;
const facts: TimingFacts = { observedAt: "2026-10-22T12:01:00Z", createdAt: "2026-10-22T12:00:00Z", terminal: false };
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.useFakeTimers(); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.useRealTimers(); });
const render = async (timing = facts, verified = true, kind: "run" | "batch" = "run") => act(async () => root.render(createElement(WorkflowTiming, { timing, verified, kind })));

it("uses server age and monotonic ticks despite wall clock changes; reload and project changes reset facts", async () => {
  await render(); expect(host.textContent).toContain("距启动已过 1 分 0 秒（含排队、暂停和等待）");
  vi.setSystemTime(new Date("2030-01-01"));
  await act(async () => vi.advanceTimersByTime(3000)); expect(host.textContent).toContain("1 分 3 秒");
  await render({ ...facts, observedAt: "2026-10-22T12:01:04Z" }); expect(host.textContent).toContain("1 分 4 秒");
  await render({ ...facts, createdAt: "2026-10-22T12:01:00Z" }); expect(host.textContent).toContain("0 秒");
});
it("failed reads freeze the clock and show the actual last observation, never liveness", async () => {
  await render(facts, false); await act(async () => vi.advanceTimersByTime(5000));
  expect(host.textContent).toContain("1 分 0 秒"); expect(host.textContent).toContain("状态待核实 · 上次成功读取");
  expect(host.textContent).toContain("时间递增不表示工作进程仍在运行");
});
it("terminal output uses completion facts or creation date; never a growing terminal age", async () => {
  await render({ ...facts, terminal: true }); await act(async () => vi.advanceTimersByTime(6000));
  expect(host.textContent).toContain("创建于"); expect(host.textContent).not.toContain("距启动已过");
  await render({ ...facts, terminal: true, completedAt: facts.observedAt }); expect(host.textContent).toContain("已完成");
});
it("batch age includes direction waiting and clamps clock skew without inventing a milestone", async () => {
  await render({ ...facts, createdAt: "2026-10-22T12:02:00Z" }, true, "batch");
  expect(host.textContent).toContain("清单创建后 0 秒（含准备方向与等待开始）");
  expect(host.textContent).not.toContain("播放片段已就绪");
});
