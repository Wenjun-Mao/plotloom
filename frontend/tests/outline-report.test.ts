import { act, createElement, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";
import { OutlineReport } from "../src/pages/OutlineReport";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("opens original report with scripts but no same-origin, navigation, forms or download grants", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const prototype = HTMLDialogElement.prototype;
  const original = prototype.showModal;
  prototype.showModal = function () { this.setAttribute("open", ""); };
  const outline = { source: "雨停以后", params: { episodes: 2, minutesPerEpisode: 0.25 }, beats: [{ id: "B1", episode: 1, setup: "<script>alert(1)</script>", payoff: "两条互斥结局", extra: "保留未知字段" }], episodes: [{ ep: 2, synopsis: "只能择一播放" }] };
  const before = JSON.stringify(outline);
  try {
    await act(async () => root.render(createElement(StrictMode, null, createElement(OutlineReport, { url: "/candidate/report", outline }))));
    const opener = host.querySelector("button")!;
    await act(async () => opener.click());
    const dialog = host.querySelector("dialog")!;
    expect(dialog.hasAttribute("open")).toBe(true);
    const iframe = dialog.querySelector("iframe")!;
    expect(iframe.getAttribute("sandbox")).toBe("allow-scripts");
    expect(iframe.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(iframe.getAttribute("src")).toBe("/candidate/report");
    expect(dialog.querySelectorAll("button")).toHaveLength(1);
    expect(dialog.querySelector("button")!.textContent).toBe("关闭阅读");
    expect(dialog.textContent).toContain("不代表已确认的成片集数");
    expect(dialog.querySelector("script")).toBeNull();
    expect(JSON.stringify(outline)).toBe(before);
    await act(async () => dialog.dispatchEvent(new Event("close")));
    expect(host.querySelector("dialog")).toBeNull();
    expect(document.activeElement).toBe(opener);
  } finally {
    await act(async () => root.unmount());
    host.remove();
    prototype.showModal = original;
  }
});
