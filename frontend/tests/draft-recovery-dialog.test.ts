import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DraftRecoveryDialog } from "../src/app/workspace/WorkspaceViews";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const onRestore = vi.fn(), onDiscard = vi.fn();
const cases = [
  ["server", "此草稿已保存在项目中；恢复后可继续修改。"],
  ["session", "此草稿只保留在当前标签页，尚未保存到项目中。"],
  ["reconcile", "当前标签页与项目中各有一份草稿。恢复会保留本标签页的输入，供你比较并重新保存。"],
] as const;
beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); vi.clearAllMocks(); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });
const button = (label: string) => [...host.querySelectorAll("button")].find(item => item.textContent === label)!;

it.each(cases)("describes the %s draft without mistaking it for confirmed content", async (source, help) => {
  await act(async () => root.render(createElement(DraftRecoveryDialog, { source, onRestore, onDiscard })));
  expect(host.querySelector("h2")?.textContent).toBe("发现可恢复草稿");
  expect(host.textContent).toContain("正式内容保持不变");
  expect(host.textContent).toContain(help);
  expect(host.textContent).not.toMatch(/project\.sqlite3|sessionStorage|规范|发现未保存草稿/);
  await act(async () => host.querySelector<HTMLButtonElement>('[aria-label="保留提示"]')!.click());
  expect(onRestore).not.toHaveBeenCalled(); expect(onDiscard).not.toHaveBeenCalled();
  await act(async () => button("恢复草稿").click()); expect(onRestore).toHaveBeenCalledOnce();
  await act(async () => button("丢弃草稿").click()); expect(onDiscard).toHaveBeenCalledOnce();
});

it("keeps restore and discard unavailable while exact project authority is being checked", async () => {
  await act(async () => root.render(createElement(DraftRecoveryDialog, { source: "server", busy: true, onRestore, onDiscard })));
  expect(button("正在核实…").disabled).toBe(true); expect(button("丢弃草稿").disabled).toBe(true);
  await act(async () => { button("正在核实…").click(); button("丢弃草稿").click(); });
  expect(onRestore).not.toHaveBeenCalled(); expect(onDiscard).not.toHaveBeenCalled();
});
