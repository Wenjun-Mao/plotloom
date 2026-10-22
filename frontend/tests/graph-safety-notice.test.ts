import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { GraphSafetyNotice } from "../src/features/graph/GraphSafetyNotice";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("presents node title, checked degree and next action with raw facts under technical details", async () => {
  const host = document.createElement("div"), root = createRoot(host), draft = graphDraftFixture();
  draft.mapping.sections[0].title = "风暴中的抉择";
  const errorDetails = { code: "graph_edit_unsafe", message: "raw internal identity", diagnostics: [{ code: "out_degree",
    identity: "out_degree:opening", severity: 1, previousSeverity: 0, facts: { nodeId: "opening", nodeKind: "decision", actual: 7, limit: 6 } }] };
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider,
    { value: graphControllerFixture({ draft, error: "raw internal identity", errorDetails }) }, createElement(GraphSafetyNotice))));
  expect(host.querySelector('[role="alert"]')?.textContent).toContain("风暴中的抉择");
  expect(host.textContent).toContain("7 条输出连接，最多允许 6 条");
  expect(host.textContent).toContain("先删除一个选项");
  const details = host.querySelector("details")!;
  expect(details.open).toBe(false);
  expect(details.textContent).toContain("out_degree:opening");
  expect(details.textContent).toContain('"actual": 7');
  expect(Array.from(host.querySelectorAll("p")).map(item => item.textContent).join(" ")).not.toContain("out_degree");
  await act(async () => root.unmount());
});

it("retains generic refusal messages without inventing safety facts", async () => {
  const host = document.createElement("div"), root = createRoot(host);
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider,
    { value: graphControllerFixture({ error: "server busy", errorDetails: { code: "project_busy" } }) }, createElement(GraphSafetyNotice))));
  expect(host.textContent).toBe("server busy"); expect(host.querySelector("details")).toBeNull();
  await act(async () => root.unmount());
});
