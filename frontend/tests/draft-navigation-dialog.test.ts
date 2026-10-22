import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DraftNavigationDialog, type DraftNavigationIntent } from "../src/app/workspace/DraftNavigationDialog";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const onSave = vi.fn(), onDiscard = vi.fn(), onCancel = vi.fn();
const cases: Array<[DraftNavigationIntent, string, string, string, string]> = [
  ["navigate", "保存当前草稿？", "保存并切换", "丢弃", "项目中已保存的草稿不会删除"],
  ["archive", "归档前保存当前修改？", "保存并归档", "丢弃本页修改并归档", "已保存的草稿仍保留"],
  ["close", "保存草稿并关闭项目？", "保存草稿并关闭", "丢弃当前草稿并关闭", "删除当前阶段对应的那一份草稿"],
];
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.clearAllMocks();
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });
function button(label: string) { return [...host.querySelectorAll("button")].find(item => item.textContent === label)!; }

it.each(cases)("names the %s action and keeps its disposition boundary", async (intent, title, save, discard, help) => {
  await act(async () => root.render(createElement(DraftNavigationDialog, { intent, onSave, onDiscard, onCancel })));
  expect(host.querySelector("h2")?.textContent).toBe(title);
  expect(host.textContent).toContain(help);
  expect(host.textContent).not.toMatch(/project\.sqlite3|CAS|规范保存/);
  if (intent === "archive") {
    expect(host.textContent).not.toContain("切换");
    expect(host.textContent).toContain("可在项目目录中恢复");
  }
  await act(async () => button(save).click());
  expect(onSave).toHaveBeenCalledTimes(1); expect(onDiscard).not.toHaveBeenCalled(); expect(onCancel).not.toHaveBeenCalled();
  await act(async () => button(discard).click()); expect(onDiscard).toHaveBeenCalledTimes(1);
  await act(async () => button("取消").click()); expect(onCancel).toHaveBeenCalledTimes(1);
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="继续编辑"]')!.click()); expect(onCancel).toHaveBeenCalledTimes(2);
});
