import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { ProjectDirectoryRow } from "../src/app/workspace/ProjectDirectoryRow";
import type { ProjectListItem, RunStatus } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const item = (patch: Partial<ProjectListItem> = {}) => ({ id: "a", brief: { title: "项目 A" }, revision: 1,
  updatedAt: "2026-10-24T12:00:00Z", lifecycleStatus: "active", archivedAt: null,
  operationalState: "open", latestRun: null, ...patch } as ProjectListItem);
async function harness(project: ProjectListItem, current = false, disabled = false, explicitProjectClose = true) {
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host), onOpen = vi.fn(), onAction = vi.fn(async () => {});
  const render = (next = project, active = current, blocked = disabled) => act(async () => root.render(createElement(ProjectDirectoryRow,
    { item: next, current: active, disabled: blocked, explicitProjectClose, onOpen, onAction })));
  await render();
  const button = (label: string) => [...host.querySelectorAll<HTMLButtonElement>("button")].find(b => b.textContent === label)!;
  return { host, button, onOpen, onAction, render, more: async () => act(async () => button("更多").click()),
    dispose: async () => { await act(async () => root.unmount()); host.remove(); } };
}
it.each([false, true])("projects get current-only save/exit and management close: current=%s", async current => {
  const h = await harness(item(), current);
  try {
    expect(Boolean(h.button("保存并关闭项目"))).toBe(current); expect(Boolean(h.button("退出工作区"))).toBe(current);
    expect(Boolean(h.button("打开"))).toBe(!current); expect(h.button("删除项目…")).toBeUndefined();
    await h.more(); expect(Boolean(h.button("关闭项目"))).toBe(!current);
    expect(h.button("复制简报与规范内容").disabled).toBe(false); expect(h.button("删除项目…").disabled).toBe(false);
    await act(async () => h.button("归档").click());
    expect(h.onAction).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }), "archive");
    expect(h.button("更多").getAttribute("aria-expanded")).toBe("false");
  } finally { await h.dispose(); }
});
it.each(["queued", "running", "cancel_requested"] as RunStatus[])("positive %s summary blocks ordinary close/archive but preserves supported actions", async status => {
  const h = await harness(item({ latestRun: { status } as ProjectListItem["latestRun"] }));
  try {
    await h.more(); expect(h.button("关闭项目").disabled).toBe(true); expect(h.button("归档").disabled).toBe(true);
    expect(h.button("删除项目…").disabled).toBe(false); expect(h.button("复制简报与规范内容").disabled).toBe(false);
    expect(h.button("打开").disabled).toBe(false); expect(h.host.textContent).toContain("任务结束前不能归档或安全关闭");
    await h.render(item({ latestRun: { status } as ProjectListItem["latestRun"] }), true);
    expect(h.button("保存并关闭项目").disabled).toBe(true); expect(h.button("退出工作区").disabled).toBe(false);
  } finally { await h.dispose(); }
});
it.each([null, "succeeded", "failed", "cancelled", "quarantined"])("absent or terminal latest run %s never claims idle", async status => {
  const h = await harness(item({ operationalState: null, latestRun: status ? { status } as ProjectListItem["latestRun"] : null }));
  try {
    await h.more(); expect(h.button("关闭项目").disabled).toBe(false);
    expect(h.host.textContent).toContain("关闭状态未确认"); expect(h.host.textContent).not.toContain("空闲");
  } finally { await h.dispose(); }
});
it.each(["closed", "archived"])("%s primary action has no save/exit or ordinary close", async state => {
  const h = await harness(item(state === "closed" ? { operationalState: "closed" } : { lifecycleStatus: "archived" }), true);
  try {
    expect(h.button(state === "closed" ? "重新打开" : "恢复").disabled).toBe(false);
    await h.more(); expect(h.button("关闭项目")).toBeUndefined(); expect(h.button("保存并关闭项目")).toBeUndefined();
    expect(h.button("退出工作区")).toBeUndefined(); expect(h.button("归档")).toBeUndefined();
  } finally { await h.dispose(); }
});
it("disclosure closes on Escape/outside/identity/read withdrawal and returns keyboard focus", async () => {
  const h = await harness(item());
  try {
    await h.more(); h.button("删除项目…").focus();
    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(document.activeElement).toBe(h.button("更多")); expect(h.button("删除项目…")).toBeUndefined();
    await h.more(); await act(async () => document.body.dispatchEvent(new Event("pointerdown", { bubbles: true })));
    expect(h.button("删除项目…")).toBeUndefined();
    await h.more(); await h.render(item({ revision: 2 })); expect(h.button("删除项目…")).toBeUndefined();
    await h.more(); await h.render(item(), true); expect(h.button("删除项目…")).toBeUndefined();
    await h.more(); await h.render(item(), true, true); expect(h.button("删除项目…")).toBeUndefined();
    expect([...h.host.querySelectorAll<HTMLButtonElement>("button")].every(b => b.disabled)).toBe(true);
  } finally { await h.dispose(); }
});

it("archived and closed restores lifecycle first, while no-close backends explain unavailable reopen", async () => {
  const h = await harness(item({ operationalState: "closed", lifecycleStatus: "archived" }));
  try {
    expect(h.button("重新打开")).toBeUndefined();
    await act(async () => h.button("恢复").click());
    expect(h.onAction).toHaveBeenCalledWith(expect.anything(), "restore");
    await h.render(item({ operationalState: "closed" })); expect(h.button("重新打开").disabled).toBe(false);
  } finally { await h.dispose(); }
  const legacy = await harness(item({ operationalState: "closed" }), false, false, false);
  try {
    expect(legacy.button("重新打开").disabled).toBe(true);
    expect(legacy.host.querySelector<HTMLButtonElement>(".directory-open")!.disabled).toBe(true);
    expect(legacy.host.textContent).toContain("当前后端未提供重新打开已关闭项目的能力");
    await legacy.more(); expect(legacy.button("删除项目…").disabled).toBe(false);
  } finally { await legacy.dispose(); }
  const current = await harness(item(), true, false, false);
  try { expect(current.button("保存并关闭项目")).toBeUndefined(); expect(current.button("退出工作区")).toBeUndefined(); }
  finally { await current.dispose(); }
});

it("command focus restoration cannot steal a confirmation input or follow a changed workspace identity", async () => {
  const h = await harness(item());
  const confirmationInput = document.createElement("input"); document.body.append(confirmationInput);
  try {
    await h.more(); await act(async () => h.button("关闭项目").click());
    await h.render(item(), false, true);
    confirmationInput.focus(); await h.render(item(), false, false);
    expect(document.activeElement).toBe(confirmationInput);
    await h.more(); await act(async () => h.button("关闭项目").click());
    await h.render(item(), false, true); document.body.tabIndex = -1; document.body.focus();
    await h.render(item(), true, false); expect(document.activeElement).toBe(document.body);
  } finally { confirmationInput.remove(); document.body.removeAttribute("tabindex"); await h.dispose(); }
});

it.each([false, true])("archived closed title requires Restore first with explicit-close=%s", async capability => {
  const h = await harness(item({ operationalState: "closed", lifecycleStatus: "archived" }), false, false, capability);
  try {
    const title = h.host.querySelector<HTMLButtonElement>(".directory-open")!;
    expect(title.disabled).toBe(true); expect(h.host.textContent).toContain("请先恢复");
    await act(async () => title.click()); expect(h.onOpen).not.toHaveBeenCalled();
    await act(async () => h.button("恢复").click()); expect(h.onAction).toHaveBeenCalledWith(expect.anything(), "restore");
    await h.render(item({ operationalState: "closed" })); expect(h.button("重新打开").disabled).toBe(!capability);
  } finally { await h.dispose(); }
});

it("outside keyboard focus dismisses A so Escape belongs only to the focused B disclosure", async () => {
  const a = await harness(item({ id: "a" })), b = await harness(item({ id: "b" }));
  try {
    await act(async () => { a.button("更多").focus(); a.button("更多").click(); });
    await act(async () => a.button("复制简报与规范内容").focus());
    expect(a.button("更多").getAttribute("aria-expanded")).toBe("true");
    await act(async () => b.button("更多").focus());
    expect(a.button("更多").getAttribute("aria-expanded")).toBe("false");
    await b.more();
    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(b.button("更多").getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(b.button("更多"));
    expect(a.onAction).not.toHaveBeenCalled(); expect(b.onAction).not.toHaveBeenCalled();
  } finally { await a.dispose(); await b.dispose(); }
});
