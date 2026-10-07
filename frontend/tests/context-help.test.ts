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
    const visible = () => [...host.querySelectorAll('[role="tooltip"] p')];
    await act(async () => later.click());
    expect(visible().map(element => element.textContent)).toEqual(["Later explanation"]);
    await act(async () => first.focus());
    expect(visible().map(element => element.textContent)).toEqual(["First explanation"]);
    expect(later.getAttribute("aria-expanded")).toBe("false");
    expect(later.hasAttribute("aria-describedby")).toBe(false);
    expect(first.getAttribute("aria-describedby")).toBe(host.querySelector('[role="tooltip"]')!.id);
    expect(host.querySelector('[role="tooltip"]')!.parentElement!.className).toBe("context-help-dock");
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

it("keeps pinned help while entering a field and closes on repeated pin without submitting", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () => root.render(createElement(ContextHelpGroup, null,
      createElement(ContextHelp, { label: "count", children: "Count explanation" }),
      createElement("input", { "aria-label": "count" }))));
    const button = host.querySelector("button")!;
    const input = host.querySelector("input")!;
    expect(button.type).toBe("button");
    await act(async () => { button.focus(); button.click(); input.focus(); });
    expect(host.querySelector('[role="tooltip"] p')!.textContent).toBe("Count explanation");
    expect(document.activeElement).toBe(input);
    await act(async () => button.click());
    expect(host.querySelector('[role="tooltip"]')).toBeNull();
    expect(button.hasAttribute("aria-describedby")).toBe(false);
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});
