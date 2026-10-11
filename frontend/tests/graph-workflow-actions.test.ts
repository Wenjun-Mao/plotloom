import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GraphWorkflowActions } from "../src/features/graph/GraphWorkflowActions";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root;
const labels = ["保存图草稿", "确认图内容", "应用到故事路线"];
const explanations = ["保存修改，仍是草稿。", "确认版本，不应用路线。", "启用已确认的故事路线。"];
const scope = "作用于全部节点和连接，不仅是当前选中的节点。";

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("shows adjacent explanations and describes every action without changing its name", async () => {
  await act(async () => root.render(createElement(GraphWorkflowActions, { save: {}, confirm: {}, apply: { variant: "primary" } })));
  const buttons = [...host.querySelectorAll("button")];
  expect(buttons.map(button => button.textContent)).toEqual(labels);
  for (const [index, button] of buttons.entries()) {
    const ids = button.getAttribute("aria-describedby")!.split(" ");
    expect(ids.map(id => document.getElementById(id)?.textContent)).toEqual([scope, explanations[index], "三项操作均不会生成影片。"]);
    expect(button.nextElementSibling?.textContent).toBe(explanations[index]);
  }
  expect(buttons[2].classList.contains("primary")).toBe(true);
  expect(host.querySelectorAll(".graph-workflow-generation-help")).toHaveLength(1);
});

it("names the whole-graph region and keeps its currentness status with global actions", async () => {
  await act(async () => root.render(createElement(GraphWorkflowActions, {
    save: {}, confirm: {}, apply: {}, status: "当前图内容已应用到故事路线。",
  })));
  const bar = host.querySelector("section")!;
  expect(document.getElementById(bar.getAttribute("aria-labelledby")!)?.textContent).toBe("整张剧情图 · 保存与应用");
  expect(document.getElementById(bar.getAttribute("aria-describedby")!)?.textContent).toBe(scope);
  expect(bar.querySelector(".graph-workflow-status")?.textContent).toBe("当前图内容已应用到故事路线。");
});

it.each(["save", "confirm", "apply"] as const)("%s delegates only its own handler and preserves disabled admission", async action => {
  const handlers = { save: vi.fn(), confirm: vi.fn(), apply: vi.fn() };
  const render = (disabled: boolean) => act(async () => root.render(createElement(GraphWorkflowActions, {
    save: { onClick: handlers.save, disabled: action === "save" && disabled },
    confirm: { onClick: handlers.confirm, disabled: action === "confirm" && disabled },
    apply: { onClick: handlers.apply, disabled: action === "apply" && disabled },
  })));
  const index = ["save", "confirm", "apply"].indexOf(action);
  await render(true);
  const button = host.querySelectorAll("button")[index];
  expect(button.disabled).toBe(true);
  await act(async () => button.click());
  expect(handlers[action]).not.toHaveBeenCalled();
  await render(false);
  await act(async () => button.click());
  expect(handlers[action]).toHaveBeenCalledTimes(1);
  for (const other of ["save", "confirm", "apply"] as const) if (other !== action) expect(handlers[other]).not.toHaveBeenCalled();
});

it("gives separate rendered groups unique help references", async () => {
  await act(async () => root.render(createElement("div", {},
    createElement(GraphWorkflowActions, { save: {}, confirm: {}, apply: {} }),
    createElement(GraphWorkflowActions, { save: {}, confirm: {}, apply: {} }),
  )));
  const ids = [...host.querySelectorAll("[id]")].map(element => element.id);
  expect(new Set(ids).size).toBe(ids.length);
});
