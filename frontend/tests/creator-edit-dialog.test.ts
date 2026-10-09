import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CreatorEditDialog, type CreatorEdit } from "../src/features/graph/CreatorEditDialog";
import { GraphWorkbenchContext, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root, controller: GraphWorkbenchController;
const close = vi.fn();
async function show(action: CreatorEdit = { type: "connection", nodeId: "opening", endpoint: "target", edgeId: "opening-ending" }) {
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, {
    value: controller,
    children: createElement(CreatorEditDialog, { action, onClose: close }),
  })));
}
function button(text: string) { return [...host.querySelectorAll("button")].find(button => button.textContent === text)!; }
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  controller = graphControllerFixture({ draft: graphDraftFixture() }); close.mockClear();
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value(this: HTMLDialogElement) { this.open = true; } });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal"); vi.restoreAllMocks(); });

it("retains endpoint selections and shows a refused preview in the editing dialog", async () => {
  controller.prepareCommand = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
  await show();
  const target = host.querySelector<HTMLSelectElement>('[aria-label="更改连接端点"]')!;
  await act(async () => { target.value = "opening"; target.dispatchEvent(new Event("change", { bubbles: true })); });
  await act(async () => button("准备修改预览").click());
  expect(close).not.toHaveBeenCalled();
  controller = { ...controller, error: "不能连接：这会形成循环。" }; await show();
  expect(target.value).toBe("opening");
  expect(host.querySelector("dialog [role=alert]")?.textContent).toContain("循环");
  await act(async () => { target.value = "ending"; target.dispatchEvent(new Event("change", { bubbles: true })); });
  await act(async () => button("准备修改预览").click());
  expect(close).toHaveBeenCalledTimes(1);
});

it("does not dismiss while the preview preparation owns an in-flight operation", async () => {
  controller = { ...controller, busy: true }; await show();
  expect(button("取消").disabled).toBe(true);
  expect(button("准备修改预览").disabled).toBe(true);
  await act(async () => host.querySelector("dialog")!.dispatchEvent(new Event("cancel", { cancelable: true })));
  expect(close).not.toHaveBeenCalled();
  controller = { ...controller, busy: false }; await show();
  await act(async () => button("取消").click()); expect(close).toHaveBeenCalledTimes(1);
});

it("labels exact connection targets in Chinese without changing their identities", async () => {
  await show();
  const target = host.querySelector<HTMLSelectElement>('[aria-label="更改连接端点"]')!;
  expect([...target.options].slice(1).map(option => [option.value, option.textContent])).toEqual([["opening", "opening · 开场"], ["ending", "ending · 结局"]]);
});

it("uses the shared kind labels for reuse, creation and continuation options", async () => {
  controller.draft!.mapping.topology.nodes.push({ id: "detached", kind: "scene" });
  controller.draft!.mapping.sections.push({ sectionId: "detached", title: "独立剧情", summary: "", ending: false, footageMode: "footage" });
  await show({ type: "row", rank: 1, nodes: ["ending"] });
  const reuse = host.querySelector<HTMLSelectElement>('[aria-label="新建或复用"]')!;
  expect([...reuse.options].slice(1).map(option => [option.value, option.textContent])).toEqual([["detached", "复用 独立剧情 · 故事发展"]]);
  const type = host.querySelector<HTMLSelectElement>('[aria-label="新增节点类型"]')!;
  expect([...type.options].map(option => [option.value, option.textContent])).toEqual([["scene", "故事发展"], ["decision", "选择点"], ["join", "汇合点"], ["ending", "结局"]]);
  const target = host.querySelector<HTMLSelectElement>('[aria-label="新增节点的后续"]')!;
  expect([...target.options].slice(1).map(option => [option.value, option.textContent])).toEqual([["opening", "opening · 开场"], ["ending", "ending · 结局"], ["detached", "独立剧情 · 故事发展"]]);
});
