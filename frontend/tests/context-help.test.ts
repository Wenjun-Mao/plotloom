import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { ContextHelp, ContextHelpGroup } from "../src/components/ContextHelp";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("replaces pinned help with the focused or tapped explanation", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(ContextHelpGroup, null,
      createElement(ContextHelp, { label: "first", children: "First explanation" }),
      createElement(ContextHelp, { label: "later", children: "Later explanation" }))));
    const [first, later] = [...host.querySelectorAll("button")];
    const visible = () => [...host.querySelectorAll('[role="tooltip"]')].filter(element => !element.hasAttribute("hidden"));
    await act(async () => later.click());
    expect(visible().map(element => element.textContent)).toEqual(["Later explanation"]);
    await act(async () => first.focus());
    expect(visible().map(element => element.textContent)).toEqual(["First explanation"]);
    expect(later.getAttribute("aria-expanded")).toBe("false");
    await act(async () => later.parentElement!.dispatchEvent(new MouseEvent("mouseover", { bubbles: true })));
    expect(visible().map(element => element.textContent)).toEqual(["First explanation"]);
    await act(async () => first.click());
    expect(visible()).toHaveLength(1);
    await act(async () => first.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
    expect(visible()).toHaveLength(0);
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});
