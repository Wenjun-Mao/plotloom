import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { AppearanceModeSelector } from "../src/pages/AppearanceModeSelector";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("exposes mutually exclusive native modes and preserves disabled guards", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const onChange = vi.fn();
  const render = async (value: "fresh" | "refine", refinementAllowed: boolean, disabled = false) => {
    await act(async () => root.render(createElement(AppearanceModeSelector, { value, refinementAllowed, disabled, onChange })));
  };
  try {
    await render("fresh", false);
    const [fresh, refine] = Array.from(host.querySelectorAll<HTMLInputElement>('input[type="radio"]'));
    expect(fresh.checked).toBe(true);
    expect(refine.checked).toBe(false);
    expect(refine.disabled).toBe(true);
    expect(fresh.name).toBe(refine.name);
    expect(host.querySelector("button")).toBeNull();
    await act(async () => refine.click());
    expect(onChange).not.toHaveBeenCalled();
    await render("fresh", true);
    await act(async () => refine.click());
    expect(onChange).toHaveBeenCalledWith("refine");
    await render("refine", true);
    expect(refine.checked).toBe(true);
    expect(fresh.checked).toBe(false);
    await render("fresh", true, true);
    expect(fresh.disabled).toBe(true);
    expect(refine.disabled).toBe(true);
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});
